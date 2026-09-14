"""Tests der Normalisierung und der Buchungskennung."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from optiabrechnung.einlesen import Buchung, Quelle, betrag_lesen


def _buchung(*, betrag: Decimal, iban: str = "DE123") -> Buchung:
    return Buchung(
        datum=date(2026, 9, 14),
        wertstellung=date(2026, 9, 14),
        betrag=betrag,
        name="Test",
        verwendungszweck="",
        iban=iban,
        bank="",
        quelle=Quelle.MONEYMONEY,
        zeilennummer=1,
    )


def test_kennung_unabhaengig_von_nachkommastellen():
    """DKB schreibt 320, MoneyMoney 320,00 -- das ist dieselbe Buchung."""
    assert _buchung(betrag=Decimal("320")).kennung == _buchung(betrag=Decimal("320.00")).kennung


def test_kennung_behandelt_leere_und_null_iban_gleich():
    """Bankgebuehren kommen in der DKB mit IBAN 0000000000, in MoneyMoney leer."""
    assert _buchung(betrag=Decimal("-27"), iban="").kennung == _buchung(
        betrag=Decimal("-27.00"), iban="0000000000"
    ).kennung


def test_betrag_lesen_ganze_euro_und_cents():
    assert betrag_lesen("320") == Decimal("320")
    assert betrag_lesen("320,00") == Decimal("320.00")
    assert betrag_lesen("-1.942,08") == Decimal("-1942.08")
