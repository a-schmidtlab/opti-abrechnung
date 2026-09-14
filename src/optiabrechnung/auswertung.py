"""Auswertungslogik als reine Funktionen.

Bewusst ohne jeden Bezug zur Oberflaeche oder zur Datenbank, damit die Kette
gegen die Bestandszahlen automatisiert getestet werden kann. Abschnitt 2.1 des
Plans formuliert den Massstab: Wenn das Tool fuer Q1-Q2 2026 nicht dieselben
Zahlen ausspuckt, ist das Tool falsch.

Gerechnet wird durchgaengig mit `Decimal` in voller Genauigkeit; gerundet wird
erst bei der Ausgabe. Das ist kein Selbstzweck: Der Netto-Anteil der WEG ergibt
sich aus dem halben Ueberschuss geteilt durch 1,19, und nur aus dem *ungerundeten*
halben Ueberschuss kommen die ausgewiesenen 6.285,60 EUR heraus. Mit vorher auf
Cent gerundeten 7.479,87 EUR waeren es 6.285,61 EUR.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .einlesen import Buchung
from .kategorien import RAEUME, Bereich, Einnahmeart, Kostenart, Raum
from .parameter import (
    ANTEIL_UEBERSCHUSS,
    BUDGETRESTE_VORJAHRE,
    UMSATZSTEUERSATZ,
    Jahresparameter,
    Zeitraum,
    parameter_fuer,
)

CENT = Decimal("0.01")
NULL = Decimal("0")


def auf_cent(betrag: Decimal) -> Decimal:
    """Rundet kaufmaennisch auf zwei Nachkommastellen.

    `ROUND_HALF_UP` und nicht Pythons Standard `ROUND_HALF_EVEN`: Die
    Bestandsauswertung rundet kaufmaennisch, und 7.479,865 EUR erscheinen dort
    als 7.479,87 EUR.
    """
    return betrag.quantize(CENT, rounding=ROUND_HALF_UP)


def summe(betraege: Iterable[Decimal]) -> Decimal:
    return sum(betraege, NULL)


# ---------------------------------------------------------------------------
# Posten -- eine Zeile der Auswertung samt ihren Einzelbuchungen
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Posten:
    """Eine Zeile einer Auswertung, aufklappbar bis zur Einzelbuchung.

    Die zugrundeliegenden Buchungen haengen unmittelbar am Posten. Das ist der
    Kern des Drilldowns aus Abschnitt 1: Jede Zahl im Bericht soll per Klick bis
    auf die einzelne Bankbuchung aufklappbar sein.
    """

    bezeichnung: str
    betrag: Decimal
    buchungen: tuple[Buchung, ...] = ()
    pruefbedarf: bool = False
    herkunft: str = ""
    """Belegt bei Posten, die nicht aus Buchungen stammen, sondern aus Parametern."""

    @property
    def aus_parameter(self) -> bool:
        return not self.buchungen and bool(self.herkunft)

    @property
    def anzahl_buchungen(self) -> int:
        return len(self.buchungen)


def _posten_aus(
    bezeichnung: str, buchungen: Sequence[Buchung], *, pruefbedarf: bool = False
) -> Posten:
    return Posten(
        bezeichnung=bezeichnung,
        betrag=summe(b.betrag for b in buchungen),
        buchungen=tuple(buchungen),
        pruefbedarf=pruefbedarf,
    )


# ---------------------------------------------------------------------------
# Filtern und Gruppieren
# ---------------------------------------------------------------------------


def im_zeitraum(buchungen: Iterable[Buchung], zeitraum: Zeitraum) -> list[Buchung]:
    """Waehlt die Buchungen des Zeitraums nach Buchungsdatum aus."""
    return [b for b in buchungen if zeitraum.enthaelt(b.datum)]


def _nach_bereich(buchungen: Iterable[Buchung], bereich: Bereich) -> list[Buchung]:
    return [b for b in buchungen if b.zielkategorie and b.zielkategorie.bereich is bereich]


REIHENFOLGE_BETRIEB: tuple[tuple[str, Bereich, object], ...] = (
    ("Koordination", Bereich.GEMEINKOSTEN, Kostenart.KOORDINATION),
    ("Reinigung", Bereich.GEMEINKOSTEN, Kostenart.REINIGUNG),
    ("Bootshaus Erhaltung", Bereich.ERHALTUNG, Raum.BOOTSHAUS),
    ("Optionsraum 2 Erhaltung", Bereich.ERHALTUNG, Raum.OPTIONSRAUM_2),
    ("Optionsraum 3 Erhaltung", Bereich.ERHALTUNG, Raum.OPTIONSRAUM_3),
    ("Werkstatt Erhaltung", Bereich.ERHALTUNG, Raum.WERKSTATT),
    ("Buchhaltung Klier + Ott", Bereich.GEMEINKOSTEN, Kostenart.BUCHHALTUNG),
    ("Verbrauchskosten", Bereich.GEMEINKOSTEN, Kostenart.VERBRAUCHSKOSTEN),
    ("Bankgebuehren", Bereich.GEMEINKOSTEN, Kostenart.BANKGEBUEHREN),
    ("unklar", Bereich.GEMEINKOSTEN, Kostenart.UNKLAR),
)
"""Reihenfolge der Kostenzeilen wie im Kategorien-Export der Bestandsauswertung.

Die Uebernahme der Reihenfolge ist nicht Kosmetik: Der Bericht soll neben die
bisherige Auswertung gelegt werden koennen, ohne dass jemand Zeilen sucht.
"""


# ---------------------------------------------------------------------------
# Rechenkette nach Abschnitt 2.1
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Rechenkette:
    """Die vollstaendige Kette von den Einnahmen bis zur Ueberweisung an die WEG."""

    zeitraum: Zeitraum
    parameter: Jahresparameter

    einnahmen: tuple[Posten, ...]
    """Je Raum, in der Reihenfolge Bootshaus, O2, O3, Werkstatt."""

    betriebskosten: tuple[Posten, ...]
    investitionen: tuple[Posten, ...]
    nebenkosten: Posten
    internet: Posten

    einnahmen_je_raum_und_art: dict[tuple[Raum, Einnahmeart], Posten] = field(
        default_factory=dict
    )
    unzugeordnet: tuple[Buchung, ...] = ()
    """Buchungen im Zeitraum ohne Zielkategorie -- muessen leer sein."""

    # --- Summen der Kette -------------------------------------------------

    @property
    def einnahmen_gesamt(self) -> Decimal:
        return summe(p.betrag for p in self.einnahmen)

    @property
    def betriebskosten_gesamt(self) -> Decimal:
        """Summe 'Betrieb & Erhaltung'.

        Enthaelt `unklar`, wie in der Bestandsauswertung (Q1-Q2 2026: -376,95 EUR
        von -21.357,40 EUR). Nicht enthalten sind Internet und Nebenkosten, die
        in der Kette eigene Zeilen bilden.
        """
        return summe(p.betrag for p in self.betriebskosten)

    @property
    def ueberschuss_gesamt(self) -> Decimal:
        """Einnahmen abzueglich Betrieb & Erhaltung, Nebenkosten und Internet."""
        return (
            self.einnahmen_gesamt
            + self.betriebskosten_gesamt
            + self.nebenkosten.betrag
            + self.internet.betrag
        )

    @property
    def halber_ueberschuss(self) -> Decimal:
        """Der ungerundete halbe Ueberschuss -- Grundlage beider 50-%-Anteile."""
        return self.ueberschuss_gesamt * ANTEIL_UEBERSCHUSS

    # --- Kuratorenbudget ---------------------------------------------------

    @property
    def budgetzufuehrung(self) -> Decimal:
        """50 % des Ueberschusses als Investitionsbudget der Kuratoren, brutto."""
        return self.halber_ueberschuss

    @property
    def investitionen_gesamt(self) -> Decimal:
        return summe(p.betrag for p in self.investitionen)

    @property
    def budget_verfuegbar(self) -> Decimal:
        """Budgetzufuehrung abzueglich der im Zeitraum getaetigten Investitionen."""
        return self.budgetzufuehrung + self.investitionen_gesamt

    # --- Abfuehrung an die WEG --------------------------------------------

    @property
    def weg_anteil_netto(self) -> Decimal:
        """50 % des Ueberschusses an die WEG, netto -- also geteilt durch 1,19."""
        return -(self.halber_ueberschuss / UMSATZSTEUERSATZ)

    @property
    def ueberweisung_weg(self) -> Decimal:
        """Netto-Ueberschussanteil plus Nebenkostenpauschale des Zeitraums."""
        return self.weg_anteil_netto + self.nebenkosten.betrag

    # --- Hinweise ----------------------------------------------------------

    @property
    def pruefposten(self) -> tuple[Posten, ...]:
        """Posten, die im Bericht ausdruecklich vorzulegen sind.

        Das sind die Investitionen -- weil die Abgrenzung Erhaltung/Investition
        nach Abschnitt 4 nicht automatisierbar ist und pruefbar bleiben muss --
        sowie alles, was in `unklar` gelandet ist.
        """
        return tuple(
            p for p in (*self.betriebskosten, *self.investitionen) if p.pruefbedarf and p.betrag
        )


def rechenkette(
    buchungen: Iterable[Buchung],
    zeitraum: Zeitraum,
    parameter: Jahresparameter | None = None,
) -> Rechenkette:
    """Berechnet die Kette aus Abschnitt 2.1 fuer einen Zeitraum.

    Nebenkosten und Internet werden aus den Jahresparametern anteilig
    angesetzt, sofern es dafuer keine eigenen Buchungen gibt. Fuer Internet
    kommen Buchungen vor, sobald die Kategorie in MoneyMoney gepflegt wird;
    dann haben sie Vorrang, und der Posten ist bis auf die Einzelbuchung
    aufklappbar statt nur mit einer Herkunftsangabe versehen.
    """
    parameter = parameter or parameter_fuer(zeitraum.jahr)
    auswahl = im_zeitraum(buchungen, zeitraum)

    einnahmen_detail: dict[tuple[Raum, Einnahmeart], Posten] = {}
    einnahmen: list[Posten] = []
    for raum in RAEUME:
        je_raum = [
            b
            for b in _nach_bereich(auswahl, Bereich.EINNAHME)
            if b.zielkategorie.raum is raum
        ]
        einnahmen.append(_posten_aus(raum.value, je_raum))
        for art in Einnahmeart:
            geteilt = [b for b in je_raum if b.zielkategorie.einnahmeart is art]
            einnahmen_detail[(raum, art)] = _posten_aus(f"{raum.value} {art.value}", geteilt)

    betriebskosten: list[Posten] = []
    for bezeichnung, bereich, merkmal in REIHENFOLGE_BETRIEB:
        if bereich is Bereich.ERHALTUNG:
            zeilen = [
                b
                for b in _nach_bereich(auswahl, Bereich.ERHALTUNG)
                if b.zielkategorie.raum is merkmal
            ]
        else:
            zeilen = [
                b
                for b in _nach_bereich(auswahl, Bereich.GEMEINKOSTEN)
                if b.zielkategorie.kostenart is merkmal
            ]
        betriebskosten.append(
            _posten_aus(bezeichnung, zeilen, pruefbedarf=merkmal is Kostenart.UNKLAR)
        )

    investitionen = [
        _posten_aus(
            f"{raum.value} Investition",
            [
                b
                for b in _nach_bereich(auswahl, Bereich.INVESTITION)
                if b.zielkategorie.raum is raum
            ],
            pruefbedarf=True,
        )
        for raum in RAEUME
    ]

    return Rechenkette(
        zeitraum=zeitraum,
        parameter=parameter,
        einnahmen=tuple(einnahmen),
        betriebskosten=tuple(betriebskosten),
        investitionen=tuple(investitionen),
        nebenkosten=_anteiliger_posten(
            f"Nebenkosten {zeitraum.bezeichnung}",
            parameter.nebenkosten_jahresbetrag,
            parameter.nebenkosten_herkunft,
            zeitraum,
        ),
        internet=_internetposten(auswahl, parameter, zeitraum),
        einnahmen_je_raum_und_art=einnahmen_detail,
        unzugeordnet=tuple(b for b in auswahl if b.zielkategorie is None),
    )


def _anteiliger_posten(
    bezeichnung: str, jahresbetrag: Decimal, herkunft: str, zeitraum: Zeitraum
) -> Posten:
    """Legt einen Jahresbetrag anteilig auf den Zeitraum um, mit negativem Vorzeichen."""
    anteil = auf_cent(abs(jahresbetrag) * zeitraum.jahresanteil)
    ergaenzung = (
        f" Jahresbetrag {abs(jahresbetrag):,.2f} EUR, davon "
        f"{zeitraum.anzahl_quartale} von 4 Quartalen."
    )
    return Posten(bezeichnung=bezeichnung, betrag=-anteil, herkunft=herkunft + ergaenzung)


def _internetposten(
    auswahl: Sequence[Buchung], parameter: Jahresparameter, zeitraum: Zeitraum
) -> Posten:
    gebucht = _nach_bereich(auswahl, Bereich.INTERNET)
    if gebucht:
        return _posten_aus("Internet Optionsraeume", gebucht)
    return _anteiliger_posten(
        "Internet Optionsraeume",
        parameter.internet_jahresbetrag,
        parameter.internet_herkunft,
        zeitraum,
    )


# ---------------------------------------------------------------------------
# Raumbilanz mit Umlage der Gemeinkosten (Abschnitt 6)
# ---------------------------------------------------------------------------


def verteilen(betrag: Decimal, gewichte: dict[Raum, Decimal]) -> dict[Raum, Decimal]:
    """Verteilt einen Betrag cent-genau nach Gewichten.

    Die Restcents gehen nach dem groessten Rundungsrest an die Raeume, damit die
    Summe der Anteile den Ausgangsbetrag exakt trifft. Ohne das entstuenden in
    der Raumbilanz Ein-Cent-Abweichungen, und genau solche Kleinigkeiten kosten
    in der Diskussion Vertrauen.
    """
    gewichtssumme = summe(gewichte.values())
    if not gewichtssumme:
        return dict.fromkeys(gewichte, NULL)

    ziel = auf_cent(betrag)
    genau = {raum: ziel * gewicht / gewichtssumme for raum, gewicht in gewichte.items()}
    anteile = {raum: wert.quantize(CENT, rounding="ROUND_DOWN") for raum, wert in genau.items()}

    rest_cents = int(((ziel - summe(anteile.values())) / CENT).to_integral_value())
    nach_rest = sorted(gewichte, key=lambda raum: genau[raum] - anteile[raum], reverse=True)
    schritt = CENT if rest_cents >= 0 else -CENT
    for i in range(abs(rest_cents)):
        anteile[nach_rest[i % len(nach_rest)]] += schritt
    return anteile


@dataclass(frozen=True, slots=True)
class Raumbilanz:
    """Ergebnis eines Raums: direkte Zuordnung plus kalkulatorische Umlage."""

    raum: Raum
    dauermiete: Decimal
    einzelbuchung: Decimal
    erhaltung: Decimal
    investition: Decimal
    gemeinkosten_umlage: Decimal
    einnahmenanteil: Decimal
    """Anteil des Raums an den Gesamteinnahmen -- der Verteilungsschluessel."""

    @property
    def einnahmen(self) -> Decimal:
        return self.dauermiete + self.einzelbuchung

    @property
    def deckungsbeitrag(self) -> Decimal:
        """Einnahmen abzueglich direkter Erhaltung und anteiliger Gemeinkosten.

        Ohne Investitionen: Die sind nach Abschnitt 4 keine laufende Ausgabe,
        sondern Entnahme aus dem Kuratorenbudget.
        """
        return self.einnahmen + self.erhaltung + self.gemeinkosten_umlage


def raumbilanz(kette: Rechenkette, *, nebenkosten_umlegen: bool = True) -> list[Raumbilanz]:
    """Erstellt die Raumbilanz mit Umlage der Gemeinkosten nach Einnahmenanteil.

    Der Schluessel folgt Henrikes Vorschlag aus Abschnitt 6: Umlage im Verhaeltnis
    der Einnahmen, weil er einfach zu erklaeren ist, keine zusaetzlichen Daten
    braucht und keine Diskussion ueber Flaechendefinitionen ausloest.

    Eine Eigenschaft des Schluessels ist zu kennen: Weil proportional zu den
    Einnahmen verteilt wird, tragen alle Raeume denselben prozentualen
    Gemeinkostenblock. Unterschiede entstehen deshalb ausschliesslich aus den
    direkt zugeordneten Erhaltungskosten. Das ist kein Fehler, sondern die
    logische Folge des Schluessels -- die Umlage selbst sagt nichts ueber die
    tatsaechliche Kostenverursachung aus.

    Die Bilanz ist eine kalkulatorische Zusatzsicht und laesst die offizielle
    Auswertung nach Abschnitt 2.1 unberuehrt.
    """
    einnahmen_je_raum = {p.bezeichnung: p.betrag for p in kette.einnahmen}
    gewichte = {raum: einnahmen_je_raum.get(raum.value, NULL) for raum in RAEUME}
    gesamteinnahmen = summe(gewichte.values())

    umzulegen = summe(
        p.betrag for p in kette.betriebskosten if not _ist_erhaltung(p)
    ) + kette.internet.betrag
    if nebenkosten_umlegen:
        umzulegen += kette.nebenkosten.betrag
    umlage = verteilen(umzulegen, gewichte)

    erhaltung_je_raum = {p.bezeichnung: p.betrag for p in kette.betriebskosten}
    investition_je_raum = {p.bezeichnung: p.betrag for p in kette.investitionen}

    return [
        Raumbilanz(
            raum=raum,
            dauermiete=kette.einnahmen_je_raum_und_art[(raum, Einnahmeart.DAUERMIETE)].betrag,
            einzelbuchung=kette.einnahmen_je_raum_und_art[
                (raum, Einnahmeart.EINZELBUCHUNG)
            ].betrag,
            erhaltung=erhaltung_je_raum.get(f"{raum.value} Erhaltung", NULL),
            investition=investition_je_raum.get(f"{raum.value} Investition", NULL),
            gemeinkosten_umlage=umlage[raum],
            einnahmenanteil=(
                gewichte[raum] / gesamteinnahmen if gesamteinnahmen else NULL
            ),
        )
        for raum in RAEUME
    ]


def _ist_erhaltung(posten: Posten) -> bool:
    return posten.bezeichnung.endswith("Erhaltung")


# ---------------------------------------------------------------------------
# Fortschreibung des Kuratorenbudgets (Abschnitt 6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Budgetjahr:
    jahr: int
    zufuehrung: Decimal
    investitionen: Decimal
    rest: Decimal
    kumuliert: Decimal
    belegt: bool
    """Wahr, wenn der Wert aus Buchungen gerechnet ist, falsch bei Uebernahme
    aus der Bestandsauswertung."""


def budgetfortschreibung(laufendes_jahr: Budgetjahr | None = None) -> list[Budgetjahr]:
    """Schreibt das Kuratorenbudget ueber die Jahre fort.

    Kumuliert ergibt das die 70.512 EUR, die als ungenutztes Budget 2022-2026
    ausgewiesen sind. Diese Zahl ist nach Abschnitt 6 politisch relevant genug,
    dass ihre Herleitung transparent sein muss -- deshalb tragen die Jahre, die
    noch aus der Bestandsauswertung uebernommen sind, ein `belegt=False`.
    """
    reihe: list[Budgetjahr] = []
    laufend = NULL
    for jahr, rest in sorted(BUDGETRESTE_VORJAHRE.items()):
        laufend += rest
        reihe.append(
            Budgetjahr(
                jahr=jahr,
                zufuehrung=rest,
                investitionen=NULL,
                rest=rest,
                kumuliert=laufend,
                belegt=False,
            )
        )
    if laufendes_jahr is not None:
        laufend += laufendes_jahr.rest
        reihe.append(
            Budgetjahr(
                jahr=laufendes_jahr.jahr,
                zufuehrung=laufendes_jahr.zufuehrung,
                investitionen=laufendes_jahr.investitionen,
                rest=laufendes_jahr.rest,
                kumuliert=laufend,
                belegt=True,
            )
        )
    return reihe


def budgetjahr_aus_kette(kette: Rechenkette) -> Budgetjahr:
    """Leitet den Budgetbeitrag eines Zeitraums aus der Rechenkette ab."""
    return Budgetjahr(
        jahr=kette.zeitraum.jahr,
        zufuehrung=auf_cent(kette.budgetzufuehrung),
        investitionen=auf_cent(kette.investitionen_gesamt),
        rest=auf_cent(kette.budget_verfuegbar),
        kumuliert=NULL,
        belegt=True,
    )
