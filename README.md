# Abrechnungstool Optionsräume Spreefeld

Lokale Web-App für die Finanzauswertung der Optionsräume Bootshaus, Optionsraum 2,
Optionsraum 3 und Werkstatt. Sie liest die Exporte, die ohnehin schon erzeugt
werden — den DKB-Kontoauszug und den MoneyMoney-Kategorienexport —, rechnet daraus
den Quartalsbericht und macht jede Zahl bis auf die einzelne Bankbuchung
aufklappbar.

Die fachliche Grundlage steht in [`PLANUNG.md`](PLANUNG.md). Dieses Dokument
beschreibt, was das Tool tut und wie man es benutzt.

---

## Inhalt

1. [Zusammenfassung](#zusammenfassung)
2. [Einrichtung](#einrichtung)
3. [Datenquelle einrichten](#datenquelle-einrichten)
4. [Bedienung der sechs Ansichten](#bedienung-der-sechs-ansichten)
5. [Kommandozeile](#kommandozeile)
6. [Wie gerechnet wird](#wie-gerechnet-wird)
7. [Aufbau des Codes](#aufbau-des-codes)
8. [Tests](#tests)
9. [Was das Tool nicht tut](#was-das-tool-nicht-tut)
10. [Befunde aus den Bestandsdaten](#befunde-aus-den-bestandsdaten)
11. [Offene fachliche Fragen](#offene-fachliche-fragen)
12. [Stand und Fahrplan](#stand-und-fahrplan)
13. [Fehlersuche](#fehlersuche)

---

## Zusammenfassung

Das Tool leistet drei Dinge:

**Einnahmen und Ausgaben der Optionsräume abbilden**, getrennt je Raum und nach
den beschlossenen Kostenarten. **Die Abführung an die WEG berechnen**, also
Überschussanteil und Nebenkostenpauschale. **Das Investitionsbudget der Kuratoren
fortschreiben**, einschließlich des über die Jahre aufgelaufenen, ungenutzten
Budgets.

Der eigentliche Zweck ist dabei weniger das Rechnen als die
**Nachvollziehbarkeit**. Das langjährige Hin und Her um die Zahlen entsteht nicht
daran, dass jemand falsch rechnet, sondern daran, dass niemand schnell zeigen
kann, wie eine Zahl zustande kam. Deshalb ist jede Zeile des Berichts
aufklappbar, und deshalb tragen alle Beträge, die nicht aus einer Bankbuchung
stammen, eine Herkunftsangabe.

Der Maßstab für die Richtigkeit ist der Bestand: Das Tool reproduziert die
vorhandene Auswertung für das erste Halbjahr 2026 auf den Cent. Es erfindet keine
neue Systematik, sondern automatisiert und dokumentiert die bestehende.

**Was man an einem Nachmittag damit machen kann:** Den Nextcloud-Freigabelink mit
den Exporten einfügen, Jahr und Quartal wählen, und den Quartalsbericht auf dem
Bildschirm haben — mit der Möglichkeit, bei jeder Summe nachzusehen, welche
Buchungen darin stecken.

---

## Einrichtung

Voraussetzung ist Python 3.12 oder neuer. Die Abhängigkeiten verwaltet
[uv](https://docs.astral.sh/uv/).

### uv installieren

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Falls das nicht durchkommt, geht es auch direkt über die Binärdatei:

```bash
curl -fsSL -o /tmp/uv.tar.gz \
  https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz
tar xzf /tmp/uv.tar.gz -C /tmp
mkdir -p ~/.local/bin && mv /tmp/uv-x86_64-unknown-linux-gnu/uv* ~/.local/bin/
```

Danach muss `~/.local/bin` im Suchpfad liegen (`export PATH="$HOME/.local/bin:$PATH"`).

### Projekt einrichten und starten

```bash
git clone git@github.com:a-schmidtlab/opti-abrechnung.git
cd opti-abrechnung

uv sync --group dev        # Umgebung anlegen, Abhängigkeiten installieren
uv run pytest              # Gegenprobe: alle Tests müssen grün sein
uv run streamlit run src/optiabrechnung/oberflaeche/app.py
```

Der letzte Befehl öffnet die App im Browser, üblicherweise unter
<http://localhost:8501>. Die Daten bleiben dabei auf dem eigenen Rechner; es
läuft kein Server im Netz.

---

## Datenquelle einrichten

Das Tool kennt zwei Wege zu den Dateien. Beide sind links in der Seitenleiste
unter **Datenquelle** wählbar, und die Wahl wird für die nächste Sitzung
gemerkt.

### Weg 1: Nextcloud-Freigabelink

Der vorgesehene Regelfall, weil die Exporte laut Planung auf Nextcloud abgelegt
werden. Das Tool liest sie direkt aus einer Ordnerfreigabe — es braucht dafür
**kein Nextcloud-Konto und keine Zugangsdaten**, nur den Freigabelink.

**In Nextcloud vorbereiten:**

1. Den Ordner mit den Exporten öffnen (den mit den CSV-Dateien, nicht den
   gesamten Rechnungsbestand).
2. Rechts auf **Teilen**, dann **Link teilen** und das Plus anklicken.
3. Als Berechtigung reicht **Lesen**. Schreibrechte braucht das Tool nicht und
   soll sie nicht haben.
4. Wahlweise ein **Passwort** setzen. Bei personenbezogenen Daten ist das
   dringend zu empfehlen.
5. Den erzeugten Link kopieren.

**Im Tool eintragen:** Den Link in das Feld **Nextcloud-Freigabelink** einfügen,
gegebenenfalls das Passwort der Freigabe eintragen — nicht das eigene
Nextcloud-Passwort — und **Dateien abrufen** anklicken.

Erkannt werden alle gängigen Linkformen:

```
https://cloud.example.org/s/AbCdEf123
https://cloud.example.org/index.php/s/AbCdEf123
https://cloud.example.org/s/AbCdEf123/download
https://cloud.example.org/s/AbCdEf123?path=%2FAuswertungen
https://example.org/nextcloud/s/AbCdEf123        (Installation im Unterverzeichnis)
```

**Was dabei passiert.** Das Tool durchsucht die Freigabe bis zu drei Ebenen tief
nach CSV-Dateien und legt sie unter `daten/nextcloud/<token>/` ab. Danach
arbeitet es auf gewöhnlichen lokalen Dateien. Das hat drei Vorteile: Der
Importweg ist derselbe wie bei lokalen Dateien, es lässt sich ohne
Netzverbindung weiterarbeiten, und unveränderte Dateien werden nicht erneut
geladen — verglichen werden Größe und Änderungszeitpunkt. **Dateien abrufen**
holt jederzeit den aktuellen Stand.

Die Suchtiefe ist absichtlich begrenzt. In der Ablage liegt auch der
Rechnungsbestand mit rund 2.900 PDFs; ohne Begrenzung würde das Aufklappen
unnötig lange dauern.

### Weg 2: Lokaler Ordner

Passt für alles, was auf dem Rechner liegt — auch für einen mit dem
Nextcloud-Desktop-Client oder mit Synology Drive synchronisierten Ordner. In das
Feld **Verzeichnis** den Pfad eintragen; das Tool durchsucht ihn einschließlich
aller Unterverzeichnisse.

### Wie die Dateien erkannt werden

Nicht am Dateinamen, sondern an der Kopfzeile. Die Exporte heißen von Jahr zu
Jahr anders — `SF Optionsräume 25.csv`, `2025_Umsatzliste_WEG-Konto
Hausgeld_DE26….csv` —, die Kopfzeilen sind dagegen stabil:

| Erkennungsmerkmal | Wird gelesen als |
|---|---|
| Kopfzeile beginnt mit `Datum;` und enthält `Kategorie` | MoneyMoney-Kategorienexport |
| Datei enthält `"Buchungsdatum"` | DKB-Umsatzliste |

Der MoneyMoney-Export ist für die Auswertung nötig. Der DKB-Auszug kommt für die
Lückenprüfung hinzu und ist optional.

---

## Bedienung der sechs Ansichten

Oben in der Seitenleiste werden Datenquelle, Export, Jahr und Zeitraum gewählt.
Als Zeitraum sind das ganze Jahr, einzelne Quartale und die beiden Halbjahre
möglich.

Die Ansichten stehen in der Reihenfolge, in der auch das Bestandsblatt aufgebaut
ist: erst die Kette, dann der Mehrjahresvergleich, dann das Budget. Raumbilanz,
Prüfung und Parameter sind Zusatzsichten und stehen dahinter.

### Der Schalter „Beschriftungen wie im Bestandsbericht"

Unten in der Seitenleiste, standardmäßig eingeschaltet. Er entscheidet, wie die
Zeilen benannt werden:

| eingeschaltet | ausgeschaltet |
|---|---|
| `Buha Klier+Ott` | `Buchhaltung Klier + Ott` |
| `Material Verbrauch` | `Verbrauchskosten` |
| `Bank` | `Bankgebühren` |
| `Optionsraum 3 invest` | `Optionsraum 3 Investition` |

Eingeschaltet ist er für den **Vergleich Zeile für Zeile** gedacht: So lässt sich
die Auswertung neben das bisherige Blatt legen, ohne dass jemand Zeilen sucht.
Ausgeschaltet erscheinen die geklärten Bezeichnungen, wie sie in einen Bericht an
Spree VV gehören.

Eine Ausnahme gibt es bewusst. Der Nebenkostenposten heißt immer nach dem
tatsächlich abgedeckten Zeitraum — `Nebenkosten 1. Halbjahr 2026` — und nie
`Nebenkosten Quartal`, wie das Blatt ihn nennt. Die Beschriftung dort ist falsch,
weil der Posten den Halbjahresbetrag enthält, und für einen Bericht an Spree VV
muss sie eindeutig sein.

### Quartalsbericht

Die vollständige Rechenkette von den Einnahmen bis zur Überweisung an die WEG,
in Reihenfolge und Wortwahl des Bestandsblattes.

Oben stehen die fünf Kennzahlen der Kurzübersicht des Blattes: Einnahmen
Vermietung, Ausgaben gesamt, Überschuss gesamt, Budget Kuratoren, Überschuss &
Nebenkosten an WEG. Darunter die Kette Zeile für Zeile.

Zu „Ausgaben gesamt": Das Blatt nennt diese Zeile „Ausgaben Betrieb &
Erhaltung" und weist −36.226,91 € aus, hat aber Nebenkosten und Internet mit
darin — obwohl beide in der ausführlichen Aufstellung derselben Seite eigene
Zeilen bilden. Der Betrag wird übernommen, damit die Kurzübersichten vergleichbar
sind; benannt wird er zutreffend.

**Jede Zeile ist aufklappbar.** Ein Klick zeigt die Einzelbuchungen mit Datum,
Betrag, Auftraggeber, Verwendungszweck, IBAN, MoneyMoney-Kategorie und der
Angabe, aus welcher Zeile welcher Quelldatei sie stammt. Der Sinn ist, eine Zahl
bis zu der Zeile zurückverfolgen zu können, die im Export stand, und nicht nur
bis zu einer ähnlich aussehenden Buchung.

Zeilen, die nicht aus Buchungen stammen — Nebenkosten und Internet — zeigen beim
Aufklappen stattdessen ihre Herkunftsangabe.

Mit **⚑** markiert sind die Posten, die im Bericht ausdrücklich vorzulegen sind:
alle Investitionen, weil die Abgrenzung zur Erhaltung nicht automatisierbar ist
und prüfbar bleiben muss, und alles, was in `unklar` gelandet ist.

### Mehrjahresvergleich

Dieselbe Übersicht, die unten auf dem Bestandsblatt steht: Einnahmen, Ausgaben,
Überschuss, 50-%-Zuführung, Investitionen und Budgetrest für 2022 bis 2025, dazu
der gewählte Zeitraum aus den Buchungen gerechnet. Die Spalte **Grundlage** sagt
bei jeder Zeile, woher sie kommt.

Zwei Dinge sind beim Lesen zu wissen, und sie stehen auch in der Ansicht. Erstens
sind die Jahre 2022 bis 2025 im Blatt in ganzen Euro angegeben; daraus folgen
Unstimmigkeiten von einem Euro. Für 2023 ergeben 79.813 − 51.490 genau 28.323,
ausgewiesen sind 28.322. Das ist die Rundung des Blattes, nicht ein Fehler in der
Übernahme.

Zweitens nennt das Blatt Zuführung und Investitionen nur für 2025. Für die
übrigen Jahre sind sie hier errechnet: Die Zuführung ist der halbe Überschuss,
die Investitionen sind die Differenz zum Budgetrest. Dass die Herleitung stimmt,
zeigt 2025 — das Blatt weist dort −10.659 € aus, und genau dieser Wert kommt aus
20.134 − 30.793 heraus. **Damit wird erstmals sichtbar, wie viel in den Jahren
2022 bis 2024 tatsächlich investiert wurde:** 5.070 €, 2.561 € und 6.612,50 €.

### Raumbilanz

Pro Raum: Einnahmen getrennt nach Dauermiete und Einzelbuchung, direkt
zugeordnete Erhaltungskosten, anteilige Gemeinkosten, Deckungsbeitrag und
Investitionen. Das ist die Auswertung, die die Frage beantwortet, welcher Raum
sich trägt.

Umgelegt wird nach dem Anteil des Raums an den Gesamteinnahmen. Der Schalter
**Nebenkosten mit umlegen** entscheidet, ob die Nebenkostenpauschale mitgeht;
mit Umlage ergibt die Summe der Deckungsbeiträge genau den Überschuss.

Eine Eigenschaft des Schlüssels sollte man beim Lesen kennen, und sie steht auch
in der Ansicht: Weil proportional zu den Einnahmen verteilt wird, tragen alle
Räume denselben prozentualen Gemeinkostenblock. Unterschiede zwischen den Räumen
entstehen deshalb ausschließlich aus den direkt zugeordneten Erhaltungskosten.
Das ist kein Fehler, sondern die logische Folge des Schlüssels — die Umlage
selbst sagt nichts über die tatsächliche Kostenverursachung aus.

Die Raumbilanz ist als kalkulatorische Zusatzsicht gekennzeichnet und lässt die
offizielle Auswertung unberührt.

### Prüfung

Zwei Dinge. Erstens die vorzulegenden Posten aus dem Bericht, gesammelt an einer
Stelle.

Zweitens die **Lückenprüfung** gegen den DKB-Kontoauszug: Das Tool stellt beide
Quellen buchungsweise gegenüber und zeigt, was nur im Kontoauszug steht — also
vermutlich nicht kategorisiert ist und damit in keiner Auswertung auftaucht — und
was nur in MoneyMoney steht, typischerweise eine Zeitraumgrenze des Exports.

Der Vergleich zählt Mehrfachvorkommen mit: Zwei gleiche Beträge am selben Tag von
derselben IBAN sind zwei Buchungen und nicht eine. Ein reiner Mengenvergleich
würde solche Fälle verschlucken.

### Kuratorenbudget

Die Fortschreibung über die Jahre mit Budgetzuführung, getätigten Investitionen,
Rest und kumulierter Summe. Die Spalte **Grundlage** sagt bei jedem Jahr, ob der
Wert aus Buchungen gerechnet oder noch aus der Bestandsauswertung übernommen
ist. Für 2022 bis 2025 ist Letzteres der Fall, weil die Exporte dieser Jahre
fehlen; die Werte stehen dort in ganzen Euro.

### Parameter

Die Werte, die nicht in den Bankdaten stehen, sondern gesetzt oder beschlossen
sind: Nebenkosten und Internet je Jahr. Neben jedem Betrag steht, woher er kommt.
Ist ein Wert hergeleitet und nicht belegt, wird die Auswertung als vorläufig
gekennzeichnet.

---

## Kommandozeile

Für den schnellen Blick und für den Vergleich mit der bisherigen Auswertung, ohne
die Oberfläche zu starten:

```bash
uv run opti-abrechnung PFAD/ZUM/EXPORT.csv --jahr 2025
uv run opti-abrechnung PFAD/ZUM/EXPORT.csv --jahr 2026 --von-quartal 1 --bis-quartal 2
uv run opti-abrechnung PFAD/ZUM/EXPORT.csv --jahr 2025 --raumbilanz
uv run opti-abrechnung PFAD/ZUM/EXPORT.csv --jahr 2025 --geklaerte-beschriftung
```

Die Ausgabe folgt in Reihenfolge und Wortwahl dem Bestandsblatt, sodass sie sich
unmittelbar danebenlegen lässt. `--geklaerte-beschriftung` schaltet auf die
geklärten Bezeichnungen um.

So sieht das erste Halbjahr 2026 aus:

```
Umsätze Optionsräume · 1. Halbjahr 2026
Zeitraum 01.01.2026 bis 30.06.2026 · alle Beträge brutto
====================================================================

Einnahmen
  Bootshaus                                               8.622,32 €
  Optionsraum 2                                          14.217,39 €
  Optionsraum 3                                          21.920,93 €
  Werkstatt                                               6.426,00 €
Summe Einnahmen =========================================51.186,64 €

Betrieb & Erhaltung
  Koordination                                           −8.895,84 €
  Reinigung                                              −4.224,50 €
  Bootshaus Erhaltung                                    −1.859,43 €
  Optionsraum 2 Erhaltung                                     0,00 €
  Optionsraum 3 Erhaltung                                −1.266,66 €
  Werkstatt Erhaltung                                    −2.241,91 €
  Buha Klier+Ott                                            −78,19 €
  Material Verbrauch                                     −2.386,92 €
  Bank                                                      −27,00 €
  unklar ⚑                                                 −376,95 €
Summe Betrieb & Erhaltung ==============================−21.357,40 €

  Nebenkosten 1. Halbjahr 2026                          −13.942,75 €
  Internet Optionsräume                                    −926,76 €
Ausgaben gesamt                                         −36.226,91 €
Überschuss gesamt =======================================14.959,73 €

Investitionen Kuratoren
  50 % Überschuss für Investition Kuratoren               7.479,87 €
    Optionsraum 3 invest                                   −174,90 €
  Investitionen getätigt                                   −174,90 €
Investitionsbetrag übrig =================================7.304,97 €

Abführung an die WEG
  50 % Überschuss an WEG (netto)                         −6.285,60 €
  Nebenkosten 1. Halbjahr 2026                          −13.942,75 €
  abz. Abschläge vorige Quartale                              0,00 €
Überweisung auf Hauptkonto =============================−20.228,35 €
```

Jede Zahl des Bestandsblattes wird getroffen. Die einzige Abweichung ist
gewollt: 7.304,97 € statt 7.305,87 €, weil das Blatt dort mit 174,00 € statt
174,90 € rechnet.

---

## Wie gerechnet wird

### Die Kette

Nach der bestehenden Systematik, hier am ersten Halbjahr 2026:

| Schritt | Betrag |
|---|---|
| Einnahmen Vermietung (Bootshaus, O2, O3, Werkstatt) | 51.186,64 € |
| − Betrieb & Erhaltung | −21.357,40 € |
| − Nebenkosten des Zeitraums | −13.942,75 € |
| − Internet Optionsräume | −926,76 € |
| **= Überschuss gesamt** | **14.959,73 €** |
| davon 50 % Investitionsbudget Kuratoren (brutto) | 7.479,87 € |
| − bereits getätigte Investitionen | −174,90 € |
| **= verfügbares Budget Kuratoren** | **7.304,97 €** |
| 50 % Überschuss an WEG (netto, also ÷ 1,19) | −6.285,60 € |
| + Nebenkosten des Zeitraums | −13.942,75 € |
| − Abschläge vorige Quartale | 0,00 € |
| **= Überweisung auf Hauptkonto** | **−20.228,35 €** |

### Warum `Decimal` und keine Zwischenrundung

Gerechnet wird durchgängig mit `Decimal` in voller Genauigkeit; gerundet wird
erst bei der Ausgabe, und zwar kaufmännisch. Das ist keine Vorsicht auf Vorrat:
Der Netto-Anteil der WEG ergibt sich aus dem *ungerundeten* halben Überschuss
geteilt durch 1,19. Mit vorher auf Cent gerundeten 7.479,87 € kämen 6.285,61 €
heraus statt der ausgewiesenen 6.285,60 €.

### Die stabile Kategoriesystematik

Die Kategoriestruktur in MoneyMoney hat sich zwischen 2025 und 2026 verschoben:
`Koordination` und `Reinigung` lagen 2025 auf oberster Ebene, 2026 unterhalb von
`Betrieb & Erhaltung`. Ein Jahresvergleich ist nur möglich, wenn beide Jahre auf
dieselbe Zielsystematik abgebildet werden.

Das Tool führt deshalb eine eigene, stabile Systematik und bildet MoneyMoney
darauf ab. Zugeordnet wird in drei Schritten: erst der vollständige Pfad, dann
die Blattkategorie, dann die Strukturregel für personenbezogene
Unterkategorien. Weil auf die Blattkategorie abgebildet wird, greift die
Zuordnung unabhängig davon, wo eine Kategorie im Baum hängt.

Die Zielsystematik:

| Bereich | Inhalt |
|---|---|
| Einnahmen | je Raum, getrennt nach Dauermiete und Einzelbuchung |
| Laufende Kosten raumübergreifend | Verbrauchskosten, Reinigung, Koordination, Buchhaltung, Bankgebühren, `unklar` |
| Erhaltungskosten | je Raum, einschließlich Ersatzgeschirr |
| Internet | eigene Zeile der Kette, nicht Teil von Betrieb & Erhaltung |
| Investitionen Kuratoren | je Raum, keine laufende Ausgabe, sondern Entnahme aus dem Budget |
| Durchlaufend | Umsatzsteuer, WEG-Entnahmen, Nebenkosten-Überweisungen, Rückbuchungen, Gästezimmer |

**Unbekannte Kategorien lassen den Import scheitern.** Das ist gewollt: Eine neue
Unterkategorie, die stillschweigend unter den Tisch fällt, wäre ein Fehler, der
erst Monate später auffällt. Die Fehlermeldung nennt die Kategorie und die
Stelle, an der sie zu ergänzen ist.

Eine Ausnahme gibt es, und sie ist bewusst gesetzt: Eine unbekannte
Unterkategorie **unterhalb eines erkannten Raums** wird als Dauermieterin
gedeutet, weil der Raum im Elternsegment steht und Einzelbuchungen erkennbar
über Kategorien auf `Buchungen` laufen. So bricht ein neuer Dauermieter den
Import nicht — und es müssen keine Klarnamen im Quelltext stehen.

### Nebenkosten und Internet als Parameter

Beide Beträge stehen nicht in den Bankdaten der Auswertung, sondern werden je
Jahr gepflegt und anteilig auf den Zeitraum umgelegt. Jeder Wert trägt eine
Herkunftsangabe.

Zur Nebenkostenfortschreibung gibt es zwei Lesarten: Fortschreibung des
Vorjahreswerts um den Verbraucherpreisindex, oder Ansatz der zuletzt verfügbaren
tatsächlichen Werte. Beide bleiben abbildbar, weil der Betrag je Jahr ein
Parameter ist — bei tatsächlichen Werten wird er eingetragen, bei einer
Indexlösung aus dem Vorjahr berechnet. Der derzeitige Stand entspricht der
zweiten Lesart: Für 2026 ist der Wert aus 2024 unverändert angesetzt, ohne
Aufschlag.

Die Beschriftung nennt immer den tatsächlich abgedeckten Zeitraum. Die
Bestandsauswertung beschriftet den Posten mit „Nebenkosten Quartal", enthält aber
den Halbjahresbetrag; für einen Bericht an Spree VV muss das eindeutig sein.

### Die SQLite-Ablage

Vorhanden als Modul, in der Oberfläche noch nicht angebunden. Ihr Zweck ist
nicht die Rechengeschwindigkeit, sondern der Schnappschuss: Sie hält fest, welche
Buchungen einem bestimmten Quartalsbericht zugrunde lagen. Fragt in einem Jahr
jemand, wie eine Zahl zustande kam, lässt sie sich mit genau dem Datenstand von
damals wieder aufrufen — auch dann, wenn in MoneyMoney inzwischen Kategorien
geändert wurden.

Deshalb wird beim Import nichts überschrieben. Jeder Import ist ein eigener Lauf
mit Zeitpunkt und Prüfsumme der Quelldatei, ein Bericht verweist auf seinen Lauf,
und beim Zurücklesen wird die Zielkategorie aus den gespeicherten Merkmalen
wiederhergestellt statt neu berechnet. Beträge liegen als ganzzahlige Cent in der
Datenbank; über Gleitkommazahlen zu gehen würde die Cent-Genauigkeit aufgeben,
auf der die ganze Auswertung beruht.

---

## Aufbau des Codes

Die Trennung ist bewusst streng: Die Auswertungslogik kennt weder die Oberfläche
noch die Datenbank noch Nextcloud. Nur so lässt sie sich gegen die Bestandszahlen
automatisiert testen, und dieser Test ist das Abnahmekriterium.

| Modul | Aufgabe |
|---|---|
| `kategorien.py` | Stabile Zielsystematik, Abbildung der MoneyMoney-Kategorien |
| `einlesen.py` | CSV-Import DKB und MoneyMoney, deutsche Zahlen- und Datumsformate, Lückenprüfung |
| `parameter.py` | Gepflegte Werte je Jahr, Zeiträume, Budgetreste der Vorjahre |
| `auswertung.py` | Rechenkette, Raumbilanz, Budgetfortschreibung — reine Funktionen |
| `datenbank.py` | SQLite-Ablage mit Import-Schnappschüssen |
| `nextcloud.py` | Freigabelink zerlegen, WebDAV lesen, Zwischenspeicher |
| `einstellungen.py` | Lokale Einstellungen, damit der Link nicht jedes Mal neu eingegeben wird |
| `kommandozeile.py` | Textausgabe der Rechenkette |
| `oberflaeche/app.py` | Streamlit-Oberfläche, fünf Ansichten |
| `oberflaeche/darstellung.py` | Deutsche Zahlenformate, Tabellen für den Drilldown |

Die Zahlenformate werden von Hand gesetzt und nicht über `locale`. Eine deutsche
Locale ist auf einem beliebigen Rechner nicht garantiert vorhanden, und ein
Bericht, der auf einem Rechner Punkte und auf einem anderen Kommas setzt, wäre in
einer Diskussion über Zahlen das Letzte, was man braucht.

Bezeichner sind deutsch, aber ohne Umlaute — `ueberschuss` statt `überschuss`.
Umlaute in Bezeichnern sind in Python zulässig, machen aber bei Werkzeugen und
Tastaturbelegungen mehr Ärger als sie Lesbarkeit bringen. In Zeichenketten und
in der Oberfläche stehen sie normal.

---

## Tests

```bash
uv run pytest              # alle Tests
uv run pytest -v           # mit Namen der einzelnen Fälle
uv run ruff check .         # Stilprüfung
```

Vier Gruppen:

**`test_rechenkette.py`** — der Regressionstest gegen die Bestandsauswertung des
ersten Halbjahrs 2026. Geprüft wird nicht nur die Endsumme, sondern jede Zeile
des Kategorien-Exports einzeln: Eine stimmende Summe bei falscher Aufteilung wäre
der unangenehmere Fehler, weil er erst auffällt, wenn jemand nachfragt. Dazu
kommen die Abgrenzungen — durchlaufende Posten und Buchungen außerhalb des
Zeitraums stehen mit erheblichen Beträgen in der Testdatei und dürfen die Kette
nicht verändern.

**`test_kategorien.py`** — die Abbildung, einschließlich der Umhängung zwischen
2025 und 2026, der historischen Schreibweisen, der Strukturregel für
personenbezogene Unterkategorien und der Sicherung dagegen, dass Namen in den
Quelltext zurückkehren.

**`test_nextcloud.py`** — Linkzerlegung und WebDAV-Antwort, beides ohne
Netzzugang. Das sind die Stellen, an denen in der Praxis etwas schiefgeht.

**`test_oberflaeche.py`** — Rauchtest über Streamlits `AppTest`, der das Skript
tatsächlich ausführt. Ein HTTP-Aufruf würde nicht genügen: Der Server antwortet
auch dann mit 200, wenn das Skript beim Rendern eine Ausnahme wirft.

---

## Was das Tool nicht tut

- **Umsatzsteuer.** Läuft weiter über die Steuerkanzlei. Die USt-Buchungen werden
  erfasst und im Kontensaldo mitgeführt, gehen aber nicht in die Auswertung ein.
- **Nebenkosten-Spitzabrechnung.** Es gibt laut Beschluss nur eine
  Quartalspauschale ohne Nachberechnung in Vorjahre.
- **Buchhaltung im engeren Sinn.** Das Tool ist ein Auswertungs- und
  Controlling-Werkzeug, kein Ersatz für die Steuerkanzlei.
- **Zahlungen ausführen.** Auch im späteren Freigabeprozess für Auslagen bleibt
  die Überweisung vollständig bei der Hausverwaltung. Das Tool dokumentiert und
  gibt frei.
- **Kategorien in MoneyMoney ändern.** MoneyMoney bleibt das führende System. Das
  Tool schlägt vor und prüft, korrigiert aber nicht.

---

## Befunde aus den Bestandsdaten

### Ein Zahlendreher von 90 Cent

Die EÜR-Seite rechnet `7.479,87 − 174,00 = 7.305,87 €`, der Kategorien-Export
weist die Investition aber mit **174,90 €** aus (Optionsraum 3 invest).
Rechnerisch richtig sind **7.304,97 €**. Festgehalten in
`test_verfuegbares_budget_weicht_um_90_cent_vom_bestand_ab`, damit die Abweichung
nicht als Fehler des Tools missverstanden wird.

### Die 1.850-€-Differenz für 2025 schrumpft auf etwa 1,15 €

Für 2025 verblieb zwischen der Summe der Kategorien und den ausgewiesenen
−74.875 € eine unerklärte Differenz von rund 1.850 €. Der Lauf gegen den echten
Export löst sie fast vollständig auf:

| | Betrag |
|---|---|
| Ausgaben aus den Kategorien (Betrieb & Erhaltung, Koordination, Reinigung) | −40.688,23 € |
| Nebenkosten-WEG-Buchungen | −32.335,54 € |
| Internet, aus dem Halbjahresbetrag 2026 auf das Jahr gerechnet | −1.853,52 € |
| **Summe** | **−74.877,29 €** |
| ausgewiesen in der EÜR | −74.875 € |
| **Rest** | **2,29 €** |

Auf der Einnahmenseite bleibt eine Differenz von 278,86 € (136.182,14 € gegen
ausgewiesene 136.461 €), die sich mit den Rückbuchungen über 280,00 € deckt — das
Tool behandelt sie als durchlaufend, die Bestandsauswertung hat sie offenbar als
Einnahme geführt. Beides zusammen gerechnet bleibt ein unerklärter Rest von etwa
**1,15 €**.

Damit sind aus einer diffusen Frage zwei kleine, benannte geworden: Gehören die
Rückbuchungen in die Einnahmen, und woher kommt der letzte Euro? Die
Investitionen stimmen unabhängig davon auf den Cent (−10.659,33 € gegen
ausgewiesene −10.659 €).

---

## Offene fachliche Fragen

Diese Fragen kann das Tool nicht beantworten. Es macht sie sichtbar und bleibt
so gebaut, dass beide Antworten abbildbar sind.

- **Brutto/Netto-Mischung.** Der Überschuss wird brutto gerechnet, der 50-%-Anteil
  an die WEG aber netto abgeführt, der Kuratorenanteil bleibt brutto. Die
  Kuratoren erhalten dadurch effektiv einen um 19 % höheren Anteil als die WEG.
  Ist das so gewollt? Bis zur Klärung rechnet das Tool den Bestand unverändert
  nach, denn der Bestand ist der Maßstab des Regressionstests.
- **Fortschreibung der Nebenkosten.** Verbraucherpreisindex oder zuletzt
  verfügbare tatsächliche Werte. Beides ist als Parameter abbildbar.
- **Gesonderte BK-Abrechnung der Räume** oder Behandlung wie Verkehrsflächen.
- **Umsatzsteuerpflicht der WEG als Ganzes** oder nur des Betriebs der Räume.
- **Rückbuchungen:** Einnahme oder durchlaufend? Siehe oben.
- **Freigabebefugnis und Betragsgrenze** bei Auslagenerstattungen, und ob die
  Hausverwaltung das Verfahren mitträgt.

---

## Stand und Fahrplan

**Umgesetzt.** Kategoriesystematik und Abbildung, CSV-Import für beide Quellen mit
Lückenprüfung, Rechenkette mit Regressionstest, Mehrjahresvergleich, Raumbilanz
mit Gemeinkostenumlage, Budgetfortschreibung, Streamlit-Oberfläche mit Drilldown
und umschaltbaren Beschriftungen, Nextcloud-Anbindung, Kommandozeile,
SQLite-Ablage als Modul.

**Für das Treffen.** Reihenfolge, Wortwahl und Kennzahlen folgen dem
Bestandsblatt, sodass sich beide Auswertungen nebeneinanderlegen lassen. Jede
Zahl der beiden Referenz-PDFs wird getroffen.

**Als Nächstes.** PDF-Export des Quartalsberichts, sodass er ohne Nacharbeit an
Spree VV gehen kann. Anbindung der SQLite-Ablage an die Oberfläche, damit
Berichte als Schnappschuss festgeschrieben werden.

**Wofür Daten fehlen.** Der Mehrjahresvergleich 2022–2024 braucht die Exporte
dieser Jahre. Für 2026 fehlt der MoneyMoney-Export; die Rechenkette ist deshalb
gegen eine anonymisierte Referenzdatei mit den Kategoriesummen aus dem Q2-PDF
getestet und nicht gegen den echten Export.

**Später.** Auswertung der rund 2.900 Rechnungs-PDFs, Offene-Posten-Liste,
Ausfallquote getrennt nach echten Ausfällen und Kulanzentscheidungen,
Auslagenerstattungen mit zweistufiger Freigabe.

---

## Fehlersuche

**„MoneyMoney-Kategorie … ist der Zielsystematik nicht zugeordnet."** Eine neue
Unterkategorie ist aufgetaucht. Das ist gewollt und kein Absturz. Die Kategorie
in `ABBILDUNG` in `src/optiabrechnung/kategorien.py` ergänzen — die Meldung nennt
den Namen. Wenn es eine neue Dauermieterin ist, sollte sie eigentlich automatisch
erkannt werden; dann liegt die Kategorie vermutlich nicht direkt unterhalb ihres
Raums.

**„Keine Parameter für 2024 gepflegt."** Für den Mehrjahresvergleich fehlen die
Nebenkostenbeträge dieser Jahre. In `PARAMETER_JE_JAHR` in
`src/optiabrechnung/parameter.py` ergänzen, mit Herkunftsangabe.

**„Die Freigabe ist passwortgeschützt."** Das Passwort der Freigabe eintragen,
nicht das eigene Nextcloud-Passwort.

**„Das ist der Link auf deine eigene Dateiansicht, keine Freigabe."** Ein Link
der Form `…/apps/files/?dir=…` funktioniert nicht, weil er ein angemeldetes Konto
voraussetzt. In Nextcloud über **Teilen → Link teilen** einen Freigabelink
erzeugen.

**Kein MoneyMoney-Export gefunden.** Die Datei muss eine CSV mit der Kopfzeile
`Datum;Wertstellung;Kategorie;…` sein. In MoneyMoney wird sie über den Export der
Kategorien erzeugt, nicht über den einfachen Umsatzexport.

**Die Oberfläche zeigt alte Zahlen.** Streamlit hält eingelesene Dateien im
Zwischenspeicher. Im Menü oben rechts **Clear cache** wählen und neu laden. Bei
Nextcloud-Daten zusätzlich **Dateien abrufen**.

**`uv: command not found`.** `~/.local/bin` liegt nicht im Suchpfad. Siehe
[Einrichtung](#einrichtung).
