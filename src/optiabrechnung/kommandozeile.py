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
    zerleger.add_argument(
        "--geklaerte-beschriftung",
        action="store_true",
        help=(
            "Geklaerte Bezeichnungen verwenden statt der Wortwahl des "
            "Bestandsblattes (Buchhaltung Klier + Ott statt Buha Klier+Ott)"
        ),
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

    # Beschriftung und Reihenfolge folgen dem Bestandsblatt, damit sich die
    # Ausgabe unmittelbar danebenlegen laesst.
    wie_im_bestand = not argumente.geklaerte_beschriftung

    print()
    print(f"Umsätze Optionsräume · {zeitraum.bezeichnung}")
    print(
        f"Zeitraum {zeitraum.beginn.strftime('%d.%m.%Y')} bis "
        f"{zeitraum.ende.strftime('%d.%m.%Y')} · alle Beträge brutto"
    )
    print(f"Quelle: {argumente.export.name}")
    print("=" * BREITE)

    print("\nEinnahmen")
    for posten in kette.einnahmen:
        print(_zeile(f"  {posten.beschriftung(wie_im_bestand=wie_im_bestand)}", posten.betrag))
    print(_zeile("Summe Einnahmen", kette.einnahmen_gesamt, hervorgehoben=True))

    print("\nBetrieb & Erhaltung")
    for posten in kette.betriebskosten:
        markierung = " ⚑" if posten.pruefbedarf and posten.betrag else ""
        beschriftung = posten.beschriftung(wie_im_bestand=wie_im_bestand)
        print(_zeile(f"  {beschriftung}{markierung}", posten.betrag))
    print(_zeile("Summe Betrieb & Erhaltung", kette.betriebskosten_gesamt, hervorgehoben=True))

    print()
    print(_zeile(f"  {kette.nebenkosten.bezeichnung}", kette.nebenkosten.betrag))
    print(_zeile(f"  {kette.internet.bezeichnung}", kette.internet.betrag))
    print(_zeile("Ausgaben gesamt", kette.ausgaben_gesamt))
    print(_zeile("Überschuss gesamt", kette.ueberschuss_gesamt, hervorgehoben=True))

    print("\nInvestitionen Kuratoren")
    print(_zeile("  50 % Überschuss für Investition Kuratoren", kette.budgetzufuehrung))
    for posten in kette.investitionen:
        beschriftung = posten.beschriftung(wie_im_bestand=wie_im_bestand)
        print(_zeile(f"    {beschriftung}", posten.betrag))
    print(_zeile("  Investitionen getätigt", kette.investitionen_gesamt))
    print(_zeile("Investitionsbetrag übrig", kette.budget_verfuegbar, hervorgehoben=True))

    print("\nAbführung an die WEG")
    print(_zeile("  50 % Überschuss an WEG (netto)", kette.weg_anteil_netto))
    print(_zeile(f"  {kette.nebenkosten.bezeichnung}", kette.nebenkosten.betrag))
    print(_zeile("  abz. Abschläge vorige Quartale", kette.abschlaege_vorige_quartale))
    print(_zeile("Überweisung auf Hauptkonto", kette.ueberweisung_weg, hervorgehoben=True))

    if kette.pruefposten:
        print("\n⚑ Vorzulegende Posten")
        for posten in kette.pruefposten:
            beschriftung = posten.beschriftung(wie_im_bestand=wie_im_bestand)
            print(_zeile(f"  {beschriftung}", posten.betrag))

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
