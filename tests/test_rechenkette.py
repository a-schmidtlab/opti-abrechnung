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

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from optiabrechnung.auswertung import (
    auf_cent,
    mehrjahresvergleich,
    raumbilanz,
    rechenkette,
)
from optiabrechnung.einlesen import Buchung, einlesen_moneymoney
from optiabrechnung.kategorien import RAEUME, Raum, zuordnen
from optiabrechnung.parameter import Zeitraum

REFERENZ = Path(__file__).parent / "fixtures" / "moneymoney_2026_h1_referenz.csv"
ERSTES_HALBJAHR_2026 = Zeitraum(jahr=2026, erstes_quartal=1, letztes_quartal=2)


@pytest.fixture(scope="module")
def kette():
    buchungen = einlesen_moneymoney(REFERENZ)
    return rechenkette(buchungen, ERSTES_HALBJAHR_2026)


def _buchung(tag: str, kategorie: str, betrag: str) -> Buchung:
    """Baut eine einzelne Buchung fuer Tests, die keinen ganzen Export brauchen.

    Der Kategoriepfad laeuft durch dieselbe Zuordnung wie ein echter Import,
    damit der Test nicht an der Abbildung vorbei prueft.
    """
    zeitpunkt = datetime.strptime(tag, "%d.%m.%Y").date()
    return Buchung(
        datum=zeitpunkt,
        wertstellung=zeitpunkt,
        betrag=Decimal(betrag.replace(".", "").replace(",", ".")),
        name="Testfall",
        verwendungszweck="Testfall",
        iban="",
        bank="",
        quelle="test",
        zeilennummer=1,
        kategorie_moneymoney=f"SF Optionsräume - {kategorie}",
        zielkategorie=zuordnen(f"SF Optionsräume - {kategorie}"),
    )


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
# Vergleichbarkeit mit dem Bestandsblatt
# ---------------------------------------------------------------------------


def test_ausgaben_gesamt_trifft_die_kurzuebersicht_des_blattes(kette):
    """Das Blatt fasst in der Kurzuebersicht -36.226,91 EUR zusammen.

    Enthalten sind dort Betrieb & Erhaltung, Nebenkosten und Internet, obwohl die
    Zeile nur „Ausgaben Betrieb & Erhaltung“ heisst.
    """
    assert auf_cent(kette.ausgaben_gesamt) == Decimal("-36226.91")


def test_abschlaege_vorige_quartale_stehen_in_der_kette(kette):
    """Das Blatt fuehrt diese Zeile mit 0,00 EUR. Sie wird mitgefuehrt, damit der
    Bericht Zeile fuer Zeile danebengelegt werden kann."""
    assert kette.abschlaege_vorige_quartale == Decimal("0")


def test_ohne_weg_rechnungen_ist_die_anrechnung_null(kette):
    """Der Referenzsatz Q1-Q2 2026 enthaelt keine bezahlten WEG-Rechnungen."""
    assert kette.anrechnung_weg.betrag == Decimal("0")
    assert kette.anrechnung_weg.buchungen == ()


def test_bezahlte_weg_rechnungen_werden_netto_angerechnet():
    """Die 6.941,58 EUR, die lange unerklaert waren, sind die Umsatzsteuer.

    Die EUER Q1-Q3 2026 setzt 'abz. bezahlte Rechnungen von WEG' mit 36.534,66 EUR
    an, waehrend die Buchungen derselben Kategorie 43.476,24 EUR ergeben. Der
    Blattwert ist genau der Nettobetrag: 43.476,24 / 1,19 = 36.534,66. Damit ist
    die Zahl nicht mehr abgeschrieben, sondern hergeleitet -- und dieser Test
    haelt die Herleitung an dem Fall fest, an dem sie sich gezeigt hat.
    """
    rechnungen = [
        _buchung("16.07.2026", "WEG - WEG Rechnungen bezahlt", "-18.950,19"),
        _buchung("29.07.2026", "WEG - WEG Rechnungen bezahlt", "-15.362,68"),
        _buchung("03.07.2026", "WEG - WEG Rechnungen bezahlt", "-4.736,20"),
        _buchung("10.07.2026", "WEG - WEG Rechnungen bezahlt", "-2.106,30"),
        _buchung("08.05.2026", "WEG - WEG Rechnungen bezahlt", "-1.724,31"),
        _buchung("12.06.2026", "WEG - WEG Rechnungen bezahlt", "-596,56"),
    ]
    kette = rechenkette(rechnungen, Zeitraum(jahr=2026, erstes_quartal=1, letztes_quartal=3))

    assert kette.weg_rechnungen_brutto == Decimal("-43476.24")
    assert kette.anrechnung_weg.betrag == Decimal("36534.66")
    assert kette.weg_rechnungen_umsatzsteuer == Decimal("6941.58")
    assert kette.anrechnung_weg.anzahl_buchungen == 6


def test_die_anrechnung_folgt_dem_zeitraum_und_nicht_einem_festen_wert():
    """Zwei der sechs Rechnungen fallen in Q1-Q2, vier in Q3.

    Vorher stand die Anrechnung als Blattwert am Zeitraum (2026, 1, 3) und war
    fuer jeden anderen Zeitraum null. Jetzt zaehlt, was im Zeitraum gebucht ist.
    """
    rechnungen = [
        _buchung("08.05.2026", "WEG - WEG Rechnungen bezahlt", "-1.724,31"),
        _buchung("12.06.2026", "WEG - WEG Rechnungen bezahlt", "-596,56"),
        _buchung("16.07.2026", "WEG - WEG Rechnungen bezahlt", "-18.950,19"),
    ]
    halbjahr = rechenkette(rechnungen, Zeitraum(jahr=2026, erstes_quartal=1, letztes_quartal=2))
    assert halbjahr.weg_rechnungen_brutto == Decimal("-2320.87")
    assert halbjahr.anrechnung_weg.betrag == Decimal("1950.31")


def test_durchlaufende_posten_stehen_gesondert_und_nicht_in_der_kette():
    """Umsatzsteuer und Freiraum bewegen das Konto, nicht das Ergebnis.

    Beides lief bisher unsichtbar mit. Der Bericht weist es jetzt aus, ohne die
    Kette zu beruehren -- die Unterscheidung ist der ganze Punkt.
    """
    buchungen = [
        _buchung("15.09.2026", "WEG - Ust", "-1.018,03"),
        _buchung("28.08.2026", "Freiraum", "-289,40"),
    ]
    kette = rechenkette(buchungen, Zeitraum(jahr=2026, erstes_quartal=1, letztes_quartal=3))

    assert kette.betriebskosten_gesamt == Decimal("0")
    assert kette.einnahmen_gesamt == Decimal("0")
    bezeichnungen = {p.bezeichnung: p.betrag for p in kette.durchlaufend}
    assert bezeichnungen == {
        "Umsatzsteuer an das Finanzamt": Decimal("-1018.03"),
        "Freiraum": Decimal("-289.40"),
    }
    assert kette.durchlaufend_gesamt == Decimal("-1307.43")


@pytest.mark.parametrize(
    ("geklaert", "im_bestand"),
    [
        ("Buchhaltung Klier + Ott", "Buha Klier+Ott"),
        ("Verbrauchskosten", "Material Verbrauch"),
        ("Bankgebuehren", "Bank"),
    ],
)
def test_beide_beschriftungen_sind_verfuegbar(kette, geklaert, im_bestand):
    """Fuer die Vorstellung beim Treffen zaehlt die Wortwahl des Blattes, fuer
    einen Bericht an Spree VV die geklaerte."""
    posten = {p.bezeichnung: p for p in kette.betriebskosten}[geklaert]
    assert posten.beschriftung(wie_im_bestand=True) == im_bestand
    assert posten.beschriftung(wie_im_bestand=False) == geklaert


def test_zeilen_ohne_abweichende_beschriftung_bleiben_gleich(kette):
    posten = {p.bezeichnung: p for p in kette.betriebskosten}["Koordination"]
    assert posten.beschriftung(wie_im_bestand=True) == "Koordination"
    assert posten.beschriftung(wie_im_bestand=False) == "Koordination"


def test_reihenfolge_der_kostenzeilen_wie_im_kategorien_export(kette):
    """Damit beim Nebeneinanderlegen niemand Zeilen suchen muss."""
    assert [p.beschriftung(wie_im_bestand=True) for p in kette.betriebskosten] == [
        "Koordination",
        "Reinigung",
        "Bootshaus Erhaltung",
        "Optionsraum 2 Erhaltung",
        "Optionsraum 3 Erhaltung",
        "Werkstatt Erhaltung",
        "Buha Klier+Ott",
        "Material Verbrauch",
        "Bank",
        "unklar",
    ]


def test_reihenfolge_der_einnahmen_wie_im_kategorien_export(kette):
    assert [p.bezeichnung for p in kette.einnahmen] == [
        "Bootshaus",
        "Optionsraum 2",
        "Optionsraum 3",
        "Werkstatt",
    ]


# ---------------------------------------------------------------------------
# Mehrjahresvergleich
# ---------------------------------------------------------------------------


def test_mehrjahresvergleich_umfasst_2022_bis_zum_laufenden_zeitraum(kette):
    reihe = mehrjahresvergleich(kette)
    assert [j.jahr for j in reihe] == [2022, 2023, 2024, 2025, 2026]
    assert not reihe[0].belegt
    assert reihe[-1].belegt


def test_hergeleitete_investitionen_treffen_den_ausgewiesenen_wert_fuer_2025():
    """Das Blatt weist die Investitionen 2025 mit -10.659 EUR eigens aus.

    Genau dieser Wert kommt aus Budgetrest minus halbem Ueberschuss heraus,
    also 20.134 - 30.793. Damit ist die Herleitung belegt und die Werte fuer
    2022 bis 2024, die das Blatt nicht nennt, sind belastbar.
    """
    jahr_2025 = {j.jahr: j for j in mehrjahresvergleich()}[2025]
    assert jahr_2025.zufuehrung == Decimal("30793")
    assert jahr_2025.investitionen == Decimal("-10659")


def test_budgetreste_ergeben_die_ausgewiesenen_70512_euro(kette):
    """Die Zahl ist politisch relevant genug, dass ihre Herleitung stimmen muss."""
    reihe = mehrjahresvergleich(kette)
    vorjahre = sum(j.budgetrest for j in reihe if not j.belegt)
    assert vorjahre == Decimal("63207")
    laufend = reihe[-1].budgetrest
    assert (vorjahre + laufend).quantize(Decimal("1")) == Decimal("70512")


def test_bestandsjahre_sind_als_unbelegt_gekennzeichnet():
    """Solange die Exporte 2022-2024 fehlen, darf niemand die Zeilen fuer
    nachgerechnet halten."""
    for jahr in mehrjahresvergleich():
        assert not jahr.belegt
        assert "investitionen" in jahr.hergeleitet


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


def test_raumbilanz_beitraege_ergeben_den_ueberschuss(kette):
    """Ohne die Investitionen, die nach Abschnitt 4 keine laufende Ausgabe sind."""
    bilanzen = raumbilanz(kette)
    summe_beitraege = sum(b.ueberschussbeitrag for b in bilanzen)
    assert auf_cent(summe_beitraege) == auf_cent(kette.ueberschuss_gesamt)


def test_raumbilanz_einnahmenanteile_ergeben_hundert_prozent(kette):
    bilanzen = raumbilanz(kette)
    assert auf_cent(sum(b.einnahmenanteil for b in bilanzen)) == Decimal("1.00")


def test_raumbilanz_umfasst_alle_vier_raeume(kette):
    assert [b.raum for b in raumbilanz(kette)] == list(RAEUME)
