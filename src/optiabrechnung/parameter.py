"""Gepflegte Parameter der Auswertung -- Nebenkosten, Internet, Schluessel.

Diese Werte stehen nicht in den Bankdaten, sondern sind gesetzt oder beschlossen.
Sie werden hier je Jahr gefuehrt und tragen jeweils eine Herkunftsangabe, damit
im Bericht nicht nur der Betrag steht, sondern auch, woher er kommt. Das ist der
Kern des Nachvollziehbarkeitsanspruchs aus Abschnitt 1 des Plans.

Zur Nebenkostenfortschreibung sind nach Abschnitt 8 zwei Lesarten offen: eine
Fortschreibung des Vorjahreswerts um den Verbraucherpreisindex, oder der Ansatz
der zuletzt verfuegbaren tatsaechlichen Werte. Beide bleiben abbildbar, weil der
Betrag je Jahr als Parameter gefuehrt wird -- bei tatsaechlichen Werten wird er
eingetragen, bei einer Indexloesung aus dem Vorjahr berechnet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# ---------------------------------------------------------------------------
# Zeitraum
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Zeitraum:
    """Ein Auswertungszeitraum, angegeben in ganzen Quartalen eines Jahres."""

    jahr: int
    erstes_quartal: int = 1
    letztes_quartal: int = 4

    def __post_init__(self) -> None:
        if not 1 <= self.erstes_quartal <= self.letztes_quartal <= 4:
            raise ValueError(
                f"unzulaessiger Zeitraum: Q{self.erstes_quartal}-Q{self.letztes_quartal}"
            )

    @property
    def anzahl_quartale(self) -> int:
        return self.letztes_quartal - self.erstes_quartal + 1

    @property
    def jahresanteil(self) -> Decimal:
        """Anteil des Zeitraums am Gesamtjahr, fuer die Umlage von Jahresbetraegen."""
        return Decimal(self.anzahl_quartale) / Decimal(4)

    @property
    def beginn(self) -> date:
        return date(self.jahr, (self.erstes_quartal - 1) * 3 + 1, 1)

    @property
    def ende(self) -> date:
        monat = self.letztes_quartal * 3
        letzter_tag = 31 if monat in (3, 12) else 30
        return date(self.jahr, monat, letzter_tag)

    @property
    def bezeichnung(self) -> str:
        """Eindeutige Beschriftung fuer Bericht und Oberflaeche.

        Abschnitt 8 des Plans bemaengelt, dass der Nebenkostenposten in der
        Q2-Auswertung mit 'Quartal' beschriftet ist, obwohl er den
        Halbjahresbetrag enthaelt. Deshalb wird hier immer der tatsaechlich
        abgedeckte Zeitraum benannt und nie pauschal 'Quartal'.
        """
        if self.anzahl_quartale == 4:
            return f"Jahr {self.jahr}"
        if self.anzahl_quartale == 1:
            return f"Q{self.erstes_quartal} {self.jahr}"
        if self.anzahl_quartale == 2 and self.erstes_quartal == 1:
            return f"1. Halbjahr {self.jahr}"
        if self.anzahl_quartale == 2 and self.erstes_quartal == 3:
            return f"2. Halbjahr {self.jahr}"
        return f"Q{self.erstes_quartal}-Q{self.letztes_quartal} {self.jahr}"

    def enthaelt(self, tag: date) -> bool:
        return self.beginn <= tag <= self.ende


# ---------------------------------------------------------------------------
# Jahresparameter
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Jahresparameter:
    """Die je Jahr gepflegten Betraege der Rechenkette."""

    jahr: int

    nebenkosten_jahresbetrag: Decimal
    """Nebenkostenpauschale an die WEG fuer das ganze Jahr, brutto."""

    nebenkosten_herkunft: str

    internet_jahresbetrag: Decimal
    """Internet Optionsraeume fuer das ganze Jahr. Eigene Zeile der Rechenkette,
    nicht Teil der Summe 'Betrieb & Erhaltung'."""

    internet_herkunft: str

    abschlaege_vorige_quartale: Decimal = Decimal(0)
    """Bereits geleistete Nebenkostenabschlaege frueherer Quartale des Jahres.

    Die Bestandsauswertung fuehrt diese Zeile ("abz. Abschlaege vorige Quartale")
    mit 0,00 EUR. Sie wird mitgefuehrt, damit der Bericht Zeile fuer Zeile neben
    das Bestandsblatt gelegt werden kann und damit ein Quartalsbericht mitten im
    Jahr nicht die volle Jahrespauschale doppelt abfuehrt.
    """

    gesichert: bool = True
    """Falsch, wenn ein Wert hergeleitet und nicht belegt ist. Solche Werte
    werden in der Auswertung als vorlaeufig gekennzeichnet."""


ANTEIL_UEBERSCHUSS = Decimal("0.5")
"""Aufteilung des Ueberschusses: 50 % Investitionsbudget Kuratoren, 50 % WEG."""

UMSATZSTEUERSATZ = Decimal("1.19")
"""Der WEG-Anteil wird netto abgefuehrt, der Kuratorenanteil bleibt brutto.

Abschnitt 8 des Plans stellt diese Brutto/Netto-Mischung ausdruecklich zur
Diskussion: Die Kuratoren erhalten dadurch effektiv einen um 19 % hoeheren
Anteil als die WEG. Bis zur Klaerung wird der Bestand unveraendert
nachgerechnet, denn nach Abschnitt 2.1 ist er der Regressionsmassstab.
"""


PARAMETER_JE_JAHR: dict[int, Jahresparameter] = {
    2025: Jahresparameter(
        jahr=2025,
        nebenkosten_jahresbetrag=Decimal("32335.54"),
        nebenkosten_herkunft=(
            "Summe der tatsaechlichen Buchungen 'WEG - Nebenkosten WEG' 2025 "
            "(BK-Vorauszahlung 2025 und Umbuchung)"
        ),
        internet_jahresbetrag=Decimal("1853.52"),
        internet_herkunft=(
            "Hergeleitet aus dem Halbjahresbetrag 926,76 EUR der Auswertung Q1-Q2 2026 "
            "(926,76 x 2). Fuer 2025 gibt es im MoneyMoney-Export keine eigene "
            "Internet-Kategorie; der Betrag erklaert aber die bisher offene Differenz "
            "von rund 1.850 EUR aus Abschnitt 8 des Plans. Zu belegen."
        ),
        gesichert=False,
    ),
    2026: Jahresparameter(
        jahr=2026,
        nebenkosten_jahresbetrag=Decimal("27885.50"),
        nebenkosten_herkunft=(
            "Tatsaechliche Nebenkosten aus 2024, unveraendert angesetzt, ohne "
            "VPI-Aufschlag -- entspricht Henrikes Lesart aus Abschnitt 8. "
            "Halbjahresanteil 13.942,75 EUR wie in der Auswertung Q1-Q2 2026."
        ),
        internet_jahresbetrag=Decimal("1853.52"),
        internet_herkunft=(
            "Halbjahresbetrag 926,76 EUR aus der Auswertung Q1-Q2 2026, auf das "
            "Jahr gerechnet."
        ),
    ),
}


class ParameterFehlt(LookupError):
    """Fuer das angefragte Jahr sind keine Parameter gepflegt.

    Betrifft derzeit 2022 bis 2024: Die Nebenkostenbetraege dieser Jahre sind
    fuer den Mehrjahresvergleich noch nachzutragen (Abschnitt 10 des Plans).
    """

    def __init__(self, jahr: int) -> None:
        vorhanden = ", ".join(str(j) for j in sorted(PARAMETER_JE_JAHR))
        super().__init__(
            f"Keine Parameter fuer {jahr} gepflegt. Vorhanden: {vorhanden}. "
            f"Bitte in optiabrechnung/parameter.py in PARAMETER_JE_JAHR ergaenzen."
        )


def parameter_fuer(jahr: int) -> Jahresparameter:
    """Liefert die gepflegten Parameter eines Jahres."""
    try:
        return PARAMETER_JE_JAHR[jahr]
    except KeyError as fehler:
        raise ParameterFehlt(jahr) from fehler


# ---------------------------------------------------------------------------
# Kuratorenbudget der Vorjahre
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Bestandsjahr:
    """Die Jahreswerte eines abgeschlossenen Jahres aus der EUER-Uebersicht.

    Alle Betraege sind dort in ganzen Euro angegeben. Daraus folgen kleine
    Unstimmigkeiten von einem Euro -- fuer 2023 etwa ergeben 79.813 - 51.490
    genau 28.323, ausgewiesen sind 28.322. Das ist die Rundung des Blattes und
    kein Fehler in der Uebernahme; die Werte werden unveraendert uebernommen,
    weil das Blatt die Vergleichsgrundlage ist.
    """

    jahr: int
    einnahmen: Decimal
    ausgaben: Decimal
    ueberschuss: Decimal
    budgetrest: Decimal


MEHRJAHRESBESTAND: dict[int, Bestandsjahr] = {
    2022: Bestandsjahr(2022, Decimal("83261"), Decimal("-48601"), Decimal("34660"),
                       Decimal("12260")),
    2023: Bestandsjahr(2023, Decimal("79813"), Decimal("-51490"), Decimal("28322"),
                       Decimal("11600")),
    2024: Bestandsjahr(2024, Decimal("114110"), Decimal("-62460"), Decimal("51651"),
                       Decimal("19213")),
    2025: Bestandsjahr(2025, Decimal("136461"), Decimal("-74875"), Decimal("61586"),
                       Decimal("20134")),
}
"""Die Mehrjahresuebersicht 2022-2025, wie sie auf dem EUER-Blatt steht.

Uebernommen, damit der Mehrjahresvergleich schon jetzt gezeigt werden kann,
obwohl die Exporte dieser Jahre noch fehlen (Abschnitt 10 des Plans). Sobald sie
vorliegen, lassen sich die Werte aus den Buchungen nachrechnen und ersetzen --
und dann wird auch sichtbar, ob die Rundungen des Blattes etwas verdecken.
"""

BUDGETRESTE_VORJAHRE: dict[int, Decimal] = {
    jahr: bestand.budgetrest for jahr, bestand in MEHRJAHRESBESTAND.items()
}
"""Ungenutztes Kuratorenbudget der abgeschlossenen Jahre.

Zusammen mit dem laufenden Jahr ergibt das die 70.512 EUR, die als ungenutztes
Budget 2022-2026 ausgewiesen sind (Abschnitt 2.1).
"""
