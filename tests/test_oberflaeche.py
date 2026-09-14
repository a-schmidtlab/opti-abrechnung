"""Rauchtest der Oberflaeche.

Dass der Streamlit-Server antwortet, sagt nichts darueber, ob das Skript
fehlerfrei durchlaeuft -- gerendert wird erst, wenn ein Browser sich verbindet.
`AppTest` fuehrt das Skript tatsaechlich aus und macht Ausnahmen sichtbar.

Der Test prueft nur, dass alle Ansichten aufbauen und dass die Kennzahlen der
Kette dort ankommen. Das Aussehen zu testen waere hier verschwendete Muehe; die
Zahlen selbst sind in test_rechenkette.py abgedeckt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optiabrechnung.oberflaeche.darstellung import euro, prozent

APP = Path(__file__).resolve().parents[1] / "src" / "optiabrechnung" / "oberflaeche" / "app.py"


@pytest.fixture(scope="module")
def app():
    from streamlit.testing.v1 import AppTest

    lauf = AppTest.from_file(str(APP), default_timeout=60)
    lauf.run()
    return lauf


def test_oberflaeche_laeuft_ohne_ausnahme(app):
    assert not app.exception, [str(a.value) for a in app.exception]


def test_alle_fuenf_ansichten_sind_vorhanden(app):
    beschriftungen = {beschriftung for tab in app.tabs for beschriftung in [tab.label]}
    assert beschriftungen >= {
        "Quartalsbericht",
        "Raumbilanz",
        "Prüfung",
        "Kuratorenbudget",
        "Parameter",
    }


def test_kennzahlen_erscheinen_im_bericht(app):
    beschriftungen = {kennzahl.label for kennzahl in app.metric}
    assert "Einnahmen Vermietung" in beschriftungen
    assert "Überschuss gesamt" in beschriftungen
    assert "Überweisung an die WEG" in beschriftungen


# ---------------------------------------------------------------------------
# Zahlenformate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("betrag", "erwartet"),
    [
        ("51186.64", "51.186,64 €"),
        ("-20228.35", "\u221220.228,35 €"),
        ("0", "0,00 €"),
        ("-0.005", "\u22120,01 €"),
        ("-0.004", "0,00 €"),
        ("7479.865", "7.479,87 €"),
        ("1853.5", "1.853,50 €"),
    ],
)
def test_euro_formatiert_deutsch(betrag, erwartet):
    """Punkt als Tausender-, Komma als Dezimaltrennzeichen, echtes Minus.

    7.479,865 muss kaufmaennisch auf 7.479,87 aufrunden, wie in der
    Bestandsauswertung. Kaufmaennisch heisst dabei von der Null weg: −0,005
    ergibt −0,01. Ein Betrag, der auf glatte Null rundet, wird ohne Vorzeichen
    ausgegeben und nicht als „−0,00 €“.
    """
    from decimal import Decimal

    assert euro(Decimal(betrag)) == erwartet


def test_prozent_formatiert_deutsch():
    from decimal import Decimal

    assert prozent(Decimal("0.1684")) == "16,8 %"
