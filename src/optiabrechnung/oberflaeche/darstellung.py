"""Formatierung fuer Oberflaeche und Bericht.

Die Zahlenformate werden von Hand gesetzt und nicht ueber `locale`. Eine
deutsche Locale ist auf einem beliebigen Rechner nicht garantiert vorhanden, und
ein Bericht, der auf einem Rechner Punkte und auf einem anderen Kommas setzt,
waere in einer Diskussion ueber Zahlen das Letzte, was man braucht.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import pandas as pd

from ..auswertung import auf_cent
from ..einlesen import Buchung

MINUS = "\u2212"
"""Typografisches Minus. Der Bindestrich ist in Zahlenkolonnen zu schmal."""

SYMBOL_HINWEIS = "\u2139\ufe0f"
SYMBOL_WARNUNG = "\u26a0\ufe0f"
SYMBOL_STIMMIG = "\u2705"
"""Zeichen fuer die `icon`-Angabe der Streamlit-Hinweisfelder.

Streamlit prueft diese Angabe gegen eine Emoji-Liste und bricht die ganze Seite
ab, wenn ein Zeichen nicht darin steht. Typografische Zeichen fallen durch: Das
Hakenzeichen U+2713 sieht aus wie ein Haken, gilt aber nicht als Emoji. Deshalb
stehen die zulaessigen Zeichen hier einmal zentral, und `test_oberflaeche.py`
haelt sie gegen Streamlits eigene Pruefung -- so faellt ein untaugliches Zeichen
im Test auf und nicht erst bei dem, der das Tool benutzt.
"""


def euro(betrag: Decimal | float | int, *, mit_einheit: bool = True) -> str:
    """Formatiert einen Betrag deutsch: 51.186,64 EUR, negativ mit echtem Minus."""
    gerundet = auf_cent(Decimal(str(betrag)))
    ziffern = f"{abs(gerundet):,.2f}".translate(str.maketrans({",": ".", ".": ","}))
    vorzeichen = MINUS if gerundet < 0 else ""
    return f"{vorzeichen}{ziffern} €" if mit_einheit else f"{vorzeichen}{ziffern}"


def prozent(anteil: Decimal | float, *, stellen: int = 1) -> str:
    wert = Decimal(str(anteil)) * 100
    ziffern = f"{wert:.{stellen}f}".replace(".", ",")
    return f"{ziffern} %"


def datum(tag) -> str:
    return tag.strftime("%d.%m.%Y")


def buchungstabelle(buchungen: Sequence[Buchung]) -> pd.DataFrame:
    """Baut die Tabelle fuer den Drilldown auf die Einzelbuchungen.

    Enthaelt bewusst auch Zeilennummer und Quelldatei-Herkunft: Der Sinn des
    Drilldowns ist, eine Zahl bis zu der Zeile zurueckverfolgen zu koennen, die
    im Export stand, und nicht nur bis zu einer aehnlich aussehenden Buchung.
    """
    if not buchungen:
        return pd.DataFrame(
            columns=["Datum", "Betrag", "Auftraggeber / Empfänger", "Verwendungszweck"]
        )
    return pd.DataFrame(
        [
            {
                "Datum": datum(b.datum),
                "Betrag": euro(b.betrag),
                "Auftraggeber / Empfänger": b.name,
                "Verwendungszweck": b.verwendungszweck,
                "IBAN": b.iban,
                "MoneyMoney-Kategorie": b.kategorie_moneymoney,
                "Quelle": f"{b.quelle}, Zeile {b.zeilennummer}",
            }
            for b in sorted(buchungen, key=lambda b: (b.datum, b.zeilennummer))
        ]
    )


def kettentabelle(zeilen: Sequence[tuple[str, Decimal | None, bool]]) -> pd.DataFrame:
    """Formatiert die Rechenkette als zweispaltige Tabelle.

    `zeilen` enthaelt Beschriftung, Betrag und ein Kennzeichen, ob die Zeile ein
    Zwischenergebnis ist. Zwischenergebnisse werden hervorgehoben, weil die
    Kette aus Abschnitt 2.1 gerade in ihren Zwischensummen gelesen wird.
    """
    daten = []
    for bezeichnung, betrag, ist_ergebnis in zeilen:
        beschriftung = f"**{bezeichnung}**" if ist_ergebnis else bezeichnung
        wert = f"**{euro(betrag)}**" if ist_ergebnis and betrag is not None else (
            euro(betrag) if betrag is not None else ""
        )
        daten.append({"Position": beschriftung, "Betrag": wert})
    return pd.DataFrame(daten)
