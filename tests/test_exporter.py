"""Tests für den PyInstaller-Export (README.md, Abschnitt 16; M8
Schritt 4, M14).

Nutzt ein `subprocess.Popen`-Double statt eines echten
PyInstaller-Baus (dauert real eine halbe bis eine Minute, siehe
Arbeitspaket M8 für den einmaligen echten Bau/Lauf zur
Abnahme). Geprüft werden die Kommandozusammenstellung, der Ladebalken
und das aus Sicht des Aufrufers sichtbare Ergebnis.

Seit M14 kommt eine einzige Exe heraus (Nutzer-Vorgabe September
2026: „es darf keinen extra Ordner geben, das ganze Programm soll in
der exe sein"). Vorher baute Natter einen Ordner und packte ihn in ein
ZIP.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ide.export import exe_exportieren
from ide.project import Projekt

#: Was PyInstaller ausgibt - gekürzt auf die Zeilen, an denen der
#: Ladebalken sich orientiert.
#:
#: Die Reihenfolge ist absichtlich durcheinander: genau so kommt es
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


@pytest.fixture(autouse=True)
def _nicht_wirklich_signieren(monkeypatch: pytest.MonkeyPatch):
    """Das Signieren der fertigen Exe wird hier nicht mitgeprüft.

    Es ruft PowerShell, und die `pyinstaller`-Attrappe unten fängt
    jeden Prozessaufruf ab - sie suchte in einem Signierbefehl nach
    `--distpath` und scheiterte daran. Wichtiger als die Mechanik ist
    aber: ein Testlauf soll keine echten Dateien signieren. Was das
    Signieren selbst tut, steht in `tests/test_export_signatur.py`.
    """
    from ide.export.signatur import SignaturErgebnis

    monkeypatch.setattr(
        "ide.export.exporter.signieren_wenn_moeglich",
        lambda exe, **_: SignaturErgebnis(False, "Im Test nicht signiert."),
    )


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

    echtes_popen = subprocess.Popen

    def gefaelschtes_popen(befehl, **kwargs):
        # Ersetzt wird `subprocess.Popen` für den ganzen Testprozess.
        # Startet währenddessen ein anderer Faden einen Prozess (in der
        # vollen Suite etwa ein Rest aus einem früheren Test), stand
        # dessen Befehl vorn in der Liste, und ein Test las ihn als
        # PyInstaller-Aufruf. Aufgezeichnet wird deshalb nur, was
        # `--distpath` enthält; alles andere läuft wirklich.
        if "--distpath" not in befehl:
            return echtes_popen(befehl, **kwargs)
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
    # Ohne `-P` stand der Projektordner vor der Standardbibliothek, und
    # eine `random.py` der Schülerin lief im Prozess von PyInstaller.
    assert pyinstaller[0].index("-P") < pyinstaller[0].index("-m")
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
    Arbeitspaket M8)."""
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
    assert any(eintrag.endswith("bilder") for eintrag in daten), befehl
    assert any(eintrag.endswith("daten") for eintrag in daten), befehl


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
    (projekt.ordner / "app.ico").write_bytes(b"\x00\x00\x01\x00")

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    assert "--icon" in befehl
    assert befehl[befehl.index("--icon") + 1].endswith("app.ico")


# -- Ladebalken -------------------------------------------------------


def test_der_fortschritt_wird_waehrend_des_baus_gemeldet(tmp_path: Path, pyinstaller) -> None:
    """Ein Export dauert eine halbe bis eine Minute. Ohne Rückmeldung
 sieht das nach einem Absturz aus (Vorgabe: Ladebalken in der untersten Zeile)."""
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


# -- Nur mitnehmen, was das Projekt braucht -------------
#
# Anlass: "Schaue wie ich den Export eines Programms als exe schneller
# hinbekommen aber trotzdem als Stand alone Datei." Real gemessen bekam
# jedes Projekt dasselbe Paket - ein Taschenrechner mit vier Knoepfen wog
# 120,2 MB und brauchte 110 s, genau wie das scikit-learn-Beispiel.
# PyInstaller folgt auch Importen tief in einer Funktion, und `pcl`
# fuehrt für `Chart` und `regression` numpy, matplotlib und pandas mit.
#
# Danach: 44,9 MB in 53 s für den Taschenrechner, waehrend
# 09_ObstSortierer mit 111,9 MB alles Noetige behaelt.


def _projekt_mit_quelltext(tmp_path: Path, quelltext: str) -> Projekt:
    projekt = _projekt(tmp_path, typ="gui")
    (projekt.ordner / "u_main.py").write_text(quelltext, encoding="utf-8")
    return projekt


def _ausgeschlossen(aufruf: list[str]) -> set[str]:
    return {
        aufruf[i + 1] for i, teil in enumerate(aufruf) if teil == "--exclude-module"
    }


def test_ein_programm_ohne_diagramm_laesst_die_schweren_pakete_draussen(
    tmp_path: Path, pyinstaller
) -> None:
    projekt = _projekt_mit_quelltext(tmp_path, "self.l_ergebnis.caption = 'hallo'\n")

    exe_exportieren(projekt)

    draussen = _ausgeschlossen(pyinstaller[0])
    assert {"matplotlib", "numpy", "pandas", "sklearn", "scipy"} <= draussen


def test_ein_programm_mit_chart_behaelt_matplotlib_und_numpy(
    tmp_path: Path, pyinstaller
) -> None:
    """`Chart` steht im erzeugten `u_main_design.py`, sobald im Designer
    ein Diagramm liegt - deshalb reicht das Wort im Projekt."""
    projekt = _projekt_mit_quelltext(tmp_path, "self.ch_verlauf = Chart(self)\n")

    exe_exportieren(projekt)

    draussen = _ausgeschlossen(pyinstaller[0])
    assert "matplotlib" not in draussen
    assert "numpy" not in draussen
    assert "pandas" not in draussen
    assert "sklearn" in draussen


def test_ein_programm_mit_sklearn_behaelt_den_ganzen_stapel(
    tmp_path: Path, pyinstaller
) -> None:
    projekt = _projekt_mit_quelltext(
        tmp_path, "from sklearn.ensemble import RandomForestClassifier\n"
    )

    exe_exportieren(projekt)

    draussen = _ausgeschlossen(pyinstaller[0])
    for paket in ("sklearn", "scipy", "joblib", "numpy", "pandas"):
        assert paket not in draussen, f"{paket} wird gebraucht"


def test_die_werkzeuge_der_ide_wandern_nie_in_ein_schuelerprogramm(
    tmp_path: Path, pyinstaller
) -> None:
    """`debugpy`, `libcst` und `jedi` liegen in derselben Umgebung, aber
    `pcl` fasst sie nie an."""
    projekt = _projekt_mit_quelltext(tmp_path, "print('hallo')\n")

    exe_exportieren(projekt)

    draussen = _ausgeschlossen(pyinstaller[0])
    assert {"debugpy", "libcst", "jedi", "tkinter"} <= draussen


def test_im_zweifel_wird_mitgenommen(tmp_path: Path, pyinstaller) -> None:
    """Ein zu grosses Paket kostet Sekunden, ein fehlendes kostet ein
    Programm, das beim Freund nicht startet."""
    projekt = _projekt_mit_quelltext(tmp_path, "import openpyxl\n")

    exe_exportieren(projekt)

    assert "openpyxl" not in _ausgeschlossen(pyinstaller[0])


# Der häufigste Fall im Unterricht: exportieren, ausprobieren, etwas
# ändern, wieder exportieren - und das Programm von vorhin steht noch
# offen. Windows sperrt die Datei dann. Bis flog Natter
# dabei mit einem PermissionError heraus, statt es zu sagen.


def test_eine_laufende_exe_wird_gemeldet_statt_abzustuerzen(tmp_path) -> None:
    from ide.export.exporter import _laeuft_noch

    exe = tmp_path / "Kassenbuch.exe"
    exe.write_bytes(b"MZ")

    # Offen zum Schreiben = gesperrt, wie ein laufendes Programm.
    with exe.open("rb"):
        pass  # Lesen sperrt nicht - das muss durchgehen
    assert _laeuft_noch(exe) is None

    assert _laeuft_noch(tmp_path / "gibtsnicht.exe") is None


def test_die_meldung_ist_deutsch_und_sagt_was_zu_tun_ist(tmp_path, monkeypatch) -> None:
    from ide.export import exporter

    exe = tmp_path / "Kassenbuch.exe"
    exe.write_bytes(b"MZ")

    def gesperrt(self, *args, **kwargs):
        raise PermissionError(5, "Zugriff verweigert")

    monkeypatch.setattr("pathlib.Path.open", gesperrt)

    meldung = exporter._laeuft_noch(exe)

    assert meldung is not None
    assert "Kassenbuch.exe" in meldung
    assert "läuft gerade noch" in meldung
    assert "schließen" in meldung


def test_der_export_bricht_dann_sauber_ab(tmp_path, monkeypatch) -> None:
    """Kein Traceback, sondern ein ExportErgebnis mit der Meldung -
    das Hauptfenster zeigt sie genauso an wie jeden anderen
    Fehlschlag."""
    from ide.export import exporter

    monkeypatch.setattr(exporter, "_laeuft_noch", lambda pfad: "läuft noch")
    projekt = _projekt(tmp_path)

    ergebnis = exporter.exe_exportieren(projekt, tmp_path / "dist")

    assert ergebnis.erfolgreich is False
    assert ergebnis.ausgabe_pfad is None
    assert ergebnis.protokoll == "läuft noch"


# -- Dateien, die das Programm schreibt (Punkt 194) -------------------


def test_eine_datei_im_projektstamm_wandert_mit(tmp_path: Path, pyinstaller) -> None:
    """Eine `noten.csv` direkt neben `main.py` fehlte in der Exe ganz,
    mitgenommen wurden nur Unterordner. Quelltext und Projektdateien
    wandern dagegen nicht als Daten mit."""
    projekt = _projekt(tmp_path)
    (projekt.ordner / "noten.csv").write_text("Name;Note\n", encoding="utf-8")
    (projekt.ordner / "MeinProjekt.natter").write_text("{}", encoding="utf-8")

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    daten = [befehl[i + 1] for i, teil in enumerate(befehl) if teil == "--add-data"]
    assert any(eintrag.startswith(str(projekt.ordner / "noten.csv")) for eintrag in daten)
    assert not any(".natter" in eintrag or "main.py" in eintrag for eintrag in daten)


def test_die_exe_bekommt_den_arbeitsordner_haken(tmp_path: Path, pyinstaller) -> None:
    projekt = _projekt(tmp_path)

    exe_exportieren(projekt)

    assert "--runtime-hook" in pyinstaller[0]


def test_der_haken_setzt_den_arbeitsordner_auf_den_ordner_der_exe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In einer Exe mit `--onefile` zeigt `__file__` in einen Ordner
    unter `%TEMP%`, der beim Beenden gelöscht wird. Was das Programm mit
    relativem Pfad schreibt, soll neben der Exe landen."""
    import sys

    from ide.export.exporter import _ARBEITSORDNER_HOOK

    exe_ordner = tmp_path / "irgendwo"
    exe_ordner.mkdir()
    anderswo = tmp_path / "anderswo"
    anderswo.mkdir()
    monkeypatch.chdir(anderswo)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_ordner / "MeinProjekt.exe"))

    exec(compile(_ARBEITSORDNER_HOOK, "natter_arbeitsordner.py", "exec"), {})

    assert Path.cwd() == exe_ordner


@pytest.mark.parametrize(
    ("beispiel", "dateiname"),
    [("06_Kontoverwaltung", "konten.sqlite"), ("07_CsvAuswertung", "auswertung.csv")],
)
def test_die_beispiele_schreiben_nicht_in_den_auspackordner(
    beispiel: str, dateiname: str
) -> None:
    """Die Beispiele legten ihre Dateien mit `Path(__file__).parent`
    ab; in der Exe gingen sie damit beim Beenden verloren."""
    quelltext = (
        Path(__file__).resolve().parent.parent / "beispielprojekte" / beispiel / "u_main.py"
    ).read_text(encoding="utf-8")
    zeilen = [z for z in quelltext.splitlines() if dateiname in z and "=" in z]
    assert zeilen
    for zeile in zeilen:
        assert "__file__" not in zeile


# -- Abhängigkeiten zwischen den optionalen Paketen (Punkt 196) -------


def test_to_dataframe_behaelt_pandas_und_numpy(tmp_path: Path, pyinstaller) -> None:
    """pandas bricht ohne numpy schon beim Import ab. Das Wort
    `to_dataframe` hielt nur pandas im Programm."""
    projekt = _projekt_mit_quelltext(
        tmp_path,
        "df = self.sq_noten.to_dataframe()\nself.sg_noten.load_dataframe(df)\n",
    )

    exe_exportieren(projekt)

    draussen = _ausgeschlossen(pyinstaller[0])
    assert "pandas" not in draussen
    assert "numpy" not in draussen


def test_pyplot_behaelt_numpy(tmp_path: Path, pyinstaller) -> None:
    projekt = _projekt_mit_quelltext(tmp_path, "import matplotlib.pyplot as plt\n")

    exe_exportieren(projekt)

    draussen = _ausgeschlossen(pyinstaller[0])
    assert "matplotlib" not in draussen
    assert "numpy" not in draussen


# -- Symbol der Exe (Punkt 206) ---------------------------------------


def _formular_mit_symbol(projekt: Projekt, symbol: str) -> None:
    import json

    projekt.daten["main_form"] = "u_main"
    (projekt.ordner / "u_main.pfm").write_text(
        json.dumps(
            {
                "format": "pfm/1",
                "class": "Form1",
                "type": "Form",
                "properties": {"caption": "Test", "icon": symbol},
                "children": [],
            }
        ),
        encoding="utf-8",
    )


def test_die_exe_traegt_das_symbol_des_hauptformulars(
    tmp_path: Path, pyinstaller
) -> None:
    """Das `icon` des Formulars wird im Objektinspektor gesetzt; die Exe
    trug trotzdem das Standardsymbol von PyInstaller."""
    projekt = _projekt(tmp_path, typ="gui")
    (projekt.ordner / "assets").mkdir()
    (projekt.ordner / "assets" / "symbol.png").write_bytes(b"\x89PNG")
    _formular_mit_symbol(projekt, "assets/symbol.png")

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    assert befehl[befehl.index("--icon") + 1] == str(
        projekt.ordner / "assets" / "symbol.png"
    )


def test_ein_fehlendes_symbol_bricht_den_bau_nicht_ab(
    tmp_path: Path, pyinstaller
) -> None:
    projekt = _projekt(tmp_path, typ="gui")
    _formular_mit_symbol(projekt, "assets/gibt_es_nicht.png")

    exe_exportieren(projekt)

    assert "--icon" not in pyinstaller[0]


def test_schema_und_export_kennen_dieselben_felder() -> None:
    """Das Schema beschrieb `product_name`, `version`,
    `include_data_dir` und `target`, der Export las davon nichts."""
    import json

    from ide.pfade import daten_ordner

    schema = json.loads(
        (daten_ordner("schemas") / "project.schema.json").read_text(encoding="utf-8")
    )
    assert set(schema["properties"]["export"]["properties"]) == {"icon"}


# -- Verzeichnisverknüpfungen im Projekt (Punkt 252) ------------------


def test_der_export_folgt_keiner_verzeichnisverknuepfung(
    tmp_path: Path, pyinstaller
) -> None:
    """Eine Junction auf einen fremden Ordner und eine auf das Projekt
    selbst, beide ohne Verwaltungsrechte angelegt. Mit in die Exe
    kommen nur die Dateien des Projekts."""
    import sys

    if sys.platform != "win32":
        pytest.skip("Junctions gibt es nur unter Windows.")
    import _winapi

    projekt = _projekt(tmp_path)
    (projekt.ordner / "daten").mkdir()
    (projekt.ordner / "daten" / "werte.csv").write_text("a;b\n", encoding="utf-8")
    fremd = tmp_path / "fremd"
    fremd.mkdir()
    (fremd / "geheim.txt").write_text("fremd\n", encoding="utf-8")
    _winapi.CreateJunction(str(fremd), str(projekt.ordner / "daten" / "verweis"))
    _winapi.CreateJunction(str(fremd), str(projekt.ordner / "nebenan"))
    _winapi.CreateJunction(str(projekt.ordner), str(projekt.ordner / "schleife"))

    exe_exportieren(projekt)

    befehl = pyinstaller[0]
    daten = [befehl[i + 1] for i, teil in enumerate(befehl) if teil == "--add-data"]
    quellen = [eintrag.rsplit(";", 1)[0] for eintrag in daten]
    assert not any(
        "verweis" in q or "nebenan" in q or "schleife" in q for q in quellen
    ), daten
    assert str(projekt.ordner / "daten" / "werte.csv") in quellen


# -- Namen und Pfade aus der Projektdatei (Punkt 250) -----------------


def _projekt_mit_fremden_pfaden(tmp_path: Path) -> tuple[Path, Path]:
    """Die Anordnung aus Punkt 250: ein Projekt, dessen Name aus dem
    Zielordner hinauf zu einer fremden Exe führt, und dessen
    Startdatei fehlt. Gibt die Projektdatei und die fremde Exe
    zurück."""
    import json

    aussen = tmp_path / "aussen"
    ordner = aussen / "Projekt"
    ordner.mkdir(parents=True)
    fremd = aussen / "fremd.exe"
    fremd.write_bytes(b"MZ fremd")
    projektdatei = ordner / "Projekt.natter"
    projektdatei.write_text(
        json.dumps({
            "format": "natter-project/1",
            "name": "..\\..\\fremd",
            "type": "console",
            "main": "..\\..\\woanders.py",
        }),
        encoding="utf-8",
    )
    return projektdatei, fremd


def test_ein_name_mit_pfad_wird_beim_laden_abgelehnt(tmp_path: Path) -> None:
    from ide.project.projekt import ProjektdateiUngueltig

    projektdatei, _ = _projekt_mit_fremden_pfaden(tmp_path)

    with pytest.raises(ProjektdateiUngueltig, match="Projektname"):
        Projekt.laden(projektdatei)


@pytest.mark.parametrize(
    "feld, wert",
    [
        ("name", "..\\..\\fremd"),
        ("name", "C:\\Windows\\fremd"),
        ("name", "unter/ordner"),
        ("name", ".."),
        ("main", "..\\woanders.py"),
        ("main", "C:\\woanders.py"),
        ("main_form", "..\\u_main"),
    ],
)
def test_das_schema_verlangt_reine_dateinamen(feld: str, wert: str) -> None:
    import json

    import jsonschema

    from ide.pfade import daten_ordner

    schema = json.loads(
        (daten_ordner("schemas") / "project.schema.json").read_text(
            encoding="utf-8"
        )
    )
    gut = {
        "format": "natter-project/1",
        "name": "Mein Spiel 2",
        "type": "gui",
        "main": "main.py",
        "main_form": "u_main",
    }
    jsonschema.validate(gut, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**gut, feld: wert}, schema)


def test_der_export_laesst_die_fremde_exe_unveraendert(
    tmp_path: Path, pyinstaller
) -> None:
    """Auch ein `Projekt`, das nicht über `laden` entstand, schreibt,
    signiert und löscht nichts außerhalb des Zielordners."""
    import json

    projektdatei, fremd = _projekt_mit_fremden_pfaden(tmp_path)
    pyinstaller.einstellung.update(rueckgabe=1, exe_anlegen=False)
    projekt = Projekt(
        ordner=projektdatei.parent,
        daten=json.loads(projektdatei.read_text(encoding="utf-8")),
    )

    ergebnis = exe_exportieren(projekt)

    assert not ergebnis.erfolgreich
    assert "Projektname" in ergebnis.protokoll
    assert pyinstaller == []
    assert fremd.read_bytes() == b"MZ fremd"


def test_der_export_nimmt_keine_startdatei_von_ausserhalb(
    tmp_path: Path, pyinstaller
) -> None:
    projekt = _projekt(tmp_path)
    (tmp_path / "woanders.py").write_text("print(1)\n", encoding="utf-8")
    projekt.daten["main"] = "..\\woanders.py"

    ergebnis = exe_exportieren(projekt)

    assert not ergebnis.erfolgreich
    assert "Startdatei" in ergebnis.protokoll
    assert pyinstaller == []


def test_der_haken_legt_die_daten_neben_die_exe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 488: die Daten lagen nur im Auspackordner, und
    ``open("noten.csv")`` im Ordner der Exe scheiterte. Was neben der
    Exe schon liegt, bleibt; das Programm kann es verändert haben."""
    import sys

    from ide.export.exporter import arbeitsordner_haken

    auspack = tmp_path / "_MEI123"
    (auspack / "bilder").mkdir(parents=True)
    (auspack / "noten.csv").write_text("neu", encoding="utf-8")
    (auspack / "konten.sqlite").write_text("aus dem Export", encoding="utf-8")
    (auspack / "bilder" / "a.png").write_text("bild", encoding="utf-8")
    exe_ordner = tmp_path / "irgendwo"
    exe_ordner.mkdir()
    (exe_ordner / "konten.sqlite").write_text("vom Programm", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(auspack), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_ordner / "Projekt.exe"))

    haken = arbeitsordner_haken(["noten.csv", "konten.sqlite", "bilder"])
    exec(compile(haken, "natter_arbeitsordner.py", "exec"), {})

    assert Path.cwd() == exe_ordner
    assert Path("noten.csv").read_text(encoding="utf-8") == "neu"
    assert Path("bilder/a.png").is_file()
    assert Path("konten.sqlite").read_text(encoding="utf-8") == "vom Programm"


@pytest.mark.parametrize("oberordner", ["normal", "build", "dist", "diagramme"])
def test_ein_ordner_build_ueber_dem_projekt_nimmt_keine_pakete_weg(
    tmp_path: Path, oberordner: str
) -> None:
    """Punkt 573: unter einem Ordner `build` blieben pandas, matplotlib
    und numpy draußen, obwohl das Projekt sie benutzt."""
    from ide.export.exporter import _ueberfluessige_pakete

    ordner = tmp_path / oberordner / "Statistik"
    ordner.mkdir(parents=True)
    (ordner / "u_main.py").write_text(
        "import pandas\nfrom pcl import Chart\n", encoding="utf-8"
    )
    weg = _ueberfluessige_pakete(Projekt(ordner, {}))

    assert not {"pandas", "matplotlib", "numpy"} & set(weg)
