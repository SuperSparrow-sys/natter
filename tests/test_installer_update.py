"""Update-Verhalten des Installers (Punkte 26, 28, 30).

Den Installer selbst baut der Auslieferungsbau; hier wird geprüft, was
sich ohne Bau prüfen lässt: das Hilfsskript für nachinstallierte
Pakete, die Einstellungen in tools/natter.iss und dass die
unpersönlichen Texte jede Anrede aus German.isl abdecken.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from ide.integritaet.manifest import STARTER_ORDNER
from tools.installer_pakete_merken import nachinstallierte

WURZEL = Path(__file__).resolve().parent.parent
ISS = WURZEL / "tools" / "natter.iss"
TEXTE = WURZEL / "tools" / "installer_texte.isl"
GERMAN_ISL = Path(r"C:\Program Files (x86)\Inno Setup 6\Languages\German.isl")


def _paket(site: Path, name: str) -> None:
    info = site / f"{name}-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n", encoding="utf-8"
    )


@pytest.fixture
def alte_python(tmp_path: Path) -> Path:
    python = tmp_path / "python"
    site = python / "Lib" / "site-packages"
    for name in ("numpy", "PySide6_Essentials", "natter", "pip", "cowsay", "Requests"):
        _paket(site, name)
    (python / "requirements-auslieferung.txt").write_text(
        "# erzeugt von uv\n"
        "numpy==2.5.3 \\\n    --hash=sha256:abc\n"
        "pyside6-essentials==6.11.2 ; sys_platform == 'win32'\n",
        encoding="utf-8",
    )
    return python


def test_nachinstallierte_pakete_werden_erkannt(alte_python: Path) -> None:
    assert nachinstallierte(alte_python) == ["cowsay", "Requests"]


def test_ohne_liste_der_mitgelieferten_wird_nichts_geraten(alte_python: Path) -> None:
    (alte_python / "requirements-auslieferung.txt").unlink()

    assert nachinstallierte(alte_python) is None


def test_das_skript_schreibt_die_liste(alte_python: Path, tmp_path: Path) -> None:
    ziel = tmp_path / "appdata" / "pakete_vor_update.txt"
    skript = WURZEL / "tools" / "installer_pakete_merken.py"

    subprocess.run([sys.executable, str(skript), str(ziel), str(alte_python)],
                   check=True, timeout=60)

    assert ziel.read_text(encoding="utf-8").split() == ["cowsay", "Requests"]


@pytest.mark.parametrize("ordner", ["python", STARTER_ORDNER])
def test_das_setup_ersetzt_die_mitgelieferte_python_vollstaendig(
    ordner: str,
) -> None:
    """Punkt 28: nur Natters eigene Ordner zu leeren, ließ die
    Qt-Module unter GPL und eine alte natter-dist-info liegen. Seit
    Punkt 399 bringt auch der Starter eine Python in seinem eigenen
    Ordner mit; alte DLLs darin meldete die Prüfung beim Start als
    fremde Dateien."""
    text = ISS.read_text(encoding="utf-8-sig")
    abschnitt = text.split("[InstallDelete]")[1].split("\n[")[0]

    assert re.search(
        rf'Type: filesandordirs; Name: "\{{app\}}\\{ordner}"\s*$',
        abschnitt,
        re.M,
    )


def test_das_setup_erkennt_ein_update() -> None:
    """Punkt 26: vorhandene Fassung nennen, Ordnerseiten überspringen,
    Pakete merken und wieder installieren, keine ältere über eine
    neuere."""
    text = ISS.read_text(encoding="utf-8-sig")

    assert "DisableDirPage=auto" in text
    assert "DisableProgramGroupPage=auto" in text
    assert "CloseApplications=yes" in text
    assert "installer_pakete_merken.py" in text
    assert "DisplayVersion" in text
    assert "wird auf" in text and "aktualisiert" in text


def test_unter_dem_systemkonto_ohne_allusers_bricht_das_setup_ab() -> None:
    """Punkt 315: eine Softwareverteilung ohne /ALLUSERS installierte
    Natter ins Profil des Systemkontos und meldete Erfolg. Jetzt
    bricht InitializeSetup dort ab, mit Protokollzeile und
    Rückgabewert ungleich 0, bevor irgendetwas kopiert wird."""
    text = ISS.read_text(encoding="utf-8-sig")
    code = text.split("\n[Code]")[1]
    start = code.split("function InitializeSetup(): Boolean;")[1]
    start = start.split("\nend;")[0]

    assert "PrivilegesRequired=lowest" in text
    assert "SYSTEMPROFILE" in code and "GetUserNameString" in code
    pruefung = start.index("LaeuftAlsDienstkonto() and not IsAdminInstallMode()")
    abbruch = start.index("Result := False;", pruefung)
    assert start.index("Melden(", pruefung) < abbruch
    assert start.index("Exit;", abbruch) < start.index("AlteFassung :=")


def _pascal_block(code: str, kopf: str) -> str:
    """Der Rumpf einer Funktion oder Prozedur aus [Code], bis zum
    `end;` am Zeilenanfang."""
    return code.split(kopf, 1)[1].split("\nend;", 1)[0]


def test_ohne_zuschauer_zeigt_das_setup_keine_meldung() -> None:
    """Punkt 357: `SuppressibleMsgBox` zeigt ohne /SUPPRESSMSGBOXES
    auch bei /VERYSILENT eine Meldung. Unter dem Systemkonto in
    Sitzung 0 bestätigt sie niemand, und das Setup wartete bis zur
    Zeitgrenze der Softwareverteilung. Alle Meldungen laufen deshalb
    über `Melden`, das unter einem Dienstkonto und bei einer stillen
    Installation nur ins Protokoll schreibt."""
    text = ISS.read_text(encoding="utf-8-sig")
    code = text.split("\n[Code]")[1]

    # Genau ein Aufruf einer Meldung, und der steht in Melden.
    assert len(re.findall(r"\b(Suppressible)?MsgBox\(", code)) == 1
    zuschauer = _pascal_block(code, "function NiemandSiehtZu(): Boolean;")
    assert "WizardSilent()" in zuschauer
    assert "LaeuftAlsDienstkonto()" in zuschauer
    melden = _pascal_block(code, "procedure Melden(")
    assert melden.index("Log(Text)") < melden.index("if not NiemandSiehtZu() then")
    assert melden.index("if not NiemandSiehtZu() then") < melden.index("SuppressibleMsgBox(")

    # Die drei Fälle aus dem Befund: Systemkonto ohne /ALLUSERS,
    # ältere über neuere Fassung und Pakete nach dem Update.
    start = _pascal_block(code, "function InitializeSetup(): Boolean;")
    schritt = _pascal_block(code, "procedure CurStepChanged(")
    assert len(re.findall(r"\bMelden\(", start)) == 2
    assert len(re.findall(r"\bMelden\(", schritt)) == 1

    # Pascal kennt nur, was weiter oben steht.
    reihenfolge = [
        "function LaeuftAlsDienstkonto()",
        "function NiemandSiehtZu()",
        "procedure Melden(",
        "procedure ZweiteInstallationMelden()",
        "function InitializeSetup()",
        "procedure CurStepChanged(",
    ]
    stellen = [code.index(kopf) for kopf in reihenfolge]
    assert stellen == sorted(stellen)


def test_das_setup_liest_die_fassung_seiner_eigenen_installationsart() -> None:
    """Punkt 358: bei /ALLUSERS las das Setup zuerst HKCU und hielt eine
    alte Installation im eigenen Konto für die zu ersetzende. Jetzt
    zählt für ein Update nur die Installationsart des Setups, und die
    jeweils andere wird gemeldet."""
    code = ISS.read_text(encoding="utf-8-sig").split("\n[Code]")[1]
    fassung = _pascal_block(code, "function InstallierteFassung(): String;")
    zweite = _pascal_block(code, "procedure ZweiteInstallationMelden();")

    assert "IsAdminInstallMode()" in fassung
    assert fassung.index("FassungUnter(HKLM)") < fassung.index("else")
    assert fassung.index("else") < fassung.index("FassungUnter(HKCU)")
    assert "FassungUnter(HKCU)" in zweite and "FassungUnter(HKLM)" in zweite
    assert "unins000.exe" in zweite
    start = _pascal_block(code, "function InitializeSetup(): Boolean;")
    assert "ZweiteInstallationMelden();" in start


def test_nur_deutsch_ohne_sprachauswahl() -> None:
    """Punkt 30: Natter ist deutsch; die Frage nach der Setup-Sprache
    entfällt."""
    text = ISS.read_text(encoding="utf-8-sig")
    sprachen = text.split("[Languages]")[1].split("\n[")[0]
    eintraege = [z for z in sprachen.splitlines() if z.startswith("Name:")]

    assert len(eintraege) == 1
    assert "installer_texte.isl" in eintraege[0]


@pytest.mark.skipif(not GERMAN_ISL.exists(), reason="Inno Setup nicht installiert")
def test_jede_anrede_aus_german_isl_ist_ueberschrieben() -> None:
    """Punkt 30: 64 Meldungen in German.isl sprechen mit „Sie“ oder
    „Ihr“ an. Jede davon braucht eine Fassung in installer_texte.isl,
    und die darf selbst niemanden ansprechen."""
    anrede = re.compile(r"\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b")

    def meldungen(pfad: Path) -> dict[str, str]:
        ergebnis = {}
        for zeile in pfad.read_text(encoding="utf-8-sig").splitlines():
            if "=" in zeile and not zeile.startswith((";", "[")):
                name, wert = zeile.split("=", 1)
                ergebnis[name.strip()] = wert
        return ergebnis

    original = meldungen(GERMAN_ISL)
    eigene = meldungen(TEXTE)
    mit_anrede = {n for n, w in original.items() if anrede.search(w)}

    assert mit_anrede, "German.isl nicht gelesen"
    assert sorted(mit_anrede - set(eigene)) == []
    assert {n: w for n, w in eigene.items() if anrede.search(w)} == {}


def test_uninstaller_raeumt_registry_reste_aelterer_fassungen() -> None:
    """Bis 0.3.3 standen die Ansichtsschalter des Diagramm-Editors in
    der Registry und blieben nach dem Deinstallieren stehen (Punkt 45
    der offenen Punkte). Angelegt wird dort nichts mehr."""
    zeilen = ISS.read_text(encoding="utf-8-sig").splitlines()
    registry = [z for z in zeilen if z.startswith('Root: HKCU; Subkey: "Software\\Natter')]

    assert any(
        'Natter\\Diagramm"' in z and "uninsdeletekey dontcreatekey" in z
        for z in registry
    )
    assert all("dontcreatekey" in z for z in registry)
    assert not any("ValueType" in z for z in registry)


def _german_isl() -> Path | None:
    import os

    for basis in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("LOCALAPPDATA", "")):
        for unter in ("Inno Setup 6", r"Programs\Inno Setup 6"):
            pfad = Path(basis) / unter / "Languages" / "German.isl"
            if basis and pfad.is_file():
                return pfad
    return None


def _abschnitt(text: str, name: str) -> dict[str, str]:
    werte: dict[str, str] = {}
    drin = False
    for zeile in text.splitlines():
        if zeile.startswith("["):
            drin = zeile.strip() == f"[{name}]"
        elif drin and "=" in zeile and not zeile.startswith(";"):
            schluessel, _, wert = zeile.partition("=")
            werte[schluessel.strip()] = wert.strip()
    return werte


def test_benutzte_custom_messages_sind_unpersoenlich() -> None:
    """Punkt 49: „Registriere Natter mit der .natter-Dateierweiterung“
    stand auf der Aufgabenseite. Der Text kommt aus `[CustomMessages]`
    von German.isl; installer_texte.isl überschrieb nur `[Messages]`."""
    import re

    benutzt = sorted(set(re.findall(r"\{cm:([A-Za-z]+)", ISS.read_text(encoding="utf-8-sig"))))
    eigene = _abschnitt((ISS.parent / "installer_texte.isl").read_text(encoding="utf-8-sig"),
                        "CustomMessages")
    german = _german_isl()
    fremd = _abschnitt(german.read_text(encoding="cp1252"), "CustomMessages") if german else {}
    befehlsformen = ("Registriere", "Erstelle", "Starte", "Entferne", "Wähle", "Klicke", "Öffne")

    assert "AssocFileExtension" in eigene
    for name in benutzt:
        text = eigene.get(name) or fremd.get(name)
        if text is None:
            continue
        erstes = text.replace("&", "").split()[0]
        assert erstes not in befehlsformen, f"{name}: {text}"
        assert not re.search(r"\b(Sie|Ihr|Ihre|du|dein)\b", text), f"{name}: {text}"


def test_die_letzte_seite_kuendigt_den_langen_ersten_start_an() -> None:
    """Punkt 48: der erste Start nach der Installation braucht 13 bis
    18 Sekunden, weil der Virenschutz jede neue Datei beim ersten
    Öffnen prüft; die ersten 8 davon ohne Ladebild. Gesagt wird das
    dort, wo „Natter starten“ angeboten wird."""
    meldungen = _abschnitt(TEXTE.read_text(encoding="utf-8-sig"), "Messages")

    for name in ("FinishedLabel", "FinishedLabelNoIcons"):
        assert "erste Start" in meldungen[name], name
        assert "Virenschutz" in meldungen[name], name
