"""Das Paket für die Schule ist vollständig.

Die Fassung 0.3.0 wurde von Hand gepackt, und zwei der neun Dateien
fehlten: das Skript zum Prüfen und das zum Zurücknehmen des
Zertifikats. Aufgefallen ist es erst, als jemand danach suchte - einem
ZIP sieht man nicht an, was nicht darin ist. Deshalb steht die Liste
jetzt an einer Stelle im Quelltext, und diese Tests halten sie mit der
Beschreibung in `tools/paket/README.md` zusammen.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools import paket_bauen

WURZEL = Path(__file__).resolve().parent.parent


# --------------------------------------------- Die Liste stimmt


def test_die_liste_und_die_beschreibung_nennen_dieselben_dateien() -> None:
    """Zwei Listen, die auseinanderlaufen können, sind schlimmer als
    eine: die Beschreibung liest jemand, der das Paket weitergibt."""
    beschreibung = (WURZEL / "tools" / "paket" / "README.md").read_text(
        encoding="utf-8"
    )

    genannt = {
        zeile.split("|")[1].strip().strip("`")
        for zeile in beschreibung.splitlines()
        if zeile.startswith("| `")
    }
    aufgelistet = {name for name, _ in paket_bauen._INHALT}
    aufgelistet |= {"Handbuch.md", "Handbuch.html", "Lizenzen\\"}

    assert genannt == aufgelistet


def test_die_skripte_gehoeren_alle_ins_paket() -> None:
    """Eintragen allein genügt nicht: wer Vertrauen vergibt, muss es
    zurücknehmen können, und wer einen Fehler sucht, braucht etwas zum
    Nachsehen."""
    namen = {name for name, _ in paket_bauen._INHALT}

    assert "Zertifikat-eintragen.ps1" in namen
    assert "Zertifikat-entfernen.ps1" in namen
    assert "Natter-pruefen.ps1" in namen


def test_der_private_schluessel_ist_nicht_dabei() -> None:
    """Ins Paket gehört der öffentliche Teil. Wer die `.pfx` hätte,
    könnte im Namen von Natter signieren, auf jedem Rechner, der das
    Zertifikat eingetragen hat."""
    for name, quelle in paket_bauen._INHALT:
        assert not name.endswith(".pfx")
        assert quelle.suffix != ".pfx"


# --------------------------------------------- Das Handbuch


def test_ueberschriften_und_absaetze() -> None:
    html = paket_bauen.handbuch_als_html("# Titel\n\nEin Satz.\n", "T")

    assert "<h1>Titel</h1>" in html
    assert "<p>Ein Satz.</p>" in html


def test_tabellen_bekommen_eine_kopfzeile() -> None:
    quelle = "| Datei | Woher |\n|---|---|\n| `a.txt` | hier |\n"

    html = paket_bauen.handbuch_als_html(quelle, "T")

    assert "<th>Datei</th><th>Woher</th>" in html
    assert "<td><code>a.txt</code></td><td>hier</td>" in html
    assert "---" not in html


def test_codebloecke_bleiben_unveraendert() -> None:
    quelle = "```\nuv run python main.py\n```\n"

    html = paket_bauen.handbuch_als_html(quelle, "T")

    assert "<pre>uv run python main.py</pre>" in html


def test_spitze_klammern_werden_entschaerft() -> None:
    """Sonst verschwindet ein Pfad wie `<Benutzer>` beim Anzeigen."""
    html = paket_bauen.handbuch_als_html("Pfad: C:\\<Benutzer>\\Natter\n", "T")

    assert "&lt;Benutzer&gt;" in html


def test_das_handbuch_laesst_sich_umsetzen() -> None:
    """Gegen die echte Datei und nicht nur gegen Schnipsel: sie ist
    das, was im Paket landet."""
    markdown = (WURZEL / "docs" / "handbuch.md").read_text(encoding="utf-8")

    html = paket_bauen.handbuch_als_html(markdown, "Natter-Handbuch")

    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert "<table>" in html
    assert "<pre>" in html
    # Nichts von der Auszeichnung darf ungewandelt durchrutschen.
    assert "\n| " not in html
    assert "\n## " not in html


# --------------------------------------------- Das ZIP


def test_das_zip_traegt_die_versionsnummer(tmp_path: Path) -> None:
    """Auf einem Stick liegen sonst zwei Fassungen nebeneinander,
    denen man nicht ansieht, welche die neuere ist."""
    ordner = tmp_path / "paket"
    ordner.mkdir()
    (ordner / "ZUERST-LESEN.txt").write_text("egal", encoding="utf-8")

    archiv = paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    assert archiv.name == "Natter-0.3.1-Setup.zip"


def test_das_zip_enthaelt_die_unterordner(tmp_path: Path) -> None:
    ordner = tmp_path / "paket"
    (ordner / "Lizenzen").mkdir(parents=True)
    (ordner / "ZUERST-LESEN.txt").write_text("egal", encoding="utf-8")
    (ordner / "Lizenzen" / "numpy.txt").write_text("egal", encoding="utf-8")

    archiv = paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    with zipfile.ZipFile(archiv) as offen:
        namen = set(offen.namelist())

    assert "ZUERST-LESEN.txt" in namen
    assert "Lizenzen/numpy.txt" in namen


def test_ein_zweiter_lauf_ersetzt_das_alte_zip(tmp_path: Path) -> None:
    """Sonst bliebe ein ZIP mit dem Stand von vorhin liegen und trüge
    trotzdem die neue Nummer im Namen."""
    ordner = tmp_path / "paket"
    ordner.mkdir()
    (ordner / "ZUERST-LESEN.txt").write_text("alt", encoding="utf-8")
    paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    (ordner / "ZUERST-LESEN.txt").write_text("neu", encoding="utf-8")
    archiv = paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    with zipfile.ZipFile(archiv) as offen:
        assert offen.read("ZUERST-LESEN.txt") == b"neu"


def test_fehlende_dateien_brechen_den_bau_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lieber kein Paket als eines, dem etwas fehlt - genau das ist
    bei 0.3.0 passiert."""
    monkeypatch.setattr(
        paket_bauen,
        "_INHALT",
        (("Fehlt.txt", tmp_path / "gibtsnicht.txt"),),
    )

    with pytest.raises(paket_bauen.PaketFehler) as fehler:
        paket_bauen.paket_bauen(version="0.3.1", ziel=tmp_path / "raus")

    assert "gibtsnicht.txt" in str(fehler.value)


def test_die_versionsnummer_wird_eingesetzt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In ZUERST-LESEN.txt stand die Nummer von Hand. Zuletzt hiess es
    dort 0.3.0, waehrend das Ladebild beim Start 0.3.1 zeigte - wer das
    liest, glaubt an die falsche Fassung."""
    quelle = tmp_path / "ZUERST-LESEN.txt"
    quelle.write_text("Natter {VERSION} - Installation", encoding="utf-8")
    monkeypatch.setattr(paket_bauen, "_INHALT", (("ZUERST-LESEN.txt", quelle),))
    monkeypatch.setattr(paket_bauen, "_HANDBUCH", tmp_path / "hand.md")
    (tmp_path / "hand.md").write_text("# Titel", encoding="utf-8")
    monkeypatch.setattr(paket_bauen, "_GEBAUT", tmp_path / "gebaut")
    (tmp_path / "gebaut" / "Lizenzen").mkdir(parents=True)

    ordner = paket_bauen.paket_bauen(version="0.3.1", ziel=tmp_path / "raus")

    gelesen = (ordner / "ZUERST-LESEN.txt").read_text(encoding="utf-8")
    assert gelesen == "Natter 0.3.1 - Installation"


def test_in_der_vorlage_steht_keine_feste_nummer() -> None:
    """Sonst laeuft sie wieder auseinander."""
    text = (WURZEL / "tools" / "paket" / "ZUERST-LESEN.txt").read_text(
        encoding="utf-8"
    )

    assert "{VERSION}" in text
    assert "0.3.0" not in text


def test_zu_jedem_skript_gehoert_ein_starter() -> None:
    """Ein PowerShell-Skript laesst sich auf einem frisch
    aufgesetzten Rechner nicht per Doppelklick starten: die
    Ausfuehrungsrichtlinie steht dort auf `Restricted`, und Dateien
    aus einem entpackten ZIP tragen die Markierung „aus dem Internet".
    Ohne den Starter daneben endet der Rechtsklick in einer roten
    Meldung."""
    namen = {name for name, _ in paket_bauen._INHALT}
    skripte = {name for name in namen if name.endswith(".ps1")}

    fehlend = {s for s in skripte if s[:-4] + ".cmd" not in namen}

    assert not fehlend, f"Ohne Doppelklick-Starter: {sorted(fehlend)}"


def test_die_starter_aendern_nichts_am_rechner() -> None:
    """`-ExecutionPolicy Bypass` gilt nur fuer den einen Aufruf. Ein
    `Set-ExecutionPolicy` waere eine dauerhafte Aenderung an den
    Einstellungen des Rechners - und die gehoert nicht in ein
    Installationspaket."""
    for name, quelle in paket_bauen._INHALT:
        if not name.endswith(".cmd"):
            continue
        text = quelle.read_text(encoding="utf-8")

        assert "-ExecutionPolicy Bypass" in text
        assert "Set-ExecutionPolicy" not in text
        assert "%~dp0" in text, f"{name} findet das Skript nicht neben sich"


def test_zertifikat_eintragen_prueft_den_fingerabdruck_selbst() -> None:
    """Punkt 29: bis 0.3.3 zeigte das Skript den Fingerabdruck nur an
    und trug im selben Zug ein. Jetzt steht der erwartete Wert im
    Skript - derselbe wie in ZUERST-LESEN.txt und wie der der
    mitgelieferten natter-codesign.cer."""
    import hashlib
    import re

    skript = (WURZEL / "tools" / "paket" / "Zertifikat-eintragen.ps1").read_text(
        encoding="utf-8"
    )
    im_skript = re.search(r'\$ERWARTET = "([0-9A-F]{40})"', skript).group(1)

    lies = (WURZEL / "tools" / "paket" / "ZUERST-LESEN.txt").read_text(encoding="utf-8")
    im_text = re.search(r"((?:[0-9A-F]{8} ){4}[0-9A-F]{8})", lies).group(1).replace(" ", "")

    cer = (WURZEL / "tools" / "signieren" / "natter-codesign.cer").read_bytes()
    if cer.startswith(b"-----BEGIN"):
        import base64

        cer = base64.b64decode(b"".join(cer.splitlines()[1:-1]))
    echt = hashlib.sha1(cer).hexdigest().upper()

    assert im_skript == im_text == echt
    # Geprüft wird vor dem Eintragen, nicht danach
    assert skript.index("$ERWARTET") < skript.index("Import-Certificate")


def test_natter_pruefen_sucht_die_installation_ueber_windows() -> None:
    """Punkt 31: der Ort kommt aus dem Deinstallationseintrag, und
    „nicht installiert“ und „unvollständig“ sind zwei Meldungen."""
    skript = (WURZEL / "tools" / "paket" / "Natter-pruefen.ps1").read_text(encoding="utf-8")

    assert "InstallLocation" in skript
    assert '"HKLM:", "HKCU:"' in skript
    assert "nicht installiert" in skript
    assert skript.index("nicht installiert") < skript.index("unvollstaendig - python")


def test_natter_pruefen_startet_python_wie_der_starter() -> None:
    """Punkt 337: der Prüflauf startet isoliert (`-I`) und ohne die
    Variablen, die `tools/launcher.py` aus der Umgebung nimmt. Sonst
    meldete der Bericht Fehler, die `Natter.exe` nicht hat."""
    from tools import launcher

    skript = (
        WURZEL / "tools" / "paket" / "Natter-pruefen.ps1"
    ).read_text(encoding="utf-8")

    assert "& $python -I $tmp" in skript
    assert '$_.Name -like "PYTHON*"' in skript
    for name in (*launcher.QT_NACHLADEN, *launcher.FREMDE_UMGEBUNG):
        assert name.startswith("PYTHON") or f'"{name}"' in skript, name
    assert '$env:PYTHONNOUSERSITE = "1"' in skript


# ------------------------------- Die Anleitung für die IT (Punkte 315 ff.)

HANDBUCH = WURZEL / "docs" / "handbuch.md"
LIES = WURZEL / "tools" / "paket" / "ZUERST-LESEN.txt"


def _abschnitt(text: str, anfang: str, ende: str) -> str:
    return text[text.index(anfang):text.index(ende, text.index(anfang))]


def _beide() -> list[str]:
    return [
        HANDBUCH.read_text(encoding="utf-8"),
        LIES.read_text(encoding="utf-8"),
    ]


def test_die_anleitung_nennt_die_installation_fuer_alle_benutzer() -> None:
    """Punkte 315 und 317: der Aufruf für viele Rechner ohne /ALLUSERS
    installierte nur für das Konto, unter dem er lief. Dazu gehören in
    beiden Dateien die beiden Installationsarten mit Ort, Rechten und
    der Folge für „Pakete“, die stille Deinstallation für beide und
    /MERGETASKS."""
    for text in _beide():
        assert "/ALLUSERS /VERYSILENT" in text
        assert "C:\\Program Files\\Natter" in text
        assert "%LOCALAPPDATA%\\Programs\\Natter" in text
        assert "Administratorrechte" in text
        assert "Paket installieren" in text
        assert "Systemkonto" in text
        assert '/MERGETASKS="!desktopicon"' in text
        assert "C:\\Program Files\\Natter\\unins000.exe" in text
        assert "Programs\\Natter\\unins000.exe" in text
        assert "%APPDATA%\\Natter" in text

    handbuch = HANDBUCH.read_text(encoding="utf-8")
    tabelle = _abschnitt(handbuch, "| Frage im Installer |", "\n\n")
    assert "Installationsart wählen" in tabelle
    ablage = _abschnitt(handbuch, "## 2. Wo die Dateien liegen", "\n\n**")
    for ort in ("C:\\Program Files\\Natter", "%APPDATA%\\Natter",
                "%LOCALAPPDATA%\\Natter`"):
        assert ort in ablage, ort


def test_die_anleitung_nennt_applocker_und_die_gestarteten_programme() -> None:
    """Punkt 316: unter den Standardregeln von AppLocker startet eine
    Installation im Profil nicht. Die Liste der Programme muss zu dem
    passen, was der Code tatsächlich startet."""
    from tools import launcher

    im_code = {
        "Natter.exe": (WURZEL / "tools" / "natter.iss", "Natter.exe"),
        f"{launcher.PYTHON_ORDNER}\\{launcher.STARTER}":
            (WURZEL / "tools" / "launcher.py", "pythonw.exe"),
        "python\\python.exe":
            (WURZEL / "ide" / "run" / "interpreter.py", '"python.exe"'),
        "python\\Scripts\\ruff.exe":
            (WURZEL / "ide" / "run" / "interpreter.py", "find_ruff_bin"),
        "powershell.exe":
            (WURZEL / "ide" / "export" / "signatur.py", '"powershell"'),
        "taskkill.exe": (WURZEL / "ide" / "prozess.py", '"taskkill"'),
    }
    for programm, (quelle, merkmal) in im_code.items():
        assert merkmal in quelle.read_text(encoding="utf-8-sig"), programm

    for text in _beide():
        assert "AppLocker" in text
        for programm in (*im_code, "unins000.exe"):
            assert programm in text, programm
        assert "dist" in _abschnitt(text, "AppLocker", "Was Natter")


def test_die_anleitung_nennt_zertifikat_und_reste_nach_dem_entfernen() -> None:
    """Punkte 318 und 324: das Zertifikat des Exe-Exports, die
    Rückfrage von Windows dazu und was nach dem Deinstallieren im
    Konto bleibt."""
    handbuch = HANDBUCH.read_text(encoding="utf-8")
    entfernen = _abschnitt(handbuch, "### 1.5 Entfernen", "## 2. Wo")
    weitergeben = _abschnitt(handbuch, "### 3.5", "### 3.6")

    for stelle in ("%APPDATA%\\Natter", "%LOCALAPPDATA%\\Natter",
                   "Software\\Natter\\Pruefungsmodus",
                   "Natter Programme dieses Rechners",
                   "-Exportzertifikate"):
        assert stelle in entfernen, stelle
    for text in (weitergeben, LIES.read_text(encoding="utf-8")):
        assert "Natter Programme dieses Rechners" in text
        assert "Sicherheitswarnung" in text
        assert "zertifikat_abgelehnt.txt" in text
        assert "jeder Anmeldung" in text


def test_die_anleitung_beschreibt_den_umstieg_auf_alle_benutzer() -> None:
    """Punkt 358: eine alte Installation im Konto bleibt nach /ALLUSERS
    stehen und hat dort Vorrang. Beide Anleitungen sagen, wie sie in
    jedem Konto still verschwindet, und Natter-pruefen nennt beide
    Installationen und prüft die neuere."""
    umstieg = "nstallationen je Konto auf eine f"
    for text in _beide():
        abschnitt = _abschnitt(text, umstieg, "\n\n#" if "## " in text else "\n\n\n")
        assert "Anmeldeskript" in abschnitt
        assert (
            '"%LOCALAPPDATA%\\Programs\\Natter\\unins000.exe" /VERYSILENT'
            in abschnitt
        )
        assert "Natter-pruefen.cmd" in abschnitt

    skript = (WURZEL / "tools" / "paket" / "Natter-pruefen.ps1").read_text(
        encoding="utf-8"
    )
    assert "Zwei Installationen gefunden" in skript
    assert "-gt (Fassung $eintrag)" in skript


def test_die_anleitung_nennt_die_erkennungsregel() -> None:
    """Punkt 359: für eine Softwareverteilung stand nirgends, woran sie
    eine installierte Fassung erkennt. Der Schlüssel muss derselbe sein
    wie im Setup."""
    iss = (WURZEL / "tools" / "natter.iss").read_text(encoding="utf-8-sig")
    schluessel = (
        "Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
        "{961DA420-CA63-4436-9023-9CA411B620DA}_is1"
    )
    assert schluessel in iss
    for text in _beide():
        assert "HKEY_LOCAL_MACHINE\\SOFTWARE\\" + schluessel in text
        assert "DisplayVersion" in text
        assert "Dateiversion" in text
        assert "C:\\Program Files\\Natter\\Natter.exe" in text


def test_das_readme_nennt_die_installation_fuer_alle_benutzer() -> None:
    """Punkt 360: das README nannte die Installation je Konto den Weg,
    „der immer funktioniert“, obwohl sie unter AppLocker nicht startet,
    und kannte /ALLUSERS nicht. Handbuch 1.1 wiederholte die
    Empfehlung für eingeschränkte Konten."""
    readme = (WURZEL / "README.md").read_text(encoding="utf-8")
    installation = _abschnitt(readme, "## Installation", "\n## ")

    # Der alte Satz war über zwei Zeilen umbrochen.
    assert "immer funktioniert" not in " ".join(installation.split())
    assert "/ALLUSERS /VERYSILENT" in installation
    assert "AppLocker" in installation
    assert "docs/handbuch.md#14-" in installation
    assert "ZUERST-LESEN.txt" in installation

    handbuch = HANDBUCH.read_text(encoding="utf-8")
    einzeln = _abschnitt(handbuch, "### 1.1 ", "### 1.2 ")
    assert "AppLocker" in einzeln
    assert "Abschnitt 1.4" in einzeln
    assert "### 1.4 Auf vielen Rechnern gleichzeitig" in handbuch


def test_die_anleitung_nennt_die_grenze_des_pruefungsmodus() -> None:
    """Punkt 319: der Modus steht nur im Profil. Mit Wächterkarte oder
    zurückgesetzten Profilen endet er beim Abmelden, und
    eingeschaltet wird er in jedem Konto einzeln."""
    handbuch = HANDBUCH.read_text(encoding="utf-8")
    pruefung = _abschnitt(handbuch, "## 4. Der Prüfungsmodus", "## 5.")
    lies = _abschnitt(LIES.read_text(encoding="utf-8"),
                      "Pruefungsmodus und zurueckgesetzte Profile", "Mehr dazu")

    assert "Wächterkarte" in pruefung and "zurückgesetzt" in pruefung
    assert "in jedem Konto einzeln" in pruefung
    assert "rote Anzeige" in pruefung and "erneut" in pruefung
    assert "Waechterkarte" in lies and "in jedem Konto einzeln" in lies
