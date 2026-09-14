# Abrechnungstool Optionsräume Spreefeld

Lokale Web-App für die Finanzauswertung der Optionsräume: Einnahmen und Ausgaben
je Raum, Abführung an die WEG, Fortschreibung des Kuratorenbudgets.

Der eigentliche Zweck ist nicht das Rechnen, sondern die **Nachvollziehbarkeit**.
Jede Zahl im Quartalsbericht lässt sich bis auf die einzelne Bankbuchung
aufklappen. Die fachliche Grundlage steht in [`PLANUNG.md`](PLANUNG.md).

## Datenschutz — bitte zuerst lesen

**Dieses Repository ist öffentlich. Es enthält keine Echtdaten und darf keine
enthalten.** Die Rohdaten führen Klarnamen von Nutzerinnen, IBANs und
Verwendungszwecke, also personenbezogene Daten. Die `.gitignore` schließt
Kontoauszüge, MoneyMoney-Exporte, Rechnungs-PDFs und die SQLite-Datenbank
pauschal aus. Vor jedem Commit lohnt ein Blick auf `git status`.

Die Testdaten unter `tests/fixtures/` sind anonymisiert: Sie tragen die
Kategoriesummen der Bestandsauswertung, aber erfundene Namen und IBANs.

## Einrichtung

Das Projekt verwendet [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev      # Umgebung anlegen und Abhängigkeiten installieren
uv run pytest            # Regressionstests
uv run streamlit run src/optiabrechnung/oberflaeche/app.py
```

## Aufbau

Die Trennung ist bewusst streng: Die Auswertungslogik kennt weder die
Oberfläche noch die Datenbank. Nur so lässt sie sich gegen die Bestandszahlen
automatisiert testen, und dieser Test ist laut Plan das Abnahmekriterium.

| Modul | Aufgabe |
|---|---|
| `kategorien.py` | Stabile Zielsystematik, Abbildung der MoneyMoney-Kategorien |
| `einlesen.py` | CSV-Import DKB und MoneyMoney, Normalisierung, Lückenprüfung |
| `parameter.py` | Gepflegte Werte je Jahr: Nebenkosten, Internet, Zeiträume |
| `auswertung.py` | Rechenkette, Raumbilanz, Budgetfortschreibung — reine Funktionen |
| `datenbank.py` | SQLite-Ablage mit Import-Schnappschüssen |
| `oberflaeche/` | Streamlit-Dashboard mit Drilldown |

Gerechnet wird durchgängig mit `Decimal`, nicht mit `float`. Das ist keine
Vorsicht auf Vorrat: Der Netto-Anteil der WEG ergibt sich aus dem *ungerundeten*
halben Überschuss geteilt durch 1,19. Mit vorher gerundeten 7.479,87 € kämen
6.285,61 € heraus statt der ausgewiesenen 6.285,60 €.

## Stand der Umsetzung

Phase 0 nach Abschnitt 9 des Plans: schmaler Durchstich zur Veranschaulichung
beim Treffen. Die Rechenkette reproduziert Q1–Q2 2026 auf den Cent.

## Zwei Funde aus den Bestandsdaten

**Ein Zahlendreher von 90 Cent.** Die EÜR-Seite rechnet
`7.479,87 − 174,00 = 7.305,87 €`, der Kategorien-Export weist die Investition
aber mit 174,90 € aus. Rechnerisch richtig sind **7.304,97 €**. Festgehalten in
`test_verfuegbares_budget_weicht_um_90_cent_vom_bestand_ab`.

**Die offene Differenz für 2025 schrumpft von rund 1.850 € auf etwa 1,15 €.**
Abschnitt 8 des Plans nennt für 2025 eine unerklärte Differenz von rund 1.850 €
zwischen der Summe der Kategorien und den ausgewiesenen −74.875 €. Der Lauf
gegen den echten Export löst sie fast vollständig auf:

| | Betrag |
|---|---|
| Ausgaben aus den Kategorien (Betrieb & Erhaltung, Koordination, Reinigung) | −40.688,23 € |
| Nebenkosten-WEG-Buchungen | −32.335,54 € |
| Internet, aus dem Halbjahresbetrag 2026 auf das Jahr gerechnet | −1.853,52 € |
| **Summe** | **−74.877,29 €** |
| ausgewiesen in der EÜR | −74.875 € |
| **Rest** | **2,29 €** |

Auf der Einnahmenseite bleibt eine Differenz von 278,86 € (136.182,14 € gegen
ausgewiesene 136.461 €), die sich mit den Rückbuchungen über 280,00 € deckt —
das Tool behandelt sie nach Abschnitt 4 als durchlaufend, die
Bestandsauswertung hat sie offenbar als Einnahme geführt. Beides zusammen
gerechnet bleibt ein unerklärter Rest von etwa **1,15 €**.

Damit sind zwei Fragen zu klären, aber beide sind klein und benannt: Gehören die
Rückbuchungen in die Einnahmen, und woher kommt der letzte Euro? Die
Investitionen stimmen unabhängig davon auf den Cent (−10.659,33 € gegen
ausgewiesene −10.659 €).
