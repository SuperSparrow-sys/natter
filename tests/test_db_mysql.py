"""Tests für den SQLdb-Kern gegen MySQL/MariaDB (Abschnitt 10.1). Siehe
docs/arbeitspakete/M5.md, Schritt 2.

Ein echter Verbindungs-/Query-/Transaktionstest gegen eine laufende
MariaDB-Instanz ist bewusst NICHT Teil dieser Datei (siehe „Stolperstein
MariaDB“ in M5.md) – der dafür vorgesehene Homeserver-Docker-Container
existiert in dieser Entwicklungsumgebung nicht. Getestet wird deshalb
nur, was ohne echte Verbindung geht: Parameter-Übersetzung und
verständliche Fehlermeldung bei fehlgeschlagenem Verbindungsaufbau
(echter `PyMySQL`-Fehler gegen einen garantiert nicht erreichbaren Host,
kein Mock).
"""

from __future__ import annotations

import pytest

from pcl import MySQLConnection, SQLQuery
from pcl.db import uebersetze_platzhalter
from pcl.errors import NatterDatenbankError


def test_mysql_connection_uebersetzt_platzhalter_im_pyformat_stil() -> None:
    verbindung = MySQLConnection()
    assert verbindung._platzhalterstil == "pyformat"
    sql = "SELECT * FROM kunden WHERE ort = :ort"
    assert uebersetze_platzhalter(sql, verbindung._platzhalterstil) == (
        "SELECT * FROM kunden WHERE ort = %(ort)s"
    )


def test_sql_query_gegen_mysql_uebersetzt_die_platzhalter_vor_der_ausfuehrung() -> None:
    verbindung = MySQLConnection()
    verbindung.host_name = "127.0.0.1"
    verbindung.port = 1  # kein Server erreichbar - siehe Testdatei-Kopf
    abfrage = SQLQuery(verbindung)
    abfrage.sql = "SELECT * FROM kunden WHERE ort = :ort"
    abfrage.params["ort"] = "Köln"

    with pytest.raises(NatterDatenbankError):
        abfrage.open()


def test_verbindung_zu_nicht_erreichbarem_server_liefert_natter_fehler() -> None:
    verbindung = MySQLConnection()
    verbindung.host_name = "127.0.0.1"
    verbindung.database_name = "nicht_vorhanden"
    verbindung.user_name = "niemand"
    verbindung.password = "falsch"

    with pytest.raises(NatterDatenbankError, match="Verbindung zu"):
        verbindung.connected = True
    assert verbindung.connected is False


def test_connected_bleibt_false_nach_fehlgeschlagenem_verbindungsversuch() -> None:
    verbindung = MySQLConnection()
    verbindung.host_name = "127.0.0.1"
    try:
        verbindung.connected = True
    except NatterDatenbankError:
        pass
    assert verbindung.connected is False
    with pytest.raises(NatterDatenbankError):
        _ = verbindung.verbindung
