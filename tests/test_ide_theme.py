"""Tests für ide/shell/theme.py: QSS-Generator für das IDE-Hauptfenster
selbst (getrennt von pcl.theme, das nur Schülerprogramme einfärbt).
Gemeldet: die IDE wirkte insgesamt farblos/grau,
weil dafür bisher gar kein eigenes Stylesheet existierte.
"""

from ide.shell.theme import ide_qss_erzeugen


def test_qss_enthaelt_die_tokens_des_gewaehlten_themes() -> None:
    hell = ide_qss_erzeugen("light")
    dunkel = ide_qss_erzeugen("dark")

    assert "#ffffff" in hell  # color.light.bg
    assert "#1e1e1e" in dunkel  # color.dark.bg
    assert hell != dunkel


def test_qss_deckt_die_wichtigsten_ide_rahmen_widgets_ab() -> None:
    qss = ide_qss_erzeugen("light")
    for auswahl in (
        "QMenuBar",
        "QMenu",
        "QToolBar",
        "QDockWidget",
        "QTabBar::tab",
        "QTreeWidget",
        "QStatusBar",
        "QScrollBar",
    ):
        assert auswahl in qss, f"{auswahl} fehlt im IDE-Stylesheet"


def test_qss_verwendet_die_akzentfarbe_fuer_ausgewaehlte_elemente() -> None:
    hell = ide_qss_erzeugen("light")
    dunkel = ide_qss_erzeugen("dark")

    assert hell.count("#0067c0") >= 3  # color.light.accent
    assert dunkel.count("#4cc2ff") >= 3  # color.dark.accent


def test_im_dunklen_thema_steht_keine_weisse_schrift_fest() -> None:
    """Weiß auf der Akzentfarbe ist die Voreinstellung für einen Knopf
 mit Akzent-Hintergrund - im hellen Thema stimmt das, weil `bg`
 ohnehin weiß ist. Im dunklen Thema ist der Akzent ein helles Blau
 (#4cc2ff), und weiße Schrift darauf ist kaum zu lesen.

 `pcl/theme` nimmt an denselben Stellen seit jeher `bg` statt einer
 festen Farbe; das IDE-Stylesheet zieht nach (Rückmeldung
 zum Hover: „die schrift darf nicht weis werden").
 """
    assert "#ffffff" not in ide_qss_erzeugen("dark").lower()
