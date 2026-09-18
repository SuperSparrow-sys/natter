"""Tests für ide/assets/symbole.py: SVG-Symbole als QIcon laden. Headless.

Der zweite Teil prüft das Symbolraster aus M11, Abschnitt 1: Rand,
Strichstärken, Farbpalette, das Umfärben fürs dunkle Theme und die
Erkennbarkeit bei 16 px. Die Regeln selbst stehen im Modul-Docstring von
`ide/assets/symbole.py`.
"""

import re
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage

from ide.assets import symbol
from ide.assets.symbole import (
    _ICON_ORDNER,
    FARBEN,
    _umgefaerbt,
    farbkarte,
    theme_ermitteln,
)


def test_bekannte_symbole_laden_ein_gueltiges_icon() -> None:
    for name in ("app", "start", "neu", "oeffnen", "projekt_oeffnen", "speichern"):
        assert not symbol(name).isNull(), name


def test_app_symbol_ist_das_png_maskottchen_nicht_leer() -> None:
    """Nutzer-Feedback (September 2026): eigenes Schlangen-Bild statt
    des bisherigen Vektor-Symbols als Fenster-/Taskleisten-Icon - `.png`
    statt `.svg`, `symbol()` muss deshalb auch `.png` finden."""
    icon = symbol("app")
    assert not icon.isNull()
    assert icon.availableSizes()  # tatsächlich Bilddaten geladen, kein Platzhalter


def test_unbekanntes_symbol_liefert_ein_leeres_icon_statt_fehler() -> None:
    assert symbol("gibt_es_nicht").isNull()


def test_leerer_name_liefert_ein_leeres_icon() -> None:
    assert symbol("").isNull()


def test_rueckgaengig_und_wiederholen_haben_ein_symbol_in_der_werkzeugleiste() -> None:
    """Nutzer-Feedback September 2026: „Ich sehe die Buttons nicht zum
    rückgängig machen“ - beide Aktionen gab es nur im Menü „Bearbeiten“,
    weil ihnen ein `symbol` fehlte (nur Aktionen mit Symbol landen in der
    Werkzeugleiste, siehe `Aktionsregister.an_hauptfenster_anhaengen`)."""
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    werkzeugleisten_aktionen = {
        aktion.text() for aktion in fenster.werkzeugleiste.actions() if not aktion.isSeparator()
    }

    assert {"Rückgängig", "Wiederholen"} <= werkzeugleisten_aktionen
    for name in ("rueckgaengig", "wiederholen"):
        assert not symbol(name).isNull()


# ---------------------------------------------------------------------
# M11, Abschnitt 1: Symbolraster, Theme-Farbe, Erkennbarkeit bei 16 px
# ---------------------------------------------------------------------

#: Erlaubte Strichstärken: Binnenlinie, Kontur, Strich, Marke.
ERLAUBTE_STRICHSTAERKEN = {"1", "1.2", "1.5", "2"}

_HEX_IM_SVG = re.compile(r"#[0-9a-fA-F]{6}")
_STRICHSTAERKE = re.compile(r'stroke-width="([0-9.]+)"')


def _svg_dateien() -> list[Path]:
    dateien = sorted(_ICON_ORDNER.glob("*.svg"))
    assert dateien, "keine Symboldateien gefunden"
    return dateien


def _gerendert(name: str, kante: int, theme: str = "light") -> QImage:
    return symbol(name, theme).pixmap(QSize(kante, kante)).toImage()


def test_palette_hat_je_theme_eindeutige_werte() -> None:
    """Umgefärbt wird über den hellen Hex-Wert. Käme derselbe helle Wert
    zweimal vor, wäre nicht mehr entscheidbar, welcher dunkle gemeint
    ist - eine der beiden Farben würde stillschweigend falsch."""
    helle = [hell for hell, _ in FARBEN.values()]
    assert len(helle) == len(set(helle))
    # Kontur und Papier sind die Farben, die zwingend umschalten müssen.
    assert FARBEN["tinte"][0] != FARBEN["tinte"][1]
    assert FARBEN["papier"][0] != FARBEN["papier"][1]


def test_umfaerben_laeuft_in_einem_durchgang() -> None:
    """Zwei aufeinanderfolgende Ersetzungen dürfen sich nicht gegenseitig
    treffen: mit `a -> b` und `b -> c` darf aus `a` nicht `c` werden."""
    karte = {"#aaaaaa": "#bbbbbb", "#bbbbbb": "#cccccc"}
    assert _umgefaerbt('fill="#aaaaaa"', karte) == 'fill="#bbbbbb"'


def test_jede_symboldatei_nutzt_nur_farben_der_palette() -> None:
    erlaubt = {hell.lower() for hell, _ in FARBEN.values()}
    for datei in _svg_dateien():
        for treffer in _HEX_IM_SVG.findall(datei.read_text(encoding="utf-8")):
            assert treffer.lower() in erlaubt, f"{datei.name}: {treffer} steht nicht in FARBEN"


def test_jede_symboldatei_nutzt_nur_die_vier_strichstaerken() -> None:
    for datei in _svg_dateien():
        for breite in _STRICHSTAERKE.findall(datei.read_text(encoding="utf-8")):
            assert breite in ERLAUBTE_STRICHSTAERKEN, f"{datei.name}: stroke-width={breite}"


def test_jede_symboldatei_haelt_sich_ans_raster() -> None:
    for datei in _svg_dateien():
        text = datei.read_text(encoding="utf-8")
        # tab_schliessen.svg ist der dokumentierte Sonderfall (16x16).
        erwartet = "0 0 16 16" if datei.stem == "tab_schliessen" else "0 0 24 24"
        assert f'viewBox="{erwartet}"' in text, datei.name
        # Eine feste Pixelgröße am <svg> würde die Größe des Aufrufers
        # aushebeln (Werkzeugleiste 18 px, Palette 22 px).
        assert not re.search(r"<svg[^>]*\swidth=", text), datei.name
        # Verläufe und Deckkraft überleben das Herunterrechnen auf 16 px
        # nicht und ließen sich nicht sauber umfärben.
        for verboten in ("Gradient", "opacity", "filter="):
            assert verboten not in text, f"{datei.name}: {verboten}"
        # currentColor löst Qt nicht gegen die Palette auf, siehe
        # test_currentcolor_wirkt_in_qt_nicht.
        assert "currentColor" not in text, datei.name


def test_jedes_symbol_haelt_den_innenabstand_ein() -> None:
    """2 von 24 Einheiten Rand ringsum, halbe Strichbreite eingerechnet.

    Real gefunden (Sichtprüfung September 2026): `neu`, `start_debug` und
    `komponente_shape` ragten um bis zu 0,4 Einheiten darüber hinaus -
    die Marke unten rechts stieß an den Bildrand.
    """
    kante = 192
    rand = kante * 2 // 24
    for datei in _svg_dateien():
        if datei.stem == "tab_schliessen":
            continue  # 16x16-Sonderfall mit eigenem Rand
        bild = _gerendert(datei.stem, kante)
        ueber = []
        for y in range(kante):
            innen_y = rand <= y < kante - rand
            for x in range(kante):
                if innen_y and rand <= x < kante - rand:
                    continue
                if bild.pixelColor(x, y).alpha() > 12:
                    ueber.append((round(x * 24 / kante, 2), round(y * 24 / kante, 2)))
        assert not ueber, f"{datei.name}: {len(ueber)} Pixel im Rand, z. B. {ueber[:3]}"


def test_dunkles_theme_faerbt_die_symbole_wirklich_um() -> None:
    """Der Beweis am gerenderten Bild, nicht an der Theorie: dieselbe
    Datei muss im dunklen Theme andere Pixel liefern.

    `komponente_memo` hat eine große `papier`-Fläche und eine
    `tinte`-Kontur - beide müssen umschalten.
    """

    def farben(theme: str) -> set[str]:
        bild = _gerendert("komponente_memo", 96, theme)
        gefunden = set()
        for y in range(96):
            for x in range(96):
                punkt = bild.pixelColor(x, y)
                if punkt.alpha() == 255:
                    gefunden.add(punkt.name())
        return gefunden

    hell, dunkel = farben("light"), farben("dark")
    assert FARBEN["papier"][0] in hell
    assert FARBEN["tinte"][0] in hell
    assert FARBEN["papier"][0] not in dunkel
    assert FARBEN["tinte"][0] not in dunkel
    assert FARBEN["papier"][1] in dunkel
    assert FARBEN["tinte"][1] in dunkel


def test_farbkarte_ist_im_hellen_theme_die_identitaet() -> None:
    karte = farbkarte("light")
    assert all(schluessel == wert for schluessel, wert in karte.items())
    assert farbkarte("dark")[FARBEN["tinte"][0]] == FARBEN["tinte"][1]


def test_symbole_folgen_der_design_wahl_des_nutzers() -> None:
    """Real gefunden (Bildschirmfoto des Hauptfensters, September 2026):
    das Fenster stand über „Ansicht → Design → Dunkel“ auf Dunkel, die
    Symbole aber blieben hell - `symbol()` fragte nur das Farbschema des
    Betriebssystems ab, nicht die Wahl des Nutzers. Auf einem hell
    eingestellten Schulrechner ergab das dunkle Umrisse auf dunklem
    Grund.
    """
    from PySide6.QtCore import QSettings

    einstellungen = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )
    einstellungen.setValue("design/thema", "dark")
    einstellungen.sync()
    try:
        assert theme_ermitteln("system") == "dark"
        # Und wirklich bis ins gerenderte Bild durch, nicht nur im Namen:
        bild = _gerendert("komponente_memo", 96, "system")
        farben = {
            bild.pixelColor(x, y).name()
            for y in range(96)
            for x in range(96)
            if bild.pixelColor(x, y).alpha() == 255
        }
        assert FARBEN["tinte"][1] in farben
        assert FARBEN["tinte"][0] not in farben
    finally:
        einstellungen.setValue("design/thema", "system")
        einstellungen.sync()


def test_currentcolor_wirkt_in_qt_nicht() -> None:
    """Hält fest, warum `symbol()` den Quelltext umfärbt, statt wie in
    M11 vorgeschlagen `currentColor` zu benutzen: Qt löst `currentColor`
    weder gegen die Palette noch gegen den Painter auf, sondern rendert
    Schwarz. Ändert sich das in einer künftigen Qt-Fassung, schlägt
    dieser Test fehl - dann lohnt es, den Weg neu zu bewerten."""
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    quelle = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<rect width="24" height="24" fill="currentColor"/></svg>'
    )
    bild = QPixmap(24, 24)
    bild.fill(Qt.GlobalColor.transparent)
    maler = QPainter(bild)
    maler.setPen(QColor("#ff0000"))
    maler.setBrush(QColor("#ff0000"))
    QSvgRenderer(QByteArray(quelle.encode("utf-8"))).render(maler)
    maler.end()

    assert bild.toImage().pixelColor(12, 12).name() == "#000000"


def test_jedes_symbol_ist_bei_16_px_noch_erkennbar() -> None:
    """Bei 16 px muss genug Deckung übrig bleiben, sonst verwäscht das
    Symbol zu einem hellen Schleier - dasselbe Problem wie seinerzeit bei
    `app.ico`. Real gefunden: das „A“ von `komponente_label` hatte mit
    Strichstärke 1,5 nur neun deckende Pixel."""
    for datei in _svg_dateien():
        bild = _gerendert(datei.stem, 16)
        deckend = sum(
            1 for y in range(16) for x in range(16) if bild.pixelColor(x, y).alpha() >= 190
        )
        sichtbar = sum(
            1 for y in range(16) for x in range(16) if bild.pixelColor(x, y).alpha() >= 30
        )
        assert deckend >= 14, f"{datei.name}: nur {deckend} deckende Pixel bei 16 px"
        assert sichtbar >= 40, f"{datei.name}: nur {sichtbar} sichtbare Pixel bei 16 px"


def test_rueckgaengig_und_wiederholen_sind_bei_16_px_unterscheidbar() -> None:
    """Die Pfeilspitze muss bei 16 px als **Fläche** auf ihrer Seite
    stehen - daran allein unterscheiden sich die beiden Knöpfe der
    Werkzeugleiste.

    Real gefunden (Sichtprüfung September 2026): als Bogen im Strich mit
    kleiner Spitze blieben auf der Spitzenseite nur zehn deckende Pixel
    gegenüber sieben auf der Gegenseite - beide Symbole sahen bei 16 px
    wie derselbe blasse Ring aus. (Ein bloßer Pixelvergleich der beiden
    Bilder taugt hier nicht: auch die falsche Fassung unterschied sich
    rechnerisch, nur eben nicht sichtbar.)
    """

    def masse(name: str, von: int, bis: int) -> int:
        bild = _gerendert(name, 16)
        return sum(
            1 for y in range(16) for x in range(von, bis) if bild.pixelColor(x, y).alpha() >= 120
        )

    for name, spitze, gegenseite in (
        ("rueckgaengig", (0, 6), (10, 16)),
        ("wiederholen", (10, 16), (0, 6)),
    ):
        auf_spitze = masse(name, *spitze)
        dagegen = masse(name, *gegenseite)
        assert auf_spitze >= 16, f"{name}: nur {auf_spitze} deckende Pixel auf der Spitzenseite"
        assert auf_spitze >= 2 * dagegen, f"{name}: {auf_spitze} gegen {dagegen} - zu wenig"


def test_aufklapppfeil_der_combobox_ist_bei_16_px_zu_sehen() -> None:
    """Real gefunden: als Winkelstrich wurde aus dem Pfeil im blauen
    Knopf bei 16 px ein weißer Fleck. Als Fläche bleibt er stehen."""
    bild = _gerendert("komponente_combobox", 16)
    hell = sum(
        1
        for y in range(16)
        for x in range(10, 16)
        if bild.pixelColor(x, y).alpha() >= 150 and bild.pixelColor(x, y).lightness() > 190
    )
    assert hell >= 3, f"nur {hell} helle Pixel im Aufklappknopf"


def test_haken_der_checkbox_ist_bei_16_px_gruen() -> None:
    """Real gefunden: bei Strichstärke 1,5 war der schräge Haken bei
    16 px kaum noch grün - eine Schräge verteilt sich auf zwei
    Pixelreihen und verliert dabei die halbe Deckung."""
    bild = _gerendert("komponente_checkbox", 16)
    gruen = 0
    for y in range(16):
        for x in range(16):
            punkt = bild.pixelColor(x, y)
            if (
                punkt.alpha() >= 120
                and punkt.green() > punkt.red() + 25
                and punkt.green() > punkt.blue() + 25
            ):
                gruen += 1
    assert gruen >= 14, f"nur {gruen} grüne Pixel im Haken"


# -- Themenwechsel zur Laufzeit ------------------------------------------


def test_werkzeugleiste_faerbt_sich_beim_designwechsel_um(qtbot) -> None:
    """Beim Überarbeiten der Symbole aufgefallen: ein `QIcon` merkt sich
    seine Farben. „Ansicht → Design → Dunkel" tauschte zwar das QSS,
    aber die Werkzeugleiste behielt die hellen Symbole, bis Natter neu
    gestartet wurde."""
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    aktion = fenster.aktionen["datei.neue_unit"].qaction

    hell = aktion.icon().pixmap(32, 32).toImage()
    fenster._design_wechseln("dark")
    dunkel = aktion.icon().pixmap(32, 32).toImage()

    assert hell != dunkel, "das Symbol der Werkzeugleiste blieb unverändert"


def test_palette_faerbt_sich_beim_designwechsel_um(qtbot) -> None:
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    eintrag = fenster.palette.standard_liste.item(0)

    hell = eintrag.icon().pixmap(32, 32).toImage()
    fenster._design_wechseln("dark")
    dunkel = eintrag.icon().pixmap(32, 32).toImage()

    assert hell != dunkel
