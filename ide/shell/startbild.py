"""Startbild der IDE (M11, Abschnitt 4).

Was sieht jemand beim allerersten Start? Bisher: ein leeres graues
Feld. Wer Natter zum ersten Mal öffnet, findet keinen Weg, ein
Projekt anzulegen – das steckt in einem Menü, in das man erst
hineinschauen muss.

Das Startbild füllt diese Lücke. Es zeigt zwei Dinge:

* Neues Projekt und Projekt öffnen
* Zuletzt geöffnete Projekte – der häufigste Fall in der zweiten
  Unterrichtsstunde

Die neun Beispielprojekte standen zunächst als dritter Abschnitt hier
und stehen seit September 2026 unter „Datei → Beispielprojekte“: auf
der Arbeitsfläche waren sie im Weg, im Menü stehen sie dort, wo auch
sonst gesucht wird.

Ein Beispiel wird beim Öffnen kopiert, nicht an Ort und Stelle
geöffnet: in einer installierten Natter liegen die Beispiele im
Programmordner, und dort darf eine Schülerin nicht schreiben. Die
Kopie landet in ihrem eigenen Dokumente-Ordner, wo sie sie behält –
und wo ein zweiter Anlauf am nächsten Tag das Angefangene wiederfindet
statt es zu überschreiben. Wo dieser Ordner liegt, sagt Windows
selbst; geraten hatte Natter ihn bis September 2026 falsch (siehe
`ide/pfade.py`).
"""

from __future__ import annotations

import contextlib
import filecmp
import functools
import hashlib
import os
import secrets
import shutil
import stat
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ide.pfade import (
    NATTER_ORDNER,
    beispielkopien_ordner,
    daten_ordner,
    einheitlicher_pfad,
    natter_ordner,
)
from ide.project.sicherung import ENDUNG as SICHERUNG_ENDUNG
from ide.project.sperre import SPERRDATEI
from ide.shell.theme import STARTBILD_EINTRAG
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft

#: Wie viele zuletzt geöffnete Projekte gemerkt werden. Mehr als acht
#: wären auf einem Schulrechner ohnehin nicht wiederzuerkennen.
ZULETZT_MAX = 8

#: Schlüssel in den Einstellungen.
ZULETZT_SCHLUESSEL = "projekt/zuletzt"

#: Wohin eine Arbeitskopie gehört, unterhalb des Dokumente-Ordners.
#: Der wird bei Windows erfragt und nicht geraten - warum, steht in
#: `ide/pfade.py`.
KOPIEN_ORDNER = NATTER_ORDNER

#: Schriftgrößen als Stylesheet, nicht über `setFont()`.
#:
#: In der Sichtprüfung stand die Begrüßung genauso groß da wie der
#: Fließtext darunter, obwohl `setPointSize(+8)` gesetzt war: das
#: IDE-weite QSS (`ide_qss_erzeugen`) enthält eine `font-size`-Regel für
#: `QWidget`, und die gewinnt in Qt gegen ein einzelnes `setFont()`.
#: Derselbe Fund war in M7 schon einmal beim Quelltexteditor gemacht
#: worden - dort steht er als Kommentar in `theme.py`. `setBold()`
#: wirkt dagegen weiter, weil das QSS keine `font-weight` setzt.
_GRUSS_STIL = "font-size: 20pt; font-weight: bold;"
_UNTERTITEL_STIL = "font-size: 11pt;"
_UEBERSCHRIFT_STIL = "font-size: 11pt; font-weight: bold; padding-top: 6px;"

#: Die Einträge sollen wie Verweise aussehen, nicht wie Schaltflächen.
#: `setFlat(True)` allein genügt nicht - auch dagegen gewinnt die
#: QSS-Regel für `QPushButton`, und im Bild standen elf Kästen
#: untereinander, die wie gesperrte Eingabefelder wirkten.
#:
#: Hier steht nur, was von den Farben des Themas unabhängig ist. Das
#: Aussehen beim Darüberfahren steht im IDE-weiten QSS unter dem
#: Objektnamen `STARTBILD_EINTRAG` (`ide/shell/theme.py`), weil nur
#: dort die Farben des gerade eingestellten Themas bekannt sind.
#:
#: Ein reiner Zusatz von `text-decoration` genügte hier ausdrücklich
#: nicht: `background: transparent` von hier gewann gegen den
#: Akzent-Hintergrund der allgemeinen Hover-Regel, deren weiße Schrift
#: mangels eigener Farbe hier aber durchkam - übrig blieb weiße Schrift
#: auf weißem Grund (gemeldet).
_EINTRAG_STIL = """
QPushButton {
    text-align: left;
    padding: 5px 8px;
    border: none;
    background: transparent;
}
"""


def beispielprojekte() -> list[Path]:
    """Die mitgelieferten Beispielprojekte, alphabetisch.

    Leer, wenn der Ordner fehlt – etwa in einem Bau, der ihn nicht
    mitgenommen hat. Das Startbild lässt den Abschnitt dann weg, statt
    auf einen leeren Bereich zu zeigen.
    """
    ordner = daten_ordner("beispielprojekte")
    if not ordner.is_dir():
        return []
    gefunden = [
        next(iter(unterordner.glob("*.natter")), None)
        for unterordner in sorted(ordner.iterdir())
        if unterordner.is_dir()
    ]
    return [pfad for pfad in gefunden if pfad is not None]


def zuletzt_geoeffnet(einstellungen: QSettings) -> list[Path]:
    """Die zuletzt geöffneten Projekte – ohne die, die es nicht mehr
    gibt. Ein Eintrag, der ins Leere zeigt, wäre schlimmer als keiner:
    man klickt darauf und bekommt eine Fehlermeldung."""
    roh = einstellungen.value(ZULETZT_SCHLUESSEL, [], type=list) or []
    pfade = [Path(eintrag) for eintrag in roh]
    return [pfad for pfad in pfade if pfad.exists()][:ZULETZT_MAX]


def zuletzt_merken(einstellungen: QSettings, pfad: Path) -> list[Path]:
    """Schiebt `pfad` an die erste Stelle der Liste. Gespeichert wird
    er in derselben Form wie die Herkunft einer kopierten Aufgabe
    (`einheitlicher_pfad`, Punkt 364)."""
    pfad = einheitlicher_pfad(pfad)
    vorhanden = [
        eintrag
        for eintrag in zuletzt_geoeffnet(einstellungen)
        if einheitlicher_pfad(eintrag) != pfad
    ]
    neu = [pfad, *vorhanden][:ZULETZT_MAX]
    einstellungen.setValue(ZULETZT_SCHLUESSEL, [str(eintrag) for eintrag in neu])
    return neu


def eindeutige_namen(pfade: list[Path]) -> list[str]:
    """Beschriftungen für die zuletzt geöffneten Projekte.

    Normalerweise der Projektordner. Heißen zwei Projekte gleich – in
    der Sichtprüfung standen zwei „Garten" untereinander, eine Kopie
    des Beispiels und das Original –, kommt der übergeordnete Ordner
    dazu. Zwei gleich beschriftete Einträge wären ein Ratespiel.
    """
    namen = [pfad.parent.name for pfad in pfade]
    return [
        f"{name}  ({pfad.parent.parent.name})" if namen.count(name) > 1 else name
        for name, pfad in zip(namen, pfade, strict=True)
    ]


#: Die Kopie einer Aufgabe aus einem Ordner ohne Schreibrecht trägt in
#: dieser Datei den Ordner, aus dem sie stammt (Punkt 340). Unter
#: „Dokumente\Natter“ liegen auch eigene Projekte, und ein eigenes
#: „Ampel“ ist keine Kopie der Aufgabe „Ampel“ aus dem Tauschordner.
#: Der Punkt am Anfang hält die Datei aus dem Export heraus.
QUELLDATEI = ".natter-quelle"

#: Was beim Kopieren eines Beispiels liegen bleibt. Übersetzter
#: Python-Code gehört zu dem Rechner, auf dem er entstand, und die
#: Sperrdatei zu dem Natter, in dem das Original gerade offen ist.
#: Mitkopiert hieß es beim Öffnen der Kopie, sie sei schon an dessen
#: Rechner geöffnet (Punkt 327). Die Quelldatei einer Aufgabe, die
#: selbst schon eine Kopie war, schreibt `aufgabe_kopieren` neu. Eine
#: Sicherung ungespeicherter Änderungen gehört zu dem, der sie
#: hinterlassen hat; in der Kopie böte Natter sonst fremden Text zum
#: Wiederherstellen an (Punkt 344).
_NICHT_MITKOPIEREN = shutil.ignore_patterns(
    "__pycache__", "*.pyc", SPERRDATEI, QUELLDATEI,
    f"*{SICHERUNG_ENDUNG}",
)


def _beschreibbar_kopieren(quelle: str, ziel: str) -> str:
    """Kopiert eine Datei samt Zeitstempel, aber ohne das Attribut
    „Schreibgeschützt“ (Punkt 333).

    Dateien von einer CD tragen es immer, und manche Lehrkräfte setzen
    es, um eine Vorlage zu schützen. `shutil.copy2` nimmt es mit, und
    die Kopie ließ sich öffnen, aber nicht speichern. Der Zeitstempel
    bleibt, damit `.pfm` und erzeugte `_design.py` in derselben
    Reihenfolge alt sind wie im Original."""
    shutil.copy2(quelle, ziel)
    modus = os.stat(ziel).st_mode
    if not modus & stat.S_IWRITE:
        os.chmod(ziel, stat.S_IMODE(modus) | stat.S_IWRITE)
    return ziel


def _ist_wurzel(ordner: Path) -> bool:
    """Ob `ordner` die Wurzel eines Laufwerks oder einer Freigabe ist,
    etwa `K:\\` oder `\\\\server\\klausur\\`. Eine Wurzel hat keinen
    Namen."""
    return not Path(ordner).name


def _projekt_kopieren(quelle: Path, ziel: Path) -> None:
    """Kopiert den Projektordner `quelle` nach `ziel`.

    Aus der Wurzel eines Laufwerks oder einer Freigabe kommen nur die
    Dateien und der Ordner `diagramme` mit, sonst keine Unterordner
    (Punkt 335). Eine Lehrkraft richtet für eine Klausur gern eine
    eigene Freigabe ein und legt die Aufgabe direkt hinein; was dort
    sonst noch liegt, gehört nicht zum Projekt und wurde vorher ganz
    mitkopiert.

    Hält ein anderes Programm eine Datei der Quelle ohne Mitlesen
    offen, folgt `DateiGesperrt` mit ihr. `shutil.copytree` sammelt
    die Fehler nur als Text; welche Datei gesperrt war, merkt sich
    deshalb die Kopierfunktion selbst (Punkt 395)."""
    gesperrt: list[Path] = []

    def kopieren(von: str, nach: str) -> str:
        try:
            return _beschreibbar_kopieren(von, nach)
        except OSError as fehler:
            if getattr(fehler, "winerror", None) in _SPERRFEHLER:
                gesperrt.append(Path(von))
            raise

    try:
        if not _ist_wurzel(quelle):
            shutil.copytree(
                quelle, ziel, ignore=_NICHT_MITKOPIEREN,
                copy_function=kopieren,
            )
            return
        namen = [eintrag.name for eintrag in quelle.iterdir()]
        weglassen = _NICHT_MITKOPIEREN(str(quelle), namen)
        ziel.mkdir(parents=True)
        for name in namen:
            if name in weglassen:
                continue
            if (quelle / name).is_file():
                kopieren(str(quelle / name), str(ziel / name))
            elif name == "diagramme":
                shutil.copytree(
                    quelle / name, ziel / name,
                    ignore=_NICHT_MITKOPIEREN, copy_function=kopieren,
                )
    except OSError as fehler:
        if gesperrt:
            raise DateiGesperrt(gesperrt[0]) from fehler
        raise


#: Die Fehlernummern, mit denen Windows das Öffnen einer Datei
#: ablehnt, die ein anderes Programm ohne Mitlesen offen hält oder
#: in Teilen gesperrt hat.
_SPERRFEHLER = (32, 33)


def _projekt_anlegen(
    quelle: Path, ziel: Path,
    danach: Callable[[Path], None] | None = None,
) -> None:
    """Legt `ziel` als vollständige Kopie von `quelle` an, oder gar
    nicht (Punkt 395).

    Kopiert wird in einen Zwischenordner neben `ziel`; `danach`
    ergänzt dort noch etwas, etwa die `QUELLDATEI` einer Aufgabe. Erst
    dann bekommt der Zwischenordner mit einer einzigen Umbenennung den
    Namen `ziel`. Bis dahin wurde direkt in `ziel` kopiert. Scheiterte
    das mittendrin, weil das Kontingent voll oder eine Datei gesperrt
    war, blieb eine halbe Kopie stehen: bei einer Aufgabe entstand
    beim nächsten Versuch „Ampel 2“ daneben, ein Beispiel ging von da
    an ohne seine Unit auf. Jetzt wird der Zwischenordner bei einem
    Fehler wieder entfernt, und der Fehler geht weiter.

    Den Zwischenordner legt `_projekt_kopieren` selbst an, nicht
    `tempfile.mkdtemp`: der gibt einem Ordner unter Windows Rechte
    nur für das eigene Konto, und die gingen mit der Umbenennung auf
    die Kopie über."""
    neu = ziel.parent / f".natter-neu-{secrets.token_hex(4)} {ziel.name}"
    try:
        _projekt_kopieren(quelle, neu)
        if danach is not None:
            danach(neu)
        os.rename(neu, ziel)
    except BaseException:
        shutil.rmtree(neu, ignore_errors=True)
        raise


def ist_beispiel_original(pfad: Path, *, aufloesen: bool = True) -> bool:
    """Ob `pfad` im Ordner der mitgelieferten Beispiele liegt.

    Ein Original wird nie an Ort und Stelle geöffnet. In einer
    installierten Natter liegt es im Programmordner, in den eine
    Schülerin nicht schreiben darf, und im Entwicklungsbaum ist es eine
    eingecheckte Datei.

    Verglichen wird ohne Unterschied zwischen Groß- und
    Kleinschreibung, wie Windows die Pfade behandelt. Ohne `aufloesen`
    nur am Text des Pfads: so fragt Natter bei einem Pfad auf einer
    Freigabe, die gerade nicht antwortet, nicht erst beim Server nach
    (Punkt 403)."""
    ordner = _vergleichbar(daten_ordner("beispielprojekte").resolve())
    ziel = (
        _vergleichbar(einheitlicher_pfad(pfad)) if aufloesen
        else _vergleichbar(os.path.abspath(pfad))
    )
    return ziel == ordner or ziel.startswith(ordner.rstrip(os.sep) + os.sep)


def _vergleichbar(pfad: Path | str) -> str:
    """`pfad` als Text zum Vergleichen: ohne `..` und doppelte
    Trenner, in Kleinbuchstaben unter Windows."""
    return os.path.normcase(os.path.normpath(str(pfad)))


def beispiel_original(projekt_ordner: Path) -> Path | None:
    """Der Ordner des Beispiels, von dem `projekt_ordner` eine Kopie
    ist - oder `None` für ein eigenes Projekt und für das Original
    selbst.

    Erkannt wird eine Kopie an ihrer Projektdatei und nicht am
    Ordnernamen: ein eigenes Projekt kann zufällig „04_CookieKlicker"
    heißen, und eine Kopie aus der Zeit, als jedes Öffnen eine neue
    anlegte, heißt „08_Regression 2".
    """
    projekt_ordner = Path(projekt_ordner)
    if ist_beispiel_original(projekt_ordner):
        return None
    # Ohne Rücksicht auf Groß- und Kleinschreibung: Windows findet
    # `04_cookieklicker.natter` auch unter `04_CookieKlicker.natter`,
    # und im Prüfungsmodus ging eine so umbenannte Kopie sonst nicht
    # als Beispiel durch (Punkt 403).
    eigene = {
        datei.name.casefold() for datei in projekt_ordner.glob("*.natter")
    }
    for projektdatei in beispielprojekte():
        if projektdatei.name.casefold() in eigene:
            return projektdatei.parent
    return None


def beispiel_als_quelle(ordner: Path) -> bool:
    """Ob `ordner`, die Quelle einer Kopie laut `QUELLDATEI`, ein
    mitgeliefertes Beispiel ist: sein Original, ein Ordner mit der
    Projektdatei eines Beispiels oder einer mit dessen Lösung
    (Punkt 403).

    `QUELLDATEI` ist gewöhnlicher Text im eigenen Projekt und lässt
    sich von Hand schreiben. Zeigte sie auf ein Beispiel, holte „Auf
    Original zurücksetzen …“ im Prüfungsmodus dessen Lösung in das
    eigene Projekt."""
    return (
        ist_beispiel_original(ordner)
        or beispiel_original(ordner) is not None
        or beispiel_nach_inhalt(ordner) is not None
    )


#: Dateien, die größer sind, werden für den Inhaltsvergleich nicht
#: gelesen. Die Units und Diagramme der Beispiele sind weit kleiner.
_VERGLEICH_HOECHSTENS = 1_000_000


def _loesungsdatei(pfad: Path) -> bool:
    """Ob `pfad` in einem Beispiel einen Teil der Lösung trägt: eine
    Unit mit Ereignisroutinen oder ein Diagramm. `main.py` und die
    erzeugten `_design.py` gleichen denen eines neuen Projekts zu sehr,
    um ein Beispiel daran zu erkennen."""
    name = pfad.name.lower()
    if name.endswith(".pdiag"):
        return True
    return (
        name.startswith("u_")
        and name.endswith(".py")
        and not name.endswith("_design.py")
    )


def _inhalt_schluessel(pfad: Path) -> str | None:
    """Prüfsumme über den Inhalt von `pfad`, unabhängig von
    Zeilenenden und Leerzeichen am Zeilenende. `None`, wenn die Datei
    sich nicht lesen lässt oder zu groß ist."""
    try:
        if pfad.stat().st_size > _VERGLEICH_HOECHSTENS:
            return None
        daten = pfad.read_bytes()
    except OSError:
        return None
    zeilen = daten.replace(b"\r\n", b"\n").split(b"\n")
    text = b"\n".join(zeile.rstrip() for zeile in zeilen).strip()
    if not text:
        return None
    return hashlib.sha256(text).hexdigest()


@functools.lru_cache(maxsize=4)
def _beispiel_inhalte(ordner: Path) -> dict[str, Path]:
    """Prüfsumme jeder Lösungsdatei der Beispiele in `ordner`, jeweils
    mit dem Ordner des Beispiels. Die Originale ändern sich während
    eines Laufs nicht, deshalb wird nur einmal gelesen."""
    inhalte: dict[str, Path] = {}
    if not ordner.is_dir():
        return inhalte
    for beispiel in sorted(ordner.iterdir()):
        if not beispiel.is_dir():
            continue
        for datei in sorted(beispiel.rglob("*")):
            if "__pycache__" in datei.parts or not _loesungsdatei(datei):
                continue
            schluessel = _inhalt_schluessel(datei)
            if schluessel is not None:
                inhalte.setdefault(schluessel, beispiel)
    return inhalte


def beispiel_nach_inhalt(pfad: Path) -> Path | None:
    """Das Beispiel, dessen Lösung in `pfad` steckt, oder `None`.

    `pfad` ist eine einzelne Datei oder ein Projektordner. Eine Datei
    zählt, wenn ihr Inhalt einer Unit oder einem Diagramm eines
    Beispiels gleicht, gleich unter welchem Namen sie liegt. Ein
    Ordner zählt, wenn eine seiner Python-Dateien oder Diagramme das
    tut, auch in einem Unterordner eine Ebene tiefer.

    `beispiel_original` erkennt eine Kopie am Namen ihrer
    Projektdatei, und die lässt sich umbenennen (Punkt 251). Der
    Inhalt geht beim Kopieren mit. Wer eine Unit auch nur um ein
    Zeichen verändert, fällt allerdings auch hier heraus; die Grenze
    steht im Handbuch, Abschnitt 4.
    """
    inhalte = _beispiel_inhalte(daten_ordner("beispielprojekte").resolve())
    if not inhalte:
        return None
    pfad = Path(pfad)
    if pfad.is_file():
        dateien = [pfad]
    elif pfad.is_dir():
        dateien = [
            datei
            for muster in ("*.py", "*.pdiag", "*/*.py", "*/*.pdiag")
            for datei in pfad.glob(muster)
            if "__pycache__" not in datei.parts
        ]
    else:
        return None
    for datei in dateien:
        schluessel = _inhalt_schluessel(datei)
        if schluessel is not None and schluessel in inhalte:
            return inhalte[schluessel]
    return None


def beispiel_kopieren(projektdatei: Path, ziel_wurzel: Path | None = None) -> Path:
    """Gibt die Arbeitskopie des Beispiels zurück und legt sie an, wenn
    es noch keine gibt.

    Eine vorhandene Kopie wird weiterbenutzt. Früher entstand bei
    jedem Öffnen eine neue daneben - „Ampel 2", „Ampel 3" -, damit die
    Arbeit von gestern nicht überschrieben wird. Überschrieben wurde sie
    nicht, aber geöffnet wurde eine frische Kopie, und die Arbeit lag
    unbemerkt im Ordner nebenan. Wer von vorn anfangen will, nimmt
    „Projekt → Auf Original zurücksetzen …".

    Nummeriert wird nur noch, wenn ein fremder Ordner den Namen schon
    belegt, etwa ein eigenes Projekt, das zufällig so heißt.

    Ohne `ziel_wurzel` liegen die Kopien unter
    `Dokumente/Natter/Beispielprojekte`, getrennt von den eigenen
    Projekten.
    """
    projektdatei = Path(projektdatei)
    quelle = projektdatei.parent
    wurzel = Path(ziel_wurzel) if ziel_wurzel else beispielkopien_ordner()

    # Liegt das Entwicklungsverzeichnis unter `Dokumente/Natter`, ist
    # `Natter/Beispielprojekte` der Ordner der Originale, denn Windows
    # unterscheidet keine Groß- und Kleinschreibung. Die Suche nach
    # einer vorhandenen Kopie fände dann das Original selbst, und es
    # würde an Ort und Stelle geöffnet.
    if ist_beispiel_original(wurzel):
        raise ValueError(
            f"Die Kopien der Beispiele würden bei den Originalen landen ({wurzel})."
        )
    if ziel_wurzel is None:
        _alte_kopie_umziehen(projektdatei, wurzel)
    wurzel.mkdir(parents=True, exist_ok=True)

    ziel = wurzel / quelle.name
    nummer = 2
    while ziel.exists():
        if _halbe_beispielkopie(ziel, projektdatei):
            _halbe_kopie_ersetzen(ziel, quelle)
            return ziel / projektdatei.name
        if (ziel / projektdatei.name).exists():
            return ziel / projektdatei.name
        ziel = wurzel / f"{quelle.name} {nummer}"
        nummer += 1

    _projekt_anlegen(quelle, ziel)
    return ziel / projektdatei.name


def _halbe_beispielkopie(ordner: Path, projektdatei: Path) -> bool:
    """Ob `ordner` eine angefangene Kopie des Beispiels `projektdatei`
    ist, bei der das Kopieren mittendrin scheiterte. Solche Ordner
    stammen aus der Zeit vor `_projekt_anlegen` (Punkt 395).

    Das ist der Fall, wenn die Projektdatei oder eine Python-Datei des
    Beispiels fehlt oder leer ist und jede Datei im Ordner auch im
    Beispiel vorkommt. Hat jemand eigene Dateien hinzugefügt, wird
    darin gearbeitet, und der Ordner bleibt, wie er ist."""
    quelle = projektdatei.parent
    original = {
        datei.relative_to(quelle) for datei in _projekt_dateien(quelle)
    }
    vorhanden = {
        datei.relative_to(ordner) for datei in _projekt_dateien(ordner)
    }
    if not vorhanden <= original:
        return False
    for name in [projektdatei.name] + [
        datei.name for datei in quelle.glob("*.py")
    ]:
        datei = ordner / name
        if not datei.is_file():
            return True
        leer = datei.stat().st_size == 0
        if leer and (quelle / name).stat().st_size > 0:
            return True
    return False


def _halbe_kopie_ersetzen(ordner: Path, quelle: Path) -> None:
    """Ersetzt die halbe Kopie in `ordner` durch eine vollständige des
    Beispiels in `quelle`. Weicht eine ihrer Dateien vom Beispiel ab,
    wurde darin schon gearbeitet; der alte Inhalt kommt dann in den
    Ordner daneben (`vorher_ordner`), sonst geht er weg."""
    geaendert = any(
        not filecmp.cmp(
            datei, quelle / datei.relative_to(ordner), shallow=False
        )
        for datei in _projekt_dateien(ordner)
    )
    _inhalt_ersetzen(
        ordner, lambda ziel: _projekt_kopieren(quelle, ziel),
        vorher_ordner(ordner) if geaendert else None,
    )


def _herkunft(ordner: Path) -> str:
    """Der Ordner als Text, wie er in `QUELLDATEI` steht und verglichen
    wird: in der Form von `einheitlicher_pfad`, also über ein
    verbundenes Laufwerk wie über den Netzpfad gleich (Punkt 364), und
    ohne Unterschied zwischen Groß- und Kleinschreibung."""
    return os.path.normcase(str(einheitlicher_pfad(ordner)))


def _projekt_dateien(quelle: Path) -> list[Path]:
    """Die Dateien, die `_projekt_kopieren` aus `quelle` mitnimmt."""
    quelle = Path(quelle)
    dateien: list[Path] = []
    wurzel = _ist_wurzel(quelle)
    for ordner, unterordner, namen in os.walk(quelle):
        weg = _NICHT_MITKOPIEREN(ordner, unterordner + namen)
        if wurzel and Path(ordner) == quelle:
            weg |= {name for name in unterordner if name != "diagramme"}
        unterordner[:] = [name for name in unterordner if name not in weg]
        dateien += [Path(ordner) / name for name in namen if name not in weg]
    return dateien


def _fingerabdruck(quelle: Path) -> str:
    """Prüfsumme über Namen, Größe und Änderungszeit der Dateien einer
    Aufgabe (Punkt 346). Gelesen wird keine Datei, nur ihre Angaben im
    Verzeichnis; eine Aufgabe auf einer langsamen Freigabe hält das
    Öffnen so nicht auf. Wer eine berichtigte Datei im Explorer über
    die alte kopiert, ändert mindestens die Zeit.

    Es sind dieselben Dateien wie in `_projekt_dateien`, aber Größe
    und Zeit kommen aus den Verzeichniseinträgen (`os.scandir`), die
    Windows beim Auflisten ohnehin mitliefert. Bis Punkt 387 fragte
    `stat()` jede Datei einzeln ab, auf einer Freigabe je Datei eine
    Anfrage an den Server: 1,4 s für eine Aufgabe mit 3.000 Dateien
    statt rund 20 ms. Verknüpfungen auf Ordner werden wie bei
    `os.walk` nicht betreten. Ist `quelle` selbst nicht lesbar, folgt
    `OSError`; ein nicht lesbarer Unterordner fehlt wie bei
    `os.walk` einfach."""
    quelle = Path(quelle)
    wurzel = _ist_wurzel(quelle)
    zeilen = []
    offen = [(str(quelle), "")]
    while offen:
        ordner, vorne = offen.pop()
        try:
            with os.scandir(ordner) as liste:
                eintraege = list(liste)
        except OSError:
            if not vorne:
                raise
            continue
        weg = _NICHT_MITKOPIEREN(ordner, [e.name for e in eintraege])
        for eintrag in eintraege:
            if eintrag.name in weg:
                continue
            try:
                ist_ordner = eintrag.is_dir()
            except OSError:
                ist_ordner = False
            if not ist_ordner:
                angaben = eintrag.stat()
                zeilen.append(
                    f"{vorne}{eintrag.name}\t"
                    f"{angaben.st_size}\t{angaben.st_mtime_ns}"
                )
            elif not eintrag.is_symlink() and not (
                wurzel and not vorne and eintrag.name != "diagramme"
            ):
                offen.append((eintrag.path, f"{vorne}{eintrag.name}/"))
    return hashlib.sha256("\n".join(sorted(zeilen)).encode()).hexdigest()


def _quellangaben(projekt_ordner: Path) -> list[str]:
    """Die Zeilen der `QUELLDATEI`: der Ordner der Aufgabe und, seit
    Punkt 346, ihr Fingerabdruck beim Kopieren. Leer, wenn es keine
    lesbare gibt."""
    try:
        text = (Path(projekt_ordner) / QUELLDATEI).read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeDecodeError):
        return []
    return [zeile.strip() for zeile in text.splitlines() if zeile.strip()]


def _quelle_eintragen(
    ziel: Path, herkunft: str, quelle: Path, stand: str | None = None
) -> None:
    """Schreibt die `QUELLDATEI` der Kopie in `ziel`. `stand` ist der
    schon gebildete Fingerabdruck von `quelle`, sonst wird er hier
    gebildet."""
    if stand is None:
        stand = _fingerabdruck(quelle)
    (ziel / QUELLDATEI).write_text(
        f"{herkunft}\n{stand}\n", encoding="utf-8"
    )


def aufgabe_original(projekt_ordner: Path) -> Path | None:
    """Der Ordner der Aufgabe, von der `projekt_ordner` eine Kopie ist,
    oder `None` für alles andere (Punkt 346). Ob er gerade erreichbar
    ist, wird hier nicht nachgesehen: das fragt Natter bei jedem Öffnen
    eines Projekts, und eine Freigabe, die nicht antwortet, ließe es
    warten."""
    zeilen = _quellangaben(projekt_ordner)
    return Path(zeilen[0]) if zeilen else None


def aufgabe_geaendert(projekt_ordner: Path) -> bool:
    """Ob die Aufgabe seit dem Anlegen der Kopie in `projekt_ordner`
    geändert wurde (Punkt 346). Eine Kopie aus der Zeit vor diesem
    Vergleich und eine Aufgabe, die nicht erreichbar ist, gelten als
    unverändert."""
    return neuer_aufgabenstand(projekt_ordner) is not None


def neuer_aufgabenstand(projekt_ordner: Path) -> str | None:
    """Der Fingerabdruck der Aufgabe, wenn sie seit dem Anlegen der
    Kopie in `projekt_ordner` geändert wurde, sonst `None`; wann sie
    als unverändert gilt, steht bei `aufgabe_geaendert`.

    Den Wert nimmt `aufgabe_stand_merken` entgegen. Bis Punkt 387
    bildete Natter den Fingerabdruck beim Öffnen einer geänderten
    Aufgabe dreimal hintereinander, obwohl sich die Aufgabe dazwischen
    nicht geändert hatte."""
    zeilen = _quellangaben(projekt_ordner)
    if len(zeilen) < 2:
        return None
    try:
        stand = _fingerabdruck(Path(zeilen[0]))
    except OSError:
        return None
    return stand if stand != zeilen[1] else None


def aufgabe_stand_merken(
    projekt_ordner: Path, stand: str | None = None
) -> None:
    """Trägt den jetzigen Stand der Aufgabe als Stand der Kopie in
    `projekt_ordner` ein, ohne eine Datei der Kopie anzufassen.
    `stand` ist der Fingerabdruck aus `neuer_aufgabenstand`; ohne ihn
    wird er neu gebildet.

    Nach der Wahl, die Kopie trotz geänderter Aufgabe zu behalten
    (Punkt 380). Vorher blieb der alte Fingerabdruck stehen, und die
    Frage kam bei jedem Öffnen wieder. Ändert die Lehrkraft die Aufgabe
    danach noch einmal, fragt Natter wieder."""
    zeilen = _quellangaben(projekt_ordner)
    if zeilen:
        _quelle_eintragen(
            Path(projekt_ordner), zeilen[0], Path(zeilen[0]), stand
        )


def vorher_ordner(projekt_ordner: Path) -> Path:
    """Der Ordner, in den beim Zurücksetzen der Kopie einer Aufgabe
    ihr bisheriger Inhalt kommt: „Ampel (vorher)“ neben „Ampel“, bei
    Bedarf „Ampel (vorher 2)“ und so weiter (Punkt 380)."""
    projekt_ordner = Path(projekt_ordner)
    name = projekt_ordner.name
    ziel = projekt_ordner.parent / f"{name} (vorher)"
    nummer = 2
    while ziel.exists():
        ziel = projekt_ordner.parent / f"{name} (vorher {nummer})"
        nummer += 1
    return ziel


def vorhandene_aufgabenkopie(
    projektdatei: Path, ziel_wurzel: Path
) -> Path | None:
    """Die Projektdatei einer schon angelegten Kopie der Aufgabe
    `projektdatei` unter `ziel_wurzel`, oder `None`.

    Als Kopie zählt nur ein Ordner, dessen `QUELLDATEI` auf denselben
    Ordner zeigt wie `projektdatei` (Punkt 340). Ein eigenes Projekt
    gleichen Namens, oder die Kopie einer gleichnamigen Aufgabe aus
    einer anderen Woche, ist keine."""
    projektdatei = Path(projektdatei)
    quelle = projektdatei.parent
    herkunft = _herkunft(quelle)
    name = projektdatei.stem if _ist_wurzel(quelle) else quelle.name
    wurzel = Path(ziel_wurzel)
    ziel = wurzel / name
    nummer = 2
    while ziel.exists():
        if (ziel / projektdatei.name).is_file():
            zeilen = _quellangaben(ziel)
            if zeilen and zeilen[0] == herkunft:
                return ziel / projektdatei.name
        ziel = wurzel / f"{name} {nummer}"
        nummer += 1
    return None


def aufgabe_kopieren(projektdatei: Path, ziel_wurzel: Path) -> Path:
    """Gibt die Kopie der Aufgabe `projektdatei` unter `ziel_wurzel`
    zurück und legt sie an, wenn es noch keine gibt (Punkte 321, 340).

    Wie bei den Beispielen wird eine vorhandene Kopie weiterbenutzt,
    damit die Arbeit der letzten Stunde wieder aufgeht
    (`vorhandene_aufgabenkopie`). Sonst kommt die Aufgabe in den
    nächsten freien Ordner, auch wenn dort schon ein eigenes Projekt
    gleichen Namens liegt („Ampel 2“).

    Liegt die Aufgabe in der Wurzel einer Freigabe, heißt der Ordner
    wie die Projektdatei (Punkt 335).
    """
    projektdatei = Path(projektdatei)
    vorhanden = vorhandene_aufgabenkopie(projektdatei, ziel_wurzel)
    if vorhanden is not None:
        return vorhanden
    quelle = projektdatei.parent
    wurzel = Path(ziel_wurzel)
    name = projektdatei.stem if _ist_wurzel(quelle) else quelle.name
    wurzel.mkdir(parents=True, exist_ok=True)

    ziel = wurzel / name
    nummer = 2
    while ziel.exists():
        ziel = wurzel / f"{name} {nummer}"
        nummer += 1

    herkunft = _herkunft(quelle)
    _projekt_anlegen(
        quelle, ziel,
        lambda neu: _quelle_eintragen(neu, herkunft, quelle),
    )
    return ziel / projektdatei.name


class DateiGesperrt(OSError):
    """Eine Datei der Kopie ließ sich beim Zurücksetzen nicht
    beiseiteschieben, meist weil ein anderes Programm sie offen hält,
    etwa Excel eine CSV (Punkt 362). `pfad` ist die Datei in der
    Kopie; die Kopie selbst ist unverändert."""

    def __init__(self, pfad: Path) -> None:
        super().__init__(f"{pfad} ist gesperrt.")
        self.pfad = Path(pfad)


class RueckwegGescheitert(OSError):
    """Beim Zurücksetzen war `pfad` gesperrt, und danach kamen nicht
    alle alten Dateien in die Kopie zurück (Punkt 375). Die übrigen
    liegen in `ablage`, und der Ordner bleibt stehen, bis sie von dort
    zurückgeholt sind."""

    def __init__(self, pfad: Path, ablage: Path) -> None:
        super().__init__(
            f"{pfad} ist gesperrt; alte Dateien liegen in {ablage}."
        )
        self.pfad = Path(pfad)
        self.ablage = Path(ablage)


def _dateien(ordner: Path) -> list[Path]:
    """Alle Dateien unter `ordner`, ohne die Sperrdatei direkt darin:
    die gehört dem offenen Fenster, nicht der Aufgabe. Ohne sie bekäme
    ein zweites Fenster keinen Hinweis mehr, und die Erneuern-Uhr legt
    eine fehlende Sperre nicht wieder an."""
    return [
        Path(wurzel) / name
        for wurzel, _unterordner, namen in os.walk(ordner)
        for name in namen
        if not (Path(wurzel) == ordner and name == SPERRDATEI)
    ]


def _zurueckstellen(erledigt: list[tuple[Path, Path]]) -> None:
    """Schiebt die Dateien aus `erledigt` an ihren alten Platz zurück.
    Eine, die sich nicht zurückschieben lässt, bleibt liegen, und es
    geht mit der nächsten weiter.

    Bis Punkt 375 brach der erste Fehler hier ab, etwa wenn ein
    Virenscanner die eben verschobene Datei gerade prüfte, und das
    Aufräumen danach löschte den Zwischenordner samt den Dateien,
    die noch darin lagen."""
    for alt, neu in reversed(erledigt):
        with contextlib.suppress(OSError):
            alt.parent.mkdir(parents=True, exist_ok=True)
            os.rename(neu, alt)


def _verschieben(
    von: Path, nach: Path, *, oben: bool = True
) -> list[tuple[Path, Path]]:
    """Verschiebt jeden Eintrag unter `von` an dieselbe Stelle unter
    `nach` und gibt die Paare zurück. Scheitert eine Datei, kommen die
    schon verschobenen Einträge zurück, und es folgt `DateiGesperrt`
    mit ihr. Die Sperrdatei direkt in `von` (`oben`) bleibt liegen,
    wie bei `_dateien`.

    Ein Unterordner wandert als Ganzes, mit einer einzigen
    Umbenennung. Bis Punkt 389 wanderte jede Datei einzeln, und für
    jede wurde ihr Zielordner angelegt: bei 3.000 Dateien 6.000
    Aufrufe und 24 s, in denen Natter stand, gegen rund 10 ms für den
    ganzen Ordner. Nur wenn Windows das Umbenennen des Ordners
    verweigert, geht es in ihm Eintrag für Eintrag weiter. Das
    geschieht, wenn darin irgendeine Datei offen ist, und Windows
    nennt dann nur den Ordner; erst der Versuch mit der einzelnen
    Datei zeigt, welche es ist (Punkt 362)."""
    erledigt: list[tuple[Path, Path]] = []
    nach.mkdir(parents=True, exist_ok=True)
    namen = sorted(os.listdir(von))
    for name in namen:
        if oben and name == SPERRDATEI:
            continue
        quelle, ziel = von / name, nach / name
        try:
            os.rename(quelle, ziel)
        except OSError as fehler:
            if (
                not quelle.is_dir() or quelle.is_symlink()
                or quelle.is_junction()
            ):
                _zurueckstellen(erledigt)
                raise DateiGesperrt(quelle) from fehler
            try:
                erledigt += _verschieben(quelle, ziel, oben=False)
            except DateiGesperrt:
                # Der eben angelegte, wieder leere Zielordner muss
                # weg; sonst scheitert daran das Zurückschieben eines
                # ganzen Ordners gleichen Namens.
                with contextlib.suppress(OSError):
                    os.rmdir(ziel)
                _zurueckstellen(erledigt)
                raise
        else:
            erledigt.append((quelle, ziel))
    return erledigt


def _leere_ordner_entfernen(ordner: Path) -> None:
    """Entfernt leere Unterordner, die innersten zuerst. Einer, der
    sich nicht entfernen lässt, bleibt stehen."""
    for wurzel, _unterordner, _namen in os.walk(ordner, topdown=False):
        if Path(wurzel) != ordner:
            with contextlib.suppress(OSError):
                os.rmdir(wurzel)


def _inhalt_ersetzen(
    projekt_ordner: Path,
    fuellen: Callable[[Path], None],
    aufheben: Path | None = None,
) -> Path | None:
    """Ersetzt den Inhalt von `projekt_ordner` durch das, was
    `fuellen` in einen neuen Ordner schreibt; für das Zurücksetzen
    einer Aufgabe wie eines Beispiels (Punkte 346, 362).

    Der Ordner selbst bleibt, damit „Zuletzt geöffnet“ weiter darauf
    zeigt. Drei Schritte, jeder mit Rückweg:

    1. `fuellen` schreibt den neuen Inhalt vollständig in einen
       Zwischenordner neben der Kopie. Bricht dabei die Verbindung zur
       Freigabe ab, ist an der Kopie noch nichts geschehen.
    2. Der alte Inhalt wandert in den Zwischenordner, jeder
       Unterordner möglichst als Ganzes (`_verschieben`). Ist eine
       Datei gesperrt, etwa eine CSV in Excel, kommt alles zurück,
       und es folgt `DateiGesperrt` mit dieser Datei.
    3. Der neue Inhalt wandert in die Kopie.

    Bis Punkt 362 wurde der alte Inhalt an Ort und Stelle gelöscht.
    Eine gesperrte Datei brach das mittendrin ab, und zurück blieb ein
    Ordner ohne Projektdatei.

    Kommt auf dem Rückweg eine alte Datei nicht zurück, bleibt der
    Zwischenordner mit ihr stehen, und es folgt
    `RueckwegGescheitert` mit seinem Unterordner `alt` (Punkt 375).

    Mit `aufheben` kommt der alte Inhalt am Ende in diesen Ordner,
    statt gelöscht zu werden, und die Funktion gibt zurück, wo er
    liegt (Punkt 380). Lässt sich der Ordner nicht anlegen, bleibt er
    im Zwischenordner stehen, und der kommt zurück.

    Den Zwischenordner legt die Funktion selbst an, nicht
    `tempfile.mkdtemp`: der gibt einem Ordner unter Windows Rechte nur
    für das eigene Konto, und verschobene Dateien behielten sie in der
    Kopie (Punkt 397)."""
    zwischen = (
        projekt_ordner.parent / f".natter-neu-{secrets.token_hex(4)}"
    )
    zwischen.mkdir()
    neu = zwischen / "neu"
    ablage = zwischen / "alt"
    liegen_lassen = False
    aufgehoben = None
    try:
        fuellen(neu)
        alt = _verschieben(projekt_ordner, ablage)
        _leere_ordner_entfernen(projekt_ordner)
        try:
            _verschieben(neu, projekt_ordner)
        except DateiGesperrt:
            _zurueckstellen(alt)
            raise
        # Leere Ordner der Aufgabe, etwa `bilder`, kommen mit.
        for wurzel, unterordner, _namen in os.walk(neu):
            for name in unterordner:
                ordner = Path(wurzel, name).relative_to(neu)
                (projekt_ordner / ordner).mkdir(parents=True, exist_ok=True)
        if aufheben is not None:
            aufgehoben = _aufheben(ablage, aufheben)
            liegen_lassen = aufgehoben == ablage
    except DateiGesperrt as fehler:
        if ablage.is_dir() and _dateien(ablage):
            liegen_lassen = True
            raise RueckwegGescheitert(fehler.pfad, ablage) from fehler
        raise
    finally:
        shutil.rmtree(
            neu if liegen_lassen else zwischen, ignore_errors=True
        )
    return aufgehoben


def _aufheben(ablage: Path, ziel: Path) -> Path:
    """Legt den alten Inhalt einer Kopie aus `ablage` nach `ziel` und
    gibt zurück, wo er danach liegt. Ohne die `QUELLDATEI` ist er ein
    gewöhnliches Projekt; sonst hielte Natter ihn für eine zweite
    Kopie derselben Aufgabe."""
    ablage.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        (ablage / QUELLDATEI).unlink(missing_ok=True)
    try:
        os.rename(ablage, ziel)
    except OSError:
        return ablage
    return ziel


def aufgabe_zuruecksetzen(
    projekt_ordner: Path,
) -> tuple[Path, Path | None]:
    """Ersetzt den Inhalt der Kopie einer Aufgabe durch den jetzigen
    Stand der Aufgabe und gibt ihre Projektdatei zurück (Punkt 346),
    dazu den Ordner, in dem der bisherige Inhalt der Kopie liegt
    (`vorher_ordner`, Punkt 380). Bis dahin wurde er gelöscht, und
    die Arbeit mehrerer Stunden war nach einem Fehlklick weg.

    Getauscht wird über `_inhalt_ersetzen`; scheitert etwas, bleibt
    die alte Kopie samt `QUELLDATEI` unverändert. `FileNotFoundError`,
    wenn die Aufgabe nicht mehr da ist, `ValueError` für einen Ordner,
    der keine Kopie einer Aufgabe ist, und im Prüfungsmodus für eine
    Kopie, deren Quelle ein Beispiel ist (Punkt 403), `DateiGesperrt`
    für eine gesperrte Datei in der Kopie, `RueckwegGescheitert`, wenn
    danach alte Dateien im Zwischenordner liegen blieben.
    """
    projekt_ordner = Path(projekt_ordner)
    zeilen = _quellangaben(projekt_ordner)
    if not zeilen:
        raise ValueError(f"{projekt_ordner} ist keine Kopie einer Aufgabe.")
    original = Path(zeilen[0])
    namen = sorted(datei.name for datei in projekt_ordner.glob("*.natter"))
    if not namen or not (original / namen[0]).is_file():
        raise FileNotFoundError(original)
    if pruefungsmodus_laeuft() and beispiel_als_quelle(original):
        raise ValueError(
            f"{original} ist ein Beispiel und keine Aufgabe."
        )

    def fuellen(ziel: Path) -> None:
        _projekt_kopieren(original, ziel)
        _quelle_eintragen(ziel, zeilen[0], original)

    aufgehoben = _inhalt_ersetzen(
        projekt_ordner, fuellen, vorher_ordner(projekt_ordner)
    )
    return projekt_ordner / namen[0], aufgehoben


def _alte_kopie_umziehen(projektdatei: Path, wurzel: Path) -> None:
    """Holt eine Kopie von ihrem früheren Platz unter `wurzel`.

    Bis Fassung 0.3.1 lagen die Kopien direkt unter
    `Dokumente/Natter`, zwischen den eigenen Projekten. Wer dort
    gearbeitet hat, findet seine Arbeit nach dem Update am neuen Ort
    wieder. Umgezogen wird nur, was an seiner Projektdatei als Kopie zu
    erkennen ist, und nur, solange am neuen Ort noch keine liegt.
    """
    alt = natter_ordner() / projektdatei.parent.name
    neu = wurzel / projektdatei.parent.name
    if not (alt / projektdatei.name).exists() or neu.exists():
        return
    wurzel.mkdir(parents=True, exist_ok=True)
    shutil.move(alt, neu)


def beispiel_zuruecksetzen(projekt_ordner: Path) -> Path:
    """Setzt die Kopie eines Beispiels auf den Auslieferungszustand
    zurück und gibt ihre Projektdatei zurück.

    Der Inhalt des Ordners wird über `_inhalt_ersetzen` getauscht, der
    Ordner selbst bleibt. So zeigt „Zuletzt geöffnet" danach auf
    dasselbe Projekt, und es entsteht kein weiterer Ordner.

    Für ein eigenes Projekt gibt es kein Original. Dann wird nichts
    angefasst, sondern ein `ValueError` geworfen: diese Funktion
    ersetzt einen ganzen Ordnerinhalt, und das darf nur geschehen, wenn
    feststeht, was danach wieder hineinkommt.
    """
    projekt_ordner = Path(projekt_ordner)
    original = beispiel_original(projekt_ordner)
    if original is None:
        raise ValueError(f"{projekt_ordner} ist keine Kopie eines Beispiels.")
    _inhalt_ersetzen(
        projekt_ordner, lambda ziel: _projekt_kopieren(original, ziel)
    )
    return next(projekt_ordner.glob("*.natter"))


class _Abschnitt(QWidget):
    """Eine Überschrift mit einer Reihe von Knöpfen darunter."""

    def __init__(self, titel: str, eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 12)
        self._layout.setSpacing(4)

        ueberschrift = QLabel(titel)
        ueberschrift.setStyleSheet(_UEBERSCHRIFT_STIL)
        self._layout.addWidget(ueberschrift)

    def knopf_hinzufuegen(
        self, text: str, tooltip: str, rueckruf: Callable[[], None]
    ) -> QPushButton:
        knopf = QPushButton(text)
        knopf.setToolTip(tooltip)
        knopf.setFlat(True)
        knopf.setCursor(Qt.CursorShape.PointingHandCursor)
        # Der Objektname holt die theme-abhängigen Farben aus dem
        # IDE-weiten QSS dazu - siehe `_EINTRAG_STIL`.
        knopf.setObjectName(STARTBILD_EINTRAG)
        knopf.setStyleSheet(_EINTRAG_STIL)
        knopf.clicked.connect(lambda *_: rueckruf())
        self._layout.addWidget(knopf)
        return knopf


class Startbild(QScrollArea):
    """Das Startbild. Meldet jede Auswahl über ein Signal – es kennt
    weder das Hauptfenster noch den Projektlader."""

    #: Ein zuletzt geöffnetes Projekt bzw. ein per „Öffnen" gewähltes
    projekt_gewaehlt = Signal(Path)
    neues_projekt_gewuenscht = Signal()
    projekt_oeffnen_gewuenscht = Signal()
    erste_schritte_gewuenscht = Signal()
    #: „Zurück zum Projekt“ - erscheint nur, wenn es eines gibt,
    #: zu dem sich zurückkehren lässt.
    zurueck_gewuenscht = Signal()

    def __init__(
        self, einstellungen: QSettings, eltern: QWidget | None = None
    ) -> None:
        super().__init__(eltern)
        self._einstellungen = einstellungen
        #: Name des offenen Projekts, oder `None`. Steht auf dem Knopf,
        #: mit dem es zurück in die Arbeit geht.
        self.offenes_projekt: str | None = None
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.knoepfe: dict[str, QPushButton] = {}
        self.aufbauen()

    def aufbauen(self) -> None:
        """Baut den Inhalt neu – nach jedem geöffneten Projekt, damit
        die Liste der zuletzt geöffneten stimmt."""
        inhalt = QWidget()
        layout = QVBoxLayout(inhalt)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)
        self.knoepfe = {}

        gruss = QLabel("Willkommen bei Natter")
        gruss.setStyleSheet(_GRUSS_STIL)
        layout.addWidget(gruss)

        untertitel = QLabel(
            "Oberfläche entwerfen, Code schreiben, Programm starten."
        )
        untertitel.setStyleSheet(_UNTERTITEL_STIL)
        layout.addWidget(untertitel)
        layout.addSpacing(24)

        layout.addWidget(self._abschnitt_anfangen())
        zuletzt = self._abschnitt_zuletzt()
        if zuletzt is not None:
            layout.addWidget(zuletzt)
        layout.addStretch(1)
        self.setWidget(inhalt)

    def _abschnitt_anfangen(self) -> _Abschnitt:
        abschnitt = _Abschnitt("Anfangen")
        if self.offenes_projekt:
            # Ganz oben und als Erstes: wer über „Ansicht → Startseite“
            # hierher gekommen ist, will meistens gleich wieder zurück.
            # Ohne diesen Knopf gäbe es dafür keinen sichtbaren Weg -
            # das Startbild verdeckt die Reiter, solange es steht.
            self.knoepfe["zurueck"] = abschnitt.knopf_hinzufuegen(
                f"Zurück zu „{self.offenes_projekt}“",
                "Zeigt wieder die geöffneten Dateien",
                self.zurueck_gewuenscht.emit,
            )
        self.knoepfe["neues_projekt"] = abschnitt.knopf_hinzufuegen(
            "Neues Projekt …",
            "Legt einen Ordner mit Formular, Unit und Startdatei an",
            self.neues_projekt_gewuenscht.emit,
        )
        self.knoepfe["projekt_oeffnen"] = abschnitt.knopf_hinzufuegen(
            "Projekt öffnen …",
            "Öffnet eine vorhandene .natter-Datei",
            self.projekt_oeffnen_gewuenscht.emit,
        )
        self.knoepfe["erste_schritte"] = abschnitt.knopf_hinzufuegen(
            "Erste Schritte",
            "Kurze Anleitung: vom leeren Projekt zum laufenden Programm",
            self.erste_schritte_gewuenscht.emit,
        )
        return abschnitt

    def _abschnitt_zuletzt(self) -> _Abschnitt | None:
        """Die zuletzt geöffneten Projekte - außer im Prüfungsmodus.

        Die Liste führt zu dem, was in der Stunde davor bearbeitet
        wurde, in einer Klausur also möglicherweise zur Lösung der
        Aufgabe, die gerade gestellt ist. Sie fällt deshalb weg,
        solange geprüft wird.
        """
        if pruefungsmodus_laeuft():
            return None
        zuletzt = zuletzt_geoeffnet(self._einstellungen)
        if not zuletzt:
            return None
        abschnitt = _Abschnitt("Zuletzt geöffnet")
        for pfad, beschriftung in zip(
            zuletzt, eindeutige_namen(zuletzt), strict=True
        ):
            self.knoepfe[f"zuletzt:{pfad.parent.name}"] = abschnitt.knopf_hinzufuegen(
                beschriftung,
                str(pfad),
                lambda p=pfad: self.projekt_gewaehlt.emit(p),
            )
        return abschnitt
