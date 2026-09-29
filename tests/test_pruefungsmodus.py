"""Tests für den Prüfungsmodus (M11, Abschnitt 6). Headless.

Gefordert: Natter wird im Unterricht auch in
Leistungssituationen benutzt, und dann darf das Programm nicht die
halbe Aufgabe lösen.

Zwei Eigenschaften sind entscheidend und werden deshalb am genauesten
geprüft: er muss einen Neustart überstehen – sonst wäre er mit
einem Schließen und Öffnen ausgehebelt – und er muss von selbst
auslaufen, damit kein vergessener Modus einen Schulrechner sperrt.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.shell.hauptfenster import HauptFenster
from pcl.fehlerkatalog import Fehlermeldung
from pcl.pruefungsmodus import (
    DAUER,
    ENDE_SCHLUESSEL,
    laeuft,
    restzeit,
    restzeit_text,
    starten,
)

JETZT = datetime(2026, 9, 19, 9, 0, 0)


@pytest.fixture
def werte(tmp_path: Path) -> QSettings:
    """Eigene Einstellungsdatei – ein Test darf den echten Rechner
    nicht vier Stunden in den Prüfungsmodus versetzen."""
    return QSettings(str(tmp_path / "pruefung.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def echte_einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    """Legt auch die IDE-weite Fassung auf eine Testdatei um, damit die
    Oberflächen-Tests nicht in die echten Einstellungen schreiben."""
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


# -- Grundverhalten ------------------------------------------------------


def test_am_anfang_laeuft_keine_pruefung(werte: QSettings) -> None:
    assert laeuft(werte) is False
    assert restzeit(werte) is None
    assert restzeit_text(werte) == ""


def test_nach_dem_start_laeuft_er(werte: QSettings) -> None:
    starten(werte, jetzt=JETZT)

    assert laeuft(werte, jetzt=JETZT + timedelta(hours=1)) is True


def test_er_laeuft_nach_vier_stunden_von_selbst_aus(werte: QSettings) -> None:
    """Niemand soll daran denken müssen, ihn abzuschalten, und ein
    vergessener Modus darf keinen Schulrechner auf Dauer sperren."""
    starten(werte, jetzt=JETZT)

    assert laeuft(werte, jetzt=JETZT + DAUER - timedelta(minutes=1)) is True
    assert laeuft(werte, jetzt=JETZT + DAUER + timedelta(seconds=1)) is False


def test_er_uebersteht_einen_neustart(tmp_path: Path) -> None:
    """Der Kern der Sache: ein Schalter im Speicher wäre mit einem
    Schließen und Öffnen ausgehebelt."""
    pfad = str(tmp_path / "pruefung.ini")
    starten(QSettings(pfad, QSettings.Format.IniFormat), jetzt=JETZT)

    # Frisch geladen, als wäre Natter neu gestartet worden
    danach = QSettings(pfad, QSettings.Format.IniFormat)

    assert laeuft(danach, jetzt=JETZT + timedelta(hours=2)) is True


def test_gespeichert_wird_das_ende_nicht_ein_schalter(werte: QSettings) -> None:
    starten(werte, jetzt=JETZT)

    gespeichert = werte.value(ENDE_SCHLUESSEL, "", type=str)
    beginn, schluss, _ = gespeichert.split("|")

    # In Sekunden seit 1970, unabhängig von der Zeitzone (Punkt 227).
    assert int(beginn) == int(JETZT.timestamp())
    assert int(schluss) == int((JETZT + DAUER).timestamp())


def test_ein_kaputter_wert_allein_sperrt_nicht(werte: QSettings) -> None:
    """Lieber die Werkzeuge freigeben, als eine kaputte
    Einstellungsdatei zu einer Dauersperre werden zu lassen - solange
    keine andere Stelle eine laufende Prüfung vermerkt."""
    werte.setValue(ENDE_SCHLUESSEL, "kein Datum")

    assert laeuft(werte) is False


def test_die_restzeit_steht_als_text_bereit(werte: QSettings) -> None:
    """Wer nicht sieht, dass der Modus an ist, sucht den Fehler bei
    sich."""
    starten(werte, jetzt=JETZT)

    text = restzeit_text(werte, jetzt=JETZT + timedelta(hours=1, minutes=15))

    assert text == "Prüfungsmodus – noch 2:45 h"


# -- Nicht vorzeitig zu beenden (Punkt 227) ------------------------------


def test_eine_andere_zeitzone_beendet_ihn_nicht(
    werte: QSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die Zeitzone darf unter Windows jedes Standardkonto ändern. Bis
    0.3.6 rechnete der Modus mit der Ortszeit, zwölf Stunden weiter
    war er vorbei."""
    import pcl.pruefungsmodus as modul

    starten(werte)

    class _ZwoelfStundenWeiter(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            return datetime.now(tz) + timedelta(hours=12)

    monkeypatch.setattr(modul, "datetime", _ZwoelfStundenWeiter)

    assert laeuft(werte) is True
    assert restzeit(werte) > timedelta(hours=3)


def test_ein_geloeschter_wert_beendet_ihn_nicht(
    werte: QSettings,
) -> None:
    starten(werte)

    werte.remove(ENDE_SCHLUESSEL)
    werte.sync()

    assert laeuft(werte) is True
    # Die fehlende Stelle ist wiederhergestellt.
    assert werte.value(ENDE_SCHLUESSEL, "", type=str)


def test_er_laeuft_solange_eine_einzige_stelle_ihn_vermerkt(
    werte: QSettings, _pruefungsablagen_isoliert
) -> None:
    datei, registry = _pruefungsablagen_isoliert
    starten(werte)

    werte.setValue(ENDE_SCHLUESSEL, "kein Datum")
    datei.text = None

    assert laeuft(werte) is True
    assert datei.lesen() == registry.text


def test_ein_gefaelschter_vermerk_zaehlt_nicht(werte: QSettings) -> None:
    import pcl.pruefungsmodus as modul

    beginn = int(JETZT.timestamp())
    echt = modul._vermerk(beginn, beginn + 3600)
    gefaelscht = echt.rsplit("|", 1)[0] + "|" + "0" * 64
    werte.setValue(ENDE_SCHLUESSEL, gefaelscht)

    assert laeuft(werte, jetzt=JETZT + timedelta(minutes=5)) is False

    # Ein gültiger Vermerk mit nachträglich verschobenem Ende auch nicht.
    b, _, pruefwert = echt.split("|")
    werte.setValue(ENDE_SCHLUESSEL, f"{b}|{beginn + 7200}|{pruefwert}")

    assert laeuft(werte, jetzt=JETZT + timedelta(minutes=90)) is False


def test_er_geht_nie_laenger_als_vier_stunden(werte: QSettings) -> None:
    import pcl.pruefungsmodus as modul

    beginn = int(JETZT.timestamp())
    werte.setValue(
        ENDE_SCHLUESSEL, modul._vermerk(beginn, beginn + 10 * 3600)
    )

    assert laeuft(werte, jetzt=JETZT + timedelta(hours=3)) is True
    assert laeuft(werte, jetzt=JETZT + DAUER + timedelta(seconds=1)) is False
    # Auch starten() nimmt keine längere Dauer an.
    ende = starten(werte, dauer=timedelta(hours=9), jetzt=JETZT + DAUER)
    assert ende.timestamp() == (JETZT + 2 * DAUER).timestamp()


def test_ein_vermerk_mit_spaeterem_beginn_zaehlt_nicht(
    werte: QSettings,
) -> None:
    import pcl.pruefungsmodus as modul

    beginn = int((JETZT + timedelta(days=1)).timestamp())
    werte.setValue(
        ENDE_SCHLUESSEL, modul._vermerk(beginn, beginn + 3600)
    )

    assert laeuft(werte, jetzt=JETZT) is False


def test_ein_anderer_kontoname_in_der_umgebung_beendet_ihn_nicht(
    werte: QSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 249: `LOGNAME`, `USER` und `USERNAME` darf jedes Konto
    für sich setzen. Früher ging der Name daraus in den Prüfwert ein,
    und mit einem anderen Wert war der Modus aus."""
    starten(werte, jetzt=JETZT)
    spaeter = JETZT + timedelta(hours=1)
    assert laeuft(werte, jetzt=spaeter) is True

    for name in ("LOGNAME", "USER", "LNAME", "USERNAME"):
        monkeypatch.setenv(name, "jemand_anderes")

    assert laeuft(werte, jetzt=spaeter) is True


def test_ein_vermerk_aus_036_laeuft_weiter_und_wird_umgeschrieben(
    werte: QSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein Modus, der beim Update läuft, endet nicht, und danach hängt
    er nicht mehr an der Umgebung."""
    import getpass

    import pcl.pruefungsmodus as modul

    beginn = int(JETZT.timestamp())
    ende = beginn + 3600
    alt = modul._pruefwert(beginn, ende, getpass.getuser())
    werte.setValue(ENDE_SCHLUESSEL, f"{beginn}|{ende}|{alt}")
    spaeter = JETZT + timedelta(minutes=30)

    assert laeuft(werte, jetzt=spaeter) is True
    assert werte.value(ENDE_SCHLUESSEL) == modul._vermerk(beginn, ende)
    monkeypatch.setenv("USERNAME", "jemand_anderes")
    monkeypatch.setenv("LOGNAME", "jemand_anderes")
    assert laeuft(werte, jetzt=spaeter) is True


def test_ein_schuelerprogramm_kann_ihn_nicht_beenden(
    werte: QSettings,
) -> None:
    """`pcl` gehört zu jedem Schülerprogramm. Es bietet kein Beenden
    mehr an, und ein zweiter Start mit kürzerer Dauer verkürzt nicht."""
    import pcl.pruefungsmodus as modul

    assert not hasattr(modul, "beenden")
    ende = starten(werte, jetzt=JETZT)

    zweites = starten(werte, dauer=timedelta(seconds=1), jetzt=JETZT)

    assert zweites == ende
    assert laeuft(werte, jetzt=JETZT + timedelta(hours=3)) is True


def test_kein_teil_von_natter_beendet_ihn_vorzeitig() -> None:
    """Auch kein Modul der IDE, das ein Schülerprogramm importieren
    könnte, löscht den Vermerk."""
    wurzel = Path(__file__).resolve().parent.parent
    for ordner in ("ide", "pcl"):
        for datei in (wurzel / ordner).rglob("*.py"):
            text = datei.read_text(encoding="utf-8")
            assert "remove(ENDE_SCHLUESSEL" not in text, datei
            assert "pruefungsmodus_beenden" not in text, datei


def test_alle_stellen_liegen_im_benutzerprofil(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import pcl.pruefungsmodus as modul

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert modul._datei_pfad() == tmp_path / "Natter" / modul.DATEINAME
    assert modul.REGISTRY_SCHLUESSEL.startswith("Software\\Natter")
    ablage = modul.DateiAblage(modul._datei_pfad())
    assert ablage.lesen() is None
    ablage.schreiben("1|2|abc")
    assert ablage.lesen() == "1|2|abc"


# -- Keine Lösungsvorschläge ---------------------------------------------


def _meldung() -> Fehlermeldung:
    return Fehlermeldung(
        ueberschrift="Fehler",
        wo="u_main.py, Zeile 12, in b_start_click",
        quelltext="    print(zaehler)",
        markierung="          ^^^^^^^",
        was="Der Name zaehler ist an dieser Stelle nicht bekannt.",
        pruefe="Ist der Name richtig geschrieben? Wurde er vorher zugewiesen?",
    )


def test_normalerweise_steht_pruefe_in_der_meldung(
    echte_einstellungen: QSettings,
) -> None:
    text = _meldung().als_text()

    assert "Zu prüfen:" in text
    assert "richtig geschrieben" in text


def test_im_pruefungsmodus_faellt_pruefe_weg(
    echte_einstellungen: QSettings,
) -> None:
    """„Zu prüfen“ ist genau der Teil, der weiterhilft – und genau deshalb
    gehört er in einer Leistungssituation nicht dazu."""
    starten(echte_einstellungen)

    text = _meldung().als_text()

    assert "Zu prüfen:" not in text
    assert "richtig geschrieben" not in text


def test_wo_und_was_bleiben_auch_im_pruefungsmodus(
    echte_einstellungen: QSettings,
) -> None:
    """Eine Schülerin soll sehen, dass und wo etwas schiefgegangen ist
    – nur nicht, woran es liegen könnte."""
    starten(echte_einstellungen)

    text = _meldung().als_text()

    assert "Wo:" in text
    assert "Zeile 12" in text
    assert "Was:" in text
    assert "nicht bekannt" in text


# -- Keine Quelltexterzeugung --------------------------------------------


@pytest.mark.parametrize("typ", ["class", "struktogramm"])
def test_quelltexterzeugung_ist_normalerweise_moeglich(
    echte_einstellungen: QSettings, tmp_path: Path, typ: str
) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "d"))

    assert fenster.aktionen["Quelltext/Erzeugen …"].isEnabled() is True


@pytest.mark.parametrize("typ", ["class", "struktogramm"])
def test_im_pruefungsmodus_ist_sie_gesperrt(
    echte_einstellungen: QSettings, tmp_path: Path, typ: str
) -> None:
    """Aus einem Klassendiagramm Python erzeugen zu lassen wäre in
    einer Leistungssituation die halbe Aufgabe."""
    starten(echte_einstellungen)

    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "d"))

    aktion = fenster.aktionen["Quelltext/Erzeugen …"]
    assert aktion.isEnabled() is False
    assert "Prüfungsmodus" in aktion.toolTip()


def test_der_eintrag_bleibt_sichtbar(echte_einstellungen: QSettings, tmp_path: Path) -> None:
    """Ein spurlos verschwundener Menüeintrag wäre verwirrender als ein
    erklärter."""
    starten(echte_einstellungen)

    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    assert fenster.aktionen["Quelltext/Erzeugen …"].isVisible() is True


def test_zeichnen_bleibt_moeglich(echte_einstellungen: QSettings, tmp_path: Path) -> None:
    """Der Modus nimmt Werkzeug weg, keine Bedienbarkeit."""
    starten(echte_einstellungen)
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)

    assert form in fenster.zeichenflaeche.formen
    assert fenster.aktionen["Datei/Speichern"].isEnabled() is True


def test_die_restzeit_steht_in_der_statusleiste_des_diagramms(
    echte_einstellungen: QSettings, tmp_path: Path
) -> None:
    starten(echte_einstellungen)

    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    assert "Prüfungsmodus" in fenster.statusBar().currentMessage()


# -- Im Hauptfenster -----------------------------------------------------


def test_das_werkzeugmenue_bietet_den_start(echte_einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    titel = [a.text() for a in fenster.menue("Werkzeuge").actions()]

    assert "Prüfungsmodus starten …" in titel


def test_ohne_bestaetigung_startet_er_nicht(
    echte_einstellungen: QSettings, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Er lässt sich vier Stunden lang nicht abschalten – das fragt man
    vorher."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )

    assert fenster._pruefungsmodus_aktion() is False
    assert laeuft(echte_einstellungen) is False


def test_mit_bestaetigung_startet_er(
    echte_einstellungen: QSettings, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    assert fenster._pruefungsmodus_aktion() is True
    assert laeuft(echte_einstellungen) is True
    assert "Prüfungsmodus" in fenster.pruefungsanzeige.text()


def test_ein_zweiter_start_verlaengert_nicht(
    echte_einstellungen: QSettings, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein zweiter Start würde die Zeit verlängern – das will in einer
    Klausur niemand."""
    starten(echte_einstellungen)
    vorher = echte_einstellungen.value(ENDE_SCHLUESSEL, "", type=str)
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    assert fenster._pruefungsmodus_aktion() is False
    assert echte_einstellungen.value(ENDE_SCHLUESSEL, "", type=str) == vorher


def test_die_anzeige_bleibt_leer_ohne_pruefung(echte_einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster.pruefungsanzeige.text() == ""


# -- Vervollstaendigung --------------------------------------------------
#
# Die letzte offene Frage aus M11, Abschnitt 6, jetzt entschieden: die
# Liste bleibt an - sie ist Schreibhilfe, und Lazarus hat sie im
# Unterricht auch. Die deutschen Erklärungen daneben fallen weg;
# "Wird beim Klicken ausgeloest" neben `on_click` ist nah an der
# Antwort auf genau die Frage, die in der Klausur steht.


def _vorschlag():
    from ide.shell.vervollstaendigung import RANG_PCL, Vorschlag

    return Vorschlag(
        name="on_click",
        art="statement",
        erklaerung="Wird beim Klicken ausgelöst",
        signatur="NoneType()",
        rang=RANG_PCL,
    )


def test_ausserhalb_der_pruefung_steht_die_erklaerung_dabei() -> None:
    assert "Wird beim Klicken ausgelöst" in _vorschlag().anzeige_text()


def test_in_der_pruefung_bleibt_nur_der_name() -> None:
    assert _vorschlag().anzeige_text(mit_erklaerung=False) == "on_click"


def test_im_pruefungsmodus_bleibt_die_liste_zu(
    echte_einstellungen: QSettings, tmp_path: Path
) -> None:
    """Bis September 2026 blieb die Liste im Prüfungsmodus an, nur ohne
    Erklärung. Der Nutzer hat entschieden, dass sie in der Prüfung
    ganz ausbleibt: auch ein Name wie `bank_abheben_konto` samt
    Parametern ist in einer Klausur schon ein Stück Antwort."""
    from ide.shell.quelltexteditor import QuelltextEditor

    quelltext = """from pcl import Form, Button


class Form1(Form):
    def create_components(self):
        self.b_start = Button(self)

    def b_start_click(self, sender):
        self.b_start.
"""
    starten(echte_einstellungen)
    editor = QuelltextEditor()
    editor.setPlainText(quelltext)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.movePosition(cursor.MoveOperation.Up)
    cursor.movePosition(cursor.MoveOperation.EndOfLine)
    editor.setTextCursor(cursor)

    anzahl = editor.vorschlaege_anzeigen(erzwungen=True)

    assert anzahl == 0
    assert not editor.vorschlagsliste.isVisible()
    assert editor.parameterhilfe_anzeigen() == ""


# ------------------------------- Kein Weg an fremden Code im Pruefmodus
#
# Punkt 8 der offenen Punkte. Die Liste "Zuletzt geoeffnet" fuehrt zu
# dem, was in der Stunde davor bearbeitet wurde - in einer Klausur
# moeglicherweise zur Loesung der Aufgabe, die gerade gestellt ist. Die
# Beispielprojekte enthalten ausformulierte Loesungen zu genau den
# Themen, die geprueft werden.


_EIN_PROJEKT = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "01_Begruessung"
    / "01_Begruessung.natter"
)


def _beispiel_menue(fenster):
    for aktion in fenster.menue("Datei").actions():
        if aktion.text().startswith("Beispielprojekte"):
            return aktion
    return None


def test_im_pruefungsmodus_fehlt_zuletzt_geoeffnet(echte_einstellungen, qtbot) -> None:
    from ide.shell.hauptfenster import HauptFenster
    from ide.shell.startbild import zuletzt_merken
    from pcl.pruefungsmodus import starten

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    zuletzt_merken(fenster.startbild._einstellungen, _EIN_PROJEKT)
    fenster.startbild.aufbauen()
    assert any(n.startswith("zuletzt:") for n in fenster.startbild.knoepfe)

    starten()
    fenster.startbild.aufbauen()

    assert not [n for n in fenster.startbild.knoepfe if n.startswith("zuletzt:")]


def test_im_pruefungsmodus_ist_das_beispielmenue_gesperrt(echte_einstellungen, qtbot) -> None:
    from ide.shell.hauptfenster import HauptFenster
    from pcl.pruefungsmodus import starten

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    assert _beispiel_menue(fenster).isEnabled()

    starten()
    fenster._beispielmenue_pruefen()

    eintrag = _beispiel_menue(fenster)
    assert not eintrag.isEnabled()
    # Gesperrt und nicht verschwunden: wer ihn sucht, soll sehen, dass
    # es ihn gibt und dass er gerade nicht geht.
    assert "gesperrt" in eintrag.text()


def test_nach_dem_einschalten_frischt_sich_beides_auf(
    echte_einstellungen, monkeypatch, qtbot
) -> None:
    """Sonst bliebe die Liste stehen, bis jemand das Fenster wechselt -
    also genau so lange, wie es darauf ankommt."""
    from PySide6.QtWidgets import QMessageBox

    from ide.shell.hauptfenster import HauptFenster
    from ide.shell.startbild import zuletzt_merken

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    zuletzt_merken(fenster.startbild._einstellungen, _EIN_PROJEKT)
    fenster.startbild.aufbauen()
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    assert fenster._pruefungsmodus_aktion() is True

    assert not [n for n in fenster.startbild.knoepfe if n.startswith("zuletzt:")]
    assert not _beispiel_menue(fenster).isEnabled()


def test_nach_ablauf_ist_beides_wieder_da(echte_einstellungen, qtbot) -> None:
    """Ein Riegel, der nach der Klausur liegenbleibt, sperrt den
    Schulrechner."""
    from datetime import datetime, timedelta

    from ide.shell.hauptfenster import HauptFenster
    from ide.shell.startbild import zuletzt_merken
    from pcl.pruefungsmodus import DAUER, starten

    # Ein Modus, der vor einer Stunde ausgelaufen ist.
    starten(
        echte_einstellungen,
        jetzt=datetime.now() - DAUER - timedelta(hours=1),
    )

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    zuletzt_merken(fenster.startbild._einstellungen, _EIN_PROJEKT)
    fenster.startbild.aufbauen()
    fenster._beispielmenue_pruefen()

    assert [n for n in fenster.startbild.knoepfe if n.startswith("zuletzt:")]
    assert _beispiel_menue(fenster).isEnabled()


# -- Design-Prüfung und Diagrammhinweise (Punkt 233) ---------------------


def test_befund_und_hinweis_verlieren_im_modus_den_loesungsteil() -> None:
    from ide.diagramm.hinweise import Hinweis
    from ide.lint.regeln import Befund

    befund = Befund(
        "r", "Layout", "hinweis", "b_ok", "Liegt außen. Nach innen ziehen.",
        "Nach innen ziehen.",
    )
    hinweis = Hinweis("r", "Überlappt. Auseinanderziehen.", (), "Auseinanderziehen.")

    assert befund.anzeige(False) == befund.meldung
    assert befund.anzeige(True) == "Liegt außen."
    assert hinweis.anzeige(True) == "Überlappt."


def test_die_design_pruefung_zeigt_im_modus_keinen_loesungsteil(
    echte_einstellungen: QSettings, tmp_path: Path, hauptfenster_bauen
) -> None:
    import json

    from ide.lint import pruefen

    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"caption": "Form1", "width": 400, "height": 300},
        "children": [
            {
                "name": "b_a",
                "type": "Button",
                "properties": {"left": 380, "top": 8, "width": 75, "height": 25},
            }
        ],
    }
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm), encoding="utf-8")
    loesungen = [b.loesung for b in pruefen(pfm) if b.loesung]
    assert loesungen
    fenster = hauptfenster_bauen()
    fenster.designer_oeffnen(pfad)
    starten(echte_einstellungen)

    fenster._design_pruefen_aktion()

    texte = [
        fenster.meldungen_liste.item(i).text()
        for i in range(fenster.meldungen_liste.count())
    ]
    assert texte
    assert not [t for t in texte for loesung in loesungen if loesung in t]


def test_der_tooltip_der_diagrammhinweise_zeigt_im_modus_keinen_loesungsteil(
    echte_einstellungen: QSettings, tmp_path: Path, qtbot
) -> None:
    from ide.diagramm.hinweise import Hinweis

    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "k.pdiag", "k")
    )
    qtbot.addWidget(fenster)
    fenster.zeichenflaeche.hinweise = [
        Hinweis("r", "Zwei Formen überlappen. Auseinanderziehen.", (),
                "Auseinanderziehen.")
    ]
    fenster._statusleiste_aktualisieren()
    assert "Auseinanderziehen" in fenster.statusBar().toolTip()

    starten(echte_einstellungen)
    fenster._statusleiste_aktualisieren()

    assert fenster.statusBar().toolTip() == "Zwei Formen überlappen."
