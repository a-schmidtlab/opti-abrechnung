# Changelog

Alle wesentlichen Änderungen am Abrechnungstool Optionsräume Spreefeld.
Die fachliche Grundlage bleibt [`PLANUNG.md`](PLANUNG.md).

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionierung nach [SemVer](https://semver.org/lang/de/).
Commits: <https://github.com/a-schmidtlab/opti-abrechnung/commits/main>

---

## [0.1.1] — 2026-09-15

Behebt die Fehler aus Tristans erstem Durchlauf auf einem fremden Rechner.

### Behoben

- Die Prüfungsansicht brach mit `StreamlitAPIException` ab, sobald Kontoauszug
  und Export buchungsweise übereinstimmten: Das Hakenzeichen U+2713 gilt
  Streamlit nicht als Emoji. Die Zeichen der Hinweisfelder stehen jetzt zentral
  in `darstellung.py`, und ein Test hält sie gegen Streamlits eigene Prüfung.
- Das Tool zeigte nach dem Klonen sofort einen vollständigen Bericht — gerechnet
  aus dem anonymisierten Regressionssatz unter `tests/`, der als Datenquelle
  gefunden wurde. Dieses Verzeichnis wird jetzt übergangen; ohne echte Daten
  erscheint ein Hinweis statt einer Auswertung.
- `use_container_width` durch `width="stretch"` ersetzt. Streamlit hat den
  Parameter zum 31.12.2025 abgekündigt; er wäre beim nächsten Update entfallen.

### Geändert

- Die Auswahl der Exporte ist nach Änderungsdatum sortiert, der neueste zuerst.
  Alphabetisch stand je nach Ordnername ein alter Export aus einem Unterordner
  vorn. Darunter steht jetzt, wie viele Buchungen die Datei enthält und welchen
  Zeitraum sie abdeckt.
- Einrichtungsanleitung im README: Klonen über HTTPS (ohne SSH-Schlüssel),
  `uv`-Binärdatei passend zur Architektur (Apple-Chip statt Intel) und der
  dauerhafte Eintrag von `~/.local/bin` in die Startdatei der Shell.

## [0.1.0] — 2026-09-14

Erster lauffähiger Stand: Rechenkette, Oberfläche, Nextcloud-Anbindung und
die Abrechnung Q1–Q3 2026 aus den aktuellen Exporten.

### Hinzugefügt

- Stabile Zielsystematik und Abbildung der MoneyMoney-Kategorien, einschließlich
  der Umhängung zwischen 2025 und 2026. Unbekannte Kategorien lassen den Import
  scheitern, statt stillschweigend zu verschwinden.
- CSV-Import für MoneyMoney-Kategorienexport und DKB-Umsatzliste, mit deutscher
  Zahlen- und Datumsnormalisierung und Lückenprüfung zwischen beiden Quellen.
- Rechenkette, Raumbilanz (Umlage nach Einnahmenanteil) und Fortschreibung des
  Kuratorenbudgets als reine Funktionen mit `Decimal`.
- Regressionstest gegen die Bestandsauswertung Q1–Q2 2026, Zeile für Zeile.
- Streamlit-Oberfläche mit sechs Ansichten: Quartalsbericht, Mehrjahresvergleich,
  Kuratorenbudget, Raumbilanz, Prüfung, Parameter. Jede Summe ist bis zur
  Einzelbuchung aufklappbar.
- Umschaltbare Beschriftungen (Wortwahl des Bestandsblattes oder geklärte Namen).
- Nextcloud-Ordnerfreigabe als Datenquelle, ohne hinterlegtes Konto. Passwort
  der Freigabe wird nicht gespeichert.
- Kommandozeile `opti-abrechnung` für den Vergleich neben dem alten Blatt.
- SQLite-Ablage als Modul (Import-Schnappschüsse, Beträge in Cent).
- Zeitraumbezogene Anrechnung bereits bezahlter WEG-Rechnungen, derzeit für
  Q1–Q3 2026 (36.534,66 € laut EÜR).
- Abbildung der 2026er-Blätter `Freiraum`, `WEG Rechnungen bezahlt`,
  `Rückbuchung/Kaution` und `Re diverse / Gästezimmer` als durchlaufend.

### Geändert

- Personenbezogene Unterkategorien werden über ihre Position im Kategoriepfad
  erkannt, nicht über eine Namensliste.
- Buchungskennung normiert Beträge auf zwei Nachkommastellen, damit DKB (`320`)
  und MoneyMoney (`320,00`) dieselbe Buchung treffen.
- Reihenfolge, Wortwahl und Kennzahlen der Auswertung folgen dem Bestandsblatt,
  damit sich beide nebeneinanderlegen lassen.

### Hinweise aus den Bestandsdaten

- Die EÜR Q2 und Q1–Q3 2026 rechnen die Investition Optionsraum 3 mit 174,00 €,
  MoneyMoney weist 174,90 € aus. Das Tool folgt den Buchungen.
- Die in der Planung genannte Differenz von rund 1.850 € für 2025 schrumpft auf
  etwa 1,15 € (Internetposten und Einordnung der Rückbuchungen).
- Die EÜR Q1–Q3 2026 setzt bezahlte WEG-Rechnungen mit 36.534,66 € an, die
  MoneyMoney-Kategorie summiert −43.476,24 €. Bis zur Klärung gilt der Blattwert.
