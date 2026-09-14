"""Tests der Nextcloud-Anbindung.

Geprueft werden die Teile, die ohne Netzzugang pruefbar sind: das Zerlegen des
Freigabelinks und das Zerlegen der WebDAV-Antwort. Beides ist der Teil, an dem
in der Praxis etwas schiefgeht -- ein Link in einer unerwarteten Form oder eine
Antwort, deren Pfade anders aussehen als angenommen.

Server und Token in diesen Tests sind erfunden.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from optiabrechnung.nextcloud import (
    NextcloudFehler,
    eintraege_zerlegen,
    freigabe_lesen,
)

# ---------------------------------------------------------------------------
# Freigabelink
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "link",
    [
        "https://cloud.example.org/s/AbCdEf123",
        "https://cloud.example.org/index.php/s/AbCdEf123",
        "https://cloud.example.org/s/AbCdEf123/download",
        "https://cloud.example.org/s/AbCdEf123/",
        "  https://cloud.example.org/s/AbCdEf123  ",
    ],
)
def test_gaengige_linkformen_ergeben_denselben_zugang(link):
    """Nextcloud und die Adresszeile des Browsers bringen verschiedene Formen
    hervor. Wer den Link einfuegt, soll sich darum nicht kuemmern muessen."""
    freigabe = freigabe_lesen(link)
    assert freigabe.server == "https://cloud.example.org"
    assert freigabe.token == "AbCdEf123"


def test_installation_in_einem_unterverzeichnis():
    """Nicht jede Nextcloud liegt auf der Wurzel der Domain."""
    freigabe = freigabe_lesen("https://example.org/nextcloud/s/AbCdEf123")
    assert freigabe.server == "https://example.org/nextcloud"
    assert freigabe.token == "AbCdEf123"


def test_unterordner_aus_dem_pfadparameter():
    freigabe = freigabe_lesen(
        "https://cloud.example.org/s/AbCdEf123?path=%2FAuswertungen%2F2026"
    )
    assert freigabe.unterpfad == "Auswertungen/2026"


def test_adresse_ohne_schema_wird_ergaenzt():
    assert freigabe_lesen("cloud.example.org/s/AbCdEf123").server == "https://cloud.example.org"


def test_link_auf_die_eigene_dateiansicht_wird_erklaert():
    """Der haeufigste Fehlgriff: den Link aus der eigenen Dateiansicht kopieren.

    Die Meldung muss sagen, was stattdessen zu tun ist, nicht nur, dass es
    falsch war.
    """
    with pytest.raises(NextcloudFehler) as fehler:
        freigabe_lesen("https://cloud.example.org/apps/files/?dir=/Optionsraeume")
    assert "Teilen" in str(fehler.value)


def test_leerer_link_wird_abgewiesen():
    with pytest.raises(NextcloudFehler):
        freigabe_lesen("   ")


def test_link_ohne_token_wird_abgewiesen():
    with pytest.raises(NextcloudFehler):
        freigabe_lesen("https://cloud.example.org/")


def test_die_anzeige_verraet_den_token_nicht():
    """Der Token ist das Geheimnis der Freigabe und hat auf einem geteilten
    Bildschirm nichts zu suchen."""
    anzeige = freigabe_lesen("https://cloud.example.org/s/AbCdEf123").anzeige
    assert "AbCdEf123" not in anzeige
    assert "cloud.example.org" in anzeige


# ---------------------------------------------------------------------------
# WebDAV-Antwort
# ---------------------------------------------------------------------------

ANTWORT = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/public.php/webdav/</d:href>
    <d:propstat><d:prop>
      <d:resourcetype><d:collection/></d:resourcetype>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/public.php/webdav/Auswertungen/</d:href>
    <d:propstat><d:prop>
      <d:displayname>Auswertungen</d:displayname>
      <d:resourcetype><d:collection/></d:resourcetype>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/public.php/webdav/SF%20Optionsr%C3%A4ume%2025.csv</d:href>
    <d:propstat><d:prop>
      <d:displayname>SF Optionsräume 25.csv</d:displayname>
      <d:getcontentlength>123456</d:getcontentlength>
      <d:getlastmodified>Mon, 07 Sep 2026 08:16:00 GMT</d:getlastmodified>
      <d:resourcetype/>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
</d:multistatus>
"""


@pytest.fixture
def eintraege():
    return eintraege_zerlegen(ANTWORT, "/public.php/webdav")


def test_der_ordner_selbst_erscheint_nicht_in_der_liste(eintraege):
    """PROPFIND liefert den abgefragten Ordner immer mit. Er darf nicht als
    Eintrag in sich selbst auftauchen."""
    assert all(eintrag.pfad for eintrag in eintraege)
    assert len(eintraege) == 2


def test_ordner_stehen_vor_dateien(eintraege):
    assert eintraege[0].ist_ordner
    assert not eintraege[1].ist_ordner


def test_umlaute_im_dateinamen_werden_entschluesselt(eintraege):
    datei = eintraege[1]
    assert datei.name == "SF Optionsräume 25.csv"
    assert datei.pfad == "SF Optionsräume 25.csv"
    assert datei.endung == ".csv"


def test_groesse_und_aenderungszeit_werden_gelesen(eintraege):
    datei = eintraege[1]
    assert datei.groesse == 123456
    assert datei.geaendert == datetime.fromisoformat("2026-09-07T08:16:00+00:00")


def test_ordner_haben_keine_groesse(eintraege):
    assert eintraege[0].groesse == 0


def test_neuer_endpunkt_mit_token_im_pfad():
    """Neuere Nextcloud-Versionen antworten unter /public.php/dav/files/<token>/."""
    antwort = ANTWORT.replace("/public.php/webdav/", "/public.php/dav/files/AbCdEf123/")
    gefunden = eintraege_zerlegen(antwort, "/public.php/dav/files/AbCdEf123")
    assert [e.pfad for e in gefunden] == ["Auswertungen", "SF Optionsräume 25.csv"]
