"""Stabile Zielsystematik der Kategorien und Abbildung der MoneyMoney-Kategorien.

Hintergrund (PLANUNG.md, Abschnitt 2.2): Die Kategoriestruktur in MoneyMoney hat
sich zwischen 2025 und 2026 verschoben. `Koordination` und `Reinigung` lagen 2025
auf oberster Ebene, 2026 unterhalb von `Betrieb & Erhaltung`; ausserdem sind
Kategorien hinzugekommen. Ein Jahresvergleich ist nur moeglich, wenn beide Jahre
auf dieselbe Zielsystematik abgebildet werden.

Dieses Modul definiert deshalb die Zielsystematik nach Abschnitt 4 des Plans und
die Abbildung darauf. Unbekannte MoneyMoney-Kategorien fuehren zu einem Fehler --
sie duerfen nicht stillschweigend unter den Tisch fallen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

TRENNER = " - "
"""MoneyMoney trennt die Kategorieebenen im Export durch ' - '."""


class Bereich(Enum):
    """Oberste Ebene der Zielsystematik.

    Bestimmt, wie eine Buchung in die Rechenkette nach Abschnitt 2.1 eingeht.
    """

    EINNAHME = "Einnahmen Vermietung"
    GEMEINKOSTEN = "Laufende Kosten raumuebergreifend"
    ERHALTUNG = "Erhaltungskosten je Raum"
    INTERNET = "Internet Optionsraeume"
    INVESTITION = "Investitionen Kuratoren"
    DURCHLAUFEND = "Durchlaufend, nicht in der Auswertung"


class Raum(Enum):
    """Die vier Optionsraeume, plus Markierung fuer raumuebergreifende Posten."""

    BOOTSHAUS = "Bootshaus"
    OPTIONSRAUM_2 = "Optionsraum 2"
    OPTIONSRAUM_3 = "Optionsraum 3"
    WERKSTATT = "Werkstatt"
    RAUMUEBERGREIFEND = "raumuebergreifend"


RAEUME = (Raum.BOOTSHAUS, Raum.OPTIONSRAUM_2, Raum.OPTIONSRAUM_3, Raum.WERKSTATT)
"""Reihenfolge der Raeume in allen Auswertungen -- wie in der Bestandsauswertung."""


class Einnahmeart(Enum):
    """Unterscheidung nach Abschnitt 2.3 -- Kennzahl fuer die Auslastungsdiskussion."""

    DAUERMIETE = "Dauermiete"
    EINZELBUCHUNG = "Einzelbuchung"


class Kostenart(Enum):
    """Kostenarten nach Abschnitt 4 des Plans."""

    VERBRAUCHSKOSTEN = "Verbrauchskosten"
    REINIGUNG = "Reinigung"
    KOORDINATION = "Koordination"
    BUCHHALTUNG = "Buchhaltung Klier + Ott"
    BANKGEBUEHREN = "Bankgebuehren"
    INTERNET = "Internet"
    ERHALTUNG = "Erhaltungskosten"
    INVESTITION = "Investition"
    UNKLAR = "unklar"


class Durchlaufart(Enum):
    """Posten, die im Kontensaldo mitlaufen, aber nicht in die Auswertung eingehen."""

    UMSATZSTEUER = "Umsatzsteuer"
    NEBENKOSTEN_WEG = "Nebenkosten-Ueberweisung an die WEG"
    WEG_ENTNAHME = "WEG-Entnahme und -Umbuchung"
    WEG_DIREKT = "WEG direkt"
    RUECKBUCHUNG = "Rueckbuchung"
    GAESTEZIMMER = "Gaestezimmer"
    FREIRAUM = "Freiraum"
    WEG_RECHNUNGEN = "WEG-Rechnungen, vom Optionsraumkonto bezahlt"


@dataclass(frozen=True, slots=True)
class Zielkategorie:
    """Ein Punkt in der stabilen Zielsystematik.

    Je Bereich sind unterschiedliche Felder belegt: Einnahmen tragen Raum und
    Einnahmeart, Erhaltung und Investition tragen Raum und Kostenart,
    Gemeinkosten tragen nur die Kostenart, Durchlaufendes nur die Durchlaufart.
    """

    bereich: Bereich
    raum: Raum = Raum.RAUMUEBERGREIFEND
    einnahmeart: Einnahmeart | None = None
    kostenart: Kostenart | None = None
    durchlaufart: Durchlaufart | None = None
    pruefbedarf: bool = False
    """Markiert Kategorien, die im Quartalsbericht ausdruecklich vorgelegt werden.

    Das betrifft `unklar` (Abschnitt 5) sowie alle Investitionen, weil die
    Abgrenzung Erhaltung/Investition nach Abschnitt 4 die einzige inhaltlich
    schwierige ist und pruefbar bleiben muss.
    """

    @property
    def bezeichnung(self) -> str:
        """Beschriftung fuer Oberflaeche und Bericht."""
        if self.bereich is Bereich.EINNAHME:
            return f"{self.raum.value} ({self.einnahmeart.value})"
        if self.bereich in (Bereich.ERHALTUNG, Bereich.INVESTITION):
            return f"{self.raum.value} {self.kostenart.value}"
        if self.bereich is Bereich.DURCHLAUFEND:
            return self.durchlaufart.value
        return self.kostenart.value if self.kostenart else self.bereich.value


def _einnahme(raum: Raum, art: Einnahmeart) -> Zielkategorie:
    return Zielkategorie(bereich=Bereich.EINNAHME, raum=raum, einnahmeart=art)


def _gemeinkosten(art: Kostenart) -> Zielkategorie:
    return Zielkategorie(
        bereich=Bereich.GEMEINKOSTEN,
        kostenart=art,
        pruefbedarf=art is Kostenart.UNKLAR,
    )


def _erhaltung(raum: Raum) -> Zielkategorie:
    return Zielkategorie(bereich=Bereich.ERHALTUNG, raum=raum, kostenart=Kostenart.ERHALTUNG)


def _investition(raum: Raum) -> Zielkategorie:
    return Zielkategorie(
        bereich=Bereich.INVESTITION,
        raum=raum,
        kostenart=Kostenart.INVESTITION,
        pruefbedarf=True,
    )


def _durchlaufend(art: Durchlaufart) -> Zielkategorie:
    return Zielkategorie(bereich=Bereich.DURCHLAUFEND, durchlaufart=art)


# ---------------------------------------------------------------------------
# Abbildung MoneyMoney -> Zielsystematik
#
# Geschluesselt wird auf die *Blattkategorie*, also das letzte Segment des
# MoneyMoney-Pfades. Das macht die Abbildung unempfindlich gegen die Umhaengung
# von 2025 auf 2026: `Koordination` wird gefunden, egal ob es direkt unter
# `SF Optionsraeume` oder unter `Betrieb & Erhaltung` haengt.
#
# Die Blattnamen sind ueber alle Jahre eindeutig -- `Werkstatt` (Einnahmen),
# `Werkstatt Erhaltung` und `Werkstatt invest` sind verschiedene Blaetter.
#
# Die personenbezogenen Unterkategorien der Dauermieterinnen stehen hier
# absichtlich nicht. Sie werden ueber ihre Position im Pfad erkannt, siehe
# `_dauermieter_unterkategorie`.
# ---------------------------------------------------------------------------

RAUM_JE_SEGMENT: dict[str, Raum] = {
    "bootshaus": Raum.BOOTSHAUS,
    "bh": Raum.BOOTSHAUS,
    "optionsraum 2": Raum.OPTIONSRAUM_2,
    "optionsraum o2": Raum.OPTIONSRAUM_2,
    "o2": Raum.OPTIONSRAUM_2,
    "optionsraum 3": Raum.OPTIONSRAUM_3,
    "optionsraum o3": Raum.OPTIONSRAUM_3,
    "o3": Raum.OPTIONSRAUM_3,
    "werkstatt": Raum.WERKSTATT,
}
"""Kategoriesegmente, die einen Raum bezeichnen -- in allen Schreibweisen.

Grundlage der Regel fuer personenbezogene Unterkategorien, siehe `zuordnen`.
"""

ABBILDUNG: dict[str, Zielkategorie] = {
    # --- Einnahmen: Bootshaus ------------------------------------------------
    "bootshaus": _einnahme(Raum.BOOTSHAUS, Einnahmeart.EINZELBUCHUNG),
    "bh buchungen": _einnahme(Raum.BOOTSHAUS, Einnahmeart.EINZELBUCHUNG),
    # --- Einnahmen: Optionsraum 2 -------------------------------------------
    "optionsraum 2": _einnahme(Raum.OPTIONSRAUM_2, Einnahmeart.EINZELBUCHUNG),
    "o2 buchungen": _einnahme(Raum.OPTIONSRAUM_2, Einnahmeart.EINZELBUCHUNG),
    # --- Einnahmen: Optionsraum 3 -------------------------------------------
    # Einzelbuchungen laufen hier direkt ueber die Raumkategorie, ohne
    # personenbezogene Unterkategorien (Abschnitt 2.3).
    "optionsraum 3": _einnahme(Raum.OPTIONSRAUM_3, Einnahmeart.EINZELBUCHUNG),
    "optionsraum o3": _einnahme(Raum.OPTIONSRAUM_3, Einnahmeart.EINZELBUCHUNG),
    "o3 buchungen": _einnahme(Raum.OPTIONSRAUM_3, Einnahmeart.EINZELBUCHUNG),
    # --- Einnahmen: Werkstatt -----------------------------------------------
    "werkstatt": _einnahme(Raum.WERKSTATT, Einnahmeart.EINZELBUCHUNG),
    "werkstatt buchungen": _einnahme(Raum.WERKSTATT, Einnahmeart.EINZELBUCHUNG),
    # --- Laufende Kosten, raumuebergreifend ---------------------------------
    "material verbrauch": _gemeinkosten(Kostenart.VERBRAUCHSKOSTEN),
    "verbrauchskosten": _gemeinkosten(Kostenart.VERBRAUCHSKOSTEN),
    "reinigung": _gemeinkosten(Kostenart.REINIGUNG),
    "koordination": _gemeinkosten(Kostenart.KOORDINATION),
    "buha klier+ott": _gemeinkosten(Kostenart.BUCHHALTUNG),
    "buchhaltung": _gemeinkosten(Kostenart.BUCHHALTUNG),
    "bank": _gemeinkosten(Kostenart.BANKGEBUEHREN),
    "bankgebuehren": _gemeinkosten(Kostenart.BANKGEBUEHREN),
    "unklar": _gemeinkosten(Kostenart.UNKLAR),
    # Internet ist in der Bestandsauswertung eine eigene Zeile der Rechenkette,
    # nicht Teil der Summe `Betrieb & Erhaltung` -- daher eigener Bereich.
    "internet": Zielkategorie(bereich=Bereich.INTERNET, kostenart=Kostenart.INTERNET),
    "internet optionsraeume": Zielkategorie(
        bereich=Bereich.INTERNET, kostenart=Kostenart.INTERNET
    ),
    # --- Erhaltungskosten je Raum -------------------------------------------
    # Einschliesslich Ersatzgeschirr: nach Henrikes Einwand vom 7.9.2026 gehoert
    # es hierher und nicht zu den Verbrauchskosten (Abschnitt 4).
    "bootshaus erhaltung": _erhaltung(Raum.BOOTSHAUS),
    "optionsraum 2 erhaltung": _erhaltung(Raum.OPTIONSRAUM_2),
    "optionsraum 3 erhaltung": _erhaltung(Raum.OPTIONSRAUM_3),
    "werkstatt erhaltung": _erhaltung(Raum.WERKSTATT),
    # --- Investitionen je Raum ----------------------------------------------
    # Historische Schreibweisen: 2025 `o2 invest`, 2026 `Optionsraum 2 invest`.
    "bootshaus invest": _investition(Raum.BOOTSHAUS),
    "bh invest": _investition(Raum.BOOTSHAUS),
    "o2 invest": _investition(Raum.OPTIONSRAUM_2),
    "optionsraum 2 invest": _investition(Raum.OPTIONSRAUM_2),
    "o3 invest": _investition(Raum.OPTIONSRAUM_3),
    "optionsraum 3 invest": _investition(Raum.OPTIONSRAUM_3),
    "werkstatt invest": _investition(Raum.WERKSTATT),
    # --- Durchlaufend --------------------------------------------------------
    "ust": _durchlaufend(Durchlaufart.UMSATZSTEUER),
    "umsatzsteuer": _durchlaufend(Durchlaufart.UMSATZSTEUER),
    "nebenkosten weg": _durchlaufend(Durchlaufart.NEBENKOSTEN_WEG),
    "weg entnahme": _durchlaufend(Durchlaufart.WEG_ENTNAHME),
    "weg direkt": _durchlaufend(Durchlaufart.WEG_DIREKT),
    "rueckbuchungen": _durchlaufend(Durchlaufart.RUECKBUCHUNG),
    "rueckbuchung/kaution": _durchlaufend(Durchlaufart.RUECKBUCHUNG),
    "gaestezimmer": _durchlaufend(Durchlaufart.GAESTEZIMMER),
    "re diverse / gaestezimmer": _durchlaufend(Durchlaufart.GAESTEZIMMER),
    # 2026: Ausgaben fuer den Freiraum und WEG-Handwerkerrechnungen laufen
    # ueber dasselbe Konto, gehoeren aber nicht in die Auswertung der Raeume
    # (PLANUNG.md, Abschnitt 8). Sie bleiben durchlaufend.
    "freiraum": _durchlaufend(Durchlaufart.FREIRAUM),
    "weg rechnungen bezahlt": _durchlaufend(Durchlaufart.WEG_RECHNUNGEN),
}


class UnbekannteKategorie(LookupError):
    """Eine MoneyMoney-Kategorie liess sich der Zielsystematik nicht zuordnen.

    Nach Abschnitt 4 des Plans erzwingt das Tool eine Zuordnung fuer jede
    Unterkategorie: 'Jede Unterkategorie braucht eine Zuordnung, sonst schlaegt
    der Import fehl.' Der Fehler ist gewollt und darf nicht abgefangen werden,
    ohne dass die Abbildung ergaenzt wird.
    """

    def __init__(self, kategorie: str) -> None:
        self.kategorie = kategorie
        super().__init__(
            f"MoneyMoney-Kategorie {kategorie!r} ist der Zielsystematik nicht zugeordnet. "
            f"Bitte in optiabrechnung/kategorien.py in ABBILDUNG ergaenzen."
        )


_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def vereinheitlichen(text: str) -> str:
    """Bringt eine Kategoriebezeichnung auf eine vergleichbare Schreibweise.

    Umlaute werden transkribiert, damit `Rueckbuchungen` und `Rückbuchungen`
    denselben Schluessel ergeben; Mehrfach-Leerzeichen werden zusammengefasst.
    """
    vereinfacht = text.strip().lower().translate(_UMLAUTE)
    return re.sub(r"\s+", " ", vereinfacht)


def blatt(kategoriepfad: str) -> str:
    """Liefert das letzte Segment eines MoneyMoney-Kategoriepfades."""
    return kategoriepfad.split(TRENNER)[-1].strip()


def _dauermieter_unterkategorie(kategoriepfad: str) -> Zielkategorie | None:
    """Erkennt personenbezogene Unterkategorien an ihrer Position im Pfad.

    Die Dauermieterinnen haben in MoneyMoney eigene Unterkategorien unterhalb
    ihres Raums, etwa `Optionsraum 2 - <Name>` oder `Bootshaus - <Name>`
    (Abschnitt 2.3 des Plans). Der Raum steht dabei immer im Elternsegment, und
    die Einzelbuchungen laufen erkennbar ueber Kategorien auf `Buchungen`.

    Zugeordnet wird deshalb nach dieser Struktur und nicht ueber eine Liste von
    Namen. Das hat zwei Gruende. Erstens ist es robuster: Ein neuer Dauermieter
    wird richtig einsortiert, statt den Import zu brechen. Zweitens -- und das
    ist der Grund, aus dem die Namensliste hier nicht stehen darf -- gehoeren
    Klarnamen von Mieterinnen nicht in ein Repository. Die Namen bleiben
    ausschliesslich in den Rohdaten, die das Tool liest.

    Gibt `None` zurueck, wenn das Elternsegment keinen Raum bezeichnet. Damit
    bleibt die Forderung aus Abschnitt 4 erhalten, dass unbekannte Kategorien
    auffallen: Die Regel greift nur unterhalb eines erkannten Raums.
    """
    segmente = [vereinheitlichen(teil) for teil in kategoriepfad.split(TRENNER)]
    if len(segmente) < 2:
        return None

    raum = RAUM_JE_SEGMENT.get(segmente[-2])
    if raum is None:
        return None

    art = (
        Einnahmeart.EINZELBUCHUNG
        if "buchungen" in segmente[-1]
        else Einnahmeart.DAUERMIETE
    )
    return _einnahme(raum, art)


def zuordnen(kategoriepfad: str) -> Zielkategorie:
    """Bildet einen MoneyMoney-Kategoriepfad auf die Zielsystematik ab.

    Geprueft wird in drei Schritten: der vollstaendige Pfad, dann die
    Blattkategorie, dann die Strukturregel fuer personenbezogene
    Unterkategorien. Bleibt alles ohne Treffer, wird `UnbekannteKategorie`
    ausgeloest.
    """
    ganzer_pfad = vereinheitlichen(kategoriepfad)
    if ganzer_pfad in ABBILDUNG:
        return ABBILDUNG[ganzer_pfad]

    blattname = vereinheitlichen(blatt(kategoriepfad))
    if blattname in ABBILDUNG:
        return ABBILDUNG[blattname]

    unterkategorie = _dauermieter_unterkategorie(kategoriepfad)
    if unterkategorie is not None:
        return unterkategorie

    raise UnbekannteKategorie(kategoriepfad)


def ist_zugeordnet(kategoriepfad: str) -> bool:
    """Prueft, ob eine Kategorie abgebildet ist, ohne einen Fehler auszuloesen."""
    try:
        zuordnen(kategoriepfad)
    except UnbekannteKategorie:
        return False
    return True
