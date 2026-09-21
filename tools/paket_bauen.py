"""Baut das Paket, das eine Lehrkraft bekommt, und packt es als ZIP.

Die `Natter-Setup.exe` allein genügt nicht: ohne das Zertifikat
blockiert Windows den Start auf jedem Rechner mit Smart App Control,
ohne die Skripte lässt sich der Eintrag weder prüfen noch wieder
zurücknehmen, und ohne Anleitung weiß niemand, warum. Welche Dateien
dazugehören, steht in `tools/paket/README.md`; hier stehen dieselben
Dateien noch einmal als Tabelle, und `tests/test_paket.py` hält beide
aneinander.

Zusammengestellt wird nicht von Hand. Das Paket zur Fassung 0.3.0 war
von Hand gepackt und zwei der neun Dateien fehlten darin - gemerkt hat
es niemand, weil dem ZIP nicht anzusehen ist, was nicht drin ist.

    uv run python -m tools.paket_bauen
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import zipfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

_PAKETQUELLE = WURZEL / "tools" / "paket"
_ZERTIFIKAT = WURZEL / "tools" / "signieren" / "natter-codesign.cer"
_INSTALLER = WURZEL / "dist" / "installer" / "Natter-Setup.exe"
_GEBAUT = WURZEL / "dist" / "Natter"
_HANDBUCH = WURZEL / "docs" / "fuer_lehrkraefte.md"
_ZIEL = WURZEL / "dist" / "paket"

#: Was ins Paket gehört, als Name im Paket und Herkunft. Die Reihenfolge
#: ist die, in der jemand die Dateien braucht: erst lesen, dann das
#: Zertifikat eintragen, dann installieren.
_INHALT: tuple[tuple[str, Path], ...] = (
    ("ZUERST-LESEN.txt", _PAKETQUELLE / "ZUERST-LESEN.txt"),
    ("Zertifikat-eintragen.ps1", _PAKETQUELLE / "Zertifikat-eintragen.ps1"),
    ("natter-codesign.cer", _ZERTIFIKAT),
    ("Natter-Setup.exe", _INSTALLER),
    ("Natter-pruefen.ps1", _PAKETQUELLE / "Natter-pruefen.ps1"),
    ("Zertifikat-entfernen.ps1", _PAKETQUELLE / "Zertifikat-entfernen.ps1"),
)


class PaketFehler(RuntimeError):
    """Etwas fehlt, das ins Paket gehört."""


# --------------------------------------------- Handbuch als HTML

_STIL = """\
  body {
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 11pt;
    line-height: 160%;
    max-width: 720px;
    margin: 32px auto;
    padding: 0 20px;
    color: #202020;
    background: #ffffff;
  }
  h1, h2, h3 { margin-top: 28px; margin-bottom: 10px; }
  code { font-family: Consolas, "Courier New", monospace; font-size: 10pt; }
  pre {
    font-family: Consolas, "Courier New", monospace;
    background-color: #f2f4f6;
    border: 1px solid #d5dade;
    padding: 10px;
    overflow-x: auto;
  }
  table { border-collapse: collapse; margin: 12px 0; }
  th, td { border: 1px solid #d5dade; padding: 5px 10px; text-align: left; }
  th { background-color: #f2f4f6; }
  hr { border: none; border-top: 1px solid #d5dade; margin: 28px 0; }
"""


def _zeichen(text: str) -> str:
    """Setzt die Auszeichnungen innerhalb einer Zeile um.

    Mehr als Code, fett und kursiv kommt im Handbuch nicht vor, und
    eine Bibliothek dafür wäre eine Abhängigkeit, die die Auslieferung
    mitschleppen müsste.
    """
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def _tabellenzeile(zeile: str, kopf: bool) -> str:
    felder = [f.strip() for f in zeile.strip().strip("|").split("|")]
    marke = "th" if kopf else "td"
    inhalt = "".join(f"<{marke}>{_zeichen(f)}</{marke}>" for f in felder)
    return f"<tr>{inhalt}</tr>"


def handbuch_als_html(markdown: str, titel: str) -> str:
    """Wandelt das Handbuch in eine Seite zum Lesen im Browser.

    Umgesetzt wird der Ausschnitt, den `docs/fuer_lehrkraefte.md`
    benutzt: Überschriften, Absätze, Aufzählungen, Tabellen,
    Codeblöcke und Trennlinien.
    """
    aus: list[str] = []
    absatz: list[str] = []
    liste: list[str] = []
    tabelle: list[str] = []
    im_code = False
    code: list[str] = []

    def absatz_schliessen() -> None:
        if absatz:
            aus.append("<p>" + " ".join(_zeichen(z) for z in absatz) + "</p>")
            absatz.clear()

    def liste_schliessen() -> None:
        if liste:
            aus.append("<ul>")
            aus.extend(f"<li>{_zeichen(z)}</li>" for z in liste)
            aus.append("</ul>")
            liste.clear()

    def tabelle_schliessen() -> None:
        if tabelle:
            aus.append("<table>")
            aus.append(_tabellenzeile(tabelle[0], kopf=True))
            # Die zweite Zeile einer Markdown-Tabelle sind nur Striche.
            for zeile in tabelle[2:]:
                aus.append(_tabellenzeile(zeile, kopf=False))
            aus.append("</table>")
            tabelle.clear()

    def alles_schliessen() -> None:
        absatz_schliessen()
        liste_schliessen()
        tabelle_schliessen()

    for zeile in markdown.splitlines():
        if zeile.startswith("```"):
            if im_code:
                aus.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code.clear()
            else:
                alles_schliessen()
            im_code = not im_code
            continue
        if im_code:
            code.append(zeile)
            continue

        blank = not zeile.strip()
        if blank:
            alles_schliessen()
            continue

        if zeile.startswith("|"):
            absatz_schliessen()
            liste_schliessen()
            tabelle.append(zeile)
            continue

        ueberschrift = re.match(r"^(#{1,4})\s+(.*)$", zeile)
        if ueberschrift:
            alles_schliessen()
            tiefe = len(ueberschrift.group(1))
            aus.append(f"<h{tiefe}>{_zeichen(ueberschrift.group(2))}</h{tiefe}>")
            continue

        if zeile.startswith("---"):
            alles_schliessen()
            aus.append("<hr>")
            continue

        aufzaehlung = re.match(r"^[-*]\s+(.*)$", zeile)
        if aufzaehlung:
            absatz_schliessen()
            tabelle_schliessen()
            liste.append(aufzaehlung.group(1))
            continue

        nummeriert = re.match(r"^\d+\.\s+(.*)$", zeile)
        if nummeriert:
            absatz_schliessen()
            tabelle_schliessen()
            liste.append(nummeriert.group(1))
            continue

        liste_schliessen()
        tabelle_schliessen()
        absatz.append(zeile.strip())

    alles_schliessen()

    rumpf = "\n".join(aus)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="de">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(titel)}</title>\n"
        f"<style>\n{_STIL}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{rumpf}\n"
        "</body>\n"
        "</html>\n"
    )


# --------------------------------------------- Das Paket


def paket_bauen(*, ziel: Path | None = None) -> Path:
    """Stellt das Paket zusammen und gibt den Ordner zurück."""
    ordner = ziel or _ZIEL
    fehlend = [str(q) for _, q in _INHALT if not q.exists()]
    if not _HANDBUCH.exists():
        fehlend.append(str(_HANDBUCH))
    if not (_GEBAUT / "Lizenzen").is_dir():
        fehlend.append(str(_GEBAUT / "Lizenzen"))
    if fehlend:
        raise PaketFehler(
            "Für das Paket fehlen Dateien:\n  " + "\n  ".join(fehlend)
        )

    if ordner.exists():
        shutil.rmtree(ordner)
    ordner.mkdir(parents=True)

    for name, quelle in _INHALT:
        shutil.copy2(quelle, ordner / name)

    markdown = _HANDBUCH.read_text(encoding="utf-8")
    (ordner / "Handbuch.md").write_text(markdown, encoding="utf-8")
    (ordner / "Handbuch.html").write_text(
        handbuch_als_html(markdown, "Natter für Lehrkräfte"), encoding="utf-8"
    )

    shutil.copytree(_GEBAUT / "Lizenzen", ordner / "Lizenzen")
    return ordner


def zip_bauen(version: str, *, ordner: Path | None = None) -> Path:
    """Packt das Paket in ein ZIP mit der Versionsnummer im Namen.

    Die Nummer steht im Dateinamen, weil auf einem USB-Stick sonst
    zwei Fassungen nebeneinander liegen, denen man nicht ansieht,
    welche die neuere ist.
    """
    quelle = ordner or _ZIEL
    ziel = quelle.parent / f"Natter-{version}-fuer-Lehrkraefte.zip"
    if ziel.exists():
        ziel.unlink()

    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as archiv:
        for pfad in sorted(quelle.rglob("*")):
            if pfad.is_file():
                archiv.write(pfad, pfad.relative_to(quelle).as_posix())
    return ziel


def main(argumente: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        prog="python -m tools.paket_bauen",
        description="Stellt das Paket für die Schule zusammen und packt es.",
    )
    zerleger.add_argument("--version", required=True, metavar="1.2.3")
    werte = zerleger.parse_args(argumente)

    try:
        ordner = paket_bauen()
    except PaketFehler as fehler:
        print(f"Abgebrochen: {fehler}")
        return 1

    archiv = zip_bauen(werte.version, ordner=ordner)
    groesse = archiv.stat().st_size / 1024 / 1024
    print(f"  {ordner}")
    print(f"  {archiv} ({groesse:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
