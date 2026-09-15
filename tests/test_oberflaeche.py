"""Rauchtest der Oberflaeche.

Dass der Streamlit-Server antwortet, sagt nichts darueber, ob das Skript
fehlerfrei durchlaeuft -- gerendert wird erst, wenn ein Browser sich verbindet.
`AppTest` fuehrt das Skript tatsaechlich aus und macht Ausnahmen sichtbar.

Der Test prueft nur, dass alle Ansichten aufbauen und dass die Kennzahlen der
Kette dort ankommen. Das Aussehen zu testen waere hier verschwendete Muehe; die
Zahlen selbst sind in test_rechenkette.py abgedeckt.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from optiabrechnung.oberflaeche.darstellung import (
    SYMBOL_HINWEIS,
    SYMBOL_STIMMIG,
    SYMBOL_WARNUNG,
    euro,
    prozent,
)

WURZEL = Path(__file__).resolve().parents[1]
APP = WURZEL / "src" / "optiabrechnung" / "oberflaeche" / "app.py"
REFERENZ = Path(__file__).resolve().parent / "fixtures" / "moneymoney_2026_h1_referenz.csv"
EINSTELLUNGEN = WURZEL / "daten" / "einstellungen.json"


@pytest.fixture(scope="module")
def datenordner(tmp_path_factory):
    """Ein Verzeichnis mit nur dem Referenzexport darin.

    Der Test gibt der Oberflaeche das Verzeichnis ausdruecklich vor. Sich darauf
    zu verlassen, dass sie im Projektverzeichnis von selbst etwas findet, hiesse
    genau das Verhalten zu testen, das wir gerade abgeschafft haben.
    """
    ordner = tmp_path_factory.mktemp("export")
    shutil.copy(REFERENZ, ordner / REFERENZ.name)
    return ordner


@pytest.fixture(scope="module")
def app(datenordner):
    from streamlit.testing.v1 import AppTest

    # Die Oberflaeche merkt sich das gewaehlte Verzeichnis auf der Platte. Ohne
    # dieses Sichern truege der Test dem Benutzer ein temporaeres Verzeichnis in
    # seine Einstellungen ein, das nach dem Testlauf nicht mehr existiert.
    vorher = EINSTELLUNGEN.read_bytes() if EINSTELLUNGEN.exists() else None
    try:
        lauf = AppTest.from_file(str(APP), default_timeout=60)
        lauf.run()
        lauf.sidebar.text_input(key="verzeichnis").set_value(str(datenordner)).run()
        yield lauf
    finally:
        if vorher is None:
            EINSTELLUNGEN.unlink(missing_ok=True)
        else:
            EINSTELLUNGEN.write_bytes(vorher)


@pytest.fixture(scope="module")
def frischer_klon(tmp_path_factory):
    """Ein Projektverzeichnis wie unmittelbar nach dem Klonen.

    Enthaelt nur den Regressionssatz unter `tests/fixtures/` und sonst keine
    Daten. Der echte Projektordner taugt dafuer nicht: Auf dem Rechner, der die
    Abrechnung fuehrt, liegen dort die tatsaechlichen Exporte.
    """
    ordner = tmp_path_factory.mktemp("klon")
    ziel = ordner / "tests" / "fixtures"
    ziel.mkdir(parents=True)
    shutil.copy(REFERENZ, ziel / REFERENZ.name)
    return ordner


def test_ohne_datenquelle_erscheint_ein_hinweis_und_kein_bericht(frischer_klon):
    """Der Regressionssatz darf nicht als Datenquelle durchgehen.

    Ein Bericht aus Testzahlen sieht einem echten zum Verwechseln aehnlich.
    Erwartet wird also ein Hinweis, keine Auswertung.
    """
    from streamlit.testing.v1 import AppTest

    vorher = EINSTELLUNGEN.read_bytes() if EINSTELLUNGEN.exists() else None
    try:
        lauf = AppTest.from_file(str(APP), default_timeout=60)
        lauf.run()
        lauf.sidebar.text_input(key="verzeichnis").set_value(str(frischer_klon)).run()
        assert not lauf.exception, [str(a.value) for a in lauf.exception]
        assert not lauf.tabs
        assert any("keine Daten" in feld.value for feld in lauf.info)
    finally:
        if vorher is None:
            EINSTELLUNGEN.unlink(missing_ok=True)
        else:
            EINSTELLUNGEN.write_bytes(vorher)


def test_der_regressionssatz_wird_nicht_als_datenquelle_gefunden(frischer_klon):
    from optiabrechnung.oberflaeche.app import MONEYMONEY, _quellen_finden

    assert _quellen_finden(str(frischer_klon))[MONEYMONEY] == []


@pytest.mark.parametrize("zeichen", [SYMBOL_HINWEIS, SYMBOL_WARNUNG, SYMBOL_STIMMIG])
def test_die_symbole_bestehen_streamlits_emoji_pruefung(zeichen):
    """Streamlit bricht die ganze Seite ab, wenn `icon=` kein Emoji ist.

    Das Hakenzeichen U+2713 stand hier einmal und hat der Nextcloud-Ansicht
    genau das angetan. Der Test greift auf Streamlits eigene Pruefung zu, damit
    er auch dann noch stimmt, wenn Streamlit seine Emoji-Liste austauscht.
    """
    from streamlit.string_util import validate_emoji

    assert validate_emoji(zeichen) == zeichen


def test_die_oberflaeche_benutzt_nur_die_geprueften_symbole():
    """Ein Zeichen unmittelbar am `icon=` waere an der Pruefung oben vorbei."""
    import re

    quelltext = APP.read_text(encoding="utf-8")
    assert not re.findall(r'(?<!page_)icon="', quelltext)


def test_oberflaeche_laeuft_ohne_ausnahme(app):
    assert not app.exception, [str(a.value) for a in app.exception]


def test_die_ansichten_stehen_in_der_reihenfolge_des_bestandsblattes(app):
    """Erst die Kette, dann der Mehrjahresvergleich, dann das Budget -- so ist
    auch das Blatt aufgebaut. Raumbilanz und Prüfung sind Zusatzsichten."""
    assert [tab.label for tab in app.tabs][:6] == [
        "Quartalsbericht",
        "Mehrjahresvergleich",
        "Kuratorenbudget",
        "Raumbilanz",
        "Prüfung",
        "Parameter",
    ]


def test_die_fuenf_kennzahlen_der_kurzuebersicht_erscheinen(app):
    """In derselben Wortwahl wie die Kurzübersicht des Bestandsblattes."""
    beschriftungen = [kennzahl.label for kennzahl in app.metric]
    assert beschriftungen[:5] == [
        "Einnahmen Vermietung",
        "Ausgaben gesamt",
        "Überschuss gesamt",
        "Budget Kuratoren",
        "Überschuss & Nebenkosten an WEG",
    ]


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
