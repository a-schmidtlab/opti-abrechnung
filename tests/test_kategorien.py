"""Tests der Kategorieabbildung.

Alle hier verwendeten Personennamen sind erfunden. Die echten Namen der
Dauermieterinnen stehen weder im Code noch in den Tests -- sie werden ueber die
Position im Kategoriepfad erkannt und bleiben ausschliesslich in den Rohdaten.
"""

from __future__ import annotations

import pytest

from optiabrechnung.kategorien import (
    Bereich,
    Durchlaufart,
    Einnahmeart,
    Kostenart,
    Raum,
    UnbekannteKategorie,
    ist_zugeordnet,
    vereinheitlichen,
    zuordnen,
)

# ---------------------------------------------------------------------------
# Personenbezogene Unterkategorien
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pfad", "raum"),
    [
        ("SF Optionsräume - Optionsraum 2 - Erika Mustermann", Raum.OPTIONSRAUM_2),
        ("SF Optionsräume - Bootshaus - Beispielverein e.V.", Raum.BOOTSHAUS),
        ("SF Optionsräume - Optionsraum 3 - Max Beispiel / Lisa Muster", Raum.OPTIONSRAUM_3),
        ("SF Optionsräume - Werkstatt - Musterbetrieb GbR", Raum.WERKSTATT),
    ],
)
def test_unbekannter_name_unter_einem_raum_wird_dauermiete(pfad, raum):
    """Ein neuer Dauermieter soll richtig einsortiert werden, nicht den Import brechen.

    Der Raum steht im Elternsegment. Genau deshalb braucht die Zuordnung keine
    Namensliste -- was zugleich verhindert, dass Klarnamen im Repository landen.
    """
    ziel = zuordnen(pfad)
    assert ziel.bereich is Bereich.EINNAHME
    assert ziel.raum is raum
    assert ziel.einnahmeart is Einnahmeart.DAUERMIETE


@pytest.mark.parametrize(
    ("pfad", "raum"),
    [
        ("SF Optionsräume - Optionsraum 2 - O2 Buchungen", Raum.OPTIONSRAUM_2),
        ("SF Optionsräume - Bootshaus - BH Buchungen", Raum.BOOTSHAUS),
    ],
)
def test_buchungskategorien_sind_einzelbuchungen(pfad, raum):
    ziel = zuordnen(pfad)
    assert ziel.raum is raum
    assert ziel.einnahmeart is Einnahmeart.EINZELBUCHUNG


def test_regel_greift_nur_unterhalb_eines_raums():
    """Sonst wuerde die Forderung aus Abschnitt 4 unterlaufen, dass unbekannte
    Kategorien auffallen und nicht stillschweigend verschwinden."""
    with pytest.raises(UnbekannteKategorie):
        zuordnen("SF Optionsräume - Irgendwas Neues - Noch Unbekannter")


def test_erhaltung_wird_nicht_mit_der_personenregel_verwechselt():
    """`Betrieb & Erhaltung - Optionsraum 2 Erhaltung` hat als Elternsegment
    `Betrieb & Erhaltung`, nicht einen Raum. Die Personenregel darf hier nicht
    greifen, sonst wuerden Kosten zu Einnahmen."""
    ziel = zuordnen("SF Optionsräume - Betrieb & Erhaltung - Optionsraum 2 Erhaltung")
    assert ziel.bereich is Bereich.ERHALTUNG
    assert ziel.raum is Raum.OPTIONSRAUM_2


def test_investition_wird_nicht_mit_der_personenregel_verwechselt():
    ziel = zuordnen("SF Optionsräume - Investitionen Kuratoren - o2 invest")
    assert ziel.bereich is Bereich.INVESTITION
    assert ziel.raum is Raum.OPTIONSRAUM_2


# ---------------------------------------------------------------------------
# Historische Schreibweisen
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("schreibweise_2025", "schreibweise_2026"),
    [
        ("SF Optionsräume - Koordination", "SF Optionsräume - Betrieb & Erhaltung - Koordination"),
        ("SF Optionsräume - Reinigung", "SF Optionsräume - Betrieb & Erhaltung - Reinigung"),
    ],
)
def test_umhaengung_zwischen_2025_und_2026_aendert_die_zuordnung_nicht(
    schreibweise_2025, schreibweise_2026
):
    """Voraussetzung fuer den Mehrjahresvergleich aus Abschnitt 2.2."""
    assert zuordnen(schreibweise_2025) == zuordnen(schreibweise_2026)


def test_einnahmen_unter_neuer_ebene_2026():
    """2026 haengen die Einnahmen unter `Einnahmen`, die Kosten unter
    `Ausgaben Betrieb & Erhaltung`. Die Blattabbildung muss trotzdem greifen."""
    ziel = zuordnen("SF Optionsräume - Einnahmen - Optionsraum 2 - Erika Mustermann")
    assert ziel.raum is Raum.OPTIONSRAUM_2
    assert ziel.einnahmeart is Einnahmeart.DAUERMIETE
    assert zuordnen(
        "SF Optionsräume - Ausgaben Betrieb & Erhaltung - Koordination"
    ).kostenart is Kostenart.KOORDINATION


@pytest.mark.parametrize(
    ("alt", "neu"),
    [
        ("SF Optionsräume - Investitionen Kuratoren - o2 invest",
         "SF Optionsräume - Investitionen Kuratoren - Optionsraum 2 invest"),
    ],
)
def test_alte_und_neue_schreibweise_der_investitionen_treffen_sich(alt, neu):
    assert zuordnen(alt) == zuordnen(neu)


def test_umlaute_und_transkription_ergeben_dieselbe_zuordnung():
    assert zuordnen("SF Optionsräume - Rückbuchungen") == zuordnen(
        "SF Optionsraeume - Rueckbuchungen"
    )


def test_vereinheitlichen_fasst_mehrfache_leerzeichen_zusammen():
    assert vereinheitlichen("  Material   Verbrauch ") == "material verbrauch"


# ---------------------------------------------------------------------------
# Abgrenzungen der Zielsystematik
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pfad", "durchlaufart"),
    [
        ("SF Optionsräume - WEG - Ust", Durchlaufart.UMSATZSTEUER),
        ("SF Optionsräume - WEG - Nebenkosten WEG", Durchlaufart.NEBENKOSTEN_WEG),
        ("SF Optionsräume - WEG - WEG Entnahme", Durchlaufart.WEG_ENTNAHME),
        ("SF Optionsräume - Rückbuchungen", Durchlaufart.RUECKBUCHUNG),
        ("SF Optionsräume - Rückbuchung/Kaution", Durchlaufart.RUECKBUCHUNG),
        ("SF Optionsräume - WEG - Gästezimmer", Durchlaufart.GAESTEZIMMER),
        ("SF Optionsräume - WEG - Re diverse / Gästezimmer", Durchlaufart.GAESTEZIMMER),
        ("SF Optionsräume - Freiraum", Durchlaufart.FREIRAUM),
        ("SF Optionsräume - WEG - WEG Rechnungen bezahlt", Durchlaufart.WEG_RECHNUNGEN),
    ],
)
def test_durchlaufende_posten(pfad, durchlaufart):
    ziel = zuordnen(pfad)
    assert ziel.bereich is Bereich.DURCHLAUFEND
    assert ziel.durchlaufart is durchlaufart


def test_internet_ist_ein_eigener_bereich():
    """In der Bestandsauswertung ist Internet eine eigene Zeile der Kette und
    nicht Teil der Summe 'Betrieb & Erhaltung'."""
    assert zuordnen("SF Optionsräume - Internet").bereich is Bereich.INTERNET


def test_unklar_ist_pruefbeduerftig():
    ziel = zuordnen("SF Optionsräume - Betrieb & Erhaltung - unklar")
    assert ziel.kostenart is Kostenart.UNKLAR
    assert ziel.pruefbedarf


def test_investitionen_sind_pruefbeduerftig():
    """Abschnitt 4: Die Abgrenzung Erhaltung/Investition ist die einzige
    inhaltlich schwierige und muss sichtbar bleiben."""
    assert zuordnen("SF Optionsräume - Investitionen Kuratoren - Werkstatt invest").pruefbedarf


def test_erhaltung_ist_nicht_pruefbeduerftig():
    assert not zuordnen("SF Optionsräume - Betrieb & Erhaltung - Werkstatt Erhaltung").pruefbedarf


def test_unbekannte_kategorie_nennt_die_kategorie_und_den_ort_der_ergaenzung():
    with pytest.raises(UnbekannteKategorie) as fehler:
        zuordnen("Völlig anderes Konto - Sonstiges")
    assert "kategorien.py" in str(fehler.value)


def test_ist_zugeordnet_loest_keinen_fehler_aus():
    assert ist_zugeordnet("SF Optionsräume - Reinigung")
    assert not ist_zugeordnet("Völlig anderes Konto - Sonstiges")


# ---------------------------------------------------------------------------
# Kein Klarname im Quelltext
# ---------------------------------------------------------------------------


def test_die_abbildung_enthaelt_keine_personennamen():
    """Sicherung gegen einen Rueckfall.

    Das Repository ist oeffentlich. Sollte jemand die Namensliste wieder
    einfuegen, weil die Strukturregel im Einzelfall unbequem ist, schlaegt
    dieser Test an. Geprueft wird auf die Blattnamen, die einen Vornamen und
    einen Nachnamen erkennen lassen.
    """
    import re

    from optiabrechnung.kategorien import ABBILDUNG

    fachbegriffe = {"buha klier+ott", "material verbrauch", "internet optionsraeume"}
    verdaechtig = [
        schluessel
        for schluessel in ABBILDUNG
        if schluessel not in fachbegriffe
        and re.fullmatch(r"[a-zäöüß]+ [a-zäöüß]+", schluessel)
        and not any(
            wort in schluessel
            for wort in ("optionsraum", "bootshaus", "werkstatt", "buchungen", "invest", "weg")
        )
    ]
    assert not verdaechtig, f"Sieht nach Personennamen aus: {verdaechtig}"
