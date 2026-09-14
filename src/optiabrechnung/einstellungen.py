"""Lokale Einstellungen, damit der Nextcloud-Link nicht jedes Mal neu eingegeben wird.

Die Datei liegt unter `daten/` und ist von der Versionsverwaltung ausgeschlossen.
Sie gehoert zum Rechner, nicht zum Projekt: Jede Person, die das Tool benutzt,
hat ihre eigene.

Das Passwort einer Freigabe wird ausdruecklich **nicht** gespeichert. Es waere ein
Zugangsgeheimnis im Klartext auf der Platte, und der Gewinn -- eine Eingabe pro
Sitzung -- wiegt das nicht auf.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

STANDARDPFAD = Path("daten/einstellungen.json")


@dataclass(slots=True)
class Einstellungen:
    """Was sich das Tool zwischen zwei Sitzungen merkt."""

    quelle: str = "lokal"
    """Entweder `lokal` fuer ein Verzeichnis oder `nextcloud` fuer eine Freigabe."""

    nextcloud_link: str = ""
    lokaler_ordner: str = ""

    def __post_init__(self) -> None:
        if self.quelle not in ("lokal", "nextcloud"):
            self.quelle = "lokal"


def laden(pfad: Path = STANDARDPFAD) -> Einstellungen:
    """Liest die Einstellungen; liefert Voreinstellungen, wenn nichts vorliegt.

    Eine beschaedigte Datei fuehrt nicht zum Abbruch. Sie enthaelt nur
    Bequemlichkeiten, keine Daten, die sich nicht wiederherstellen liessen --
    also ist es richtiger, mit Voreinstellungen weiterzulaufen.
    """
    pfad = Path(pfad)
    if not pfad.exists():
        return Einstellungen()
    try:
        inhalt = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Einstellungen()
    if not isinstance(inhalt, dict):
        return Einstellungen()
    bekannt = {feld for feld in Einstellungen.__slots__}
    return Einstellungen(**{k: v for k, v in inhalt.items() if k in bekannt})


def speichern(einstellungen: Einstellungen, pfad: Path = STANDARDPFAD) -> None:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(asdict(einstellungen), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
