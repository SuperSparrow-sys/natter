"""Was HTML-Vorschau und Markdown-Ansicht laden und öffnen dürfen.

Beide Ansichten zeigen Dateien aus fremder Hand, etwa eine
eingesammelte Abgabe. Ein Bild oder Verweis darin kann auf jeden Pfad
zeigen: mit `..` aus dem Ordner hinaus, auf ein anderes Laufwerk oder
als Netzpfad auf einen anderen Rechner. Beim Anzeigen
lud `QTextBrowser` jedes Bild selbst, im Hauptfaden und für ein Bild
mehrfach. Ein Netzpfad verband Natter so ohne Klick mit dem genannten
Rechner, und war der nicht erreichbar, stand die Oberfläche.

Deshalb gilt in beiden Ansichten dieselbe Grenze wie im Designer: ein
Ordner und was darunter liegt. Liegt die Datei in einem geöffneten
Projekt, ist das der Projektordner, sonst der Ordner der Datei. Mit
dem Ordner der Datei allein fehlten auf einer Unterseite wie
`seiten/kontakt.html` die Bilder aus `../bilder/`, und der Verweis
zurück auf `../index.html` wurde abgewiesen.

Entschieden wird allein am Text des Pfads, bevor irgendetwas das
Dateisystem fragt; auch `Path.resolve()` hätte einen Netzpfad schon
angefragt.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray, QUrl
from PySide6.QtGui import QTextCursor, QTextDocument, QTextImageFormat


def pfad_im_ordner(
    adresse: QUrl, ordner: Path, bezug: Path | None = None
) -> Path | None:
    """Die Datei, auf die `adresse` zeigt, wenn sie in `ordner` oder
    darunter liegt, sonst `None`.

    Ein relativer Pfad gilt ab `bezug` (ohne Angabe ab `ordner`). Eine
    `file`-Adresse mit Rechnernamen, ein anderes Schema und ein leerer
    Pfad ergeben `None`. Das Dateisystem wird nicht gefragt; ob die
    Datei existiert, prüft der Aufrufer erst danach."""
    if adresse.host():
        return None
    schema = adresse.scheme()
    if schema == "file":
        text = adresse.toLocalFile()
    elif not schema:
        text = adresse.path()
    elif len(schema) == 1:
        # `C:/…` liest QUrl als Adresse mit dem Schema „c“.
        text = f"{schema}:{adresse.path()}"
    else:
        return None
    if not text:
        return None

    grenze = os.path.normpath(os.path.abspath(ordner))
    start = os.path.normpath(os.path.abspath(bezug or ordner))
    ziel = os.path.normpath(os.path.join(start, text))
    try:
        gemeinsam = os.path.commonpath(
            [os.path.normcase(grenze), os.path.normcase(ziel)]
        )
    except ValueError:
        # Verschiedene Laufwerke, oder ein Netzpfad neben einem
        # lokalen Ordner.
        return None
    if gemeinsam != os.path.normcase(grenze):
        return None
    return Path(ziel)


def grenze_waehlen(datei: Path, projektordner: Path | None) -> Path:
    """Der Ordner, über den Bilder und Verweise von `datei` nicht
    hinaus dürfen: der Projektordner, wenn `datei` darin liegt, sonst
    der Ordner von `datei`.

    Verglichen wird wie in `pfad_im_ordner` nur am Text. Liegt das
    Projekt auf einem Netzlaufwerk, gilt dasselbe; die Datei selbst
    kommt dann ohnehin von dort."""
    datei = Path(os.path.normpath(os.path.abspath(datei)))
    if projektordner is None:
        return datei.parent
    grenze = os.path.normpath(os.path.abspath(projektordner))
    try:
        gemeinsam = os.path.commonpath(
            [os.path.normcase(grenze), os.path.normcase(str(datei))]
        )
    except ValueError:
        return datei.parent
    if gemeinsam != os.path.normcase(grenze):
        return datei.parent
    return Path(grenze)


def verweis_meldung(
    adresse: QUrl,
    ziel: Path | None,
    grenze: Path,
    seite: Path,
    anzeigbar: Callable[[Path], bool],
) -> str:
    """Der Satz für die Statuszeile, wenn ein Verweis nicht aufgeht.

    HTML-Vorschau und Markdown-Ansicht melden damit dieselben Fälle
    mit denselben Worten: der Verweis führt aus `grenze` hinaus, die
    Datei gibt es nicht, oder sie ist da, lässt sich in der Ansicht
    aber nicht zeigen. `ziel` ist das Ergebnis von `pfad_im_ordner`,
    `seite` die Datei, in der der Verweis steht. Das Dateisystem wird
    nur für ein `ziel` innerhalb der Grenze gefragt."""
    text = adresse.toString()
    schema = adresse.scheme()
    if schema and schema != "file" and len(schema) > 1:
        return f"Der Verweis „{text}“ wird in dieser Ansicht nicht geöffnet."
    if ziel is None:
        return (
            f"„{text}“ liegt außerhalb des Ordners "
            f"„{grenze.name or grenze}“ und "
            "wird deshalb nicht geöffnet."
        )
    if not ziel.exists():
        # Ein relativer Verweis so, wie er in der Datei steht; darin
        # steckt der Tippfehler.
        wie = str(ziel) if schema else adresse.path()
        return f"„{wie}“ gibt es neben „{seite.name}“ nicht."
    if not anzeigbar(ziel):
        return f"„{ziel.name}“ lässt sich in dieser Ansicht nicht anzeigen."
    return ""


def text_lesen(pfad: Path) -> str:
    """Liest eine Textdatei als UTF-8, sonst in der Windows-Codepage.

    Eine von Hand angelegte Datei kann in der Codepage geschrieben
    sein. Lieber mit falschen Umlauten anzeigen als gar nicht. Ein
    `OSError` (Datei fehlt, gesperrt) geht an den Aufrufer."""
    try:
        return pfad.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return pfad.read_text(encoding="cp1252", errors="replace")


def _laden(
    typ: int,
    name: QUrl,
    ordner: Path | None,
    bezug: Path | None,
    weiter: Callable[[int, QUrl], Any],
) -> Any:
    """Gemeinsamer Kern beider `loadResource`: prüfen, dann über
    `weiter` laden, und zwar genau den geprüften Pfad.

    Abgewiesen wird mit einem leeren `QByteArray` und nicht mit
    `None`: auf `None` hin öffnet `QTextDocument` eine `file`-Adresse
    selbst, auch eine mit Rechnernamen (nachgeprüft mit einem Bild
    außerhalb des Ordners, das so trotzdem erschien)."""
    if name.scheme() == "data":
        # In die Seite eingebettet; kein Dateizugriff.
        return weiter(typ, name)
    if ordner is None:
        return QByteArray()
    ziel = pfad_im_ordner(name, ordner, bezug)
    if ziel is None:
        return QByteArray()
    return weiter(typ, QUrl.fromLocalFile(str(ziel)))


class _Vorlage(QTextDocument):
    """Ein Dokument ohne Anzeige, in dem die Seite zuerst eingelesen
    wird. Es wird nicht gesetzt; nur ein Hintergrundbild aus dem
    Stylesheet lädt schon beim Einlesen, und das geht hier durch
    dieselbe Prüfung."""

    def __init__(self, ordner: Path | None, bezug: Path | None) -> None:
        super().__init__()
        self._ordner = ordner
        self._bezug = bezug

    def loadResource(self, typ: int, name: QUrl) -> Any:  # noqa: N802 - Qt-Name
        return _laden(
            typ, name, self._ordner, self._bezug, super().loadResource
        )


def html_bereinigen(
    text: str,
    vorbild: QTextDocument,
    ordner: Path | None,
    bezug: Path | None = None,
) -> str:
    """Die Seite mit Bildnamen, die nur noch in den Ordner zeigen.

    Ein Bild im Ordner bekommt seine vollständige `file`-Adresse, jedes
    andere einen leeren Namen. Die Prüfung in `loadResource` allein
    reicht nicht: findet Qt beim Setzen kein Bild, versucht es den
    Namen aus der Seite selbst als Datei zu öffnen, und auf einem
    Bildschirm mit Skalierung über 100 % fragt es vorher nach
    `name@2x.png`. Beides ginge an einem Netzpfad vorbei an jeder
    Prüfung. Deshalb wird die Seite zuerst in einem Dokument ohne
    Anzeige eingelesen und erst mit bereinigten Namen gesetzt.

    `vorbild` liefert Stylesheet und Schrift, damit die Seite danach
    genauso aussieht wie ohne den Umweg."""
    vorlage = _Vorlage(ordner, bezug)
    vorlage.setDefaultStyleSheet(vorbild.defaultStyleSheet())
    vorlage.setDefaultFont(vorbild.defaultFont())
    vorlage.setHtml(text)

    stellen: list[tuple[int, int, QTextImageFormat]] = []
    block = vorlage.begin()
    while block.isValid():
        teil = block.begin()
        while not teil.atEnd():
            stueck = teil.fragment()
            zeichen = stueck.charFormat()
            if stueck.isValid() and zeichen.isImageFormat():
                bild = zeichen.toImageFormat()
                neu = _bildname(bild.name(), ordner, bezug)
                if neu != bild.name():
                    bild.setName(neu)
                    stellen.append(
                        (stueck.position(), stueck.length(), bild)
                    )
            teil += 1
        block = block.next()

    # Erst sammeln, dann ändern: ein Eingriff ins Dokument macht die
    # Durchlaufzeiger oben ungültig.
    cursor = QTextCursor(vorlage)
    for anfang, laenge, bild in stellen:
        cursor.setPosition(anfang)
        cursor.setPosition(anfang + laenge, QTextCursor.MoveMode.KeepAnchor)
        cursor.setCharFormat(bild)
    return vorlage.toHtml()


def _bildname(name: str, ordner: Path | None, bezug: Path | None) -> str:
    """Der Name, unter dem ein Bild gesetzt wird: die Adresse im
    Ordner, ein eingebettetes Bild unverändert, sonst leer."""
    adresse = QUrl(name)
    if adresse.scheme() == "data":
        return name
    if ordner is None:
        return ""
    ziel = pfad_im_ordner(adresse, ordner, bezug)
    if ziel is None:
        return ""
    return QUrl.fromLocalFile(str(ziel)).toString()


class NurAusDemOrdner:
    """Beimischung für einen `QTextBrowser`: Bilder und andere
    eingebundene Dateien kommen nur aus dem gesetzten Ordner.

    Vor der Klasse des Browsers zu nennen, damit `loadResource` und
    `setHtml` hier ankommen. Solange kein Ordner gesetzt ist, wird
    nichts geladen."""

    _ordner: Path | None = None
    _bezug: Path | None = None

    def ordner_setzen(self, ordner: Path, bezug: Path | None = None) -> None:
        """Der erlaubte Ordner und der Ordner, ab dem relative Pfade
        gelten (ohne Angabe derselbe)."""
        self._ordner = ordner
        self._bezug = bezug

    def setHtml(self, text: str) -> None:  # noqa: N802 - Qt-Name
        vorbild = self.document()  # type: ignore[attr-defined]
        super().setHtml(  # type: ignore[misc]
            html_bereinigen(text, vorbild, self._ordner, self._bezug)
        )

    def loadResource(self, typ: int, name: QUrl) -> Any:  # noqa: N802 - Qt-Name
        return _laden(
            typ, name, self._ordner, self._bezug,
            super().loadResource,  # type: ignore[misc]
        )
