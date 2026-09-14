"""SQLite-Ablage der importierten Buchungen.

Nach Abschnitt 3 des Plans ist diese Ablage der entscheidende Punkt der
Architektur, und zwar nicht wegen der Rechengeschwindigkeit: Sie haelt fest,
welche Buchungen einem bestimmten Quartalsbericht zugrunde lagen. Fragt in einem
Jahr jemand, wie die Zahl im Bericht fuer Q1-Q2 2026 zustande kam, laesst sie
sich mit genau dem Datenstand von damals wieder aufrufen -- auch dann, wenn in
MoneyMoney inzwischen Kategorien geaendert wurden.

Deshalb wird beim Import nichts ueberschrieben. Jeder Import ist ein eigener
Lauf mit Zeitpunkt und Pruefsumme der Quelldatei, und ein Bericht verweist auf
den Lauf, aus dem er gerechnet wurde.

Betraege liegen als ganzzahlige Cent in der Datenbank. SQLite kennt kein
Dezimalformat, und ueber REAL zu gehen wuerde die Cent-Genauigkeit aufgeben, auf
der die ganze Auswertung beruht.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .einlesen import Buchung
from .kategorien import (
    Bereich,
    Durchlaufart,
    Einnahmeart,
    Kostenart,
    Raum,
    Zielkategorie,
)

SCHEMA = """
PRAGMA foreign_keys = ON;

-- Ein Importlauf: eine Quelldatei zu einem Zeitpunkt.
CREATE TABLE IF NOT EXISTS importlauf (
    id              INTEGER PRIMARY KEY,
    zeitpunkt       TEXT    NOT NULL,
    quelle          TEXT    NOT NULL,
    dateiname       TEXT    NOT NULL,
    pruefsumme      TEXT    NOT NULL,
    anzahl          INTEGER NOT NULL,
    bemerkung       TEXT    NOT NULL DEFAULT ''
);

-- Die Einzelbuchungen eines Laufs, mit Roh- und Zielkategorie.
CREATE TABLE IF NOT EXISTS buchung (
    id                    INTEGER PRIMARY KEY,
    importlauf_id         INTEGER NOT NULL REFERENCES importlauf(id) ON DELETE CASCADE,
    kennung               TEXT    NOT NULL,
    datum                 TEXT    NOT NULL,
    wertstellung          TEXT    NOT NULL,
    betrag_cent           INTEGER NOT NULL,
    name                  TEXT    NOT NULL,
    verwendungszweck      TEXT    NOT NULL,
    iban                  TEXT    NOT NULL,
    bank                  TEXT    NOT NULL,
    quelle                TEXT    NOT NULL,
    zeilennummer          INTEGER NOT NULL,
    kategorie_moneymoney  TEXT    NOT NULL DEFAULT '',
    bereich               TEXT,
    raum                  TEXT,
    einnahmeart           TEXT,
    kostenart             TEXT,
    durchlaufart          TEXT
);

CREATE INDEX IF NOT EXISTS buchung_nach_lauf   ON buchung(importlauf_id);
CREATE INDEX IF NOT EXISTS buchung_nach_datum  ON buchung(datum);
CREATE INDEX IF NOT EXISTS buchung_nach_kennung ON buchung(kennung);

-- Ein erstellter Bericht, verankert an dem Lauf, aus dem er gerechnet wurde.
CREATE TABLE IF NOT EXISTS bericht (
    id              INTEGER PRIMARY KEY,
    zeitpunkt       TEXT    NOT NULL,
    jahr            INTEGER NOT NULL,
    erstes_quartal  INTEGER NOT NULL,
    letztes_quartal INTEGER NOT NULL,
    importlauf_id   INTEGER NOT NULL REFERENCES importlauf(id),
    erstellt_von    TEXT    NOT NULL DEFAULT '',
    bemerkung       TEXT    NOT NULL DEFAULT ''
);
"""

STANDARDPFAD = Path("daten/abrechnung.sqlite")


@contextmanager
def verbindung(pfad: Path = STANDARDPFAD):
    """Oeffnet die Datenbank und legt Schema und Verzeichnis bei Bedarf an."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    verb = sqlite3.connect(pfad)
    verb.row_factory = sqlite3.Row
    try:
        verb.executescript(SCHEMA)
        yield verb
        verb.commit()
    finally:
        verb.close()


def pruefsumme(pfad: Path) -> str:
    """SHA-256 der Quelldatei, gekuerzt.

    Damit laesst sich nachtraeglich feststellen, ob zwei Laeufe dieselbe Datei
    gelesen haben -- und ob eine Datei sich seit dem Import geaendert hat.
    """
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Schreiben
# ---------------------------------------------------------------------------


def _cent(betrag: Decimal) -> int:
    return int((betrag * 100).to_integral_value())


def _wert(merkmal) -> str | None:
    return merkmal.value if merkmal is not None else None


def importlauf_ablegen(
    verb: sqlite3.Connection,
    buchungen: Sequence[Buchung],
    *,
    quelle: str,
    dateipfad: Path,
    bemerkung: str = "",
) -> int:
    """Legt einen Importlauf samt seinen Buchungen ab und gibt seine Kennung zurueck."""
    zeiger = verb.execute(
        "INSERT INTO importlauf (zeitpunkt, quelle, dateiname, pruefsumme, anzahl, bemerkung)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(timespec="seconds"),
            quelle,
            Path(dateipfad).name,
            pruefsumme(dateipfad),
            len(buchungen),
            bemerkung,
        ),
    )
    lauf_id = int(zeiger.lastrowid)

    verb.executemany(
        "INSERT INTO buchung (importlauf_id, kennung, datum, wertstellung, betrag_cent,"
        " name, verwendungszweck, iban, bank, quelle, zeilennummer, kategorie_moneymoney,"
        " bereich, raum, einnahmeart, kostenart, durchlaufart)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                lauf_id,
                b.kennung,
                b.datum.isoformat(),
                b.wertstellung.isoformat(),
                _cent(b.betrag),
                b.name,
                b.verwendungszweck,
                b.iban,
                b.bank,
                b.quelle,
                b.zeilennummer,
                b.kategorie_moneymoney,
                _wert(b.zielkategorie.bereich) if b.zielkategorie else None,
                _wert(b.zielkategorie.raum) if b.zielkategorie else None,
                _wert(b.zielkategorie.einnahmeart) if b.zielkategorie else None,
                _wert(b.zielkategorie.kostenart) if b.zielkategorie else None,
                _wert(b.zielkategorie.durchlaufart) if b.zielkategorie else None,
            )
            for b in buchungen
        ],
    )
    return lauf_id


def bericht_festschreiben(
    verb: sqlite3.Connection,
    *,
    jahr: int,
    erstes_quartal: int,
    letztes_quartal: int,
    importlauf_id: int,
    erstellt_von: str = "",
    bemerkung: str = "",
) -> int:
    """Haelt fest, aus welchem Importlauf ein Bericht gerechnet wurde."""
    zeiger = verb.execute(
        "INSERT INTO bericht (zeitpunkt, jahr, erstes_quartal, letztes_quartal,"
        " importlauf_id, erstellt_von, bemerkung) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(timespec="seconds"),
            jahr,
            erstes_quartal,
            letztes_quartal,
            importlauf_id,
            erstellt_von,
            bemerkung,
        ),
    )
    return int(zeiger.lastrowid)


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Importlauf:
    id: int
    zeitpunkt: str
    quelle: str
    dateiname: str
    pruefsumme: str
    anzahl: int
    bemerkung: str

    @property
    def beschreibung(self) -> str:
        return f"#{self.id} {self.dateiname} ({self.quelle}, {self.anzahl} Buchungen)"


def laeufe_auflisten(verb: sqlite3.Connection, quelle: str | None = None) -> list[Importlauf]:
    """Listet die Importlaeufe, jüngster zuerst."""
    if quelle:
        zeilen = verb.execute(
            "SELECT * FROM importlauf WHERE quelle = ? ORDER BY id DESC", (quelle,)
        )
    else:
        zeilen = verb.execute("SELECT * FROM importlauf ORDER BY id DESC")
    return [Importlauf(**dict(zeile)) for zeile in zeilen]


def _zielkategorie_aus(zeile: sqlite3.Row) -> Zielkategorie | None:
    if not zeile["bereich"]:
        return None
    return Zielkategorie(
        bereich=Bereich(zeile["bereich"]),
        raum=Raum(zeile["raum"]) if zeile["raum"] else Raum.RAUMUEBERGREIFEND,
        einnahmeart=Einnahmeart(zeile["einnahmeart"]) if zeile["einnahmeart"] else None,
        kostenart=Kostenart(zeile["kostenart"]) if zeile["kostenart"] else None,
        durchlaufart=Durchlaufart(zeile["durchlaufart"]) if zeile["durchlaufart"] else None,
        pruefbedarf=zeile["kostenart"]
        in (Kostenart.UNKLAR.value, Kostenart.INVESTITION.value),
    )


def buchungen_lesen(verb: sqlite3.Connection, importlauf_id: int) -> list[Buchung]:
    """Liest die Buchungen eines Importlaufs zurueck.

    Die Zielkategorie wird aus den gespeicherten Merkmalen wiederhergestellt und
    nicht neu aus der Abbildung berechnet. Genau darin liegt der Sinn der
    Ablage: Ein alter Bericht bleibt reproduzierbar, auch wenn die Abbildung
    inzwischen erweitert oder korrigiert wurde.
    """
    zeilen = verb.execute(
        "SELECT * FROM buchung WHERE importlauf_id = ? ORDER BY datum, id", (importlauf_id,)
    )
    return [
        Buchung(
            datum=date.fromisoformat(zeile["datum"]),
            wertstellung=date.fromisoformat(zeile["wertstellung"]),
            betrag=Decimal(zeile["betrag_cent"]) / 100,
            name=zeile["name"],
            verwendungszweck=zeile["verwendungszweck"],
            iban=zeile["iban"],
            bank=zeile["bank"],
            quelle=zeile["quelle"],
            zeilennummer=zeile["zeilennummer"],
            kategorie_moneymoney=zeile["kategorie_moneymoney"],
            zielkategorie=_zielkategorie_aus(zeile),
        )
        for zeile in zeilen
    ]


def jahre_im_lauf(verb: sqlite3.Connection, importlauf_id: int) -> list[int]:
    """Welche Jahre der Importlauf abdeckt -- fuer die Auswahl in der Oberflaeche."""
    zeilen = verb.execute(
        "SELECT DISTINCT substr(datum, 1, 4) AS jahr FROM buchung"
        " WHERE importlauf_id = ? ORDER BY jahr",
        (importlauf_id,),
    )
    return [int(zeile["jahr"]) for zeile in zeilen]


def einlesen_und_ablegen(
    pfad: Path,
    *,
    datenbank: Path = STANDARDPFAD,
    bemerkung: str = "",
) -> tuple[int, list[Buchung]]:
    """Bequemer Weg fuer die Oberflaeche: Datei einlesen und als Lauf ablegen."""
    from .einlesen import Quelle, einlesen_moneymoney

    buchungen = einlesen_moneymoney(pfad)
    with verbindung(datenbank) as verb:
        lauf_id = importlauf_ablegen(
            verb,
            buchungen,
            quelle=Quelle.MONEYMONEY,
            dateipfad=pfad,
            bemerkung=bemerkung,
        )
    return lauf_id, buchungen


def alle_kennungen(verb: sqlite3.Connection, importlauf_id: int) -> set[str]:
    zeilen = verb.execute(
        "SELECT kennung FROM buchung WHERE importlauf_id = ?", (importlauf_id,)
    )
    return {zeile["kennung"] for zeile in zeilen}


def summe_cent(buchungen: Iterable[Buchung]) -> Decimal:
    return sum((b.betrag for b in buchungen), Decimal(0))
