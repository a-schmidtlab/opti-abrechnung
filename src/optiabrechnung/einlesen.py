"""Einlesen und Normalisieren der beiden Rohdatenquellen.

Quelle 1 ist der MoneyMoney-Export mit Kategorien, Quelle 2 der DKB-Kontoauszug.
MoneyMoney bleibt nach Abschnitt 5 des Plans das fuehrende System fuer die
Kategorisierung; der DKB-Auszug dient der Lueckenpruefung, also dem Nachweis,
dass keine Buchung fehlt.

Beide Dateien liegen im deutschen Zahlen- und Datumsformat vor, unterscheiden
sich aber im Aufbau: MoneyMoney beginnt direkt mit der Kopfzeile, der
DKB-Auszug hat einen vierzeiligen Vorspann mit Konto, Zeitraum und Kontostand.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .kategorien import Zielkategorie, zuordnen

ZEICHENSATZ = "utf-8-sig"
"""Beide Exporte tragen eine Byte-Order-Mark, die mitgelesen werden muss."""


class Quelle(str):
    """Herkunft einer Buchung -- fuer die Nachvollziehbarkeit mitgefuehrt."""

    MONEYMONEY = "MoneyMoney"
    DKB = "DKB"


class EinleseFehler(ValueError):
    """Eine Zeile liess sich nicht auswerten, mit Angabe von Datei und Zeile."""

    def __init__(self, pfad: Path, zeilennummer: int, grund: str) -> None:
        self.pfad = pfad
        self.zeilennummer = zeilennummer
        super().__init__(f"{pfad.name}, Zeile {zeilennummer}: {grund}")


# ---------------------------------------------------------------------------
# Normalisierung deutscher Zahlen und Datumsangaben
# ---------------------------------------------------------------------------

_NICHT_ZIFFER = re.compile(r"[^\d,.\-+]")


def betrag_lesen(text: str) -> Decimal:
    """Wandelt einen Betrag im deutschen Format in ein `Decimal`.

    Beherrscht die Schreibweisen, die in beiden Exporten auftreten:
    `-1.942,08`, `546`, `-27`, `83.272,46 €` -- einschliesslich geschuetzter
    Leerzeichen, wie sie die DKB im Kontostand verwendet.

    `Decimal` und nicht `float`, weil die Rechenkette auf den Cent stimmen
    muss; in Gleitkommaarithmetik waere das nicht zuverlaessig zu halten.
    """
    bereinigt = _NICHT_ZIFFER.sub("", text.replace("\xa0", " ")).strip()
    if not bereinigt:
        raise InvalidOperation(f"leerer Betrag: {text!r}")
    # Punkt ist Tausendertrennzeichen, Komma ist Dezimaltrennzeichen.
    bereinigt = bereinigt.replace(".", "").replace(",", ".")
    return Decimal(bereinigt)


def datum_lesen(text: str) -> date:
    """Wandelt ein Datum im Format TT.MM.JJJJ oder TT.MM.JJ in ein `date`.

    Der DKB-Auszug verwendet zweistellige Jahreszahlen (`30.12.25`), der
    MoneyMoney-Export vierstellige (`30.12.2025`).
    """
    teile = text.strip().split(".")
    if len(teile) != 3:
        raise ValueError(f"unerwartetes Datumsformat: {text!r}")
    tag, monat, jahr = (int(teil) for teil in teile)
    if jahr < 100:
        # Die Daten beginnen 2016; ein zweistelliges Jahr meint immer 20xx.
        jahr += 2000
    return date(jahr, monat, tag)


# ---------------------------------------------------------------------------
# Buchung
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Buchung:
    """Eine einzelne Bankbuchung, normalisiert und der Zielsystematik zugeordnet.

    Die Rohfelder bleiben unveraendert erhalten, damit der Drilldown aus dem
    Bericht bis auf genau die Zeile zurueckfuehrt, die im Export stand.
    """

    datum: date
    wertstellung: date
    betrag: Decimal
    name: str
    verwendungszweck: str
    iban: str
    bank: str
    quelle: str
    zeilennummer: int
    kategorie_moneymoney: str = ""
    zielkategorie: Zielkategorie | None = None

    @property
    def kennung(self) -> str:
        """Stabiler Fingerabdruck der Buchung, fuer Dubletten und Wiedereinlesen.

        Bewusst ohne Verwendungszweck: MoneyMoney haengt an diesen noch
        `, Umsatzart: ...` an, der DKB-Auszug nicht. Datum, Betrag und IBAN
        beschreiben dieselbe Buchung in beiden Quellen identisch.

        Der Betrag wird auf zwei Nachkommastellen normiert: Die DKB schreibt
        glatte Euro als `320`, MoneyMoney als `320,00`. Ohne Normierung waeren
        das zwei verschiedene Kennungen fuer dieselbe Buchung.
        """
        iban = self.iban.strip()
        if set(iban) <= {"0"}:
            iban = ""
        roh = f"{self.datum.isoformat()}|{self.betrag.quantize(Decimal('0.01'))}|{iban}"
        return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:16]

    @property
    def jahr(self) -> int:
        return self.datum.year

    @property
    def quartal(self) -> int:
        return (self.datum.month - 1) // 3 + 1


# ---------------------------------------------------------------------------
# MoneyMoney-Export
# ---------------------------------------------------------------------------

SPALTEN_MONEYMONEY = (
    "Datum",
    "Wertstellung",
    "Kategorie",
    "Name",
    "Verwendungszweck",
    "Konto",
    "Bank",
    "Betrag",
)


def einlesen_moneymoney(pfad: Path, *, kategorien_pruefen: bool = True) -> list[Buchung]:
    """Liest den MoneyMoney-Kategorienexport ein.

    Ist `kategorien_pruefen` gesetzt, schlaegt der Import bei einer unbekannten
    Kategorie fehl -- so verlangt es Abschnitt 4 des Plans. Nur fuer die
    Bestandsaufnahme einer neuen Datei laesst sich die Pruefung abschalten.
    """
    pfad = Path(pfad)
    with pfad.open(encoding=ZEICHENSATZ, newline="") as datei:
        leser = csv.DictReader(datei, delimiter=";")
        fehlende = [s for s in SPALTEN_MONEYMONEY if s not in (leser.fieldnames or ())]
        if fehlende:
            raise EinleseFehler(pfad, 1, f"Spalten fehlen: {', '.join(fehlende)}")

        buchungen: list[Buchung] = []
        for nummer, zeile in enumerate(leser, start=2):
            if not (zeile.get("Datum") or "").strip():
                continue  # Leerzeilen am Dateiende
            try:
                kategoriepfad = (zeile["Kategorie"] or "").strip()
                buchungen.append(
                    Buchung(
                        datum=datum_lesen(zeile["Datum"]),
                        wertstellung=datum_lesen(zeile["Wertstellung"] or zeile["Datum"]),
                        betrag=betrag_lesen(zeile["Betrag"]),
                        name=(zeile["Name"] or "").strip(),
                        verwendungszweck=(zeile["Verwendungszweck"] or "").strip(),
                        iban=(zeile["Konto"] or "").strip(),
                        bank=(zeile["Bank"] or "").strip(),
                        quelle=Quelle.MONEYMONEY,
                        zeilennummer=nummer,
                        kategorie_moneymoney=kategoriepfad,
                        zielkategorie=zuordnen(kategoriepfad) if kategorien_pruefen else None,
                    )
                )
            except (ValueError, InvalidOperation, LookupError) as fehler:
                raise EinleseFehler(pfad, nummer, str(fehler)) from fehler
    return buchungen


# ---------------------------------------------------------------------------
# DKB-Kontoauszug
# ---------------------------------------------------------------------------

SPALTE_BETRAG_DKB = "Betrag (€)"


@dataclass(frozen=True, slots=True)
class DkbAuszug:
    """Ein DKB-Kontoauszug samt der Angaben aus dem Vorspann.

    Der Kontostand aus dem Vorspann ist die Gegenprobe fuer den Import: Die
    Summe aller Buchungen muss sich mit ihm vertragen.
    """

    kontobezeichnung: str
    iban: str
    zeitraum: str
    kontostand: Decimal | None
    buchungen: list[Buchung]


def einlesen_dkb(pfad: Path) -> DkbAuszug:
    """Liest einen DKB-Kontoauszug samt Vorspann ein.

    Der Vorspann umfasst Kontobezeichnung, Zeitraum und Kontostand und endet
    mit einer Leerzeile; erst danach folgt die Kopfzeile der Umsatztabelle.
    Die Zeilen werden gesucht statt abgezaehlt, damit ein geaenderter Vorspann
    den Import nicht bricht.
    """
    pfad = Path(pfad)
    zeilen = pfad.read_text(encoding=ZEICHENSATZ).splitlines()

    kopfzeile_index = next(
        (i for i, zeile in enumerate(zeilen) if zeile.startswith('"Buchungsdatum"')),
        None,
    )
    if kopfzeile_index is None:
        raise EinleseFehler(pfad, 1, "Kopfzeile der Umsatztabelle nicht gefunden")

    vorspann = _vorspann_lesen(zeilen[:kopfzeile_index])
    tabelle = "\n".join(zeilen[kopfzeile_index:])

    buchungen: list[Buchung] = []
    leser = csv.DictReader(io.StringIO(tabelle), delimiter=";", quotechar='"')
    for nummer, zeile in enumerate(leser, start=kopfzeile_index + 2):
        if not (zeile.get("Buchungsdatum") or "").strip():
            continue
        try:
            # Bei Eingaengen ist der Zahlungspflichtige die Gegenseite, bei
            # Ausgaengen der Zahlungsempfaenger.
            eingang = (zeile.get("Umsatztyp") or "").strip() == "Eingang"
            gegenseite = zeile["Zahlungspflichtige*r"] if eingang else zeile["Zahlungsempfänger*in"]
            buchungen.append(
                Buchung(
                    datum=datum_lesen(zeile["Buchungsdatum"]),
                    wertstellung=datum_lesen(zeile["Wertstellung"] or zeile["Buchungsdatum"]),
                    betrag=betrag_lesen(zeile[SPALTE_BETRAG_DKB]),
                    name=(gegenseite or "").strip(),
                    verwendungszweck=" ".join((zeile["Verwendungszweck"] or "").split()),
                    iban=(zeile["IBAN"] or "").strip(),
                    bank="",
                    quelle=Quelle.DKB,
                    zeilennummer=nummer,
                )
            )
        except (ValueError, InvalidOperation, KeyError) as fehler:
            raise EinleseFehler(pfad, nummer, str(fehler)) from fehler

    return DkbAuszug(buchungen=buchungen, **vorspann)


def _vorspann_lesen(zeilen: list[str]) -> dict[str, object]:
    """Zieht Kontobezeichnung, IBAN, Zeitraum und Kontostand aus dem Vorspann."""
    angaben: dict[str, object] = {
        "kontobezeichnung": "",
        "iban": "",
        "zeitraum": "",
        "kontostand": None,
    }
    for zeile in zeilen:
        felder = [feld.strip('" ') for feld in zeile.split(";")]
        if len(felder) < 2 or not felder[1]:
            continue
        schluessel, wert = felder[0], felder[1]
        if schluessel.startswith("Zeitraum"):
            angaben["zeitraum"] = wert
        elif schluessel.startswith("Kontostand"):
            # Der Kontostand ist eine Gegenprobe, keine Pflichtangabe: Wenn die
            # DKB das Format aendert, soll der Import trotzdem durchlaufen.
            with suppress(InvalidOperation):
                angaben["kontostand"] = betrag_lesen(wert)
        elif not angaben["kontobezeichnung"]:
            angaben["kontobezeichnung"] = schluessel
            angaben["iban"] = wert
    return angaben


# ---------------------------------------------------------------------------
# Lueckenpruefung zwischen den Quellen (Abschnitt 5 des Plans)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Abgleichergebnis:
    """Ergebnis des Abgleichs zwischen MoneyMoney-Export und DKB-Auszug."""

    nur_in_dkb: list[Buchung] = field(default_factory=list)
    """Im Kontoauszug vorhanden, im MoneyMoney-Export nicht -- also vermutlich
    nicht kategorisiert und damit in keiner Auswertung enthalten."""

    nur_in_moneymoney: list[Buchung] = field(default_factory=list)
    """Nur in MoneyMoney -- typischerweise eine Zeitraumgrenze."""

    uebereinstimmend: int = 0

    @property
    def vollstaendig(self) -> bool:
        return not self.nur_in_dkb and not self.nur_in_moneymoney

    @property
    def summe_nur_in_dkb(self) -> Decimal:
        return sum((b.betrag for b in self.nur_in_dkb), Decimal(0))

    @property
    def summe_nur_in_moneymoney(self) -> Decimal:
        return sum((b.betrag for b in self.nur_in_moneymoney), Decimal(0))


def abgleichen(
    moneymoney: list[Buchung], dkb: list[Buchung]
) -> Abgleichergebnis:
    """Vergleicht beide Quellen buchungsweise ueber die Kennung.

    Der Vergleich zaehlt Mehrfachvorkommen mit: Zwei gleiche Betraege am
    gleichen Tag von derselben IBAN sind zwei Buchungen, nicht eine. Ein
    reiner Mengenvergleich wuerde solche Faelle verschlucken.
    """
    bestand_moneymoney = Counter(b.kennung for b in moneymoney)
    bestand_dkb = Counter(b.kennung for b in dkb)

    ergebnis = Abgleichergebnis()
    ergebnis.uebereinstimmend = sum((bestand_moneymoney & bestand_dkb).values())

    fehlt_in_moneymoney = bestand_dkb - bestand_moneymoney
    fehlt_in_dkb = bestand_moneymoney - bestand_dkb

    ergebnis.nur_in_dkb = list(_auswaehlen(dkb, fehlt_in_moneymoney))
    ergebnis.nur_in_moneymoney = list(_auswaehlen(moneymoney, fehlt_in_dkb))
    return ergebnis


def _auswaehlen(buchungen: list[Buchung], offen: Counter[str]):
    """Gibt so viele Buchungen je Kennung zurueck, wie in `offen` vermerkt sind."""
    rest = Counter(offen)
    for buchung in buchungen:
        if rest[buchung.kennung] > 0:
            rest[buchung.kennung] -= 1
            yield buchung
