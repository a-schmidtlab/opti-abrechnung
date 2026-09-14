"""Streamlit-Oberflaeche des Abrechnungstools.

Phase 0 nach Abschnitt 9 des Plans: ein schmaler Durchstich, der das Prinzip
sichtbar macht. Import des MoneyMoney-Exports, die Rechenkette aus Abschnitt 2.1,
eine Raumbilanz und der Drilldown von einer Summe bis auf die einzelne
Bankbuchung.

Aufruf:
    uv run streamlit run src/optiabrechnung/oberflaeche/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Erlaubt den Aufruf ueber `streamlit run <pfad>`, bei dem das Paket nicht
# automatisch im Suchpfad liegt.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optiabrechnung import __version__
from optiabrechnung.auswertung import (
    budgetfortschreibung,
    budgetjahr_aus_kette,
    raumbilanz,
    rechenkette,
)
from optiabrechnung.einlesen import (
    EinleseFehler,
    abgleichen,
    einlesen_dkb,
    einlesen_moneymoney,
)
from optiabrechnung.kategorien import UnbekannteKategorie
from optiabrechnung.oberflaeche.darstellung import (
    buchungstabelle,
    euro,
    prozent,
)
from optiabrechnung.parameter import ParameterFehlt, Zeitraum

PROJEKTWURZEL = Path(__file__).resolve().parents[3]

st.set_page_config(
    page_title="Abrechnung Optionsräume Spreefeld",
    page_icon="◫",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Datenquellen
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _exporte_finden() -> list[str]:
    """Sucht im Projektverzeichnis nach MoneyMoney-Exporten.

    Erkennungsmerkmal ist die Kopfzeile, nicht der Dateiname: Die Exporte heissen
    von Jahr zu Jahr unterschiedlich, die Kopfzeile ist dagegen stabil.
    """
    gefunden = []
    for pfad in sorted(PROJEKTWURZEL.rglob("*.csv")):
        try:
            kopf = pfad.open(encoding="utf-8-sig").readline()
        except OSError:
            continue
        if kopf.startswith("Datum;") and "Kategorie" in kopf:
            gefunden.append(str(pfad.relative_to(PROJEKTWURZEL)))
    return gefunden


@st.cache_data(show_spinner=False)
def _kontoauszuege_finden() -> list[str]:
    gefunden = []
    for pfad in sorted(PROJEKTWURZEL.rglob("*.csv")):
        try:
            inhalt = pfad.open(encoding="utf-8-sig").read(4000)
        except OSError:
            continue
        if '"Buchungsdatum"' in inhalt:
            gefunden.append(str(pfad.relative_to(PROJEKTWURZEL)))
    return gefunden


@st.cache_data(show_spinner="Export wird eingelesen …")
def _buchungen_laden(relativer_pfad: str):
    return einlesen_moneymoney(PROJEKTWURZEL / relativer_pfad)


@st.cache_data(show_spinner="Kontoauszug wird eingelesen …")
def _auszug_laden(relativer_pfad: str):
    return einlesen_dkb(PROJEKTWURZEL / relativer_pfad)


# ---------------------------------------------------------------------------
# Seitenleiste
# ---------------------------------------------------------------------------


def _seitenleiste():
    st.sidebar.title("Optionsräume Spreefeld")
    st.sidebar.caption(f"Abrechnungstool, Fassung {__version__} · Phase 0")

    exporte = _exporte_finden()
    if not exporte:
        st.sidebar.error(
            "Kein MoneyMoney-Export gefunden. Erwartet wird eine CSV-Datei mit der "
            "Kopfzeile `Datum;Wertstellung;Kategorie;…` irgendwo im Projektverzeichnis."
        )
        st.stop()

    quelle = st.sidebar.selectbox("MoneyMoney-Export", exporte, format_func=lambda p: Path(p).name)

    try:
        buchungen = _buchungen_laden(quelle)
    except UnbekannteKategorie as fehler:
        st.sidebar.error(str(fehler))
        st.stop()
    except EinleseFehler as fehler:
        st.sidebar.error(f"Der Export ließ sich nicht einlesen. {fehler}")
        st.stop()

    jahre = sorted({b.jahr for b in buchungen})
    jahr = st.sidebar.selectbox("Jahr", jahre, index=len(jahre) - 1)

    beschriftungen = {
        (1, 4): "ganzes Jahr",
        (1, 1): "Q1",
        (2, 2): "Q2",
        (3, 3): "Q3",
        (4, 4): "Q4",
        (1, 2): "1. Halbjahr (Q1–Q2)",
        (3, 4): "2. Halbjahr (Q3–Q4)",
    }
    auswahl = st.sidebar.selectbox(
        "Zeitraum",
        list(beschriftungen),
        format_func=lambda schluessel: beschriftungen[schluessel],
    )
    zeitraum = Zeitraum(jahr=jahr, erstes_quartal=auswahl[0], letztes_quartal=auswahl[1])

    st.sidebar.divider()
    st.sidebar.caption(
        f"{len(buchungen)} Buchungen gelesen, davon "
        f"{sum(1 for b in buchungen if zeitraum.enthaelt(b.datum))} im gewählten Zeitraum."
    )
    return buchungen, zeitraum


# ---------------------------------------------------------------------------
# Quartalsbericht
# ---------------------------------------------------------------------------


def _posten_mit_drilldown(posten, *, einrueckung: str = "") -> None:
    """Zeigt einen Posten als aufklappbare Zeile mit seinen Einzelbuchungen."""
    spalte_bezeichnung, spalte_betrag = st.columns([5, 1])
    beschriftung = f"{einrueckung}{posten.bezeichnung}"
    if posten.pruefbedarf and posten.betrag:
        beschriftung += "  ⚑"

    if posten.buchungen:
        with spalte_bezeichnung.expander(f"{beschriftung}  ·  {posten.anzahl_buchungen} Buchungen"):
            st.dataframe(
                buchungstabelle(posten.buchungen),
                use_container_width=True,
                hide_index=True,
            )
    elif posten.aus_parameter:
        with spalte_bezeichnung.expander(f"{beschriftung}  ·  aus Parametern"):
            st.info(posten.herkunft, icon="ℹ")
    else:
        spalte_bezeichnung.write(f"{beschriftung}  ·  keine Buchungen")

    spalte_betrag.markdown(f"<div style='text-align:right'>{euro(posten.betrag)}</div>",
                           unsafe_allow_html=True)


def _zwischensumme(bezeichnung: str, betrag) -> None:
    spalte_bezeichnung, spalte_betrag = st.columns([5, 1])
    spalte_bezeichnung.markdown(f"**{bezeichnung}**")
    spalte_betrag.markdown(
        f"<div style='text-align:right'><b>{euro(betrag)}</b></div>", unsafe_allow_html=True
    )


def seite_quartalsbericht(kette) -> None:
    st.header(f"Quartalsbericht · {kette.zeitraum.bezeichnung}")
    st.caption(
        "Jede Zeile ist aufklappbar bis auf die einzelne Bankbuchung. Die mit ⚑ "
        "markierten Posten sind ausdrücklich vorzulegen: Investitionen, weil die "
        "Abgrenzung zur Erhaltung nicht automatisierbar ist, und „unklar“."
    )

    if kette.unzugeordnet:
        st.error(
            f"{len(kette.unzugeordnet)} Buchungen im Zeitraum haben keine Zielkategorie. "
            "Die Auswertung ist damit unvollständig."
        )

    oben = st.columns(4)
    oben[0].metric("Einnahmen Vermietung", euro(kette.einnahmen_gesamt))
    oben[1].metric("Überschuss gesamt", euro(kette.ueberschuss_gesamt))
    oben[2].metric("Budget Kuratoren verfügbar", euro(kette.budget_verfuegbar))
    oben[3].metric("Überweisung an die WEG", euro(kette.ueberweisung_weg))

    st.divider()

    st.subheader("Einnahmen Vermietung")
    for posten in kette.einnahmen:
        _posten_mit_drilldown(posten)
    _zwischensumme("Summe Einnahmen", kette.einnahmen_gesamt)

    st.subheader("Betrieb & Erhaltung")
    for posten in kette.betriebskosten:
        _posten_mit_drilldown(posten)
    _zwischensumme("Summe Betrieb & Erhaltung", kette.betriebskosten_gesamt)

    st.subheader("Weitere Positionen der Kette")
    _posten_mit_drilldown(kette.nebenkosten)
    _posten_mit_drilldown(kette.internet)

    st.divider()
    _zwischensumme("Überschuss gesamt", kette.ueberschuss_gesamt)

    st.subheader("Investitionsbudget der Kuratoren")
    _zwischensumme(
        "50 % Überschuss als Budgetzuführung (brutto)", kette.budgetzufuehrung
    )
    for posten in kette.investitionen:
        _posten_mit_drilldown(posten, einrueckung="− bereits getätigt: ")
    _zwischensumme("Verfügbares Budget Kuratoren", kette.budget_verfuegbar)

    st.subheader("Abführung an die WEG")
    _zwischensumme("50 % Überschuss an die WEG (netto, ÷ 1,19)", kette.weg_anteil_netto)
    _zwischensumme(kette.nebenkosten.bezeichnung, kette.nebenkosten.betrag)
    _zwischensumme("Überweisung an die WEG", kette.ueberweisung_weg)

    with st.expander("Warum der WEG-Anteil netto und der Kuratorenanteil brutto ist"):
        st.markdown(
            "Der Überschuss wird brutto gerechnet, der 50-%-Anteil an die WEG aber "
            "netto abgeführt, also geteilt durch 1,19. Der Kuratorenanteil bleibt "
            "brutto. Das ist eine Entscheidung mit realer Wirkung: Die Kuratoren "
            "erhalten effektiv einen um 19 % höheren Anteil als die WEG.\n\n"
            "Abschnitt 8 der Planung führt diesen Punkt als offene Frage. Bis zur "
            "Klärung rechnet das Tool den Bestand unverändert nach, denn der "
            "Bestand ist der Maßstab des Regressionstests."
        )


# ---------------------------------------------------------------------------
# Raumbilanz
# ---------------------------------------------------------------------------


def seite_raumbilanz(kette) -> None:
    st.header(f"Raumbilanz · {kette.zeitraum.bezeichnung}")
    st.caption(
        "Kalkulatorische Zusatzsicht. Die offizielle Auswertung nach Abschnitt 2.1 "
        "bleibt davon unberührt."
    )

    nebenkosten_umlegen = st.toggle(
        "Nebenkosten mit umlegen",
        value=True,
        help=(
            "Mit Umlage ergibt die Summe der Deckungsbeiträge genau den Überschuss. "
            "Ohne Umlage zeigt sie das Ergebnis vor Nebenkosten."
        ),
    )
    bilanzen = raumbilanz(kette, nebenkosten_umlegen=nebenkosten_umlegen)

    st.dataframe(
        [
            {
                "Raum": b.raum.value,
                "Dauermiete": euro(b.dauermiete),
                "Einzelbuchungen": euro(b.einzelbuchung),
                "Einnahmen": euro(b.einnahmen),
                "Anteil an Einnahmen": prozent(b.einnahmenanteil),
                "Erhaltung direkt": euro(b.erhaltung),
                "Gemeinkosten anteilig": euro(b.gemeinkosten_umlage),
                "Deckungsbeitrag": euro(b.deckungsbeitrag),
                "Investitionen": euro(b.investition),
            }
            for b in bilanzen
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "**Zum Verteilungsschlüssel.** Umgelegt wird nach dem Anteil des Raums an den "
        "Gesamteinnahmen. Der Schlüssel ist einfach zu erklären, braucht keine "
        "zusätzlichen Daten und löst keine Diskussion über Flächendefinitionen aus.\n\n"
        "Eine Eigenschaft sollte man beim Lesen kennen: Weil proportional zu den "
        "Einnahmen verteilt wird, tragen alle Räume denselben prozentualen "
        "Gemeinkostenblock. Unterschiede zwischen den Räumen entstehen deshalb "
        "ausschließlich aus den direkt zugeordneten Erhaltungskosten. Das ist kein "
        "Fehler, sondern die logische Folge des Schlüssels — die Umlage selbst sagt "
        "nichts über die tatsächliche Kostenverursachung aus.",
        icon="ℹ",
    )

    st.subheader("Dauermiete gegen Einzelbuchung")
    st.caption(
        "Die Aufteilung ist die Kennzahl für die Auslastungsdiskussion — nicht "
        "zuletzt, weil die 50/50-Sonderregel ausdrücklich auf die schwächer "
        "ausgelasteten Räume O2 und Bootshaus verweist."
    )
    st.bar_chart(
        {
            "Dauermiete": {b.raum.value: float(b.dauermiete) for b in bilanzen},
            "Einzelbuchungen": {b.raum.value: float(b.einzelbuchung) for b in bilanzen},
        }
    )


# ---------------------------------------------------------------------------
# Kategorisierungs-Pruefung
# ---------------------------------------------------------------------------


def seite_pruefung(buchungen, kette) -> None:
    st.header("Kategorisierungs-Prüfung")
    st.caption(
        "MoneyMoney bleibt das führende System. Das Tool prüft auf Lücken und "
        "Auffälligkeiten und zeigt Abweichungen als Frage, nicht als Korrektur."
    )

    st.subheader("Vorzulegende Posten")
    if kette.pruefposten:
        for posten in kette.pruefposten:
            _posten_mit_drilldown(posten)
    else:
        st.success("Keine Investitionen und keine unklaren Buchungen im Zeitraum.", icon="✓")

    st.subheader("Lückenprüfung gegen den Kontoauszug")
    auszuege = _kontoauszuege_finden()
    if not auszuege:
        st.info(
            "Kein DKB-Kontoauszug gefunden. Für die Lückenprüfung wird eine "
            "Umsatzliste der DKB im CSV-Format benötigt.",
            icon="ℹ",
        )
        return

    gewaehlt = st.selectbox(
        "DKB-Kontoauszug", auszuege, format_func=lambda p: Path(p).name
    )
    try:
        auszug = _auszug_laden(gewaehlt)
    except EinleseFehler as fehler:
        st.error(f"Der Kontoauszug ließ sich nicht einlesen. {fehler}")
        return

    st.caption(
        f"{auszug.kontobezeichnung} · {auszug.iban} · Zeitraum {auszug.zeitraum} · "
        f"{len(auszug.buchungen)} Buchungen"
    )

    ergebnis = abgleichen(buchungen, auszug.buchungen)
    spalten = st.columns(3)
    spalten[0].metric("Übereinstimmend", ergebnis.uebereinstimmend)
    spalten[1].metric(
        "Nur im Kontoauszug", len(ergebnis.nur_in_dkb), delta=euro(ergebnis.summe_nur_in_dkb)
    )
    spalten[2].metric(
        "Nur in MoneyMoney",
        len(ergebnis.nur_in_moneymoney),
        delta=euro(ergebnis.summe_nur_in_moneymoney),
    )

    if ergebnis.vollstaendig:
        st.success(
            "Beide Quellen stimmen buchungsweise überein. Es fehlt keine Buchung "
            "in der Auswertung.",
            icon="✓",
        )
        return

    if ergebnis.nur_in_dkb:
        st.warning(
            "Diese Buchungen stehen im Kontoauszug, aber nicht im MoneyMoney-Export. "
            "Sie sind damit in keiner Auswertung enthalten.",
            icon="⚠",
        )
        st.dataframe(
            buchungstabelle(ergebnis.nur_in_dkb), use_container_width=True, hide_index=True
        )

    if ergebnis.nur_in_moneymoney:
        st.warning(
            "Diese Buchungen stehen nur in MoneyMoney — typischerweise eine "
            "Zeitraumgrenze des Exports.",
            icon="⚠",
        )
        st.dataframe(
            buchungstabelle(ergebnis.nur_in_moneymoney),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------------------------
# Kuratorenbudget
# ---------------------------------------------------------------------------


def seite_budget(kette) -> None:
    st.header("Kuratorenbudget")
    st.caption(
        "Fortschreibung über die Jahre. Die kumulierte Summe ist politisch relevant "
        "genug, dass ihre Herleitung transparent sein muss."
    )

    reihe = budgetfortschreibung(budgetjahr_aus_kette(kette))
    st.dataframe(
        [
            {
                "Jahr": j.jahr,
                "Budgetzuführung": euro(j.zufuehrung),
                "Investitionen": euro(j.investitionen),
                "Rest": euro(j.rest),
                "Kumuliert": euro(j.kumuliert),
                "Grundlage": "aus Buchungen" if j.belegt else "aus Bestandsauswertung",
            }
            for j in reihe
        ],
        use_container_width=True,
        hide_index=True,
    )

    kumuliert = reihe[-1].kumuliert if reihe else 0
    st.metric("Ungenutztes Budget kumuliert", euro(kumuliert))
    st.caption(
        "Die Jahre 2022 bis 2025 sind noch aus der Bestandsauswertung übernommen und "
        "in ganzen Euro angegeben. Sobald die Exporte dieser Jahre vorliegen, lassen "
        "sie sich aus den Buchungen nachrechnen."
    )


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------


def seite_parameter(kette) -> None:
    st.header("Parameter und Herkunft")
    st.caption(
        "Diese Werte stehen nicht in den Bankdaten, sondern sind gesetzt oder "
        "beschlossen. Deshalb steht neben jedem Betrag, woher er kommt."
    )
    p = kette.parameter
    if not p.gesichert:
        st.warning(
            f"Für {p.jahr} ist mindestens ein Wert hergeleitet und nicht belegt. "
            "Die Auswertung ist insoweit vorläufig.",
            icon="⚠",
        )

    st.metric("Nebenkosten, Jahresbetrag", euro(p.nebenkosten_jahresbetrag))
    st.write(p.nebenkosten_herkunft)
    st.divider()
    st.metric("Internet Optionsräume, Jahresbetrag", euro(p.internet_jahresbetrag))
    st.write(p.internet_herkunft)
    st.divider()
    st.markdown(
        "**Offen nach Abschnitt 8 der Planung.** Zur Nebenkostenfortschreibung gibt "
        "es zwei Lesarten: Fortschreibung des Vorjahreswerts um den "
        "Verbraucherpreisindex, oder Ansatz der zuletzt verfügbaren tatsächlichen "
        "Werte. Beide bleiben abbildbar, weil der Betrag je Jahr als Parameter "
        "geführt wird. Der derzeitige Stand entspricht der zweiten Lesart: Für "
        "2026 ist der Wert aus 2024 unverändert angesetzt, ohne VPI-Aufschlag."
    )


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------


def hauptprogramm() -> None:
    buchungen, zeitraum = _seitenleiste()

    try:
        kette = rechenkette(buchungen, zeitraum)
    except ParameterFehlt as fehler:
        st.error(str(fehler))
        st.stop()

    bericht, bilanz, pruefung, budget, parameter = st.tabs(
        ["Quartalsbericht", "Raumbilanz", "Prüfung", "Kuratorenbudget", "Parameter"]
    )
    with bericht:
        seite_quartalsbericht(kette)
    with bilanz:
        seite_raumbilanz(kette)
    with pruefung:
        seite_pruefung(buchungen, kette)
    with budget:
        seite_budget(kette)
    with parameter:
        seite_parameter(kette)


hauptprogramm()
