"""Tests für den Design-Prüfer (Abschnitt 14). Siehe
Arbeitspaket M7, Schritt 1. Reine Logik gegen den geparsten
`.pfm`-Inhalt, kein Qt nötig. Je Regel ein absichtlich fehlerhaftes
Beispiel und ein sauberes Gegenbeispiel.
"""

from __future__ import annotations

import pytest

from ide.lint.regeln import lesereihenfolge, pruefen


def _pfm(kinder: list[dict], *, breite: int = 400, hoehe: int = 300, farbe: str = "") -> dict:
    form = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"caption": "Form1", "width": breite, "height": hoehe, "theme": "system"},
        "children": kinder,
    }
    if farbe:
        form["properties"]["color"] = farbe
    return form


def _komponente(
    name: str, typ: str, *, left: int = 8, top: int = 8, width: int = 75, height: int = 25, **rest
) -> dict:
    eigenschaften = {"left": left, "top": top, "width": width, "height": height, **rest}
    return {"name": name, "type": typ, "properties": eigenschaften}


def _regeln(pfm: dict) -> set[str]:
    return {befund.regel for befund in pruefen(pfm)}


def test_geometrie_komponente_ausserhalb_des_formulars() -> None:
    ausserhalb = _pfm([_komponente("b_x", "Button", left=380, top=8, width=75, height=24)])
    innerhalb = _pfm([_komponente("b_x", "Button", left=100, top=8, width=75, height=24)])

    assert "geometrie.ausserhalb_formular" in _regeln(ausserhalb)
    assert "geometrie.ausserhalb_formular" not in _regeln(innerhalb)


def test_krumme_koordinaten_sind_kein_befund() -> None:
    """Die Regel „steht nicht am 8px-Raster" gab es bis dahin
 und ist auf Wunsch entfallen.

 Sie meldete etwas ohne sichtbare Folge und traf dabei ausgerechnet
 die mitgelieferten Beispiele: 35 von 76 Komponenten dort stehen
 zwischen den Rasterpunkten, weil ihre Layouts von Hand gesetzt
 sind. Mechanisch aufs Raster zu rücken machte sie nachweislich
 schlechter - im Versuch entstanden dadurch vier neue
 Überlappungen im Cookie-Klicker. Was wirklich schief aussieht,
 melden `uneinheitliche_abstaende` und `kante_nicht_buendig`.

 Neu abgelegte Komponenten rasten seither beim Ablegen selbst ein
 (`ide.designer.canvas`), also dort, wo es nichts kostet.
 """
    schief = _pfm([_komponente("b_x", "Button", left=5, top=3)])

    assert _regeln(schief) == set()


def test_geometrie_ueberlappung() -> None:
    ueberlappend = _pfm(
        [
            _komponente("b_a", "Button", left=8, top=8, width=100, height=24),
            _komponente("b_b", "Button", left=50, top=16, width=100, height=24),
        ]
    )
    getrennt = _pfm(
        [
            _komponente("b_a", "Button", left=8, top=8, width=100, height=24),
            _komponente("b_b", "Button", left=200, top=8, width=100, height=24),
        ]
    )

    assert "geometrie.ueberlappung" in _regeln(ueberlappend)
    assert "geometrie.ueberlappung" not in _regeln(getrennt)


def test_geometrie_kante_nicht_buendig() -> None:
    fast_buendig = _pfm(
        [
            _komponente("l_a", "Label", left=8, top=8, width=50, height=20),
            _komponente("l_b", "Label", left=11, top=40, width=50, height=20),
        ]
    )
    exakt_buendig = _pfm(
        [
            _komponente("l_a", "Label", left=8, top=8, width=50, height=20),
            _komponente("l_b", "Label", left=8, top=40, width=50, height=20),
        ]
    )

    assert "geometrie.kante_nicht_buendig" in _regeln(fast_buendig)
    assert "geometrie.kante_nicht_buendig" not in _regeln(exakt_buendig)


def test_geometrie_uneinheitliche_abstaende() -> None:
    ungleichmaessig = _pfm(
        [
            _komponente("b_a", "Button", left=8, top=8, width=40, height=24),
            _komponente("b_b", "Button", left=56, top=8, width=40, height=24),
            _komponente("b_c", "Button", left=200, top=8, width=40, height=24),
        ]
    )
    gleichmaessig = _pfm(
        [
            _komponente("b_a", "Button", left=8, top=8, width=40, height=24),
            _komponente("b_b", "Button", left=56, top=8, width=40, height=24),
            _komponente("b_c", "Button", left=104, top=8, width=40, height=24),
        ]
    )

    assert "geometrie.uneinheitliche_abstaende" in _regeln(ungleichmaessig)
    assert "geometrie.uneinheitliche_abstaende" not in _regeln(gleichmaessig)


def test_lesbarkeit_kontrast() -> None:
    # Ein fester Hintergrund kann rechnerisch nie in beiden Themes
    # gleichzeitig genug Kontrast zur (je nach Theme unterschiedlichen)
    # Textfarbe haben - "gut" heißt hier deshalb: gar keine feste Farbe
    # setzen und dem Theme die Textfarbe überlassen.
    schlecht = _pfm([], farbe="#202020")
    gut = _pfm([])

    assert "lesbarkeit.kontrast" in _regeln(schlecht)
    assert "lesbarkeit.kontrast" not in _regeln(gut)


def test_konsistenz_button_groesse() -> None:
    uneinheitlich = _pfm(
        [
            _komponente("b_a", "Button", left=8, top=8, width=75, height=24),
            _komponente("b_b", "Button", left=8, top=40, width=75, height=24),
            _komponente("b_c", "Button", left=8, top=72, width=120, height=32),
        ]
    )
    einheitlich = _pfm(
        [
            _komponente("b_a", "Button", left=8, top=8, width=75, height=24),
            _komponente("b_b", "Button", left=8, top=40, width=75, height=24),
        ]
    )

    assert "konsistenz.button_groesse" in _regeln(uneinheitlich)
    assert "konsistenz.button_groesse" not in _regeln(einheitlich)


def test_konsistenz_label_ausrichtung() -> None:
    versetzt = _pfm(
        [
            _komponente("l_name", "Label", left=8, top=10, width=60, height=20),
            _komponente("e_name", "Edit", left=80, top=50, width=100, height=24),
        ]
    )
    ausgerichtet = _pfm(
        [
            _komponente("l_name", "Label", left=8, top=10, width=60, height=20),
            _komponente("e_name", "Edit", left=80, top=10, width=100, height=24),
        ]
    )

    assert "konsistenz.label_ausrichtung" in _regeln(versetzt)
    assert "konsistenz.label_ausrichtung" not in _regeln(ausgerichtet)


def test_bedienbarkeit_zu_kleine_klickflaeche() -> None:
    klein = _pfm([_komponente("b_x", "Button", left=8, top=8, width=16, height=16)])
    gross_genug = _pfm([_komponente("b_x", "Button", left=8, top=8, width=32, height=32)])

    assert "bedienbarkeit.klickflaeche" in _regeln(klein)
    assert "bedienbarkeit.klickflaeche" not in _regeln(gross_genug)


def test_bedienbarkeit_eingabefeld_ohne_beschriftung() -> None:
    ohne_label = _pfm([_komponente("e_name", "Edit", left=8, top=8, width=100, height=24)])
    mit_label = _pfm(
        [
            _komponente("l_name", "Label", left=8, top=10, width=60, height=20),
            _komponente("e_name", "Edit", left=80, top=8, width=100, height=24),
        ]
    )

    assert "bedienbarkeit.ohne_beschriftung" in _regeln(ohne_label)
    assert "bedienbarkeit.ohne_beschriftung" not in _regeln(mit_label)


def test_bedienbarkeit_tab_reihenfolge() -> None:
    durcheinander = _pfm(
        [
            _komponente("b_unten", "Button", left=8, top=200, width=75, height=24),
            _komponente("b_oben", "Button", left=8, top=8, width=75, height=24),
        ]
    )
    logisch = _pfm(
        [
            _komponente("b_oben", "Button", left=8, top=8, width=75, height=24),
            _komponente("b_unten", "Button", left=8, top=200, width=75, height=24),
        ]
    )

    assert "bedienbarkeit.tab_reihenfolge" in _regeln(durcheinander)
    assert "bedienbarkeit.tab_reihenfolge" not in _regeln(logisch)


def test_namenskonvention_fehlendes_praefix() -> None:
    falsch = _pfm([_komponente("knopf1", "Button", caption="Start")])
    richtig = _pfm([_komponente("b_start", "Button", caption="Start")])

    assert "namenskonvention.praefix" in _regeln(falsch)
    assert "namenskonvention.praefix" not in _regeln(richtig)


def test_namenskonvention_standardname() -> None:
    standard = _pfm([_komponente("button1", "Button", caption="Start")])
    eigener_name = _pfm([_komponente("b_start", "Button", caption="Start")])

    assert "namenskonvention.standardname" in _regeln(standard)
    assert "namenskonvention.standardname" not in _regeln(eigener_name)


def test_namenskonvention_standardtext() -> None:
    standard = _pfm([_komponente("b_start", "Button", caption="Button1")])
    eigener_text = _pfm([_komponente("b_start", "Button", caption="Start")])

    assert "namenskonvention.standardtext" in _regeln(standard)
    assert "namenskonvention.standardtext" not in _regeln(eigener_text)


def test_abgeschaltete_regeln_werden_uebersprungen() -> None:
    pfm = _pfm([_komponente("knopf1", "Button", caption="Start")])

    befunde = pruefen(pfm, abgeschaltete_regeln={"namenskonvention.praefix"})

    regeln = {b.regel for b in befunde}
    assert "namenskonvention.praefix" not in regeln


def test_fehlende_width_height_defaulten_wie_pcl_control_statt_auf_null() -> None:
    # Die .pfm speichert nur vom Standardwert abweichende Eigenschaften
    # (Abschnitt 4.2) - ein Kind an der Standardgröße hat also gar
    # keinen "width"/"height"-Schlüssel. Ohne die Control-Standardwerte
    # (75x25) würde die Geometrie fälschlich als 0x0 gelesen und keine
    # der Geometrie-Regeln würde je etwas an dieser Komponente finden.
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"caption": "Form1", "width": 50, "height": 50},
        "children": [{"name": "b_x", "type": "Button", "properties": {"left": 0, "top": 0}}],
    }

    assert "geometrie.ausserhalb_formular" in _regeln(pfm)


def test_befunde_sind_nie_fehler() -> None:
    pfm = _pfm([_komponente("knopf1", "Button", left=5, top=5, width=16, height=16)])

    befunde = pruefen(pfm)

    assert all(b.schweregrad in ("hinweis", "warnung") for b in befunde)


def test_button_mit_standardgroesse_wird_nicht_als_abweichend_gemeldet() -> None:
    """In der Sichtprüfung des Panels „Meldungen“ gefunden: die Regel
    las `width`/`height` mit der Vorbelegung 0 statt mit der echten
    Standardgröße. Ein Button, an dem niemand etwas geändert hatte,
    erschien deshalb als „hat eine andere Größe (0×0)“ – und schickte
    den Schüler an eine Stelle, an der nichts falsch war.
    """
    pfm = {
        "name": "Form1",
        "type": "Form",
        "properties": {"width": 400, "height": 300},
        # Alle drei gleich groß, aber nur der letzte trägt die Größe
        # ausgeschrieben: eine .pfm speichert nur Eigenschaften, die vom
        # Standardwert abweichen (Abschnitt 4.2).
        "children": [
            {"type": "Button", "name": "b_ja", "properties": {"left": 8, "top": 8}},
            {"type": "Button", "name": "b_nein", "properties": {"left": 8, "top": 40}},
            {
                "type": "Button",
                "name": "b_vielleicht",
                "properties": {"left": 8, "top": 72, "width": 75, "height": 25},
            },
        ],
    }

    befunde = pruefen(pfm)

    groessenbefunde = [b for b in befunde if b.regel == "konsistenz.button_groesse"]
    assert not groessenbefunde, [b.meldung for b in groessenbefunde]


def test_button_mit_abweichender_groesse_nennt_die_echte_standardgroesse() -> None:
    pfm = {
        "name": "Form1",
        "type": "Form",
        "properties": {"width": 400, "height": 300},
        "children": [
            {"type": "Button", "name": "b_ja", "properties": {"left": 8, "top": 8}},
            {"type": "Button", "name": "b_nein", "properties": {"left": 8, "top": 40}},
            {
                "type": "Button",
                "name": "b_gross",
                "properties": {"left": 8, "top": 80, "width": 150, "height": 50},
            },
        ],
    }

    befunde = [b for b in pruefen(pfm) if b.regel == "konsistenz.button_groesse"]

    assert len(befunde) == 1
    assert "b_gross" in befunde[0].meldung
    assert "150×50" in befunde[0].meldung
    assert "75×25" in befunde[0].meldung
    assert "0×0" not in befunde[0].meldung


# -- Standardgrößen aus der Komponente (Punkt 36) --------------------------


def _neues_formular(kinder: list[dict]) -> dict:
    """So speichert ein frisch angelegtes Projekt: ohne Größe."""
    return {"format": "pfm/1", "class": "Form1", "type": "Form",
            "properties": {"caption": "Umrechner"}, "children": kinder}


def _ohne_groesse(name: str, typ: str, left: int, top: int, **rest) -> dict:
    return {"name": name, "type": typ, "properties": {"left": left, "top": top, **rest}}


def test_ein_neues_formular_hat_seine_standardgroesse() -> None:
    """Die Auswertung zu 0.3.3: Label, Edit, Button bei 32/32 bis
    32/128 in einem neuen Formular ergaben „teilweise außerhalb des
    Formulars“, weil die Prüfung mit 0 × 0 rechnete."""
    pfm = _neues_formular([
        _ohne_groesse("label", "Label", 32, 32),
        _ohne_groesse("edit", "Edit", 32, 80),
        _ohne_groesse("button", "Button", 224, 192),
    ])

    assert "geometrie.ausserhalb_formular" not in _regeln(pfm)


def test_die_standardgroesse_der_komponente_zaehlt() -> None:
    """Ein Chart ist 320 × 240 groß, nicht 75 × 25: bei left 200 ragt
    es über das 480 breite Formular hinaus."""
    pfm = _neues_formular([_ohne_groesse("ch", "Chart", 200, 8)])

    assert "geometrie.ausserhalb_formular" in _regeln(pfm)


def test_eine_zu_lange_beschriftung_wird_gemeldet() -> None:
    pfm = _neues_formular([
        _ohne_groesse("b_verdoppeln", "Button", 8, 8, caption="Verdoppeln"),
        _ohne_groesse("b_ok", "Button", 8, 48, caption="OK"),
    ])

    befunde = [b for b in pruefen(pfm) if b.regel == "lesbarkeit.text_abgeschnitten"]

    assert [b.komponente for b in befunde] == ["b_verdoppeln"]
    assert "„Verdoppeln“" in befunde[0].meldung


def test_eine_beschriftung_genau_an_der_grenze_wird_gemeldet() -> None:
    """Punkt 52: „Speichern“ war im 75 Pixel breiten Knopf sichtbar
    abgeschnitten; die Schätzung ergab genau 75 und damit keinen Fund.
    Kurze Beschriftungen bleiben ohne Fund."""
    pfm = _neues_formular([
        _ohne_groesse("b_speichern", "Button", 8, 8, caption="Speichern"),
        _ohne_groesse("b_aendern", "Button", 8, 48, caption="Ändern"),
        _ohne_groesse("b_start", "Button", 8, 88, caption="Button"),
    ])

    befunde = [b for b in pruefen(pfm) if b.regel == "lesbarkeit.text_abgeschnitten"]

    assert [b.komponente for b in befunde] == ["b_speichern"]


def test_namenskonvention_passt_zu_allen_beispielformularen() -> None:
    # Nur lesend: die eingecheckten Formulare werden nicht verändert.
    import json
    from pathlib import Path

    wurzel = Path(__file__).resolve().parent.parent
    dateien = sorted((wurzel / "beispielprojekte").rglob("*.pfm"))
    dateien += sorted((wurzel / "templates").rglob("*.pfm.template"))
    assert dateien
    gemeldet = []
    for datei in dateien:
        text = datei.read_text(encoding="utf-8")
        text = text.replace("{{name}}", "Projekt")
        for befund in pruefen(json.loads(text)):
            if befund.regel == "namenskonvention.praefix":
                gemeldet.append(f"{datei.name}: {befund.meldung}")
    assert gemeldet == []


def test_namenskonvention_prueft_komponenten_im_panel() -> None:
    panel = _komponente("p_rahmen", "Panel", width=200, height=100)
    panel["children"] = [
        _komponente("knopf1", "Button", width=75, height=24, caption="Los")
    ]
    befunde = pruefen(_pfm([panel]))

    assert any(
        b.regel == "namenskonvention.praefix" and b.komponente == "knopf1"
        for b in befunde
    )


def test_namenskonvention_comboboxpraefix_eindeutig() -> None:
    from ide.lint.regeln import _PRAEFIXE

    empfohlen = [praefixe[0] for praefixe in _PRAEFIXE.values()]
    assert len(empfohlen) == len(set(empfohlen))
    for name in ("cb_ort", "cbo_ort"):
        pfm = _pfm([_komponente(name, "ComboBox", width=120, height=24)])
        assert "namenskonvention.praefix" not in _regeln(pfm)


def test_standardname_des_designers_bekommt_nur_einen_hinweis() -> None:
    """Punkt 301: `button`, wie der Designer ihn vergibt, bekam einen
    Hinweis wegen des Präfixes und einen wegen des Standardnamens.
    Es bleibt einer, und der nennt das Präfix mit."""
    pfm = _pfm([_komponente("button", "Button", caption="Start")])

    namenshinweise = [
        b for b in pruefen(pfm) if b.regel.startswith("namenskonvention.")
    ]

    assert len(namenshinweise) == 1
    assert "'b_'" in namenshinweise[0].meldung


def test_auch_in_einem_panel_wird_geprueft_und_ein_timer_ueberlappt_nichts() -> None:
    """Die Regeln sahen nur die oberste Ebene: zwei überlappende
    Knöpfe in einem Panel und einer, der über das Panel hinausragt,
    blieben ohne Meldung. Ein Timer, der im Programm unsichtbar ist,
    hieß dagegen Überlappung."""
    panel = _komponente("p_knoepfe", "Panel", left=8, top=8, width=200, height=100)
    panel["children"] = [
        _komponente("b_a", "Button", left=8, top=8),
        _komponente("b_b", "Button", left=40, top=8),
        _komponente("b_c", "Button", left=180, top=50),
    ]
    pfm = _pfm(
        [
            panel,
            _komponente("b_start", "Button", left=250, top=8),
            {"name": "t_takt", "type": "Timer", "properties": {"left": 260, "top": 12}},
        ]
    )

    befunde = pruefen(pfm)
    ueberlappungen = [b for b in befunde if b.regel == "geometrie.ueberlappung"]
    ausserhalb = [b for b in befunde if b.regel == "geometrie.ausserhalb_formular"]

    assert [b.komponente for b in ueberlappungen] == ["b_a"]
    assert [b.komponente for b in ausserhalb] == ["b_c"]
    assert "außerhalb von p_knoepfe" in ausserhalb[0].meldung



@pytest.mark.parametrize(
    "rechts_oben, links_oben", [(46, 50), (40, 47), (50, 46)]
)
def test_lesereihenfolge_nach_abstand_nicht_nach_rastergrenze(
    rechts_oben: int, links_oben: int
) -> None:
    """Punkt 562: was weniger als 24 Pixel auseinander liegt, steht in
    einer Zeile, auch über ein Vielfaches von 24 hinweg."""
    eintraege = [("rechts", 200, rechts_oben), ("links", 10, links_oben),
                 ("unten", 0, 90)]
    geordnet = lesereihenfolge(eintraege, lambda e: (e[1], e[2]))
    assert [e[0] for e in geordnet] == ["links", "rechts", "unten"]
