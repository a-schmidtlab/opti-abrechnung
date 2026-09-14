"""Regressionstest der Rechenkette gegen die Bestandsauswertung Q1-Q2 2026.

Abschnitt 2.1 des Plans macht diesen Test zum Abnahmekriterium: Die bestehende
Systematik funktioniert, das Tool automatisiert und dokumentiert sie, und der
Bestand dient als Regressionstest. Wenn hier etwas rot wird, ist das Tool falsch
und nicht die Bestandsauswertung.

Die Referenzwerte stammen aus '2026 Q2 Kategorien.pdf' und '2026 Q2 EUER.pdf'.
Die Testdatei enthaelt je Kategorie eine Sammelbuchung mit genau der dort
ausgewiesenen Summe; die Rohdaten selbst gehoeren nicht ins Repository.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from optiabrechnung.auswertung import auf_cent, raumbilanz, rechenkette
from optiabrechnung.einlesen import einlesen_moneymoney
from optiabrechnung.kategorien import RAEUME, Raum
from optiabrechnung.parameter import Zeitraum

REFERENZ = Path(__file__).parent / "fixtures" / "moneymoney_2026_h1_referenz.csv"
ERSTES_HALBJAHR_2026 = Zeitraum(jahr=2026, erstes_quartal=1, letztes_quartal=2)


@pytest.fixture(scope="module")
def kette():
    buchungen = einlesen_moneymoney(REFERENZ)
    return rechenkette(buchungen, ERSTES_HALBJAHR_2026)


# ---------------------------------------------------------------------------
# Einnahmen je Raum
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raum", "erwartet"),
    [
        (Raum.BOOTSHAUS, "8622.32"),
        (Raum.OPTIONSRAUM_2, "14217.39"),
        (Raum.OPTIONSRAUM_3, "21920.93"),
        (Raum.WERKSTATT, "6426.00"),
    ],
)
def test_einnahmen_je_raum(kette, raum, erwartet):
    posten = {p.bezeichnung: p.betrag for p in kette.einnahmen}
    assert posten[raum.value] == Decimal(erwartet)


def test_einnahmen_gesamt(kette):
    assert kette.einnahmen_gesamt == Decimal("51186.64")


# ---------------------------------------------------------------------------
# Betrieb & Erhaltung
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bezeichnung", "erwartet"),
    [
        ("Koordination", "-8895.84"),
        ("Reinigung", "-4224.50"),
        ("Bootshaus Erhaltung", "-1859.43"),
        ("Optionsraum 2 Erhaltung", "0.00"),
        ("Optionsraum 3 Erhaltung", "-1266.66"),
        ("Werkstatt Erhaltung", "-2241.91"),
        ("Buchhaltung Klier + Ott", "-78.19"),
        ("Verbrauchskosten", "-2386.92"),
        ("Bankgebuehren", "-27.00"),
        ("unklar", "-376.95"),
    ],
)
def test_betriebskosten_je_zeile(kette, bezeichnung, erwartet):
    """Jede Zeile des Kategorien-Exports einzeln, nicht nur die Summe.

    Eine stimmende Summe bei falscher Aufteilung waere der unangenehmere Fehler,
    weil er in der Diskussion erst auffaellt, wenn jemand nachfragt.
    """
    posten = {p.bezeichnung: p.betrag for p in kette.betriebskosten}
    assert posten[bezeichnung] == Decimal(erwartet)


def test_betriebskosten_gesamt(kette):
    assert kette.betriebskosten_gesamt == Decimal("-21357.40")


def test_koordination_und_reinigung_trotz_umhaengung_2026(kette):
    """2025 lagen beide auf oberster Ebene, 2026 unter 'Betrieb & Erhaltung'.

    Die Testdatei verwendet die verschachtelte Schreibweise von 2026. Dass die
    Zuordnung trotzdem greift, ist die Voraussetzung fuer den Jahresvergleich
    aus Abschnitt 2.2.
    """
    posten = {p.bezeichnung: p.betrag for p in kette.betriebskosten}
    assert posten["Koordination"] != Decimal(0)
    assert posten["Reinigung"] != Decimal(0)


# ---------------------------------------------------------------------------
# Parameterposten
# ---------------------------------------------------------------------------


def test_nebenkosten_halbjahresanteil(kette):
    """27.885,50 EUR aus 2024, halbes Jahr -- die ausgewiesenen 13.942,75 EUR."""
    assert kette.nebenkosten.betrag == Decimal("-13942.75")


def test_nebenkosten_beschriftung_nennt_den_zeitraum(kette):
    """Abschnitt 8 ruegt die Beschriftung 'Nebenkosten Quartal' fuer einen
    Halbjahresbetrag. Der Bericht muss den tatsaechlichen Zeitraum nennen."""
    assert kette.nebenkosten.bezeichnung == "Nebenkosten 1. Halbjahr 2026"
    assert "Quartal" not in kette.nebenkosten.bezeichnung


def test_internet_halbjahresanteil(kette):
    assert kette.internet.betrag == Decimal("-926.76")


def test_parameterposten_tragen_eine_herkunftsangabe(kette):
    """Nachvollziehbarkeit: Betraege ohne Buchung muessen erklaeren, woher sie kommen."""
    for posten in (kette.nebenkosten, kette.internet):
        assert posten.aus_parameter
        assert len(posten.herkunft) > 40


# ---------------------------------------------------------------------------
# Die Kette
# ---------------------------------------------------------------------------


def test_ueberschuss_gesamt(kette):
    """51.186,64 - 21.357,40 - 13.942,75 - 926,76 = 14.959,73"""
    assert kette.ueberschuss_gesamt == Decimal("14959.73")


def test_budgetzufuehrung_kuratoren(kette):
    """50 % des Ueberschusses, brutto: 7.479,87 EUR."""
    assert auf_cent(kette.budgetzufuehrung) == Decimal("7479.87")


def test_investitionen_gesamt(kette):
    assert kette.investitionen_gesamt == Decimal("-174.90")


def test_weg_anteil_netto(kette):
    """Der Netto-Anteil der WEG, 6.285,60 EUR.

    Nur aus dem ungerundeten halben Ueberschuss: 7.479,865 / 1,19 = 6.285,6008.
    Aus den gerundeten 7.479,87 EUR kaemen 6.285,61 EUR heraus, und der Bestand
    weist 6.285,60 EUR aus.
    """
    assert auf_cent(kette.weg_anteil_netto) == Decimal("-6285.60")


def test_ueberweisung_an_die_weg(kette):
    """-6.285,60 - 13.942,75 = -20.228,35"""
    assert auf_cent(kette.ueberweisung_weg) == Decimal("-20228.35")


# ---------------------------------------------------------------------------
# Abgrenzungen
# ---------------------------------------------------------------------------


def test_durchlaufende_posten_bleiben_ausserhalb(kette):
    """Umsatzsteuer, WEG-Entnahmen, Rueckbuchungen und Gaestezimmer stehen in der
    Testdatei mit erheblichen Betraegen. Gingen sie in die Kette ein, waere der
    Ueberschuss ein anderer -- Abschnitt 1 grenzt sie ausdruecklich aus."""
    assert kette.ueberschuss_gesamt == Decimal("14959.73")


def test_buchungen_ausserhalb_des_zeitraums_zaehlen_nicht(kette):
    """Die Testdatei enthaelt eine Oktoberbuchung ueber 999,99 EUR."""
    assert kette.einnahmen_gesamt == Decimal("51186.64")


def test_keine_unzugeordneten_buchungen(kette):
    assert kette.unzugeordnet == ()


def test_pruefposten_zeigen_investition_und_unklar(kette):
    """Abschnitt 4 verlangt, die Abgrenzung Erhaltung/Investition sichtbar zu
    machen; Abschnitt 5 verlangt dasselbe fuer 'unklar'."""
    bezeichnungen = {p.bezeichnung for p in kette.pruefposten}
    assert bezeichnungen == {"unklar", "Optionsraum 3 Investition"}


# ---------------------------------------------------------------------------
# Ein Fehler in der Bestandsauswertung
# ---------------------------------------------------------------------------


def test_verfuegbares_budget_weicht_um_90_cent_vom_bestand_ab(kette):
    """Die EUER-Seite rechnet 7.479,87 - 174,00 = 7.305,87 EUR.

    Der Kategorien-Export weist die Investition aber mit 174,90 EUR aus
    (Optionsraum 3 invest), und PLANUNG.md nennt in Abschnitt 2.1 ebenfalls
    174,90 EUR, kommt aber trotzdem auf 7.305,87 EUR. Rechnerisch richtig sind
    7.304,97 EUR; die Bestandszahl enthaelt einen Zahlendreher von 90 Cent.

    Der Test haelt beides fest, damit die Abweichung nicht als Fehler des Tools
    missverstanden wird und beim Klaeren nicht in Vergessenheit geraet.
    """
    ausgewiesen_im_bestand = Decimal("7305.87")
    rechnerisch_richtig = Decimal("7304.97")

    assert auf_cent(kette.budget_verfuegbar) == rechnerisch_richtig
    assert ausgewiesen_im_bestand - rechnerisch_richtig == Decimal("0.90")


# ---------------------------------------------------------------------------
# Raumbilanz
# ---------------------------------------------------------------------------


def test_raumbilanz_umlage_trifft_die_gemeinkosten_genau(kette):
    """Die Summe der Umlagen muss den umzulegenden Betrag exakt treffen.

    Ein-Cent-Abweichungen durch Rundung sind in einer Auswertung, die
    Vertrauen schaffen soll, teurer als der Aufwand, sie zu vermeiden.
    """
    bilanzen = raumbilanz(kette)
    umzulegen = (
        kette.betriebskosten_gesamt
        - sum(p.betrag for p in kette.betriebskosten if p.bezeichnung.endswith("Erhaltung"))
        + kette.internet.betrag
        + kette.nebenkosten.betrag
    )
    assert sum(b.gemeinkosten_umlage for b in bilanzen) == auf_cent(umzulegen)


def test_raumbilanz_deckungsbeitraege_ergeben_den_ueberschuss(kette):
    """Ohne die Investitionen, die nach Abschnitt 4 keine laufende Ausgabe sind."""
    bilanzen = raumbilanz(kette)
    summe_deckungsbeitraege = sum(b.deckungsbeitrag for b in bilanzen)
    assert auf_cent(summe_deckungsbeitraege) == auf_cent(kette.ueberschuss_gesamt)


def test_raumbilanz_einnahmenanteile_ergeben_hundert_prozent(kette):
    bilanzen = raumbilanz(kette)
    assert auf_cent(sum(b.einnahmenanteil for b in bilanzen)) == Decimal("1.00")


def test_raumbilanz_umfasst_alle_vier_raeume(kette):
    assert [b.raum for b in raumbilanz(kette)] == list(RAEUME)
