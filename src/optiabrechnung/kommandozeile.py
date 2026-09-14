"""Kommandozeilenzugang: Rechenkette ausgeben und Quellen pruefen.

Gedacht fuer den schnellen Blick und fuer den Vergleich mit der bisherigen
Auswertung, ohne die Oberflaeche zu starten -- etwa um die Zahlen eines Quartals
neben den alten Bericht zu legen.

    uv run opti-abrechnung "…/SF Optionsräume 25.csv" --jahr 2025
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .auswertung import raumbilanz, rechenkette
from .einlesen import EinleseFehler, einlesen_moneymoney
from .kategorien import UnbekannteKategorie
from .oberflaeche.darstellung import euro, prozent
from .parameter import ParameterFehlt, Zeitraum

BREITE = 68


def _zeile(bezeichnung: str, betrag, *, hervorgehoben: bool = False) -> str:
    text = euro(betrag)
    fuellung = "=" if hervorgehoben else " "
    return f"{bezeichnung} ".ljust(BREITE - len(text), fuellung) + text


def _argumente(argv: list[str] | None = None) -> argparse.Namespace:
    zerleger = argparse.ArgumentParser(
        prog="opti-abrechnung",
        description="Rechenkette der Optionsraeume fuer einen Zeitraum ausgeben.",
    )
    zerleger.add_argument("export", type=Path, help="MoneyMoney-Export als CSV")
    zerleger.add_argument("--jahr", type=int, required=True)
    zerleger.add_argument("--von-quartal", type=int, default=1, choices=(1, 2, 3, 4))
    zerleger.add_argument("--bis-quartal", type=int, default=4, choices=(1, 2, 3, 4))
    zerleger.add_argument(
        "--raumbilanz", action="store_true", help="Raumbilanz zusaetzlich ausgeben"
    )
    return zerleger.parse_args(argv)


def hauptprogramm(argv: list[str] | None = None) -> int:
    argumente = _argumente(argv)
    try:
        buchungen = einlesen_moneymoney(argumente.export)
        zeitraum = Zeitraum(
            jahr=argumente.jahr,
            erstes_quartal=argumente.von_quartal,
            letztes_quartal=argumente.bis_quartal,
        )
        kette = rechenkette(buchungen, zeitraum)
    except (UnbekannteKategorie, EinleseFehler, ParameterFehlt, ValueError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1

    print()
    print(f"Auswertung Optionsräume · {zeitraum.bezeichnung}")
    print(f"Quelle: {argumente.export.name}")
    print("=" * BREITE)

    print("\nEinnahmen Vermietung")
    for posten in kette.einnahmen:
        print(_zeile(f"  {posten.bezeichnung}", posten.betrag))
    print(_zeile("Summe Einnahmen", kette.einnahmen_gesamt, hervorgehoben=True))

    print("\nBetrieb & Erhaltung")
    for posten in kette.betriebskosten:
        markierung = " ⚑" if posten.pruefbedarf and posten.betrag else ""
        print(_zeile(f"  {posten.bezeichnung}{markierung}", posten.betrag))
    print(_zeile("Summe Betrieb & Erhaltung", kette.betriebskosten_gesamt, hervorgehoben=True))

    print()
    print(_zeile(f"  {kette.nebenkosten.bezeichnung}", kette.nebenkosten.betrag))
    print(_zeile(f"  {kette.internet.bezeichnung}", kette.internet.betrag))
    print(_zeile("Überschuss gesamt", kette.ueberschuss_gesamt, hervorgehoben=True))

    print("\nInvestitionsbudget Kuratoren")
    print(_zeile("  50 % Überschuss (brutto)", kette.budgetzufuehrung))
    print(_zeile("  bereits getätigte Investitionen", kette.investitionen_gesamt))
    print(_zeile("Verfügbares Budget Kuratoren", kette.budget_verfuegbar, hervorgehoben=True))

    print("\nAbführung an die WEG")
    print(_zeile("  50 % Überschuss netto (÷ 1,19)", kette.weg_anteil_netto))
    print(_zeile(f"  {kette.nebenkosten.bezeichnung}", kette.nebenkosten.betrag))
    print(_zeile("Überweisung an die WEG", kette.ueberweisung_weg, hervorgehoben=True))

    if kette.pruefposten:
        print("\n⚑ Vorzulegende Posten")
        for posten in kette.pruefposten:
            print(_zeile(f"  {posten.bezeichnung}", posten.betrag))

    if kette.unzugeordnet:
        print(
            f"\nWarnung: {len(kette.unzugeordnet)} Buchungen ohne Zielkategorie.",
            file=sys.stderr,
        )

    if argumente.raumbilanz:
        print("\nRaumbilanz (kalkulatorisch, Umlage nach Einnahmenanteil)")
        print("-" * BREITE)
        for bilanz in raumbilanz(kette):
            print(f"  {bilanz.raum.value} · Anteil {prozent(bilanz.einnahmenanteil)}")
            print(_zeile("    Dauermiete", bilanz.dauermiete))
            print(_zeile("    Einzelbuchungen", bilanz.einzelbuchung))
            print(_zeile("    Erhaltung direkt", bilanz.erhaltung))
            print(_zeile("    Gemeinkosten anteilig", bilanz.gemeinkosten_umlage))
            print(_zeile("    Deckungsbeitrag", bilanz.deckungsbeitrag, hervorgehoben=True))
            print()

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(hauptprogramm())
