"""Zugriff auf einen Nextcloud-Ordner ueber einen Freigabelink.

Nach Abschnitt 10 des Plans legt Tristan die Exporte auf Nextcloud ab. Damit
niemand Dateien von Hand herunterladen und herumkopieren muss, liest das Tool
sie direkt aus einer Ordnerfreigabe.

Verwendet wird die oeffentliche WebDAV-Schnittstelle von Nextcloud. Sie braucht
keine Zugangsdaten eines Kontos, sondern nur den Freigabetoken aus dem Link --
und, falls die Freigabe passwortgeschuetzt ist, dieses Passwort. Das ist der
Grund fuer diesen Weg: Es muss kein Nextcloud-Konto im Tool hinterlegt werden.

Heruntergeladene Dateien landen in einem lokalen Zwischenspeicher. Der
restliche Import arbeitet dann auf gewoehnlichen Dateien und muss nichts vom
Netz wissen; ausserdem laesst sich ohne Verbindung weiterarbeiten. Der
Zwischenspeicher liegt unter `daten/` und ist von der Versionsverwaltung
ausgeschlossen.

Umgesetzt mit der Standardbibliothek. Eine zusaetzliche Abhaengigkeit waere fuer
zwei HTTP-Anfragen nicht zu rechtfertigen.
"""

from __future__ import annotations

import base64
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

ZWISCHENSPEICHER = Path("daten/nextcloud")
ZEITSPERRE = 30
"""Zeitgrenze der HTTP-Anfragen in Sekunden."""

DAV = "{DAV:}"


class NextcloudFehler(RuntimeError):
    """Der Zugriff auf die Freigabe ist fehlgeschlagen.

    Die Meldungen sind absichtlich als Handlungsanweisung formuliert. Wer den
    Link einfuegt, ist nicht zwingend die Person, die die Freigabe angelegt hat,
    und ein nackter HTTP-Fehlercode hilft dann niemandem weiter.
    """


# ---------------------------------------------------------------------------
# Freigabelink zerlegen
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Freigabe:
    """Eine Nextcloud-Ordnerfreigabe, zerlegt aus ihrem Link."""

    server: str
    """Adresse ohne abschliessenden Schraegstrich, etwa `https://cloud.example.org`."""

    token: str
    """Der Freigabetoken, also der Teil hinter `/s/` im Link."""

    unterpfad: str = ""
    """Ordner innerhalb der Freigabe, falls der Link einen `path`-Parameter trug."""

    passwort: str = ""

    @property
    def anzeige(self) -> str:
        """Kurzform fuer die Oberflaeche, ohne den vollstaendigen Token.

        Der Token ist das Geheimnis der Freigabe. Er hat auf einem Bildschirm,
        der bei einer Besprechung geteilt wird, nichts zu suchen.
        """
        gekuerzt = f"{self.token[:4]}…" if len(self.token) > 4 else "…"
        ort = f"/{self.unterpfad}" if self.unterpfad else ""
        return f"{self.server}/s/{gekuerzt}{ort}"


_TOKEN_IM_LINK = re.compile(r"/(?:index\.php/)?s/(?P<token>[A-Za-z0-9\-_]{4,})")


def freigabe_lesen(link: str, passwort: str = "") -> Freigabe:
    """Zerlegt einen Nextcloud-Freigabelink.

    Erkannt werden die gaengigen Formen, die Nextcloud und die Browser-Adresszeile
    hervorbringen:

        https://cloud.example.org/s/AbCdEf123
        https://cloud.example.org/index.php/s/AbCdEf123
        https://cloud.example.org/s/AbCdEf123/download
        https://cloud.example.org/s/AbCdEf123?path=%2FAuswertungen

    Ein Link auf die Dateiansicht des eigenen Kontos (`/apps/files/?dir=…`) ist
    keine Freigabe und wird mit einem entsprechenden Hinweis abgewiesen.
    """
    link = link.strip()
    if not link:
        raise NextcloudFehler("Bitte einen Nextcloud-Freigabelink eingeben.")

    zerlegt = urllib.parse.urlparse(link if "//" in link else f"https://{link}")
    if zerlegt.scheme not in ("http", "https") or not zerlegt.netloc:
        raise NextcloudFehler(
            f"„{link}“ sieht nicht wie eine Web-Adresse aus. Erwartet wird ein Link "
            "der Form https://cloud.example.org/s/AbCdEf123"
        )

    treffer = _TOKEN_IM_LINK.search(zerlegt.path)
    if treffer is None:
        if "/apps/files" in zerlegt.path:
            raise NextcloudFehler(
                "Das ist der Link auf deine eigene Dateiansicht, keine Freigabe. "
                "Bitte in Nextcloud den Ordner freigeben („Teilen“ → „Link teilen“) "
                "und den dabei erzeugten Link verwenden."
            )
        raise NextcloudFehler(
            "In diesem Link steckt kein Freigabetoken. Erwartet wird ein Link der "
            "Form https://cloud.example.org/s/AbCdEf123 — in Nextcloud über "
            "„Teilen“ → „Link teilen“ zu erzeugen."
        )

    # Alles vor dem Token gehoert zur Server-Adresse; manche Installationen
    # liegen in einem Unterverzeichnis, etwa https://example.org/nextcloud/s/…
    vorlauf = zerlegt.path[: treffer.start()].rstrip("/")
    server = f"{zerlegt.scheme}://{zerlegt.netloc}{vorlauf}"

    unterpfad = ""
    for schluessel, werte in urllib.parse.parse_qs(zerlegt.query).items():
        if schluessel == "path" and werte:
            unterpfad = werte[0].strip("/")

    return Freigabe(
        server=server,
        token=treffer.group("token"),
        unterpfad=unterpfad,
        passwort=passwort,
    )


# ---------------------------------------------------------------------------
# Verzeichnis der Freigabe
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Eintrag:
    """Eine Datei oder ein Ordner in der Freigabe."""

    name: str
    pfad: str
    """Pfad innerhalb der Freigabe, ohne fuehrenden Schraegstrich."""

    groesse: int
    geaendert: datetime | None
    ist_ordner: bool

    @property
    def endung(self) -> str:
        return Path(self.name).suffix.lower()


_PROPFIND_ANFRAGE = b"""<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:displayname/>
    <d:getcontentlength/>
    <d:getlastmodified/>
    <d:resourcetype/>
  </d:prop>
</d:propfind>
"""


def _endpunkte(freigabe: Freigabe) -> list[str]:
    """Die WebDAV-Einstiegspunkte, in der Reihenfolge, in der sie probiert werden.

    Neuere Nextcloud-Versionen bieten `/public.php/dav/files/<token>/`, aeltere
    nur `/public.php/webdav/`. Beide werden probiert, damit das Tool nicht an der
    Version der Gegenstelle scheitert.
    """
    return [
        f"{freigabe.server}/public.php/dav/files/{freigabe.token}",
        f"{freigabe.server}/public.php/webdav",
    ]


def _anfrage(freigabe: Freigabe, adresse: str, methode: str, koerper: bytes | None = None):
    kopf = {
        "Authorization": "Basic "
        + base64.b64encode(f"{freigabe.token}:{freigabe.passwort}".encode()).decode(),
        "User-Agent": "opti-abrechnung",
    }
    if methode == "PROPFIND":
        kopf["Depth"] = "1"
        kopf["Content-Type"] = 'application/xml; charset="utf-8"'
    return urllib.request.Request(adresse, data=koerper, headers=kopf, method=methode)


def _fehler_deuten(fehler: urllib.error.HTTPError, freigabe: Freigabe) -> NextcloudFehler:
    """Uebersetzt HTTP-Fehlercodes in etwas, mit dem man etwas anfangen kann."""
    if fehler.code == 401:
        if freigabe.passwort:
            return NextcloudFehler(
                "Die Freigabe hat das Passwort abgelehnt. Bitte prüfen — Groß- und "
                "Kleinschreibung zählt."
            )
        return NextcloudFehler(
            "Die Freigabe ist passwortgeschützt. Bitte das Passwort der Freigabe "
            "eintragen (nicht das eigene Nextcloud-Passwort)."
        )
    if fehler.code == 404:
        return NextcloudFehler(
            "Die Freigabe wurde nicht gefunden. Möglich ist, dass der Link abgelaufen "
            "ist oder der Ordner inzwischen nicht mehr geteilt wird."
        )
    if fehler.code == 403:
        return NextcloudFehler(
            "Die Freigabe erlaubt kein Lesen der Dateiliste. Bitte in Nextcloud "
            "prüfen, ob es eine Ordnerfreigabe ist und nicht die Freigabe einer "
            "einzelnen Datei."
        )
    return NextcloudFehler(f"Nextcloud antwortete mit HTTP {fehler.code} ({fehler.reason}).")


def _zeit_lesen(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None


def eintraege_zerlegen(xml_text: str, endpunkt_pfad: str) -> list[Eintrag]:
    """Zerlegt eine WebDAV-Mehrfachantwort in Eintraege.

    Getrennt von der HTTP-Anfrage, damit die Zerlegung ohne Netzzugang und ohne
    Nextcloud-Installation getestet werden kann.
    """
    baum = ET.fromstring(xml_text)
    eintraege: list[Eintrag] = []

    for antwort in baum.findall(f"{DAV}response"):
        adresse = antwort.findtext(f"{DAV}href") or ""
        pfad = urllib.parse.unquote(urllib.parse.urlparse(adresse).path)
        innen = pfad[len(endpunkt_pfad) :].strip("/") if pfad.startswith(endpunkt_pfad) else ""
        if not innen:
            continue  # Der Ordner selbst, den PROPFIND immer mitliefert.

        eigenschaften = antwort.find(f"{DAV}propstat/{DAV}prop")
        if eigenschaften is None:
            continue

        ist_ordner = eigenschaften.find(f"{DAV}resourcetype/{DAV}collection") is not None
        groesse = eigenschaften.findtext(f"{DAV}getcontentlength") or "0"

        eintraege.append(
            Eintrag(
                name=eigenschaften.findtext(f"{DAV}displayname") or Path(innen).name,
                pfad=innen,
                groesse=int(groesse) if groesse.isdigit() else 0,
                geaendert=_zeit_lesen(eigenschaften.findtext(f"{DAV}getlastmodified")),
                ist_ordner=ist_ordner,
            )
        )

    return sorted(eintraege, key=lambda e: (not e.ist_ordner, e.name.lower()))


def eintraege_auflisten(freigabe: Freigabe, unterpfad: str | None = None) -> list[Eintrag]:
    """Listet den Inhalt eines Ordners der Freigabe."""
    innen = (unterpfad if unterpfad is not None else freigabe.unterpfad).strip("/")
    letzter_fehler: Exception | None = None

    for endpunkt in _endpunkte(freigabe):
        adresse = f"{endpunkt}/{urllib.parse.quote(innen)}" if innen else f"{endpunkt}/"
        try:
            with urllib.request.urlopen(
                _anfrage(freigabe, adresse, "PROPFIND", _PROPFIND_ANFRAGE), timeout=ZEITSPERRE
            ) as antwort:
                xml_text = antwort.read().decode("utf-8", errors="replace")
            endpunkt_pfad = urllib.parse.urlparse(endpunkt).path
            return eintraege_zerlegen(xml_text, endpunkt_pfad)
        except urllib.error.HTTPError as fehler:
            # 401 und 403 sind Aussagen ueber die Freigabe, nicht ueber den
            # Endpunkt -- weiterprobieren wuerde nur dieselbe Antwort bringen.
            if fehler.code in (401, 403):
                raise _fehler_deuten(fehler, freigabe) from fehler
            letzter_fehler = fehler
        except urllib.error.URLError as fehler:
            raise NextcloudFehler(
                f"Keine Verbindung zu {freigabe.server}: {fehler.reason}. Bitte die "
                "Adresse und die Netzverbindung prüfen."
            ) from fehler

    if isinstance(letzter_fehler, urllib.error.HTTPError):
        raise _fehler_deuten(letzter_fehler, freigabe) from letzter_fehler
    raise NextcloudFehler("Die Dateiliste der Freigabe ließ sich nicht abrufen.")


def dateien_suchen(
    freigabe: Freigabe, *, endungen: tuple[str, ...] = (".csv",), tiefe: int = 3
) -> list[Eintrag]:
    """Durchsucht die Freigabe rekursiv nach Dateien mit den genannten Endungen.

    Die Suchtiefe ist begrenzt, weil in der Ablage auch der Rechnungsbestand mit
    rund 2.900 PDFs liegt. Ohne Begrenzung wuerde das Aufklappen der Freigabe
    unnoetig lange dauern.
    """
    gefunden: list[Eintrag] = []
    offen: list[tuple[str, int]] = [(freigabe.unterpfad, 0)]

    while offen:
        ordner, ebene = offen.pop(0)
        for eintrag in eintraege_auflisten(freigabe, ordner):
            if eintrag.ist_ordner:
                if ebene < tiefe:
                    offen.append((eintrag.pfad, ebene + 1))
            elif eintrag.endung in endungen:
                gefunden.append(eintrag)

    return gefunden


# ---------------------------------------------------------------------------
# Herunterladen mit Zwischenspeicher
# ---------------------------------------------------------------------------


def datei_holen(
    freigabe: Freigabe,
    eintrag: Eintrag,
    *,
    ordner: Path = ZWISCHENSPEICHER,
    erneuern: bool = False,
) -> Path:
    """Laedt eine Datei der Freigabe in den Zwischenspeicher und gibt den Pfad zurueck.

    Ist die Datei schon vorhanden und stimmen Groesse und Aenderungszeit mit der
    Freigabe ueberein, wird nicht erneut geladen. Das ist nicht nur schneller: Es
    heisst auch, dass sich mit dem Tool weiterarbeiten laesst, wenn Nextcloud
    einmal nicht erreichbar ist.
    """
    ziel = Path(ordner) / freigabe.token / eintrag.pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)

    if not erneuern and _ist_aktuell(ziel, eintrag):
        return ziel

    letzter_fehler: Exception | None = None
    for endpunkt in _endpunkte(freigabe):
        adresse = f"{endpunkt}/{urllib.parse.quote(eintrag.pfad)}"
        try:
            with urllib.request.urlopen(
                _anfrage(freigabe, adresse, "GET"), timeout=ZEITSPERRE
            ) as antwort:
                inhalt = antwort.read()
            break
        except urllib.error.HTTPError as fehler:
            if fehler.code in (401, 403):
                raise _fehler_deuten(fehler, freigabe) from fehler
            letzter_fehler = fehler
        except urllib.error.URLError as fehler:
            raise NextcloudFehler(
                f"Keine Verbindung zu {freigabe.server}: {fehler.reason}"
            ) from fehler
    else:
        raise NextcloudFehler(
            f"„{eintrag.name}“ ließ sich nicht herunterladen."
        ) from letzter_fehler

    # Erst vollstaendig schreiben, dann umbenennen. Sonst koennte ein Abbruch
    # eine halbe CSV im Zwischenspeicher hinterlassen, die beim naechsten Lauf
    # als gueltige Datei gelesen wuerde.
    vorlaeufig = ziel.with_suffix(ziel.suffix + ".teil")
    vorlaeufig.write_bytes(inhalt)
    vorlaeufig.replace(ziel)

    if eintrag.geaendert is not None:
        zeitstempel = eintrag.geaendert.timestamp()
        import os

        os.utime(ziel, (zeitstempel, zeitstempel))

    return ziel


def _ist_aktuell(ziel: Path, eintrag: Eintrag) -> bool:
    if not ziel.exists():
        return False
    zustand = ziel.stat()
    if eintrag.groesse and zustand.st_size != eintrag.groesse:
        return False
    if eintrag.geaendert is None:
        return True
    ortszeit = datetime.fromtimestamp(zustand.st_mtime, tz=UTC)
    return abs((ortszeit - eintrag.geaendert).total_seconds()) < 2
