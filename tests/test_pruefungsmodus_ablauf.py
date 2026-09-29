"""Der Prüfungsmodus im laufenden Hauptfenster: Ablauf ohne Neustart
(Punkt 151) und das Menü „Zuletzt geöffnet“ (Punkt 145)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster
from ide.shell.startbild import zuletzt_merken
from pcl.pruefungsmodus import starten


@pytest.fixture
def pruefung(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    """Eigene Einstellungsdatei für den Modus, wie in
    tests/test_pruefungsmodus.py."""
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _gesperrt(fenster: HauptFenster) -> dict[str, object]:
    return {
        "anzeige": fenster.pruefungsanzeige.text(),
        "beispiele": fenster._beispiel_menue.title(),
        "vervollstaendigung": fenster.vervollstaendigung_aktion.isEnabled(),
        "zuletzt": fenster._zuletzt_menue.title(),
    }


def test_restzeit_zaehlt_und_nach_dem_ablauf_ist_alles_wieder_frei(
    pruefung: QSettings, qtbot, pruefung_beenden
) -> None:
    starten(pruefung, dauer=timedelta(hours=2))
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster._pruefungsuhr.setInterval(50)

    vorher = _gesperrt(fenster)
    assert "1:59 h" in vorher["anzeige"]
    assert vorher["beispiele"] == "Beispielprojekte (im Prüfungsmodus gesperrt)"
    assert vorher["vervollstaendigung"] is False
    assert "gesperrt" in vorher["zuletzt"]

    # Eine andere Restzeit muss ohne Zutun in der Anzeige ankommen.
    # Ein zweiter Start ändert nichts, solange der Modus läuft
    # (Punkt 227); dafür wird er hier im Test vorher geleert.
    pruefung_beenden(pruefung)
    starten(pruefung, dauer=timedelta(hours=3))
    qtbot.waitUntil(lambda: "2:59 h" in fenster.pruefungsanzeige.text(), timeout=3000)

    # Und nach dem Ablauf ist alles wieder im Normalzustand.
    pruefung_beenden(pruefung)
    starten(pruefung, dauer=timedelta(milliseconds=300))
    qtbot.waitUntil(lambda: fenster.pruefungsanzeige.text() == "", timeout=3000)
    nachher = _gesperrt(fenster)
    assert nachher["beispiele"] == "Beispielprojekte"
    assert nachher["vervollstaendigung"] is True
    assert nachher["zuletzt"] == "Zuletzt geöffnet"


def test_zuletzt_geoeffnet_ist_im_pruefungsmodus_gesperrt(
    pruefung: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projektdatei = tmp_path / "Garten" / "Garten.natter"
    projektdatei.parent.mkdir()
    projektdatei.write_text("{}", encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    zuletzt_merken(fenster._design_einstellungen, projektdatei)
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    fenster._pruefungsmodus_aktion()

    assert not fenster._zuletzt_menue.isEnabled()
    assert fenster._zuletzt_menue.actions() == []
    fenster._zuletzt_menue_aufbauen()
    assert fenster._zuletzt_menue.actions() == []
    assert fenster._zuletzt_geoeffnetes_oeffnen(projektdatei) is None
    assert fenster.projekt is None


def test_zuletzt_geoeffnet_meldet_eine_beschaedigte_projektdatei(
    pruefung: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projektdatei = tmp_path / "Garten" / "Garten.natter"
    projektdatei.parent.mkdir()
    projektdatei.write_text("{ kaputt", encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    zuletzt_merken(fenster._design_einstellungen, projektdatei)
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )

    fenster._zuletzt_menue_aufbauen()
    eintraege = fenster._zuletzt_menue.actions()
    assert [e.text() for e in eintraege] == ["Garten"]
    eintraege[0].trigger()

    assert len(meldungen) == 1
    assert "beschädigt" in meldungen[0]
    assert fenster.projekt is None


def test_ein_vorher_geoeffnetes_diagramm_erzeugt_im_modus_keinen_code(
    pruefung_beenden, pruefung: QSettings, qtbot, tmp_path: Path
) -> None:
    # Punkt 188: das Diagrammfenster prüfte den Modus nur beim Aufbau
    # seines Menüs.
    from ide.diagramm import diagramm_erzeugen

    pfad = tmp_path / "s.pdiag"
    diagramm_erzeugen("struktogramm", pfad, "s")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    diagramm = fenster.diagramm_oeffnen(pfad)
    qtbot.addWidget(diagramm)
    erzeugen = diagramm.aktionen["Quelltext/Erzeugen …"]
    assert erzeugen.isEnabled()

    starten(pruefung, dauer=timedelta(hours=2))
    fenster._pruefungsmodus_nachfuehren()

    assert not erzeugen.isEnabled()
    assert (
        diagramm.quelltext_erzeugen("fenster", "alles", tmp_path / "x.py")
        is None
    )

    pruefung_beenden(pruefung)
    fenster._pruefungsmodus_nachfuehren()

    assert erzeugen.isEnabled()
    code = diagramm.quelltext_erzeugen("fenster", "alles", tmp_path / "x.py")
    assert code is not None
    assert "def s(" in code.ansicht.toPlainText()


def test_ein_im_modus_geoeffnetes_diagramm_ist_danach_wieder_frei(
    pruefung_beenden, pruefung: QSettings, qtbot, tmp_path: Path
) -> None:
    from ide.diagramm import diagramm_erzeugen

    pfad = tmp_path / "s.pdiag"
    diagramm_erzeugen("struktogramm", pfad, "s")
    starten(pruefung, dauer=timedelta(hours=2))
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    diagramm = fenster.diagramm_oeffnen(pfad)
    qtbot.addWidget(diagramm)
    erzeugen = diagramm.aktionen["Quelltext/Erzeugen …"]
    assert not erzeugen.isEnabled()

    pruefung_beenden(pruefung)
    fenster._pruefungsmodus_nachfuehren()

    assert erzeugen.isEnabled()


def test_projekt_oeffnen_sperrt_beispiele_im_pruefungsmodus(
    pruefung_beenden, pruefung: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Punkt 197: gesperrt war nur das Menü „Datei → Beispielprojekte“.
    import shutil

    from ide.shell.startbild import beispielprojekte
    from pcl.pruefungsmodus import GESPERRT_HINWEIS

    original = beispielprojekte()[0]
    # Eine Arbeitskopie wie in Dokumente\Natter\Beispielprojekte, hier
    # in tmp_path, damit das eingecheckte Beispiel unberührt bleibt.
    kopie_ordner = tmp_path / "Kopien" / original.parent.name
    shutil.copytree(original.parent, kopie_ordner)
    kopie = kopie_ordner / original.name
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    starten(pruefung, dauer=timedelta(hours=2))
    fenster._pruefungsmodus_nachfuehren()

    assert fenster.projekt_oeffnen_gemeldet(original) is None
    assert fenster.projekt_oeffnen_gemeldet(kopie) is None
    assert fenster.projekt_oeffnen_gemeldet(kopie_ordner) is None
    assert fenster.beispiel_oeffnen(original) is None
    assert fenster.projekt is None
    assert len(meldungen) == 4
    assert all(GESPERRT_HINWEIS in text for text in meldungen)

    # Ein eigenes Projekt öffnet weiter.
    from ide.project import projekt_erzeugen

    eigenes = projekt_erzeugen("console", tmp_path / "Garten", "Garten")
    projekt = fenster.projekt_oeffnen_gemeldet(
        eigenes.ordner / "Garten.natter"
    )
    assert projekt is not None
    assert projekt.name == "Garten"

    pruefung_beenden(pruefung)
    # Nach dem Ende geht die Kopie wieder auf.
    assert fenster.projekt_oeffnen_gemeldet(kopie) is not None


def _offene_reiter(fenster: HauptFenster) -> list[str]:
    return [
        fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())
    ]


def test_datei_oeffnen_sperrt_die_dateien_der_beispiele(
    pruefung: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Punkt 211: über „Datei → Öffnen …“ ließ sich jede Unit eines
    # Beispiels einzeln öffnen, im Original wie in der Arbeitskopie.
    import shutil

    from ide.shell.startbild import beispielprojekte
    from pcl.pruefungsmodus import GESPERRT_HINWEIS

    original = next(
        p for p in beispielprojekte() if p.parent.name == "03_Taschenrechner"
    ).parent
    kopie = tmp_path / "Kopien" / original.name
    shutil.copytree(original, kopie)
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    starten(pruefung, dauer=timedelta(hours=2))
    fenster._pruefungsmodus_nachfuehren()
    vorher = _offene_reiter(fenster)

    for pfad in (
        original / "u_main.py",
        kopie / "u_main.py",
        kopie / "u_main.pfm",
    ):
        fenster.oeffnen(pfad)

    assert _offene_reiter(fenster) == vorher
    assert len(meldungen) == 3
    assert all(GESPERRT_HINWEIS in text for text in meldungen)

    # Eine Datei eines eigenen Projekts öffnet weiter.
    eigene = tmp_path / "Garten" / "notizen.py"
    eigene.parent.mkdir()
    eigene.write_text("x = 1\n", encoding="utf-8")
    fenster.oeffnen(eigene)
    assert "notizen.py" in _offene_reiter(fenster)


def test_eine_kopie_mit_umbenannter_projektdatei_bleibt_gesperrt(
    pruefung: QSettings, hauptfenster, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Punkt 251: eine Kopie erkannte Natter nur am Namen ihrer
    # `.natter`. Umbenannt öffnete sie sich samt Lösung, und eine
    # einzeln herauskopierte Unit unter anderem Namen ebenso.
    import shutil

    from ide.shell.startbild import beispiel_nach_inhalt, beispielprojekte
    from pcl.pruefungsmodus import GESPERRT_HINWEIS

    original = next(
        p for p in beispielprojekte() if p.parent.name == "03_Taschenrechner"
    )
    kopie = tmp_path / "Rechner"
    shutil.copytree(original.parent, kopie)
    projektdatei = kopie / "Rechner.natter"
    (kopie / original.name).rename(projektdatei)
    einzeln = tmp_path / "Lose" / "loesung.py"
    einzeln.parent.mkdir()
    shutil.copy(original.parent / "u_main.py", einzeln)
    assert beispiel_nach_inhalt(kopie) == original.parent
    assert beispiel_nach_inhalt(einzeln) == original.parent

    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    fenster = hauptfenster
    starten(pruefung, dauer=timedelta(hours=2))
    fenster._pruefungsmodus_nachfuehren()
    vorher = _offene_reiter(fenster)

    assert fenster.projekt_oeffnen_gemeldet(projektdatei) is None
    assert fenster.projekt is None
    fenster.oeffnen(einzeln)
    fenster.oeffnen(kopie / "u_main.py")

    assert _offene_reiter(fenster) == vorher
    assert len(meldungen) == 3
    assert all(GESPERRT_HINWEIS in text for text in meldungen)

    # Ein eigenes Projekt im selben Ordner darüber sperrt das nicht.
    from ide.project import projekt_erzeugen

    eigenes = projekt_erzeugen("console", tmp_path / "Garten", "Garten")
    assert beispiel_nach_inhalt(eigenes.ordner) is None
    assert fenster.projekt_oeffnen_gemeldet(
        eigenes.ordner / "Garten.natter"
    ) is not None


def test_datei_oeffnen_nimmt_fuer_ein_original_die_arbeitskopie(
    qtbot, tmp_path: Path
) -> None:
    """Auch außerhalb des Prüfungsmodus wird ein Original nicht an Ort
    und Stelle geöffnet: der Designer schriebe jede Änderung sofort ins
    Beispiel zurück (Punkt 211)."""
    from ide.pfade import beispielkopien_ordner
    from ide.shell.startbild import beispielprojekte

    original = next(
        p for p in beispielprojekte() if p.parent.name == "01_Begruessung"
    ).parent
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.oeffnen(original / "u_main.py")

    editor = fenster._tab_inhalt(fenster.editor_tabs.currentWidget())
    geoeffnet = Path(editor.property("pfad"))
    assert geoeffnet.resolve() == (
        beispielkopien_ordner() / original.name / "u_main.py"
    ).resolve()
    assert "Arbeitskopie" in fenster.statusBar().currentMessage()



def test_ein_offenes_beispiel_geht_beim_einschalten_zu(
    pruefung: QSettings, hauptfenster, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Punkt 228: eine offene Arbeitskopie blieb ganz bedienbar.
    import shutil

    from ide.shell.startbild import beispielprojekte
    from pcl.pruefungsmodus import GESPERRT_HINWEIS

    original = next(
        p for p in beispielprojekte() if p.parent.name == "03_Taschenrechner"
    )
    kopie = tmp_path / "Kopien" / original.parent.name
    shutil.copytree(original.parent, kopie)
    fenster = hauptfenster
    fenster.projekt_oeffnen(kopie / original.name)
    unit = kopie / "u_main.py"
    fenster.datei_oeffnen(unit)
    assert fenster.projekt_dateien()
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    assert fenster._pruefungsmodus_aktion() is True

    assert fenster.projekt is None
    assert _offene_reiter(fenster) == []
    # Strg+P findet nichts mehr, und direkt geht die Datei nicht auf.
    assert fenster.projekt_dateien() == []
    assert fenster.datei_oeffnen(unit) is None
    fenster._datei_an_zeile(unit, 3)
    assert _offene_reiter(fenster) == []
    assert meldungen and all(GESPERRT_HINWEIS in m for m in meldungen)
    # Die Suche in allen Dateien hat kein Projekt mehr.
    fenster._in_dateien_suchen_aktion()
    assert "Kein Projekt offen" in fenster.statusBar().currentMessage()
    assert getattr(fenster, "letzter_dateisuche_dialog", None) is None
