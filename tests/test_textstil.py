"""Natters Texte sprechen niemanden direkt an.

Weder „du" noch „Sie" - in Meldungen, Hilfeseiten, Projektvorlagen und
auf den Textseiten des Installers. Formuliert wird unpersönlich, wie
in deutscher Software üblich: „Die Datei lässt sich nicht öffnen",
„Zum Fortfahren die Bedingungen annehmen".

Was dieser Test bewusst nicht anfasst: die Ausgaben der
Beispielprogramme. `input("Wie heißt du? ")` ist das Programm einer
Schülerin, das mit seinem Benutzer spricht - nicht Natter, das mit der
Schülerin spricht. Ein Begrüßungsprogramm, das „Wie ist der Name?"
fragt, wäre gestelzt und pädagogisch falsch.

Dazu die zweite Regel: Kommentare und Docstrings tragen keine
Markdown-Hervorhebung. `**so**` schreibt niemand in Quelltext; es war
das deutlichste Zeichen dafür, dass ein Text nicht von Hand entstanden
ist.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent

DU_FORMEN = re.compile(
    r"\b(du|dir|dich|dein|deine|deinen|deinem|deines|deiner|Du|Dir|Dich|Dein|Deine)\b"
)

#: „Sie" nur mitten im Satz. Am Satzanfang ist es das gewöhnliche
#: „sie", nur groß geschrieben („Die Beispiele … Sie sind keine
#: Sammlung"), und das ist keine Anrede. Davor muss deshalb ein
#: Buchstabe oder ein Komma stehen - kein Punkt, keine Klammer, kein
#: Zeilenanfang.
SIE_FORMEN = re.compile(r"(?<=[a-zäöüß,]) (Sie|Ihnen|Ihre|Ihren|Ihrem|Ihres|Ihrer)\b")

#: Dateien, die jemand liest und die deshalb der Regel unterliegen.
TEXTDATEIEN = [
    *sorted((WURZEL / "templates").rglob("*.template")),
    WURZEL / "tools" / "lizenz_vorlagen" / "INSTALLER_LIZENZ.txt",
    WURZEL / "tools" / "lizenz_vorlagen" / "INSTALLER_HINWEIS.txt",
    WURZEL / "docs" / "erste_schritte.md",
    WURZEL / "docs" / "komponenten.md",
    WURZEL / "docs" / "handbuch.md",
]


def _lesen(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("pfad", TEXTDATEIEN, ids=lambda p: p.name)
def test_kein_du_in_den_texten(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {zeile.strip()}"
        for nummer, zeile in enumerate(_lesen(pfad).splitlines(), 1)
        if DU_FORMEN.search(zeile)
    ]
    assert not treffer, f"{pfad.name} spricht direkt an:\n" + "\n".join(treffer[:5])


@pytest.mark.parametrize("pfad", TEXTDATEIEN, ids=lambda p: p.name)
def test_kein_sie_in_den_texten(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {zeile.strip()}"
        for nummer, zeile in enumerate(_lesen(pfad).splitlines(), 1)
        if SIE_FORMEN.search(zeile)
    ]
    assert not treffer, f"{pfad.name} siezt:\n" + "\n".join(treffer[:5])


def test_die_liste_der_textdateien_stimmt() -> None:
    """Sonst prüfte der Test oben stillschweigend nichts."""
    assert len(TEXTDATEIEN) >= 8
    for pfad in TEXTDATEIEN:
        assert pfad.is_file(), pfad


# --------------------------------------------------- Quelltext der IDE


def _python_dateien() -> list[Path]:
    dateien = []
    for teil in ("ide", "pcl"):
        for pfad in sorted((WURZEL / teil).rglob("*.py")):
            if "__pycache__" not in pfad.parts:
                dateien.append(pfad)
    return dateien


ALLE_PYTHON = _python_dateien()

#: Für die beiden Tests auf Etiketten und Fettschrift kommen die
#: Beispielprojekte dazu: ihre Kommentare lesen Schülerinnen und
#: Schüler, mehr als jeden anderen Quelltext.
MIT_BEISPIELEN = ALLE_PYTHON + [
    pfad
    for pfad in sorted((WURZEL / "beispielprojekte").rglob("*.py"))
    if "__pycache__" not in pfad.parts
]

#: Ein Kommentar in einem Stylesheet, das als Zeichenkette im Code
#: steht (`/* ... */`). Er ist für Python eine gewöhnliche
#: Zeichenkette und kein Kommentar, gelesen wird er trotzdem.
QSS_KOMMENTAR = re.compile(r"/\*.*?\*/", re.DOTALL)


def _kommentare_und_docstrings(pfad: Path) -> list[tuple[int, str]]:
    quelle = pfad.read_text(encoding="utf-8")
    stuecke = []
    vorheriger = tokenize.INDENT
    for marke in tokenize.generate_tokens(io.StringIO(quelle).readline):
        ist_docstring = marke.type == tokenize.STRING and vorheriger in (
            tokenize.INDENT,
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.DEDENT,
            tokenize.ENCODING,
        )
        if marke.type == tokenize.COMMENT or ist_docstring:
            stuecke.append((marke.start[0], marke.string))
        elif marke.type in (tokenize.STRING, tokenize.FSTRING_MIDDLE):
            # FSTRING_MIDDLE: die Stylesheets der IDE sind f-Strings,
            # und deren Text liefert `tokenize` seit Python 3.12 nicht
            # mehr als STRING.
            for kommentar in QSS_KOMMENTAR.findall(marke.string):
                stuecke.append((marke.start[0], kommentar))
        if marke.type not in (tokenize.COMMENT, tokenize.NL):
            vorheriger = marke.type
    return stuecke


def test_keine_markdown_hervorhebung_in_kommentaren() -> None:
    """`**so**` in einem Python-Kommentar schreibt kein Mensch."""
    fett = re.compile(r"\*\*(?!\s)[^*\n]+?(?<!\s)\*\*")
    treffer = []
    for pfad in MIT_BEISPIELEN:
        for nummer, text in _kommentare_und_docstrings(pfad):
            if fett.search(text):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nummer}")
    assert not treffer, "Markdown-Fettschrift im Quelltext:\n" + "\n".join(treffer[:10])


def test_keine_datumsetiketten_in_kommentaren() -> None:
    """„Nutzer-Feedback September 2026:" vor jeder Begründung war das
    zweite Erkennungszeichen. Die Begründung bleibt, das Etikett
    nicht."""
    etikett = re.compile(r"Nutzer-(Feedback|Wunsch|Vorgabe|Auftrag|Meldung|Hinweis)")
    treffer = []
    for pfad in MIT_BEISPIELEN:
        for nummer, text in _kommentare_und_docstrings(pfad):
            if etikett.search(text):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nummer}")
    assert not treffer, "Zuschreibungs-Etikett im Quelltext:\n" + "\n".join(treffer[:10])


def test_die_meldungen_der_ide_sprechen_niemanden_an() -> None:
    """Nur die Anrede mit „du": ein „Sie" liesse sich von einem
    gewöhnlichen „sie" am Satzanfang nicht zuverlässig unterscheiden."""
    treffer = []
    for pfad in ALLE_PYTHON:
        quelle = pfad.read_text(encoding="utf-8")
        for marke in tokenize.generate_tokens(io.StringIO(quelle).readline):
            if marke.type != tokenize.STRING:
                continue
            # Nur Texte, die wie ein Satz aussehen - kein Bezeichner,
            # kein Muster, kein Pfad.
            inhalt = marke.string
            if " " not in inhalt or len(inhalt) < 12:
                continue
            if DU_FORMEN.search(inhalt):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{marke.start[0]}: {inhalt[:70]}")
    assert not treffer, "Direkte Anrede in einem Text:\n" + "\n".join(treffer[:10])


# --------------------------------------------- Befehlsform in Du-Form
#
# Auch ohne „du" spricht ein Text an, wenn er befiehlt: „Prüfe: Ist
# der Name richtig geschrieben?" stand bis 0.3.5 in jeder
# Laufzeitmeldung (Punkt 298). Unpersönlich heißt es „Zu prüfen:"
# oder „Den Namen prüfen".
#
# Geprüft werden die Verben, die in Meldungen und Anleitungen
# tatsächlich vorkommen, und nur am Anfang eines Satzes, nach einem
# Doppelpunkt, einer Klammer, einem Anführungszeichen oder einem
# Tabellenstrich. Mitten im Satz ist „Lege" oder „Frage" fast immer
# etwas anderes. Nicht in der Liste: „Siehe" im Verweis auf ein
# anderes Dokument, das seit jeher so geschrieben wird, und „Klick",
# das auch das Hauptwort ist.

DU_BEFEHLE = re.compile(
    r"(?:^|[.!?:;„\"'(|]\s*|\s[-–]\s)"
    r"(Prüfe|Klicke|Wähle|Gib|Öffne|Drücke|Speichere|Lege|Schau|"
    r"Schaue|Versuche|Beachte|Achte|Starte|Schreibe|Benutze|Nutze|"
    r"Trage|Setze|Füge|Lösche|Ändere|Denke|Probiere|Mach|Mache|Gehe|"
    r"Geh|Schließe|Tippe|Kopiere|Ziehe|Lies|Wechsle|Installiere|"
    r"Behebe|Korrigiere|Entferne|Ergänze|Bestätige|Warte|Vergiss|"
    r"Nimm|Hole)\b(?!-)",
    re.MULTILINE,
)


def _sichtbare_zeichenketten(pfad: Path) -> list[tuple[int, str]]:
    """Die Zeichenketten einer Python-Datei ohne Docstrings - also
    das, was auf dem Bildschirm landen kann.

    Ein f-String kommt als Ganzes, samt Platzhaltern: sein Textteil
    allein ist oft nur ein Wort wie in `f"Prüfe: {text}"`."""
    quelle = pfad.read_text(encoding="utf-8")
    zeilen = quelle.splitlines(keepends=True)
    stuecke = []
    vorheriger = tokenize.INDENT
    fstring_anfang: list[tuple[int, int]] = []
    for marke in tokenize.generate_tokens(io.StringIO(quelle).readline):
        ist_docstring = marke.type == tokenize.STRING and vorheriger in (
            tokenize.INDENT,
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.DEDENT,
        )
        if marke.type not in (tokenize.COMMENT, tokenize.NL):
            vorheriger = marke.type
        inhalt = None
        if marke.type == tokenize.FSTRING_START:
            fstring_anfang.append(marke.start)
        elif marke.type == tokenize.FSTRING_END and fstring_anfang:
            (z1, s1), (z2, s2) = fstring_anfang.pop(), marke.end
            if not fstring_anfang:
                inhalt = "".join(zeilen[z1 - 1 : z2])
                inhalt = inhalt[s1 : len(inhalt) - len(zeilen[z2 - 1]) + s2]
        elif marke.type == tokenize.STRING and not ist_docstring:
            inhalt = marke.string
        if inhalt and " " in inhalt and len(inhalt) >= 12:
            stuecke.append((marke.start[0], inhalt))
    return stuecke


def test_die_meldungen_der_ide_befehlen_nicht_in_du_form() -> None:
    treffer = [
        f"{pfad.relative_to(WURZEL)}:{nummer}: {inhalt[:70]}"
        for pfad in ALLE_PYTHON
        for nummer, inhalt in _sichtbare_zeichenketten(pfad)
        if DU_BEFEHLE.search(inhalt)
    ]
    assert not treffer, "Befehlsform in Du-Form:\n" + "\n".join(treffer[:10])


@pytest.mark.parametrize("pfad", TEXTDATEIEN, ids=lambda p: p.name)
def test_die_texte_befehlen_nicht_in_du_form(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {zeile.strip()[:70]}"
        for nummer, zeile in _ohne_codebloecke(_lesen(pfad))
        if DU_BEFEHLE.search(zeile)
    ]
    assert not treffer, f"{pfad.name} befiehlt in Du-Form:\n" + "\n".join(treffer[:5])


def test_die_pruefung_auf_die_befehlsform_greift() -> None:
    """Die Gegenprobe: ohne sie prüfte das Muster oben womöglich
    nichts."""
    assert DU_BEFEHLE.search("Was: x fehlt.\nPrüfe: Ist er richtig?")
    assert DU_BEFEHLE.search("| Strg+G | Gehe zu Zeile |")
    assert not DU_BEFEHLE.search("Zu prüfen: Ist er richtig?")
    assert not DU_BEFEHLE.search("Die Stelle, an der die Frage steht")


def test_ein_f_string_wird_als_ganzes_geprueft(tmp_path: Path) -> None:
    """In `f"Prüfe: {self.pruefe}"` ist der Textteil allein kürzer
    als die Mindestlänge eines Satzes. Genau so stand die Überschrift
    bis 0.3.5 im Fehlerkatalog."""
    datei = tmp_path / "probe.py"
    datei.write_text(
        'def f(x):\n    """Doc."""\n    return f"Prüfe: {x}"\n',
        encoding="utf-8",
    )

    stuecke = _sichtbare_zeichenketten(datei)

    assert [nummer for nummer, _ in stuecke] == [3]
    assert DU_BEFEHLE.search(stuecke[0][1])


# --------------------------------------------------------- Umlaute
#
# In allem, was jemand liest, stehen echte Umlaute - kein „fuer",
# „ueber", „heisst". Bezeichner bleiben davon unberuehrt: `loeschen`
# als Methodenname ist richtig so, `wird geloescht` in einem Satz
# nicht.

#: Woerter, in denen ae/oe/ue/ss fast immer eine Umschreibung ist.
UMSCHRIEBEN = re.compile(
    r"\b([Ff]uer|[Uu]eber\w*|[Kk]oenn\w*|[Mm]uess\w*|[Ww]aer\w*|[Zz]urueck\w*|"
    r"[Nn]aechst\w*|[Gg]roess\w*|[Ss]chliess\w*|[Hh]eiss\w*|[Ll]oesch\w*|"
    r"[Ll]oesung\w*|[Oo]effn\w*|[Ss]chueler\w*|[Aa]ender\w*|[Aa]usfuehr\w*|"
    r"[Ee]infueg\w*|[Pp]ruef\w*|[Ee]rklaer\w*|[Ww]aehl\w*|[Mm]oegl\w*|"
    r"[Hh]oehe|[Bb]loecke|[Kk]noepfe|[Mm]enue\w*|[Ff]laeche\w*|[Hh]aeng\w*|"
    r"[Gg]ehoer\w*|[Aa]nhaelt|[Ll]aeuft|[Ll]aesst|[Ss]paeter|[Hh]aett\w*)\b"
)

#: Was kein Fliesstext ist: Backticks, Bezeichner, Pfade, Aufrufe und
#: Zeichenketten in Anfuehrungszeichen.
NICHT_PROSA = re.compile(
    r"`[^`\n]*`|\b\w*_\w+\b|\b\w+\.\w+\b|\b\w+\(|\"[^\"\n]*\"|'[^'\n]*'"
)


def _prosa(text: str) -> str:
    return NICHT_PROSA.sub(" ", text)


def _ohne_codebloecke(text: str) -> list[tuple[int, str]]:
    """Die Zeilen eines Textes ohne die Codebeispiele.

    In einem Beispiel wie `class Schueler:` oder
    `regression(groessen, schuhgroessen)` ist der ASCII-Bezeichner
    richtig - ein Umlaut hätte dort nichts zu suchen. Gemeint ist die
    Prosa darum herum.
    """
    zeilen = []
    im_block = False
    for nummer, zeile in enumerate(text.splitlines(), 1):
        if zeile.lstrip().startswith("```"):
            im_block = not im_block
            continue
        if not im_block:
            zeilen.append((nummer, zeile))
    return zeilen


@pytest.mark.parametrize("pfad", TEXTDATEIEN, ids=lambda p: p.name)
def test_die_texte_benutzen_echte_umlaute(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {wort}"
        for nummer, zeile in _ohne_codebloecke(_lesen(pfad))
        for wort in UMSCHRIEBEN.findall(_prosa(zeile))
    ]
    assert not treffer, f"{pfad.name} schreibt Umlaute um:\n" + "\n".join(treffer[:8])


def test_kommentare_und_docstrings_benutzen_echte_umlaute() -> None:
    treffer = []
    for pfad in ALLE_PYTHON:
        for nummer, text in _kommentare_und_docstrings(pfad):
            for wort in UMSCHRIEBEN.findall(_prosa(text)):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nummer}  {wort}")
    assert not treffer, "Umschriebene Umlaute im Quelltext:\n" + "\n".join(treffer[:10])


def test_der_installer_liest_seine_texte_als_utf8() -> None:
    """Inno Setup 6 erkennt eine Textdatei nur an der Byte-Order-Mark
    als Unicode. Ohne sie liest es in der ANSI-Codepage des Rechners,
    und aus „für" wird Zeichensalat - genau deshalb standen dort frueher
    „ue"-Umschreibungen."""
    for name in ("INSTALLER_LIZENZ.txt", "INSTALLER_HINWEIS.txt"):
        pfad = WURZEL / "tools" / "lizenz_vorlagen" / name
        roh = pfad.read_bytes()
        assert roh.startswith(b"\xef\xbb\xbf"), f"{name} hat keine BOM"
        text = roh.decode("utf-8-sig")
        assert any(zeichen in text for zeichen in "äöüÄÖÜß"), f"{name} ohne Umlaute"

    iss = (WURZEL / "tools" / "natter.iss").read_bytes()
    assert iss.startswith(b"\xef\xbb\xbf"), "natter.iss hat keine BOM"


# ------------------------------------------------------- Eigenständig
#
# Natter erklärt sich aus sich heraus. Ein Vergleich wie „wie Lazarus
# `TLabel.Color`" sagt jemandem, der Lazarus nie benutzt hat, nichts -
# und stellt Natter als Nachbau dar, der es nicht sein soll.
#
# Eine Ausnahme: `ide/import_lfm/`. Dort ist das fremde Dateiformat der
# Gegenstand des Codes, und ohne seinen Namen wäre nicht mehr zu
# verstehen, was die Module eigentlich lesen.

FREMDE_WERKZEUGE = re.compile(r"\bLazarus\b|\bLCL\w*\b|\bDelphi\b")

AUSGENOMMEN = ("import_lfm",)


def _ohne_ausnahmen(dateien: list[Path]) -> list[Path]:
    return [p for p in dateien if not any(teil in p.parts for teil in AUSGENOMMEN)]


def test_der_quelltext_erklaert_sich_ohne_fremdes_werkzeug() -> None:
    treffer = []
    for pfad in _ohne_ausnahmen(ALLE_PYTHON):
        for nummer, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
            if FREMDE_WERKZEUGE.search(zeile):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nummer}: {zeile.strip()[:70]}")
    assert not treffer, "Verweis auf ein fremdes Werkzeug:\n" + "\n".join(treffer[:10])


SEITEN_FUER_LERNENDE = [
    # Auch die Paketangabe: sie steht im gebauten Wheel, in `pip show
    # natter` und damit in jeder Auslieferung. Sie war die eine Stelle,
    # die beim Aufraeumen stehengeblieben ist, weil der Test nur
    # Python-Dateien und Hilfeseiten kannte.
    WURZEL / "pyproject.toml",
    WURZEL / "tools" / "natter.iss",
    WURZEL / "README.md",
    WURZEL / "docs" / "erste_schritte.md",
    WURZEL / "docs" / "komponenten.md",
    WURZEL / "docs" / "handbuch.md",
    *sorted((WURZEL / "templates").rglob("*.template")),
]


@pytest.mark.parametrize("pfad", SEITEN_FUER_LERNENDE, ids=lambda p: p.name)
def test_die_seiten_fuer_lernende_stehen_fuer_sich(pfad: Path) -> None:
    treffer = [
        f"Zeile {nummer}: {zeile.strip()[:70]}"
        for nummer, zeile in enumerate(_lesen(pfad).splitlines(), 1)
        if FREMDE_WERKZEUGE.search(zeile)
    ]
    assert not treffer, f"{pfad.name} verweist auf ein fremdes Werkzeug:\n" + "\n".join(
        treffer[:5]
    )


# ------------------------- Punkt 4: was sich am Installer prüfen lässt
#
# Wie die Lizenz- und die Hinweisseite im Assistenten *aussehen*, zeigt
# nur ein Durchklicken mit angemeldeter Sitzung. Zwei Dinge lassen sich
# aber auch ohne das festhalten, und beide waren die Sorge des
# Eintrags: dass die Seiten überhaupt eingebunden sind und dass ihre
# Zeilen ins Fenster passen.

#: Inno Setup zeigt beide Seiten in einem Feld fester Breite. Bei
#: rund 80 Zeichen je Zeile ist Schluss; was länger ist, bricht um und
#: sieht nach einem Fehler aus.
INSTALLER_ZEILENBREITE = 80

INSTALLER_TEXTE = (
    WURZEL / "tools" / "lizenz_vorlagen" / "INSTALLER_LIZENZ.txt",
    WURZEL / "tools" / "lizenz_vorlagen" / "INSTALLER_HINWEIS.txt",
)


@pytest.mark.parametrize("pfad", INSTALLER_TEXTE, ids=lambda p: p.name)
def test_die_zeilen_passen_in_das_fenster_des_installers(pfad: Path) -> None:
    zu_lang = [
        f"Zeile {nummer}: {len(zeile)} Zeichen"
        for nummer, zeile in enumerate(_lesen(pfad).splitlines(), 1)
        if len(zeile) > INSTALLER_ZEILENBREITE
    ]

    assert not zu_lang, f"{pfad.name}:\n" + "\n".join(zu_lang[:5])


def test_beide_seiten_sind_im_installer_eingebunden() -> None:
    """Eine Seite, die niemand einbindet, kann noch so schön sein."""
    skript = (WURZEL / "tools" / "natter.iss").read_text(encoding="utf-8-sig")

    assert r"LicenseFile=lizenz_vorlagen\INSTALLER_LIZENZ.txt" in skript
    assert r"InfoBeforeFile=lizenz_vorlagen\INSTALLER_HINWEIS.txt" in skript
