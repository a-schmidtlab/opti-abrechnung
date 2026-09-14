# Abrechnungstool Optionsräume Spreefeld

Stand: 7.9.2026, Fassung 2 · Grundlage: Protokoll Finanzcontrolling-Treffen vom 29.6.2026 (Axel, Tristan, Henrike), Auswertungen 2025 und Q1–Q2 2026, Rechnungsbestand 2016–2026

Diese Fassung arbeitet Henrikes Rückmeldung vom 7.9.2026 ein. Geändert haben sich: die Einordnung des Ersatzgeschirrs (Abschnitt 4), der Verteilungsschlüssel für Gemeinkosten und die Erfassung von Mietausfällen (Abschnitt 6), das Verständnis der Nebenkostenfortschreibung (Abschnitt 8) sowie ein neuer Abschnitt 7 zum Freigabeprozess für Belege und Auslagenerstattungen.

---

## 1. Ziel und Abgrenzung

Das Tool soll die Finanzauswertung der Optionsräume so weit vereinheitlichen, dass alle Beteiligten auf dieselbe Zahlenbasis schauen. Konkret leistet es drei Dinge:

1. **Einnahmen und Ausgaben der Optionsräume abbilden** — pro Raum getrennt, nach den im Protokoll festgelegten Kostenarten.
2. **Die Abführung an die WEG berechnen** — Überschussanteil und Nebenkostenpauschale.
3. **Das Investitionsbudget der Kuratoren fortschreiben** — inklusive des über die Jahre aufgelaufenen, ungenutzten Budgets.

Der eigentliche Zweck ist dabei weniger das Rechnen als die **Nachvollziehbarkeit**: Jede Zahl im Quartalsbericht soll per Klick bis auf die einzelne Bankbuchung aufklappbar sein. Das langjährige Hin und Her entsteht nicht daran, dass jemand falsch rechnet, sondern daran, dass niemand schnell zeigen kann, wie eine Zahl zustande kam.

**Bewusst außerhalb des Tools:**

- **Umsatzsteuer.** Läuft weiter über Klier + Ott. Die USt-Buchungen auf dem Konto werden erfasst und im Kontensaldo mitgeführt, aber nicht in die Auswertung einbezogen — sonst doppelte Arbeit.
- **Nebenkosten-Spitzabrechnung.** Es gibt laut Beschluss nur noch eine Quartalspauschale ohne Nachberechnung in Vorjahre.
- **Buchhaltung im engeren Sinn.** Das Tool ist ein Auswertungs- und Controlling-Werkzeug, kein Ersatz für die Steuerkanzlei.

---

## 2. Was ich in den Bestandsdaten gefunden habe

### 2.1 Die vorhandene Rechenlogik geht exakt auf

Ich habe die Q2-2026-Auswertung aus dem Kategorien-Export nachgerechnet. Die Kette stimmt auf den Cent:

| Schritt | Betrag |
|---|---|
| Einnahmen Vermietung (BH + O2 + O3 + Werkstatt) | 51.186,64 € |
| − Betrieb & Erhaltung | −21.357,40 € |
| − Nebenkosten Halbjahr | −13.942,75 € |
| − Internet Optionsräume | −926,76 € |
| **= Überschuss gesamt** | **14.959,73 €** |
| davon 50 % Investitionsbudget Kuratoren (brutto) | 7.479,87 € |
| − bereits getätigte Investitionen | −174,90 € |
| **= verfügbares Budget Kuratoren** | **7.305,87 €** |
| 50 % Überschuss an WEG (netto, also ÷ 1,19) | −6.285,60 € |
| + Nebenkosten Halbjahr | −13.942,75 € |
| **= Überweisung an WEG** | **−20.228,35 €** |

Auch die Budget-Fortschreibung ließ sich verifizieren: 12.260 + 11.600 + 19.213 + 20.134 + 7.305 = 70.512 €, das ausgewiesene ungenutzte Budget 2022–2026.

**Das ist die wichtigste Erkenntnis für die Planung.** Es geht nicht darum, eine neue Systematik zu erfinden — die bestehende funktioniert. Das Tool automatisiert und dokumentiert sie, und der Bestand dient als Regressionstest: Wenn das Tool für Q2 2026 nicht dieselben Zahlen ausspuckt, ist das Tool falsch.

### 2.2 Die Kategorien haben sich zwischen 2025 und 2026 verschoben

In der MoneyMoney-Struktur 2025 sind `Koordination` und `Reinigung` Kategorien auf oberster Ebene. In der Auswertung Q2 2026 stehen sie unterhalb von `Betrieb & Erhaltung`. Ebenso sind 2026 Kategorien hinzugekommen, die es 2025 noch nicht gab (`Bootshaus Erhaltung`, `Optionsraum 3 invest`, `Bootshaus invest`).

Für einen Jahresvergleich ist das ein echtes Problem: Zwei Jahre lassen sich nur nebeneinanderstellen, wenn beide auf dieselbe Zielsystematik abgebildet werden. Das Tool braucht deshalb eine **eigene, stabile Kategorie-Definition** und eine Mapping-Tabelle, die MoneyMoney-Kategorienamen (in allen historischen Schreibweisen) darauf abbildet. Neue, unbekannte MoneyMoney-Kategorien müssen als Fehler auffallen und nicht stillschweigend unter den Tisch fallen.

### 2.3 Die Einnahmen liegen teils auf personenbezogenen Unterkategorien

Die Dauermieter haben in MoneyMoney eigene Unterkategorien, jeweils unterhalb ihres Raums und auf den Namen der Mieterin lautend — fünf unter `Optionsraum 2`, eine unter `Bootshaus`. Die Einzelbuchungen laufen dagegen über `- O2 Buchungen`, `- BH Buchungen` bzw. direkt über `Optionsraum O3`. (Die Klarnamen sind hier durch diese Beschreibung ersetzt, weil dieses Dokument in einem öffentlichen Repository liegt; sie stehen in den Rohdaten.)

Für die Raumzuordnung muss also über die Unterkategorien hinweg aggregiert werden. Zugleich ist die Aufteilung nützlich: Der Anteil Dauermiete vs. Einzelbuchung pro Raum ist eine Kennzahl, die für die Auslastungsdiskussion interessant ist — nicht zuletzt, weil die 50/50-Regel aus dem Protokoll ausdrücklich auf die schwächer ausgelasteten Räume (O2, Bootshaus) verweist.

### 2.4 Der Rechnungsbestand ist umfangreich, aber uneinheitlich

Rund 2.900 PDFs von 2016 bis 2026. Zwei Namensschemata: bis 2020 `SFB-JJMMTT-RG-<Nr>-<Raum>.pdf`, ab 2021 `Rechnung-<Nr>-<raum>.pdf`. Der Raum steckt als Suffix im Dateinamen (`o2`, `o3`, `bh`, `div`, `gz`).

Der Bearbeitungsstand steckt in der Ordnerstruktur, die aber pro Jahr variiert (`3. bezahlt` vs. `4. bezahlt`, `0. neu`, `1. Mahnung 26.07`, `5. bleibt unbezahlt`, `4. Storno`, `zzz neu buchen`). Zusätzlich tragen viele Dateinamen freien Kommentartext, der de facto Sachstand dokumentiert — etwa *„hat nur 25% bezahlt trotz Gewerbenutzung"*, *„angeblich storniert, und pleite"*, *„ukrainische Geflüchtete, kein Geld"*.

Diese Information ist wertvoll und darf nicht verlorengehen, ist aber in Dateinamen strukturell nicht auswertbar. Das ist das Kernargument dafür, die Rechnungsseite in Phase 2 zu überführen: nicht um Ordnung um der Ordnung willen, sondern damit Ausfälle und Kulanzentscheidungen quantifizierbar werden.

Die Rechnungs-PDFs selbst sind sauber maschinenlesbar. Eine Beispielrechnung enthält Rechnungsnummer, Buchungsnummer, Raum und Tageszeit, Datum und Dauer, Grundbetrag, Rabatt, Gesamtbetrag und MwSt. Insbesondere der **Rabatt** ist eine Größe, die bisher nirgends ausgewertet wird, für die Diskussion über die Preisgestaltung aber zentral sein dürfte.

---

## 3. Architektur

Entschieden ist: **lokale Web-App in Python (Streamlit)**, Daten bleiben lokal auf dem Synology-Drive, Nutzung durch Axel, Tristan und Henrike.

**In Worten, ohne Technik:** Das Tool liest die Dateien, die Tristan ohnehin schon exportiert — den Kontoauszug der DKB und den Kategorien-Export aus MoneyMoney. Es rechnet nichts von Hand nach, sondern übernimmt die Buchungen unverändert und legt sie in einer eigenen Ablage ab. Diese Ablage ist der entscheidende Punkt: Sie hält fest, welche Buchungen einem bestimmten Quartalsbericht zugrunde lagen. Wenn also in einem Jahr jemand fragt, wie die Zahl im Bericht für Q2 2026 zustande kam, lässt sie sich mit genau dem Datenstand von damals wieder aufrufen — auch dann, wenn in MoneyMoney inzwischen Kategorien geändert wurden. Aus dieser Ablage werden die Auswertungen berechnet und als Bildschirmansicht sowie als PDF ausgegeben.

Die technische Darstellung darunter ist für die Umsetzung gedacht und muss beim Lesen des Plans nicht nachvollzogen werden.

```
Rohdaten (Nextcloud/SynologyDrive, unverändert)
    │
    ├── DKB-Kontoauszug CSV
    ├── MoneyMoney-Export CSV (mit Kategorien)
    ├── Rechnungs-PDFs                    ← Phase 2
    ├── Koordinations- und Auslagenbelege ← Phase 2
    │
    ▼
Import & Normalisierung
    - Parsen, deutsche Zahlen-/Datumsformate
    - Kategorie-Mapping auf stabile Zielsystematik
    - Dublettenerkennung zwischen DKB und MoneyMoney
    │
    ▼
SQLite-Datenbank (eine Datei, versionierbar, kein Server)
    - buchungen, kategorien, mapping, regeln
    - parameter (NK-Pauschale, VPI, Verteilungsschlüssel)
    - rechnungen                          ← Phase 2
    │
    ▼
Auswertungslogik (reine Python-Funktionen, testbar)
    - Raumbilanz · Kostenarten · Überschuss
    - WEG-Abführung · Kuratorenbudget · Budgetfortschreibung
    │
    ▼
Streamlit-Oberfläche + Export
    - Dashboard, Drilldown bis zur Einzelbuchung
    - Kategorisierungs-Prüfung
    - PDF-/Excel-Quartalsbericht für Spree VV und Beirat
```

**Warum SQLite und nicht direkt aus den CSVs rechnen:** Die Nachvollziehbarkeit verlangt, dass ein einmal erstellter Quartalsbericht reproduzierbar bleibt, auch wenn später Kategorien in MoneyMoney korrigiert werden. Mit einer Datenbank lässt sich festhalten, welcher Datenstand einem Bericht zugrunde lag. Die Datei liegt im Drive und ist damit automatisch gesichert.

**Warum die Auswertungslogik strikt von der Oberfläche getrennt ist:** Damit sie gegen die Bestandszahlen automatisiert getestet werden kann. Wenn Q2 2026 auf den Cent reproduziert wird, ist das ein belastbares Argument in der Diskussion mit dem Beirat.

**Technikstack:** Python 3.12, pandas, Streamlit, SQLite, pdfplumber (Phase 2), reportlab oder WeasyPrint für den PDF-Export, pytest für die Regressionstests.

---

## 4. Kategoriesystematik

Nach Protokoll, mit den Kategorien aus 2025/2026 abgeglichen:

### Einnahmen — je Raum
Bootshaus · Optionsraum 2 · Optionsraum 3 · Werkstatt

Zuordnungsregeln bei Mehrraumbuchungen (aus dem Protokoll): Die Rechnung wird bei dem Raum verbucht, für den die Nutzungsgebühr höher ist. Bei 50/50 beim schwächer ausgelasteten Raum, also O2 oder Bootshaus.

### Laufende Kosten — raumübergreifend
**Verbrauchskosten** (Glühbirnen, Klopapier und Ähnliches) · **Reinigung** · **Koordination** · **Buchhaltung Klier + Ott** · **Bankgebühren** · **Internet**

### Laufende Kosten — je Raum
**Erhaltungskosten**: alles, was den Stand der Räume erhält — Sägeblätter, Beamer, Boxen, Ersatz für den geklauten Akkuschrauber, **Ersatzgeschirr**.

Das Ersatzgeschirr stand im Protokoll noch bei den Verbrauchskosten. Nach Henrikes Einwand gehört es hierher: Es ist vergleichsweise teures Material, das sich klar einem Raum zuordnen lässt, und ist damit den Sägeblättern näher als dem Klopapier. Die Trennlinie zwischen beiden Kategorien ist damit auch besser beschreibbar — raumübergreifend sind die Verbrauchsgüter, bei denen eine Zuordnung weder möglich noch den Aufwand wert wäre.

### Investitionen — je Raum
Alles, was im Budget der Optionsräume erfasst war und aus den bei den Optionsräumen verbleibenden Geldern der Vorjahre bezahlt wird. **Keine laufende Ausgabe**, sondern Entnahme aus dem Kuratorenbudget.

### Durchlaufend / nicht in der Auswertung
Umsatzsteuer · WEG-Entnahmen und -Umbuchungen · Nebenkosten-Überweisungen an die WEG · Rückbuchungen · Gästezimmer

Die Abgrenzung **Erhaltung vs. Investition** ist die einzige inhaltlich schwierige und muss beim Buchen entschieden werden. Das Tool kann sie nicht automatisch treffen, aber es kann sie sichtbar machen: eine Liste aller so gebuchten Vorgänge im Quartalsbericht, damit die Einordnung geprüfbar bleibt statt unbemerkt zu passieren.

Weitere Unterkategorien sind zulässig, müssen sich aber laut Protokoll eindeutig einer der obigen Kategorien zuordnen lassen. Das Tool erzwingt genau das: Jede Unterkategorie braucht eine Zuordnung, sonst schlägt der Import fehl.

---

## 5. Der Kategorisierungs-Assistent (Hybrid-Ansatz)

Entschieden ist der Hybrid-Weg: **MoneyMoney bleibt führendes System**, das Tool schlägt Kategorien vor und prüft auf Fehler und Lücken. Das ist die risikoärmste Variante, weil Tristans eingespielter Arbeitsablauf unangetastet bleibt und das Tool sich erst beweisen muss.

Das Tool importiert beide CSVs und gleicht sie ab:

**Lückenprüfung.** Buchungen, die in der DKB-CSV stehen, aber im MoneyMoney-Export fehlen (oder umgekehrt) — typischerweise Zeitraumgrenzen oder vergessene Kategorisierungen.

**Regelbasierte Vorschläge.** Aus den 2025er-Daten lassen sich stabile Muster ableiten: IBAN und Auftraggeber sind bei Dauermietern eindeutig, Verwendungszwecke enthalten oft die Rechnungsnummer oder den Raumnamen. Für jede Buchung schlägt das Tool eine Kategorie vor.

**Abweichungsanzeige.** Wo Vorschlag und MoneyMoney-Kategorie auseinandergehen, zeigt das Tool das an — als Frage, nicht als Korrektur. Meist wird MoneyMoney recht haben; die Fälle, in denen nicht, sind genau die interessanten.

**Plausibilitätsprüfungen.** Einnahmen ohne zugehörige Rechnung, Beträge, die stark vom Muster des Dauermieters abweichen, Buchungen in `unklar` (Q2 2026: 376,95 €), unbekannte Kategorien.

Erst wenn die Trefferquote über mehrere Quartale überzeugt, lässt sich sinnvoll darüber reden, ob MoneyMoney überhaupt noch gebraucht wird. Diese Entscheidung gehört nicht in die Planung, sondern ans Ende von Phase 1.

---

## 6. Auswertungen

### Quartals- und Jahresbericht
Die vollständige Kette aus Abschnitt 2.1, aufklappbar bis zur Einzelbuchung. Formatiert als PDF, das ohne Nacharbeit an Spree VV und den Beirat gehen kann.

### Raumbilanz
Pro Raum: Einnahmen (getrennt nach Dauermiete und Einzelbuchung), direkt zugeordnete Erhaltungskosten, anteilige Gemeinkosten, Investitionen, Deckungsbeitrag. Dies ist die Auswertung, die die Frage beantwortet, welcher Raum sich trägt — und damit die Grundlage für die Diskussion, warum O2 und Bootshaus die 50/50-Sonderregel bekommen.

**Verteilungsschlüssel für die Gemeinkosten:** nach dem Anteil des Raums an den Gesamteinnahmen, wie von Henrike vorgeschlagen. Reinigung, Koordination und Verbrauchskosten werden also im Verhältnis der Einnahmen auf die vier Räume umgelegt. Der Schlüssel ist einfach zu erklären, braucht keine zusätzlichen Daten und ist nicht angreifbar — ein wesentlicher Vorteil gegenüber einer Umlage nach Fläche, bei der sofort die Frage nach der richtigen Flächendefinition aufkäme.

Eine Eigenschaft dieses Schlüssels sollte man beim Lesen der Raumbilanz kennen: Weil die Gemeinkosten proportional zu den Einnahmen verteilt werden, tragen alle Räume denselben prozentualen Gemeinkostenblock. Unterschiede zwischen den Räumen entstehen deshalb ausschließlich aus den direkt zugeordneten Erhaltungskosten und Investitionen. Das ist kein Fehler, sondern die logische Folge des Schlüssels — es heißt nur, dass die Umlage selbst nichts über die tatsächliche Kostenverursachung aussagt. Sobald in Phase 3 die Nutzungsstunden aus den Buchungsdaten vorliegen, lässt sich eine zweite Sicht nach Nutzungsstunden danebenstellen. Gerade die Reinigung dürfte eher mit der Nutzung als mit dem Umsatz skalieren, und die Differenz zwischen beiden Sichten wäre dann selbst eine interessante Information.

Die Umlage ist in jedem Fall als kalkulatorische Zusatzsicht gekennzeichnet und lässt die offizielle Auswertung nach Abschnitt 2.1 unberührt.

### Mietausfälle und Ausfallquote
Erfassung der uneinbringlichen Forderungen je Jahr und Raum, mit Ausweis der Ausfallquote in Prozent der gestellten Rechnungen. Henrikes Argument dafür ist überzeugend: Bei Gewerbevermietung kalkuliert man Mietausfälle grundsätzlich ein, und wenn wir sie für die zurückliegenden Jahre quantifizieren können, wissen wir, mit welchem Prozentsatz wir künftig planen sollten.

Die Datengrundlage dafür ist vorhanden — der Ordner `5. bleibt unbezahlt` reicht bis 2022 zurück —, aber sie liegt in Dateinamen statt in auswertbaren Feldern. Die Auswertung setzt deshalb die Rechnungserfassung aus Phase 2 voraus. Sinnvoll ist zudem, zwischen echten Ausfällen (Insolvenz, keine Reaktion) und bewussten Kulanzentscheidungen zu unterscheiden: Beides steht heute unterschiedslos im selben Ordner, ist betriebswirtschaftlich aber grundverschieden. Nur der erste Teil ist eine Ausfallquote, der zweite ist eine Förderentscheidung und sollte auch als solche sichtbar werden.

### Kuratorenbudget
Fortschreibung über die Jahre: Budgetzuführung je Jahr (50 % Überschuss), getätigte Investitionen, Rest. Kumuliert ergibt das die 70.512 €, die derzeit als ungenutztes Budget 2022–2026 ausgewiesen sind. Diese Zahl ist politisch relevant genug, dass ihre Herleitung transparent sein sollte.

### Mehrjahresvergleich
2022–2026 auf einheitliche Kategorien normalisiert — Einnahmen, Ausgaben, Überschuss je Jahr und Raum.

---

## 7. Freigabeprozess für Belege und Auslagenerstattungen

Henrikes Einwand: Auslagenerstattungen dürfen nicht ohne Prüfung innerhalb des Kuratoren- und Koordinatorenteams an die Hausverwaltung gehen. Ihr Vorschlag ist ein zweistufiges Verfahren, wie es die eG bei den Buchungen auf dem Umweltbankkonto hatte — intern freigeben und die Belege hinterlegen, die HV bekommt dann den Hinweis, dass Buchungen zur Freigabe bereitstehen.

Das lässt sich gut im Tool abbilden. Vorschlag für den Ablauf:

**Stufe 1 — Erfassung.** Wer eine Auslage hatte, legt sie im Tool an: Betrag, Datum, Zweck, betroffener Raum, Kategorie (Verbrauch, Erhaltung oder Investition) und der Beleg als Scan oder Foto. Ohne angehängten Beleg lässt sich der Antrag nicht abschicken.

**Stufe 2 — Interne Freigabe im Vier-Augen-Prinzip.** Eine zweite Person aus dem Team prüft sachlich und gibt frei. Antragsteller und Prüfer dürfen nicht dieselbe Person sein — das erzwingt das Tool. Die Freigabe wird mit Person und Zeitpunkt protokolliert und ist später nicht mehr stillschweigend änderbar.

**Stufe 3 — Übergabe an die Hausverwaltung.** Freigegebene Anträge werden gesammelt und als eine PDF-Freigabeliste mit den zugehörigen Belegen an vabene übermittelt. Bewusst niedrigschwellig: Die HV soll nicht unser Tool bedienen müssen, sie bekommt eine Liste, die sie abarbeiten kann. Die eigentliche Überweisung bleibt vollständig bei der HV — das Tool führt keine Zahlungen aus, es dokumentiert und gibt frei.

**Stufe 4 — Rückkopplung aus dem Kontoauszug.** Hier liegt der eigentliche Mehrwert gegenüber einer Lösung auf Papier: Das Tool liest den Kontoauszug ohnehin ein und kann die Erstattung automatisch wiederfinden und dem Antrag zuordnen. Damit schließt sich der Kreis, und es wird sichtbar, wenn eine freigegebene Erstattung nach Wochen immer noch nicht ausgeführt ist oder wenn umgekehrt eine Abbuchung erfolgt, zu der es keinen freigegebenen Antrag gibt. Genau diese beiden Fälle sind heute praktisch nicht auffindbar.

Zwei Dinge sind dafür noch zu klären, beide organisatorisch und nicht technisch: Wer im Team hat Freigabebefugnis, und gibt es eine Betragsgrenze, oberhalb derer nicht die Zweitprüfung genügt, sondern eine Entscheidung des Kuratorenteams nötig ist? Und: Das Verfahren muss mit vabene abgestimmt werden, sonst läuft die Freigabeliste ins Leere.

---

## 8. Offene Punkte

Diese Fragen kann das Tool nicht beantworten; sie müssen fachlich geklärt werden, bevor die Logik festgeschrieben wird.

**Durch Henrikes Rückmeldung erledigt:** Die Einordnung des Ersatzgeschirrs ist entschieden (Abschnitt 4), der Verteilungsschlüssel für die Gemeinkosten steht (Abschnitt 6), und die Erfassung der Mietausfälle ist beschlossen statt nur angefragt (ebenfalls Abschnitt 6). Diese drei Punkte sind aus der Liste unten herausgefallen.

**Aus dem Protokoll noch offen (Henrike klärt):**

- Gibt es eine gesonderte BK-Abrechnung der Räume, oder werden sie wie Verkehrsflächen behandelt und in die BK-Abrechnung aller Einheiten eingepreist?
- Ist die WEG als Ganzes umsatzsteuerpflichtig und kann aus allen Rechnungen anteilig MwSt ziehen — oder fließt allein der Betrieb der O'Räume in die Umsatzsteuererklärung? Davon hängt ab, ob es sinnvoll ist, Ausgaben für den Freiraum über das Optionsraumkonto laufen zu lassen, wo sie eigentlich nicht hingehören.

**Aus der Datenanalyse neu aufgetaucht:**

- **Brutto/Netto-Mischung.** Der Überschuss wird brutto gerechnet, der 50-%-Anteil an die WEG aber netto abgeführt (7.479,87 ÷ 1,19 = 6.285,60). Der Kuratorenanteil bleibt brutto. Ist das so gewollt? Es ist eine Entscheidung mit realer Wirkung: Die Kuratoren erhalten effektiv einen um 19 % höheren Anteil als die WEG.

- **Fortschreibung der Nebenkosten.** Hier gibt es zwei unterschiedliche Lesarten, die vor der Umsetzung zusammengeführt werden müssen. Im Protokoll steht, die Zahlen der letzten Ablesung würden für das Folgejahr um den Verbraucherpreisindex erhöht. Henrike hat es dagegen so verstanden, dass ab Beginn des Folgejahres immer die zuletzt verfügbaren tatsächlichen Werte angesetzt werden — dann zahlen wir im Grunde genau den richtigen Betrag, nur ein bis zwei Jahre später. Das ist ein sauberer Ansatz, weil er sich über die Jahre selbst korrigiert und keine Indexdiskussion erfordert; er setzt aber voraus, dass sich die tatsächlichen Kosten der Räume überhaupt genau ermitteln lassen. Henrike klärt das zusammen mit der BK-Frage. Der derzeitige Stand entspricht bereits ihrer Lesart: In Q1–Q2 2026 ist der 2024er-Wert unverändert angesetzt (27.885,50 ÷ 2 = 13.942,75), ohne VPI-Aufschlag. Das Tool wird die Nebenkosten so oder so als gepflegten Parameter je Jahr führen, sodass beide Varianten abbildbar bleiben — bei tatsächlichen Werten wird der Betrag eingetragen, bei einer Indexlösung aus dem Vorjahreswert berechnet.

- **Bezeichnung „Nebenkosten Quartal".** Der Posten ist in der Q2-Auswertung mit „Quartal" beschriftet, enthält aber den Halbjahresbetrag. Für einen Bericht an Spree VV sollte die Beschriftung eindeutig sein.

- **Abstimmung 2025.** Für Q2 2026 geht die Rechnung exakt auf. Für 2025 verbleibt zwischen der Summe der Kategorien und den ausgewiesenen −74.875 € eine Differenz von rund 1.850 €. Vermutlich Internet und Abgrenzungen, aber das gehört vor dem Produktivstart geklärt — eine unerklärte Differenz in den Vergleichszahlen ist genau die Sorte Detail, an der Diskussionen wieder aufbrechen.

- **Freigabebefugnis und Betragsgrenze bei Auslagen.** Siehe Abschnitt 7 — wer darf freigeben, ab welchem Betrag braucht es eine Entscheidung des Kuratorenteams, und ist vabene bereit, das Verfahren mitzutragen?

---

## 9. Vorgehen in Phasen

### Phase 0 — Anschauungsbeispiel für das Treffen

Henrike hat angeregt, den Lösungsansatz beim Treffen möglichst mit einer echten Auswertung zu veranschaulichen. Das ist gut machbar und aus meiner Sicht auch der wirksamste Teil der Präsentation: Eine Systematik zu erklären überzeugt weniger als zu zeigen, dass die Zahlen des letzten Quartalsberichts auf Knopfdruck und auf den Cent genau herauskommen.

Vorgesehen ist deshalb ein schmaler Durchstich auf Basis der bereits vorliegenden 2025er-Daten: Import des MoneyMoney-Exports, die Rechenkette aus Abschnitt 2.1, eine Raumbilanz und der Drilldown von einer Summe bis auf die einzelne Bankbuchung. Bewusst ohne Feinschliff — es geht darum, das Prinzip sichtbar zu machen, nicht um ein fertiges Werkzeug.

Für den Ablauf des Treffens schlage ich vor, dass wir zunächst kurz vorstellen, was wir zu dritt besprochen haben, und ich im Anschluss den Lösungsansatz anhand dieser Auswertung erläutere.

### Phase 1 — Auswertung der Bankdaten (der Kern)

Ziel: Ein Quartalsbericht, der ohne Nacharbeit an Spree VV gehen kann, und der die Bestandszahlen exakt reproduziert.

1. Kategorie-Systematik und Mapping-Tabelle festlegen — gemeinsam mit Tristan, da er die Buchungspraxis kennt
2. CSV-Import für DKB und MoneyMoney, Normalisierung, SQLite-Ablage
3. Auswertungslogik als getestete Python-Funktionen
4. **Regressionstest gegen 2025 und Q1–Q2 2026** — dieser Schritt ist die Abnahme
5. Streamlit-Oberfläche: Dashboard, Drilldown, Kategorisierungs-Prüfung
6. PDF-Export des Quartalsberichts
7. Historische Jahre 2022–2024 nachladen für den Mehrjahresvergleich

Der Regressionstest steht bewusst vor der Oberfläche. Solange die Zahlen nicht stimmen, ist jede Oberfläche wertlos.

### Phase 2 — Rechnungswesen

Ziel: Die Rechnungsprüfung wandert vom Beirat ins O'Team, wie im Protokoll vorgesehen.

1. PDF-Extraktion: Rechnungsnummer, Datum, Buchungsnummer, Raum, Kunde, Betrag, Rabatt, MwSt
2. Automatischer Abgleich zwischen Rechnung und Zahlungseingang über die Rechnungsnummer im Verwendungszweck, mit Betrags- und Zeitfensterprüfung als Rückfallebene
3. Offene-Posten-Liste, Mahnstufen, Ausfälle — die Information aus Ordnernamen und Dateinamens-Kommentaren wird dabei in strukturierte Felder überführt
4. Ausfallquote je Jahr und Raum, getrennt nach echten Ausfällen und Kulanzentscheidungen (Abschnitt 6)
5. Koordinationsrechnungen erfassen
6. Auslagenerstattungen mit dem zweistufigen Freigabeprozess aus Abschnitt 7, einschließlich der automatischen Rückkopplung aus dem Kontoauszug
7. Rechnungsprüfungs-Workflow im Tool

### Phase 3 — Ausbau

Auslastungsstatistik je Raum aus den Buchungsdaten · Rabattauswertung · Prognose des Kuratorenbudgets · ggf. Ablösung von MoneyMoney, sofern sich die automatische Kategorisierung in Phase 1 bewährt hat

---

## 10. Benötigte Daten

Laut Protokoll legt Tristan auf Nextcloud ab. Bereits vorhanden ist:

| Daten | Status |
|---|---|
| DKB-Kontoauszug CSV 2025 | vorhanden |
| MoneyMoney-Export mit Kategorien 2025 | vorhanden |
| An Nutzerinnen gestellte Rechnungen 2016–2026 | vorhanden (~2.900 PDFs) |
| Rechnungen für die Koordination | teilweise (2025, 2026) |
| USt-Erklärung 2025 | vorhanden |
| Auswertungen Q1–Q2 2026 | vorhanden (als Referenz für den Regressionstest) |
| **Belege und Auslagenerstattungsanträge an die WEG** | **fehlt** (Ordner `Auslagen` ist leer) — Grundlage für Abschnitt 7 |
| **DKB-CSV und MoneyMoney-Export 2026** | **fehlt** |
| **DKB-CSV und MoneyMoney-Export 2022–2024** | **fehlt** (für Mehrjahresvergleich) |

Für das Anschauungsbeispiel in Phase 0 reichen die bereits vorliegenden 2025er-Daten aus; dafür muss nichts nachgeliefert werden. Für Phase 1 kommt der 2026er-Export hinzu, sobald er verfügbar ist. Die Auslagenbelege werden erst in Phase 2 gebraucht — für die Ausgestaltung des Freigabeprozesses wäre es aber hilfreich, vorab ein paar typische Anträge der letzten Zeit zu sehen, um zu verstehen, wie sie heute aussehen und was daran geprüft werden muss.
