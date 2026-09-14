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
    mehrjahresvergleich,
    raumbilanz,
    rechenkette,
)
from optiabrechnung.einlesen import (
    EinleseFehler,
    abgleichen,
    einlesen_dkb,
    einlesen_moneymoney,
)
from optiabrechnung.einstellungen import Einstellungen
from optiabrechnung.einstellungen import laden as einstellungen_laden
from optiabrechnung.einstellungen import speichern as einstellungen_speichern
from optiabrechnung.kategorien import UnbekannteKategorie
from optiabrechnung.nextcloud import (
    NextcloudFehler,
    datei_holen,
    dateien_suchen,
    freigabe_lesen,
)
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


MONEYMONEY = "moneymoney"
DKB = "dkb"


def _art_der_datei(pfad: Path) -> str | None:
    """Erkennt an der Kopfzeile, um welche Art von Export es sich handelt.

    Erkannt wird am Inhalt und nicht am Dateinamen. Die Exporte heissen von Jahr
    zu Jahr unterschiedlich -- `SF Optionsräume 25.csv`,
    `2025_Umsatzliste_WEG-Konto Hausgeld_DE26….csv` --, die Kopfzeilen sind
    dagegen stabil.
    """
    try:
        anfang = pfad.open(encoding="utf-8-sig", errors="replace").read(4000)
    except OSError:
        return None
    if anfang.startswith("Datum;") and "Kategorie" in anfang.splitlines()[0]:
        return MONEYMONEY
    if '"Buchungsdatum"' in anfang:
        return DKB
    return None


@st.cache_data(show_spinner=False)
def _quellen_finden(ordner: str) -> dict[str, list[str]]:
    """Durchsucht ein Verzeichnis nach MoneyMoney-Exporten und DKB-Auszuegen."""
    wurzel = Path(ordner)
    gefunden: dict[str, list[str]] = {MONEYMONEY: [], DKB: []}
    if not wurzel.is_dir():
        return gefunden
    for pfad in sorted(wurzel.rglob("*.csv")):
        art = _art_der_datei(pfad)
        if art:
            gefunden[art].append(str(pfad))
    return gefunden


@st.cache_data(show_spinner="Export wird eingelesen …")
def _buchungen_laden(pfad: str):
    return einlesen_moneymoney(Path(pfad))


@st.cache_data(show_spinner="Kontoauszug wird eingelesen …")
def _auszug_laden(pfad: str):
    return einlesen_dkb(Path(pfad))


# ---------------------------------------------------------------------------
# Nextcloud
# ---------------------------------------------------------------------------


def _nextcloud_abrufen(link: str, passwort: str) -> tuple[Path, int]:
    """Holt alle CSV-Dateien einer Nextcloud-Freigabe in den Zwischenspeicher.

    Gibt das Verzeichnis des Zwischenspeichers und die Anzahl der Dateien
    zurueck. Danach arbeitet der Rest der Oberflaeche auf gewoehnlichen
    Dateien -- die Nextcloud-Anbindung ist damit auf diese eine Stelle begrenzt.
    """
    freigabe = freigabe_lesen(link, passwort)
    eintraege = dateien_suchen(freigabe, endungen=(".csv",))
    fortschritt = st.sidebar.progress(0.0, text="Dateiliste gelesen …")
    for nummer, eintrag in enumerate(eintraege, start=1):
        datei_holen(freigabe, eintrag, ordner=PROJEKTWURZEL / "daten" / "nextcloud")
        fortschritt.progress(nummer / len(eintraege), text=f"{eintrag.name} geladen")
    fortschritt.empty()
    return PROJEKTWURZEL / "daten" / "nextcloud" / freigabe.token, len(eintraege)


def _datenquelle_waehlen(einstellungen: Einstellungen) -> Path | None:
    """Zeigt die Auswahl der Datenquelle und liefert das Verzeichnis mit den Dateien."""
    arten = {"lokal": "Lokaler Ordner", "nextcloud": "Nextcloud-Freigabe"}
    quelle = st.sidebar.radio(
        "Datenquelle",
        list(arten),
        format_func=lambda schluessel: arten[schluessel],
        index=list(arten).index(einstellungen.quelle),
        horizontal=True,
        help=(
            "„Lokaler Ordner“ passt auch für einen mit Nextcloud oder Synology Drive "
            "synchronisierten Ordner auf diesem Rechner. „Nextcloud-Freigabe“ liest "
            "die Dateien direkt aus einem geteilten Ordner."
        ),
    )

    if quelle == "lokal":
        ordner = st.sidebar.text_input(
            "Verzeichnis",
            value=einstellungen.lokaler_ordner or str(PROJEKTWURZEL),
            help="Wird einschließlich Unterverzeichnissen durchsucht.",
        )
        if ordner != einstellungen.lokaler_ordner or quelle != einstellungen.quelle:
            einstellungen.quelle = quelle
            einstellungen.lokaler_ordner = ordner
            einstellungen_speichern(einstellungen, PROJEKTWURZEL / "daten/einstellungen.json")
        pfad = Path(ordner).expanduser()
        if not pfad.is_dir():
            st.sidebar.error(f"„{ordner}“ ist kein Verzeichnis.")
            return None
        return pfad

    link = st.sidebar.text_input(
        "Nextcloud-Freigabelink",
        value=einstellungen.nextcloud_link,
        placeholder="https://cloud.example.org/s/AbCdEf123",
        help=(
            "In Nextcloud den Ordner mit den Exporten über „Teilen“ → „Link teilen“ "
            "freigeben und den erzeugten Link hier einfügen."
        ),
    )
    passwort = st.sidebar.text_input(
        "Passwort der Freigabe",
        type="password",
        help=(
            "Nur nötig, wenn die Freigabe passwortgeschützt ist. Das Passwort wird "
            "nicht gespeichert und ist nach dem Schließen des Tools wieder weg."
        ),
    )

    if st.sidebar.button("Dateien abrufen", type="primary", use_container_width=True):
        try:
            ordner, anzahl = _nextcloud_abrufen(link, passwort)
        except NextcloudFehler as fehler:
            st.sidebar.error(str(fehler))
            return None
        einstellungen.quelle = quelle
        einstellungen.nextcloud_link = link
        einstellungen_speichern(einstellungen, PROJEKTWURZEL / "daten/einstellungen.json")
        st.session_state["nextcloud_ordner"] = str(ordner)
        _quellen_finden.clear()
        st.sidebar.success(f"{anzahl} CSV-Dateien geladen.")

    zwischenspeicher = st.session_state.get("nextcloud_ordner")
    if zwischenspeicher:
        st.sidebar.caption(
            "Gearbeitet wird auf dem lokalen Zwischenspeicher der Freigabe. "
            "„Dateien abrufen“ holt den aktuellen Stand."
        )
        return Path(zwischenspeicher)

    st.sidebar.info(
        "Link eingeben und „Dateien abrufen“ wählen. Beim ersten Mal kann das einen "
        "Moment dauern.",
        icon="ℹ",
    )
    return None


# ---------------------------------------------------------------------------
# Seitenleiste
# ---------------------------------------------------------------------------


def _seitenleiste():
    st.sidebar.title("Optionsräume Spreefeld")
    st.sidebar.caption(f"Abrechnungstool, Fassung {__version__} · Phase 0")

    einstellungen = einstellungen_laden(PROJEKTWURZEL / "daten/einstellungen.json")
    ordner = _datenquelle_waehlen(einstellungen)
    if ordner is None:
        st.info(
            "Bitte links eine Datenquelle wählen. Benötigt wird der MoneyMoney-Export "
            "mit Kategorien; der DKB-Kontoauszug kommt für die Lückenprüfung hinzu.",
            icon="ℹ",
        )
        st.stop()

    st.sidebar.divider()
    quellen = _quellen_finden(str(ordner))
    if not quellen[MONEYMONEY]:
        st.sidebar.error(
            "Kein MoneyMoney-Export gefunden. Erwartet wird eine CSV-Datei mit der "
            "Kopfzeile `Datum;Wertstellung;Kategorie;…`."
        )
        st.stop()

    quelle = st.sidebar.selectbox(
        "MoneyMoney-Export", quellen[MONEYMONEY], format_func=lambda p: Path(p).name
    )

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
    st.sidebar.toggle(
        "Beschriftungen wie im Bestandsbericht",
        key="bestandsbeschriftung",
        value=True,
        help=(
            "Eingeschaltet stehen die Zeilen so da wie im bisherigen Blatt "
            "(„Buha Klier+Ott“, „Bank“). Das ist für den Vergleich Zeile für Zeile "
            "gedacht. Ausgeschaltet erscheinen die geklärten Bezeichnungen, wie sie "
            "in einen Bericht an Spree VV gehören."
        ),
    )

    st.sidebar.divider()
    st.sidebar.caption(
        f"{len(buchungen)} Buchungen gelesen, davon "
        f"{sum(1 for b in buchungen if zeitraum.enthaelt(b.datum))} im gewählten Zeitraum."
    )
    st.sidebar.caption(f"Quelle: {Path(quelle).name}")
    return buchungen, zeitraum, quellen[DKB]


# ---------------------------------------------------------------------------
# Quartalsbericht
# ---------------------------------------------------------------------------


def _wie_im_bestand() -> bool:
    return bool(st.session_state.get("bestandsbeschriftung", True))


def _posten_mit_drilldown(posten, *, einrueckung: str = "") -> None:
    """Zeigt einen Posten als aufklappbare Zeile mit seinen Einzelbuchungen."""
    spalte_bezeichnung, spalte_betrag = st.columns([5, 1])
    beschriftung = f"{einrueckung}{posten.beschriftung(wie_im_bestand=_wie_im_bestand())}"
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
    st.header(f"Umsätze Optionsräume · {kette.zeitraum.bezeichnung}")
    st.caption(
        f"Zeitraum {kette.zeitraum.beginn.strftime('%d.%m.%Y')} bis "
        f"{kette.zeitraum.ende.strftime('%d.%m.%Y')} · alle Beträge brutto"
    )

    if kette.unzugeordnet:
        st.error(
            f"{len(kette.unzugeordnet)} Buchungen im Zeitraum haben keine Zielkategorie. "
            "Die Auswertung ist damit unvollständig."
        )

    # Fuenf Kennzahlen in der Reihenfolge und Wortwahl der Kurzuebersicht des
    # Bestandsblattes, damit sich beide unmittelbar vergleichen lassen.
    oben = st.columns(5)
    oben[0].metric("Einnahmen Vermietung", euro(kette.einnahmen_gesamt))
    oben[1].metric(
        "Ausgaben gesamt",
        euro(kette.ausgaben_gesamt),
        help=(
            "Betrieb & Erhaltung, Nebenkosten und Internet zusammen. Das "
            "Bestandsblatt nennt diese Zeile „Ausgaben Betrieb & Erhaltung“, "
            "obwohl Nebenkosten und Internet mit enthalten sind."
        ),
    )
    oben[2].metric("Überschuss gesamt", euro(kette.ueberschuss_gesamt))
    oben[3].metric("Budget Kuratoren", euro(kette.budget_verfuegbar))
    oben[4].metric("Überschuss & Nebenkosten an WEG", euro(kette.ueberweisung_weg))

    st.divider()
    st.caption(
        "Jede Zeile ist aufklappbar bis auf die einzelne Bankbuchung. Die mit ⚑ "
        "markierten Posten sind ausdrücklich vorzulegen: Investitionen, weil die "
        "Abgrenzung zur Erhaltung nicht automatisierbar ist, und „unklar“."
    )

    st.subheader("Einnahmen")
    for posten in kette.einnahmen:
        _posten_mit_drilldown(posten)
    _zwischensumme("Summe Einnahmen", kette.einnahmen_gesamt)

    st.subheader("Betrieb & Erhaltung")
    for posten in kette.betriebskosten:
        _posten_mit_drilldown(posten)
    _zwischensumme("Summe Betrieb & Erhaltung", kette.betriebskosten_gesamt)

    st.subheader("Weitere Positionen der Kette")
    st.caption(
        "Beide Zeilen stehen auch im Bestandsblatt, dort unbeschriftet neben den "
        "Betriebskosten bzw. am Seitenfuß."
    )
    _posten_mit_drilldown(kette.nebenkosten)
    _posten_mit_drilldown(kette.internet)

    st.divider()
    _zwischensumme("Überschuss gesamt", kette.ueberschuss_gesamt)

    st.subheader("Investitionen Kuratoren")
    _zwischensumme(
        "50 % Überschuss für Investition Kuratoren", kette.budgetzufuehrung
    )
    for posten in kette.investitionen:
        _posten_mit_drilldown(posten, einrueckung="− getätigt: ")
    _zwischensumme("Summe Investitionen getätigt", kette.investitionen_gesamt)
    _zwischensumme("Investitionsbetrag übrig", kette.budget_verfuegbar)

    st.subheader("Abführung an die WEG")
    _zwischensumme("50 % Überschuss an WEG (netto)", kette.weg_anteil_netto)
    _zwischensumme(kette.nebenkosten.bezeichnung, kette.nebenkosten.betrag)
    _zwischensumme("abz. Abschläge vorige Quartale", kette.abschlaege_vorige_quartale)
    _zwischensumme("Überweisung auf Hauptkonto", kette.ueberweisung_weg)

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


def seite_pruefung(buchungen, kette, auszuege: list[str]) -> None:
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
    if not auszuege:
        st.info(
            "Kein DKB-Kontoauszug in der gewählten Datenquelle gefunden. Für die "
            "Lückenprüfung wird eine Umsatzliste der DKB im CSV-Format benötigt.",
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
# Mehrjahresvergleich
# ---------------------------------------------------------------------------


def seite_mehrjahresvergleich(kette) -> None:
    st.header("Mehrjahresvergleich")
    st.caption(
        "Dieselbe Übersicht, die unten auf dem Bestandsblatt steht — 2022 bis 2025 "
        "aus dem Blatt übernommen, der gewählte Zeitraum aus den Buchungen gerechnet."
    )

    reihe = mehrjahresvergleich(kette)
    st.dataframe(
        [
            {
                "Jahr": f"{j.jahr} ({kette.zeitraum.bezeichnung})" if j.belegt else str(j.jahr),
                "Einnahmen": euro(j.einnahmen),
                "Ausgaben": euro(j.ausgaben),
                "Überschuss": euro(j.ueberschuss),
                "50 % Zuführung": euro(j.zufuehrung),
                "Investitionen": euro(j.investitionen),
                "Budgetrest": euro(j.budgetrest),
                "Grundlage": "aus Buchungen" if j.belegt else "aus Bestandsblatt",
            }
            for j in reihe
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.bar_chart(
        {
            "Einnahmen": {str(j.jahr): float(j.einnahmen) for j in reihe},
            "Ausgaben": {str(j.jahr): float(abs(j.ausgaben)) for j in reihe},
            "Überschuss": {str(j.jahr): float(j.ueberschuss) for j in reihe},
        }
    )

    st.info(
        "**Zwei Hinweise zum Lesen.** Die Jahre 2022 bis 2025 stehen im Bestandsblatt "
        "in ganzen Euro. Daraus folgen Unstimmigkeiten von einem Euro — für 2023 "
        "ergeben 79.813 − 51.490 genau 28.323, ausgewiesen sind 28.322. Das ist die "
        "Rundung des Blattes, nicht ein Fehler in der Übernahme.\n\n"
        "Zuführung und Investitionen nennt das Blatt nur für 2025. Für die übrigen "
        "Jahre sind sie hier errechnet: Zuführung ist der halbe Überschuss, "
        "Investitionen sind die Differenz zum Budgetrest. Dass die Herleitung "
        "stimmt, zeigt 2025: Das Blatt weist dort −10.659 € aus, und genau dieser "
        "Wert kommt aus 20.134 − 30.793 heraus. Damit wird erstmals sichtbar, wie "
        "viel in den Jahren 2022 bis 2024 tatsächlich investiert wurde.",
        icon="ℹ",
    )
    st.caption(
        "Sobald die Exporte 2022–2024 vorliegen, lassen sich diese Zeilen aus den "
        "Buchungen nachrechnen — und dann wird auch sichtbar, ob die Rundungen des "
        "Blattes etwas verdecken."
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
    buchungen, zeitraum, auszuege = _seitenleiste()

    try:
        kette = rechenkette(buchungen, zeitraum)
    except ParameterFehlt as fehler:
        st.error(str(fehler))
        st.stop()

    # Reihenfolge wie auf dem Bestandsblatt: erst die Kette, dann der
    # Mehrjahresvergleich, dann das Budget. Raumbilanz und Pruefung sind
    # Zusatzsichten und stehen dahinter.
    bericht, mehrjahr, budget, bilanz, pruefung, parameter = st.tabs(
        [
            "Quartalsbericht",
            "Mehrjahresvergleich",
            "Kuratorenbudget",
            "Raumbilanz",
            "Prüfung",
            "Parameter",
        ]
    )
    with bericht:
        seite_quartalsbericht(kette)
    with mehrjahr:
        seite_mehrjahresvergleich(kette)
    with budget:
        seite_budget(kette)
    with bilanz:
        seite_raumbilanz(kette)
    with pruefung:
        seite_pruefung(buchungen, kette, auszuege)
    with parameter:
        seite_parameter(kette)


hauptprogramm()
