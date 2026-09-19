"""Tests für den PyInstaller-Export (README.md, Abschnitt 16; M8
Schritt 4, M14).

Nutzt ein `subprocess.Popen`-Double statt eines echten
PyInstaller-Baus (dauert real eine halbe bis eine Minute, siehe
`docs/arbeitspakete/M8.md` für den einmaligen echten Bau/Lauf zur
Abnahme). Geprüft werden die Kommandozusammenstellung, der Ladebalken
und das aus Sicht des Aufrufers sichtbare Ergebnis.

Seit M14 kommt **eine einzige Exe** heraus (Nutzer-Vorgabe September
2026: „es darf keinen extra Ordner geben, das ganze Programm soll in
der exe sein"). Vorher baute Natter einen Ordner und packte ihn in ein
ZIP.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.export import exe_exportieren
from ide.project import Projekt

#: Was PyInstaller ausgibt - gekürzt auf die Zeilen, an denen der
#: Ladebalken sich orientiert.
#:
#: Die Reihenfolge ist **absichtlich durcheinander**: genau so kommt es
#: aus einem echten Lauf. PyInstaller arbeitet seine Phasen nicht sauber
#: nacheinander ab, sondern kehrt nach „Looking for" noch mehrfach zu
#: „Analyzing" zurück. Mit einer sauber sortierten Attrappe wäre der
#: zurückspringende Balken hier nie aufgefallen - in der gebauten
#: Fassung dagegen sofort (M14).
AUSGABE = """\
42 INFO: PyInstaller: 6.22.3
90 INFO: Analyzing base_library.zip ...
300 INFO: Processing module hooks ...
420 INFO: Looking for ctypes DLLs
430 INFO: Analyzing hidden import 'pkg_resources'
440 INFO: Processing pre-safe import module hook
450 INFO: Looking for eggs
500 INFO: Building PYZ (ZlibArchive) ...
610 INFO: Building PKG (CArchive) MeinProjekt.pkg
700 INFO: Building EXE from EXE-00.toc
800 INFO: Build complete! The results are available in: dist
"""


def _projekt(tmp_path: Path, export_optionen: dict | None = None, typ: str = "console") -> Projekt:
    ordner = tmp_path / "MeinProjekt"
    ordner.mkdir()
    (ordner / "main.py").write_text("print('hallo')\n", encoding="utf-8")
    daten = {
        "format": "natter-project/1",
        "name": "MeinProjekt",
        "type": typ,
        "main": "main.py",
    }
    if export_optionen is not None:
        daten["export"] = export_optionen
    return Projekt(ordner=ordner, daten=daten)


class _LaufAttrappe:
    """Verhält sich wie das, was `subprocess.Popen` zurückgibt."""

    def __init__(self, ausgabe: str, rueckgabe: int) -> None:
        self.stdout = iter(ausgabe.splitlines(keepends=True))
        self._rueckgabe = rueckgabe

    def wait(self) -> int:
        return self._rueckgabe


@pytest.fixture
def pyinstaller(monkeypatch: pytest.MonkeyPatch):
    """Fängt den PyInstaller-Aufruf ab und legt die Exe an, die er
    angelegt hätte. Gibt die Liste der Aufrufe zurück."""
    class _Aufrufe(list):
        """Eine Liste der Aufrufe, an der zusätzlich die Einstellungen
        der Attrappe hängen - so braucht ein Test nur ein Objekt."""

        einstellung: dict

    aufrufe = _Aufrufe()
    aufrufe.einstellung = {"rueckgabe": 0, "ausgabe": AUSGABE, "exe_anlegen": True}
    einstellung = aufrufe.einstellung

    def gefaelschtes_popen(befehl, **kwargs):
        aufrufe.append(befehl)
        if einstellung["exe_anlegen"]:
            dist = Path(befehl[befehl.index("--distpath") + 1])
            dist.mkdir(parents=True, exist_ok=True)
            (dist / "MeinProjekt.exe").write_bytes(b"MZ")
        return _LaufAttrappe(einstellung["ausgabe"], einstellung["rueckgabe"])

    monkeypatch.setattr("ide.export.exporter.subprocess.Popen", gefaelschtes_popen)
    return aufrufe


# -- Aufbau des Aufrufs ----------------------------------------------


def test_baut_eine_einzige_exe(tmp_path: Path, pyinstaller) -> None:
    """Der Kern der Vorgabe: `--onefile`, und heraus kommt eine Datei."""
    projekt = _projekt(tmp_path)

    ergebnis = exe_exportieren(projekt)

    assert "--onefile" in pyinstaller[0]
    assert ergebnis.erfolgreich
    assert ergebnis.ausgabe_pfad.suffix == ".exe"
    assert ergebnis.ausgabe_pfad.is_file()


def test_es_bleibt_kein_ordner_neben_der_exe(tmp_path: Path, pyinstaller) -> None:
    """Die Gegenprobe: im Ausgabeordner liegt nichts als die Exe - kein
    Programmordner, kein ZIP zum Entpacken."""
    projekt = _projekt(tmp_path)

    ergebnis = exe_exportieren(projekt)

    danebenliegend = sorted(p.name for p in ergebnis.ausgabe_pfad.parent.iterdir())
    assert danebenliegend == ["MeinProjekt.exe"]


def test_bindet_den_design_ordner_ein_damit_pcl_theme_tokens_findet(
    tmp_path: Path, pyinstaller
) -> None:
    """Ohne `--add-data` stürzt jede exportierte Exe beim Start ab, weil
    `pcl.theme` `design/tokens.json` zur Laufzeit lädt statt es zu
    importieren (real mit einem echten PyInstaller-Bau gefunden, siehe
    `docs/arbeitspakete/M8.md`)."""
    projekt = _projekt(tmp_path)

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    daten = [befehl[i + 1] for i, teil in enumerate(befehl) if teil == "--add-data"]
    assert any(eintrag.endswith("design") for eintrag in daten)


def test_eigene_unterordner_wandern_mit_in_die_exe(tmp_path: Path, pyinstaller) -> None:
    """Wer `bilder/` anlegt und darauf zugreift, erwartet, dass das
    Programm auch auf einem fremden Rechner läuft - ohne den Ordner
    vorher in einer Einstellung anzumelden."""
    projekt = _projekt(tmp_path)
    (projekt.ordner / "bilder").mkdir()
    (projekt.ordner / "daten").mkdir()

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    daten = [befehl[i + 1] for i, teil in enumerate(befehl) if teil == "--add-data"]
    assert any(eintrag.endswith("bilder") for eintrag in daten)
    assert any(eintrag.endswith("daten") for eintrag in daten)


def test_bauabfall_wandert_nicht_mit(tmp_path: Path, pyinstaller) -> None:
    """Die Gegenprobe: `dist/`, `__pycache__` und die Diagramme haben im
    fertigen Programm nichts zu suchen."""
    projekt = _projekt(tmp_path)
    for name in ("dist", "__pycache__", "diagramme", "_pyinstaller_build"):
        (projekt.ordner / name).mkdir()

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    daten = [befehl[i + 1] for i, teil in enumerate(befehl) if teil == "--add-data"]
    for unerwuenscht in ("dist", "__pycache__", "diagramme", "_pyinstaller_build"):
        assert not any(eintrag.endswith(unerwuenscht) for eintrag in daten)


def test_gui_projekt_baut_mit_windowed(tmp_path: Path, pyinstaller) -> None:
    """Ohne `--windowed` öffnet sich hinter jedem GUI-Programm ein
    schwarzes Konsolenfenster."""
    projekt = _projekt(tmp_path, typ="gui")

    exe_exportieren(projekt)

    assert "--windowed" in pyinstaller[0]


def test_konsolenprojekt_baut_ohne_windowed(tmp_path: Path, pyinstaller) -> None:
    """Die Gegenprobe: ein Konsolenprogramm braucht seine Konsole."""
    projekt = _projekt(tmp_path)

    exe_exportieren(projekt)

    assert "--windowed" not in pyinstaller[0]


def test_icon_wird_als_pyinstaller_option_uebergeben(tmp_path: Path, pyinstaller) -> None:
    projekt = _projekt(tmp_path, {"icon": "app.ico"})

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    assert "--icon" in befehl
    assert befehl[befehl.index("--icon") + 1].endswith("app.ico")


# -- Ladebalken -------------------------------------------------------


def test_der_fortschritt_wird_waehrend_des_baus_gemeldet(tmp_path: Path, pyinstaller) -> None:
    """Ein Export dauert eine halbe bis eine Minute. Ohne Rückmeldung
    sieht das nach einem Absturz aus (Nutzer-Vorgabe September 2026:
    Ladebalken in der untersten Zeile)."""
    projekt = _projekt(tmp_path)
    gemeldet: list[tuple[int, str]] = []

    exe_exportieren(projekt, fortschritt=lambda prozent, text: gemeldet.append((prozent, text)))

    werte = [prozent for prozent, _ in gemeldet]
    assert werte, "Es wurde überhaupt kein Fortschritt gemeldet."
    assert werte == sorted(werte), f"Der Balken läuft rückwärts: {werte}"
    assert werte[-1] == 100
    assert all(text for _, text in gemeldet), "Zu jedem Schritt gehört ein Text."


def test_ohne_rueckruf_laeuft_der_export_genauso(tmp_path: Path, pyinstaller) -> None:
    """Der Ladebalken ist Beiwerk - `exe_exportieren` muss auch ohne
    Oberfläche laufen, etwa in einem Test."""
    projekt = _projekt(tmp_path)

    ergebnis = exe_exportieren(projekt)

    assert ergebnis.erfolgreich


# -- Fehlerfall -------------------------------------------------------


def test_fehlgeschlagener_build_liefert_keinen_pfad(tmp_path: Path, pyinstaller) -> None:
    projekt = _projekt(tmp_path)
    pyinstaller.einstellung["rueckgabe"] = 1
    pyinstaller.einstellung["exe_anlegen"] = False

    ergebnis = exe_exportieren(projekt)

    assert not ergebnis.erfolgreich
    assert ergebnis.ausgabe_pfad is None


def test_das_protokoll_kommt_vollstaendig_zurueck(tmp_path: Path, pyinstaller) -> None:
    """Bei einem Fehlschlag ist das Protokoll das Einzige, woran sich
    die Ursache ablesen lässt."""
    projekt = _projekt(tmp_path)
    pyinstaller.einstellung["rueckgabe"] = 1
    pyinstaller.einstellung["exe_anlegen"] = False

    ergebnis = exe_exportieren(projekt)

    assert "Building PYZ" in ergebnis.protokoll


def test_zwischenstaende_bleiben_nicht_im_projekt_liegen(tmp_path: Path, pyinstaller) -> None:
    """PyInstaller legt `build/` und eine `.spec` an. Im Projektordner
    einer Schülerin hat beides nichts verloren."""
    projekt = _projekt(tmp_path)

    exe_exportieren(projekt)

    assert not (projekt.ordner / "_pyinstaller_build").exists()
    assert not (projekt.ordner / "_pyinstaller_spec").exists()
