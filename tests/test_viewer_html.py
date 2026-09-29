"""Tests für die HTML-Vorschau (Abschnitt 11.3). Siehe
Arbeitspaket M5, Schritt 7. Headless. `open_url` wird gemockt
(kein echter Browser, wie in tests/test_files.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.viewers import HtmlVorschau


def test_htmlvorschau_zeigt_gespeicherten_inhalt(tmp_path: Path) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Highscore</h1>", encoding="utf-8")

    vorschau = HtmlVorschau(datei)

    assert "Highscore" in vorschau.browser.toPlainText()


def test_htmlvorschau_aktualisiert_sich_bei_dateiaenderung(tmp_path: Path) -> None:
    """Die tatsächliche Zustellung des Betriebssystem-Ereignisses über
    `QFileSystemWatcher` selbst ist in dieser Entwicklungsumgebung nicht
    zuverlässig genug für einen Test (Zustellung teils über 5s verzögert,
    teils gar nicht beobachtet - vermutlich Sandbox-/Virenscanner-
    Interferenz mit dem Windows-Temp-Ordner). Getestet wird deshalb die
    Reaktion auf das Signal direkt (echte Neuladung mit echtem Inhalt),
    nicht die Zustellung durch das Betriebssystem selbst - die
    Verdrahtung (`fileChanged.connect(self._neu_laden)`) bleibt
    unverändert Produktionscode."""
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Alt</h1>", encoding="utf-8")
    vorschau = HtmlVorschau(datei)

    datei.write_text("<h1>Neu</h1>", encoding="utf-8")
    vorschau._beobachter.fileChanged.emit(str(datei))

    assert "Neu" in vorschau.browser.toPlainText()


def test_im_browser_oeffnen_ruft_open_url_mit_dem_dateipfad_auf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Highscore</h1>", encoding="utf-8")
    vorschau = HtmlVorschau(datei)

    aufgerufen = []
    monkeypatch.setattr("ide.viewers.html_vorschau.open_url", lambda ziel: aufgerufen.append(ziel))

    vorschau._im_browser_oeffnen()

    assert aufgerufen == [str(datei)]


def test_verweis_mit_fremdem_schema_geht_nicht_an_windows(
    tmp_path: Path, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 332: nur `http`, `https` und `mailto` verlassen die
    Vorschau. Ausgelöst wird der Verweis wie von Hand, mit Tab und
    Eingabetaste; ein eigener Empfänger für das Schema zeigt, ob
    `QDesktopServices.openUrl` gerufen wurde."""
    from PySide6.QtCore import QObject, Qt, Slot
    from PySide6.QtGui import QDesktopServices

    class Empfaenger(QObject):
        def __init__(self) -> None:
            super().__init__()
            self.adressen: list[str] = []

        @Slot("QUrl")
        def empfangen(self, adresse) -> None:
            self.adressen.append(adresse.toString())

    datei = tmp_path / "seite.html"
    datei.write_text(
        '<p><a href="natterprobe:etwas">Verweis</a></p>',
        encoding="utf-8",
    )
    browser_aufrufe: list[str] = []
    monkeypatch.setattr(
        "ide.viewers.html_vorschau.open_url", browser_aufrufe.append
    )
    empfaenger = Empfaenger()
    QDesktopServices.setUrlHandler("natterprobe", empfaenger, "empfangen")
    try:
        vorschau = HtmlVorschau(datei)
        qtbot.addWidget(vorschau)
        vorschau.show()
        vorschau.browser.setFocus()
        qtbot.keyClick(vorschau.browser, Qt.Key.Key_Tab)
        qtbot.keyClick(vorschau.browser, Qt.Key.Key_Return)
        qtbot.wait(50)
    finally:
        QDesktopServices.unsetUrlHandler("natterprobe")

    assert empfaenger.adressen == []
    assert browser_aufrufe == []


def test_verweise_funktionieren_auch_nach_dem_ersten_seitenwechsel(
    tmp_path: Path, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 368: eine kleine Website aus zwei Seiten lässt sich in der
    Vorschau durchklicken, hin, zu einer Sprungmarke und zurück.
    Ausgelöst wird jeder Verweis mit Tab und Eingabetaste. Ein
    Empfänger für `file` zeigt, ob etwas an Windows gegangen wäre."""
    from PySide6.QtCore import QObject, Qt, Slot
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMainWindow

    class Empfaenger(QObject):
        def __init__(self) -> None:
            super().__init__()
            self.adressen: list[str] = []

        @Slot("QUrl")
        def empfangen(self, adresse) -> None:
            self.adressen.append(adresse.toString())

    (tmp_path / "index.html").write_text(
        '<h1>Startseite</h1><p><a href="seite2.html">weiter</a></p>',
        encoding="utf-8",
    )
    fuellung = "".join(f"<p>Absatz {n}</p>" for n in range(200))
    (tmp_path / "seite2.html").write_text(
        '<h1>Seite zwei</h1><p><a href="#ende">nach unten</a></p>'
        f'{fuellung}<p><a name="ende"></a>'
        '<a href="index.html">zurück</a></p>',
        encoding="utf-8",
    )
    browser_aufrufe: list[str] = []
    monkeypatch.setattr(
        "ide.viewers.html_vorschau.open_url", browser_aufrufe.append
    )
    empfaenger = Empfaenger()
    QDesktopServices.setUrlHandler("file", empfaenger, "empfangen")
    try:
        fenster = QMainWindow()
        qtbot.addWidget(fenster)
        vorschau = HtmlVorschau(tmp_path / "index.html")
        fenster.setCentralWidget(vorschau)
        fenster.resize(400, 300)
        fenster.show()
        browser = vorschau.browser

        def verweis_folgen() -> None:
            browser.setFocus()
            qtbot.keyClick(browser, Qt.Key.Key_Tab)
            qtbot.keyClick(browser, Qt.Key.Key_Return)
            qtbot.wait(50)

        verweis_folgen()
        assert "Seite zwei" in browser.toPlainText()

        verweis_folgen()
        assert "Seite zwei" in browser.toPlainText()
        assert browser.verticalScrollBar().value() > 0

        verweis_folgen()
        assert "Startseite" in browser.toPlainText()
    finally:
        QDesktopServices.unsetUrlHandler("file")

    assert fenster.statusBar().currentMessage() == ""
    assert empfaenger.adressen == []
    assert browser_aufrufe == []


def _ist_geladen(ressource: object) -> bool:
    """Ob `QTextDocument.resource` etwas Brauchbares geliefert hat:
    Bytes der Datei oder ein Bild, das nicht leer ist."""
    if ressource is None:
        return False
    ist_leer = getattr(ressource, "isNull", None)
    if ist_leer is not None:
        return not ist_leer()
    return bool(ressource)


def _bildnamen(dokument) -> list[str]:
    """Die Namen aller Bilder im Dokument, in Tabellen eingeschlossen."""
    namen: list[str] = []
    block = dokument.begin()
    while block.isValid():
        teil = block.begin()
        while not teil.atEnd():
            zeichen = teil.fragment().charFormat()
            if zeichen.isImageFormat():
                namen.append(zeichen.toImageFormat().name())
            teil += 1
        block = block.next()
    return namen


@pytest.mark.parametrize("art", ["html", "md"])
def test_bilder_und_verweise_bleiben_im_ordner_der_datei(
    art: str, tmp_path: Path, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 370, für HTML-Vorschau und Markdown-Ansicht: ein Bild
    oder Verweis außerhalb des Ordners der Datei, mit `..`, als
    absoluter Pfad oder auf einem anderen Rechner, wird weder geladen
    noch geöffnet, und für den Netzpfad fragt nichts das Dateisystem.

    Der Rechner `natter-attrappe` wird nie wirklich angefragt: eine
    Wache ersetzt das Laden in `QTextBrowser` selbst, zeichnet jede
    Anfrage auf und reicht nur solche weiter, die weder die Attrappe
    noch den Nachbarordner nennen. Ebenso zeichnen `Path.resolve`,
    `Path.is_file` und `Path.exists` jede Frage nach der Attrappe auf
    und geben nichts weiter. So bleibt auch ein Stand ohne Grenze beim
    Nachprüfen vom Netz fern.

    Geprüft werden außerdem die Bildnamen im gesetzten Dokument: Qt
    versucht einen Namen selbst als Datei zu öffnen, wenn kein Bild
    kommt, an jeder Wache vorbei. Deshalb darf dort nur noch ein Name
    im Ordner oder ein leerer stehen."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QColor, QImage, QTextDocument
    from PySide6.QtWidgets import QMainWindow, QTextBrowser

    from ide.viewers import MarkdownAnsicht

    fremd = "aussen_f370"
    attrappe = "natter-attrappe"
    aufgabe = tmp_path / "aufgabe"
    aussen = tmp_path / fremd
    aufgabe.mkdir()
    aussen.mkdir()
    bild = QImage(4, 4, QImage.Format.Format_RGB32)
    bild.fill(QColor("red"))
    assert bild.save(str(aufgabe / "bild.png"))
    assert bild.save(str(aussen / "geheim.png"))
    (aussen / "seite.html").write_text("<h1>Fremd</h1>", encoding="utf-8")

    geheim = aussen / "geheim.png"
    netz = "\\\\" + attrappe + "\\freigabe\\"
    bilder = [
        f"../{fremd}/geheim.png",
        geheim.as_posix(),
        f"file://./{geheim.as_posix()}",
        "\\\\?\\" + str(geheim),
        netz + "a.png",
        f"file://{attrappe}/freigabe/b.png",
    ]
    verweise = [
        f"../{fremd}/seite.html",
        netz + "c.html",
        f"file:////{attrappe}/freigabe/d.html",
        f"file://{attrappe}/freigabe/e.html",
    ]

    anfragen: list[str] = []
    original_laden = QTextBrowser.loadResource
    ersatz = QImage(1, 1, QImage.Format.Format_RGB32)
    ersatz.fill(QColor("blue"))

    def wache(browser, typ, name):
        anfragen.append(name.toString())
        if attrappe in name.toString() or fremd in name.toString():
            # Ein Ersatzbild und weder `None` noch leere Bytes: auf
            # beides hin öffnet Qt die Adresse oder den Bildnamen
            # selbst.
            return ersatz
        return original_laden(browser, typ, name)

    monkeypatch.setattr(QTextBrowser, "loadResource", wache)

    fragen: list[str] = []

    def aufzeichner(methode: str, antwort):
        original = getattr(Path, methode)

        def ersatz(pfad: Path, *args, **kwargs):
            if attrappe in str(pfad):
                fragen.append(f"{methode}: {pfad}")
                return pfad if antwort is None else antwort
            return original(pfad, *args, **kwargs)

        monkeypatch.setattr(Path, methode, ersatz)

    aufzeichner("resolve", None)
    aufzeichner("is_file", False)
    aufzeichner("exists", False)

    if art == "html":
        datei = aufgabe / "index.html"
        datei.write_text(
            "<h1>Aufgabe</h1>"
            + "".join(f'<img src="{q}">' for q in ["bild.png", *bilder]),
            encoding="utf-8",
        )
        ansicht = HtmlVorschau(datei)
        browser = ansicht.browser
    else:
        # In Markdown hebt ein Rückstrich den nächsten auf.
        datei = aufgabe / "index.md"
        datei.write_text(
            "# Aufgabe\n\n"
            + "".join(
                f"![b]({q.replace(chr(92), chr(92) * 2)})\n\n"
                for q in ["bild.png", *bilder]
            ),
            encoding="utf-8",
        )
        ansicht = MarkdownAnsicht(datei)
        browser = ansicht.ansicht
    angefordert: list[Path] = []
    if art == "md":
        ansicht.datei_angefordert.connect(angefordert.append)

    fenster = QMainWindow()
    qtbot.addWidget(fenster)
    fenster.setCentralWidget(ansicht)
    meldungen: list[str] = []
    fenster.statusBar().messageChanged.connect(meldungen.append)
    fenster.resize(400, 300)
    fenster.show()
    qtbot.wait(50)

    for verweis in verweise:
        ansicht._verweis_geklickt(QUrl(verweis))

    fremde_anfragen = [
        a for a in anfragen if attrappe in a or fremd in a
    ]
    assert fremde_anfragen == []
    dokument = browser.document()
    im_ordner = QUrl.fromLocalFile(str(aufgabe / "bild.png")).toString()
    assert sorted(_bildnamen(dokument)) == sorted(
        [im_ordner] + [""] * len(bilder)
    )
    bildart = QTextDocument.ResourceType.ImageResource
    assert _ist_geladen(dokument.resource(bildart, QUrl(im_ordner))), (
        "das Bild neben der Datei fehlt"
    )
    assert fragen == []
    assert angefordert == []
    assert "Aufgabe" in browser.toPlainText()
    abgewiesen = [m for m in meldungen if "nicht geöffnet" in m]
    assert len(abgewiesen) == len(verweise)


def test_vorschau_zeigt_ansi_datei_und_meldet_eine_fehlende(
    tmp_path: Path, qtbot
) -> None:
    """Punkt 377: eine Datei in der Windows-Codepage wird angezeigt,
    und eine während der Vorschau gelöschte Datei ergibt beim
    Neuladen einen Hinweis statt einer Ausnahme."""
    datei = tmp_path / "alt.html"
    datei.write_bytes("<h1>Grüße</h1>".encode("cp1252"))

    vorschau = HtmlVorschau(datei)
    qtbot.addWidget(vorschau)
    assert "Grüße" in vorschau.browser.toPlainText()

    datei.unlink()
    vorschau._beobachter.fileChanged.emit(str(datei))

    assert "lässt sich nicht lesen" in vorschau.browser.toPlainText()

def test_verweise_die_nicht_aufgehen_bekommen_je_einen_eigenen_satz(
    tmp_path: Path, qtbot
) -> None:
    """Punkt 383: ein Tippfehler im Dateinamen, eine PDF und ein Verweis
    aus dem Ordner hinaus ergeben drei verschiedene Meldungen, und
    HTML-Vorschau und Markdown-Ansicht formulieren sie gleich. Nur die
    Vorschau nennt bei der PDF zusätzlich „Im Browser öffnen“, denn nur
    sie hat den Knopf."""
    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QMainWindow

    from ide.viewers import MarkdownAnsicht

    aufgabe = tmp_path / "aufgabe"
    (aufgabe / "seiten").mkdir(parents=True)
    (aufgabe / "seiten" / "kontakt.html").write_text(
        "<h1>Kontakt</h1>", encoding="utf-8"
    )
    (aufgabe / "plan.pdf").write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    (tmp_path / "draussen.html").write_text("Fremd", encoding="utf-8")
    verweise = ["seiten/kontackt.html", "plan.pdf", "../draussen.html"]

    def meldungen(ansicht) -> list[str]:
        fenster = QMainWindow()
        qtbot.addWidget(fenster)
        fenster.setCentralWidget(ansicht)
        ergebnis = []
        for verweis in verweise:
            fenster.statusBar().clearMessage()
            ansicht._verweis_geklickt(QUrl(verweis))
            ergebnis.append(fenster.statusBar().currentMessage())
        return ergebnis

    (aufgabe / "index.html").write_text("<h1>Start</h1>", encoding="utf-8")
    (aufgabe / "index.md").write_text("# Start\n", encoding="utf-8")
    vorschau = meldungen(HtmlVorschau(aufgabe / "index.html"))
    angefordert: list[Path] = []
    md_ansicht = MarkdownAnsicht(aufgabe / "index.md")
    md_ansicht.datei_angefordert.connect(angefordert.append)
    markdown = [
        m.replace("index.md", "index.html") for m in meldungen(md_ansicht)
    ]

    assert len(set(vorschau)) == 3, vorschau
    fehlt, pdf, draussen = vorschau
    assert "„seiten/kontackt.html“ gibt es neben „index.html“ nicht" in fehlt
    assert "Im Browser öffnen" in pdf
    assert "außerhalb" in draussen
    assert markdown[0] == fehlt
    assert pdf.startswith(markdown[1]) and markdown[1]
    assert markdown[2] == draussen
    assert angefordert == []
