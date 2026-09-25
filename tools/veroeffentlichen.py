"""Stellt eine fertig gebaute Fassung auf GitHub bereit.

Nach einem erfolgreichen Bau gehören `Natter-Setup.exe` und die ZIP
mit dem ganzen Paket dorthin, wo eine Schule sie findet: unter „Releases"
im öffentlichen Repository. Die Dateien hängen an einem GitHub-Release
und nicht in der Git-Historie - GitHub nimmt dort keine Datei über
100 MB an, und die ZIP hat rund 280 MB.

Ablauf:

1. Die Versionsänderung aus Schritt 2 des Baus wird eingecheckt. Liegt
   sonst etwas nicht Eingechecktes im Baum, wird nicht veröffentlicht:
   eine Fassung, deren Stand in keinem Commit steht, lässt sich später
   nicht wiederfinden.
2. `main` und ein Tag `v<Version>` gehen nach GitHub.
3. Das Release entsteht mit beiden Dateien und einer Beschreibung,
   die erklärt, wie es unter Windows weitergeht, samt Prüfsummen.

Gibt es das Tag schon und zeigt es auf einen anderen Stand, bleibt es
dabei: eine veröffentlichte Nummer wird nicht umgebogen. Zeigt es auf
denselben Stand, etwa weil beim ersten Mal das Hochladen abbrach,
werden die Dateien ersetzt.

    uv run python -m tools.veroeffentlichen --version 0.3.2
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
_SETUP = WURZEL / "dist" / "installer" / "Natter-Setup.exe"
_REPOSITORY = "SuperSparrow-sys/natter"

#: Die Dateien, die Schritt 2 des Baus beim Setzen der Versionsnummer
#: ändert. Nur sie dürfen beim Veröffentlichen noch offen sein; sie
#: werden dann als „Version …" eingecheckt.
_VERSIONSDATEIEN = ("pyproject.toml", "tools/natter.iss", "ide/main.py", "uv.lock")

#: Wo `gh` liegt, wenn es nicht im Suchpfad steht - direkt nach der
#: Installation über winget ist das der Normalfall, bis die Konsole
#: neu gestartet wird.
_GH_ORTE = (
    Path(r"C:\Program Files\GitHub CLI\gh.exe"),
    Path.home() / "AppData" / "Local" / "Programs" / "GitHub CLI" / "gh.exe",
)


class VeroeffentlichungFehler(RuntimeError):
    """Es wurde nicht veröffentlicht; die Meldung sagt, warum."""


def zip_pfad(version: str) -> Path:
    return WURZEL / "dist" / f"Natter-{version}-Setup.zip"


def _ausfuehren(befehl: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        befehl,
        cwd=WURZEL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git(*argumente: str) -> subprocess.CompletedProcess[str]:
    return _ausfuehren(["git", *argumente])


def gh_finden() -> Path | None:
    gefunden = shutil.which("gh")
    if gefunden:
        return Path(gefunden)
    return next((ort for ort in _GH_ORTE if ort.is_file()), None)


def beschreibung(version: str) -> str:
    """Der Text unter dem Release. Wer von der Schule kommt, liest ihn
    vor dem Herunterladen - deshalb nur der Weg unter Windows, in drei
    Schritten.

    Prüfsummen stehen hier bewusst nicht. Eine Tabelle mit 64-stelligen
    Zeichenketten hilft niemandem, der nur herunterladen will, und wer
    sie braucht, findet sie bei GitHub an jeder Datei.
    """
    zeilen = [
        f"## Natter {version} für Windows",
        "",
        f"**`Natter-{version}-Setup.zip`** herunterladen. Darin liegen das "
        "Installationsprogramm, das Zertifikat, die Hilfsskripte und das "
        "Handbuch.",
        "",
        "1. Die ZIP herunterladen.",
        "2. **Vor dem Entpacken** Rechtsklick auf die ZIP → *Eigenschaften* → "
        "unten *Zulassen* anhaken → *OK*. Sonst fragt Windows bei jeder "
        "entpackten Datei einzeln nach, weil sie aus dem Internet stammt.",
        "3. Rechtsklick → *Alle extrahieren …*, danach `ZUERST-LESEN.txt` öffnen.",
        "",
        "`Natter-Setup.exe` allein genügt auf einem Rechner, auf dem das "
        "Zertifikat schon eingetragen ist - etwa für ein Update.",
    ]
    return "\n".join(zeilen) + "\n"


def _offene_dateien() -> list[str]:
    ergebnis = _git("status", "--porcelain")
    if ergebnis.returncode != 0:
        raise VeroeffentlichungFehler("git status ließ sich nicht ausführen.")
    return [zeile[3:].strip() for zeile in ergebnis.stdout.splitlines() if zeile.strip()]


def _versionsaenderung_einchecken(version: str) -> None:
    offen = _offene_dateien()
    fremd = [datei for datei in offen if datei not in _VERSIONSDATEIEN]
    if fremd:
        raise VeroeffentlichungFehler(
            "Nicht veröffentlicht: im Arbeitsbaum liegen Änderungen, die in "
            "keinem Commit stehen:\n    "
            + "\n    ".join(fremd[:10])
            + "\nErst einchecken, dann neu bauen - sonst ließe sich später nicht "
            "sagen, aus welchem Stand diese Fassung stammt."
        )
    if not offen:
        return
    _git("add", "--", *offen)
    ergebnis = _git("commit", "-m", f"Version {version}")
    if ergebnis.returncode != 0:
        raise VeroeffentlichungFehler(f"Commit fehlgeschlagen:\n{ergebnis.stderr.strip()}")


class SchonVeroeffentlicht(VeroeffentlichungFehler):
    """Die Nummer ist schon an einen anderen Stand vergeben."""


def _tag_setzen(version: str, commit: str) -> None:
    """Setzt `v<version>` auf `commit`. Gibt es das Tag schon auf
    genau diesem Stand, bleibt es, wie es ist."""
    tag = f"v{version}"
    ziel = _git("rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    if ziel.returncode != 0:
        raise VeroeffentlichungFehler(f"Den Stand {commit} gibt es nicht.")
    vorhanden = _git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")
    if vorhanden.returncode == 0:
        if vorhanden.stdout.strip() != ziel.stdout.strip():
            raise SchonVeroeffentlicht(
                f"{tag} gibt es schon, und es zeigt auf einen anderen Stand. Eine "
                "veröffentlichte Nummer wird nicht umgebogen - für eine neue "
                "Fassung mit --version eine neue Nummer angeben."
            )
        return
    ergebnis = _git("tag", "-a", tag, ziel.stdout.strip(), "-m", f"Natter {version}")
    if ergebnis.returncode != 0:
        raise VeroeffentlichungFehler(f"Tag fehlgeschlagen:\n{ergebnis.stderr.strip()}")


def _pushen(version: str) -> None:
    for ziel in ("main", f"v{version}"):
        ergebnis = _git("push", "origin", ziel)
        if ergebnis.returncode != 0:
            raise VeroeffentlichungFehler(
                f"git push {ziel} fehlgeschlagen:\n{ergebnis.stderr.strip()}"
            )


def vorbedingungen_pruefen() -> None:
    """Prüft vorab, ob sich veröffentlichen ließe, und wirft sonst.

    Der Bau ruft das in Schritt 1 auf. Scheiterte es erst in Schritt 12,
    wäre eine halbe Stunde vergangen, bis jemand erfährt, dass `gh`
    fehlt oder eine Datei nicht eingecheckt ist.
    """
    gh = gh_finden()
    if gh is None:
        raise VeroeffentlichungFehler(
            "Die GitHub-Kommandozeile fehlt. Einmalig `winget install GitHub.cli` "
            "und danach `gh auth login` - oder mit --nicht-veroeffentlichen bauen."
        )
    if _ausfuehren([str(gh), "auth", "status"]).returncode != 0:
        raise VeroeffentlichungFehler(
            "`gh` ist nicht bei GitHub angemeldet. Einmalig `gh auth login` - "
            "oder mit --nicht-veroeffentlichen bauen."
        )
    fremd = [datei for datei in _offene_dateien() if datei not in _VERSIONSDATEIEN]
    if fremd:
        raise VeroeffentlichungFehler(
            "Im Arbeitsbaum liegen Änderungen, die in keinem Commit stehen:\n    "
            + "\n    ".join(fremd[:10])
            + "\nErst einchecken - sonst ließe sich später nicht sagen, aus "
            "welchem Stand diese Fassung stammt. Zum Ausprobieren: "
            "--nicht-veroeffentlichen."
        )


def veroeffentlichen(
    version: str, *, commit: str | None = None, melden=print  # noqa: ANN001
) -> str:
    """Stellt Fassung `version` auf GitHub bereit und liefert die
    Adresse des Releases.

    Ohne `commit` wird die Versionsänderung eingecheckt und der
    aktuelle Stand markiert - der Fall direkt nach dem Bau. Mit
    `commit` wird genau dieser Stand markiert, etwa wenn nach dem Bau
    schon weitergearbeitet wurde: das Tag soll auf den Stand zeigen, aus
    dem die Dateien gebaut sind, nicht auf einen späteren.
    """
    setup, archiv = _SETUP, zip_pfad(version)
    fehlend = [str(datei) for datei in (setup, archiv) if not datei.is_file()]
    if fehlend:
        raise VeroeffentlichungFehler(
            "Nicht veröffentlicht, es fehlt:\n    " + "\n    ".join(fehlend)
        )

    gh = gh_finden()
    if gh is None:
        raise VeroeffentlichungFehler(
            "Nicht veröffentlicht: die GitHub-Kommandozeile fehlt. Einmalig "
            "`winget install GitHub.cli` und danach `gh auth login`."
        )
    angemeldet = _ausfuehren([str(gh), "auth", "status"])
    if angemeldet.returncode != 0:
        raise VeroeffentlichungFehler(
            "Nicht veröffentlicht: `gh` ist nicht bei GitHub angemeldet. "
            "Einmalig `gh auth login` ausführen."
        )

    if commit is None:
        _versionsaenderung_einchecken(version)
    _tag_setzen(version, commit or "HEAD")
    melden("  main und Tag gehen nach GitHub …")
    _pushen(version)

    tag = f"v{version}"
    dateien = [archiv, setup]
    with tempfile.TemporaryDirectory() as ordner:
        notizen = Path(ordner) / "notizen.md"
        notizen.write_text(beschreibung(version), encoding="utf-8")

        melden(f"  {archiv.name} und {setup.name} werden hochgeladen …")
        vorhanden = _ausfuehren([str(gh), "release", "view", tag, "-R", _REPOSITORY])
        if vorhanden.returncode == 0:
            # Beim ersten Versuch abgebrochen: dieselbe Nummer, derselbe
            # Stand, nur die Dateien fehlten oder waren halb oben.
            befehl = [
                str(gh), "release", "upload", tag, *map(str, dateien),
                "--clobber", "-R", _REPOSITORY,
            ]
        else:
            befehl = [
                str(gh), "release", "create", tag, *map(str, dateien),
                "--title", f"Natter {version}",
                "--notes-file", str(notizen),
                "--latest",
                "-R", _REPOSITORY,
            ]
        ergebnis = _ausfuehren(befehl)
        if ergebnis.returncode != 0:
            raise VeroeffentlichungFehler(
                f"Hochladen fehlgeschlagen:\n{(ergebnis.stderr or ergebnis.stdout).strip()}"
            )

    return f"https://github.com/{_REPOSITORY}/releases/tag/{tag}"


def main(argumente: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        prog="python -m tools.veroeffentlichen",
        description="Stellt eine fertig gebaute Fassung als GitHub-Release bereit.",
    )
    zerleger.add_argument("--version", required=True, metavar="1.2.3")
    zerleger.add_argument(
        "--commit",
        metavar="STAND",
        help="Diesen Stand markieren statt des aktuellen - der, aus dem gebaut wurde.",
    )
    werte = zerleger.parse_args(argumente)
    try:
        adresse = veroeffentlichen(werte.version, commit=werte.commit)
    except VeroeffentlichungFehler as fehler:
        print(fehler, file=sys.stderr)
        return 1
    print(f"Veröffentlicht: {adresse}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
