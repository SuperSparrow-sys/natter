"""Bildprüfungen am gerenderten Widget für die Komponenten aus Schritt 6.

Jeder Test hier hält einen Fehler fest, den erst ein Bildschirmfoto
gezeigt hat, obwohl die Eigenschaften-Tests grün waren (siehe
`tests/test_components_werte.py`). Sie messen deshalb Pixel, nicht
Eigenschaften.

Gerendert wird mit `QT_QPA_PLATFORM=offscreen`; `tests/conftest.py`
setzt dafür `QT_QPA_FONTDIR`, sonst stünden statt Glyphen Kästchen im
Bild (AGENTS.md, Abschnitt „Tests“).
"""

from PySide6.QtGui import QImage

from pcl import Form, GroupBox, Label, SpinEdit, TrackBar
from pcl.theme import qss_erzeugen


def _ink_je_zeile(bild: QImage, von_x: int, bis_x: int, hintergrund) -> list[int]:
    """Zählt je Bildzeile die Punkte im Streifen `von_x`..`bis_x`, die
    sich deutlich vom Hintergrund abheben."""
    zeilen = []
    for y in range(2, bild.height() - 2):
        anzahl = 0
        for x in range(von_x, bis_x):
            punkt = bild.pixelColor(x, y)
            abstand = (
                abs(punkt.red() - hintergrund.red())
                + abs(punkt.green() - hintergrund.green())
                + abs(punkt.blue() - hintergrund.blue())
            )
            if abstand > 120:
                anzahl += 1
        zeilen.append(anzahl)
    return zeilen


class _SpinFormular(Form):
    def create_components(self) -> None:
        self.width, self.height = 120, 50
        self.se_zahl = SpinEdit(self)
        self.se_zahl.left, self.se_zahl.top = 10, 10
        self.se_zahl.width, self.se_zahl.height = 90, 26


def _pfeil_zeilen(theme: str) -> list[int]:
    formular = _SpinFormular()
    formular.theme = theme
    formular.show()
    bild = formular.se_zahl._qwidget.grab().toImage()
    hintergrund = bild.pixelColor(bild.width() // 4, bild.height() // 2)
    return _ink_je_zeile(bild, bild.width() - 18, bild.width() - 2, hintergrund)


def test_spinedit_zeigt_seine_beiden_pfeilspitzen() -> None:
    """Real gefunden (Bildschirmfoto, Schritt 6): nachdem `QSpinBox` in
    die QSS-Regel für Eingabefelder aufgenommen worden war, zeichnete Qt
    die Komponente vollständig aus dem Stylesheet - und die beiden
    Pfeilspitzen fielen ersatzlos weg, übrig blieben zwei Striche.

    Gemessen wird die Treppe: eine Pfeilspitze ergibt Bildzeilen mit
    3, 5, 7, 9 deckenden Punkten, eine waagerechte Linie dagegen nur
    Zeilen über die volle Breite (12-13) oder gar nichts. Ein bloßes
    Abzählen aller Punkte reichte nicht - im hellen Theme lagen kaputt
    und heil mit 46 zu 52 zu dicht beieinander.
    """
    for theme in ("light", "dark"):
        zeilen = _pfeil_zeilen(theme)
        treppe = [anzahl for anzahl in zeilen if 2 <= anzahl <= 10]
        assert len(treppe) >= 4, f"{theme}: keine Pfeilspitzen, Zeilen {zeilen}"


def test_theme_stylt_die_spinbox_bewusst_nicht() -> None:
    """Gegenstück zum Bildtest darüber, als Erklärung an der Quelle:
    keine Regel im Theme-QSS darf `QSpinBox`/`QDoubleSpinBox` treffen.
    Ein Nachbau der Pfeile über `::up-arrow`/`::down-arrow` half nicht -
    Qt versteht den CSS-Trick „Dreieck aus Rahmen" nicht und malte zwei
    schwarze Quadrate."""
    for theme in ("light", "dark"):
        qss = qss_erzeugen(theme)
        # Im erklärenden Kommentar dürfen die Namen stehen, in einem
        # Selektor nicht - deshalb auf die Zeilen ohne Kommentar sehen.
        ohne_kommentare = []
        im_kommentar = False
        for zeile in qss.splitlines():
            if "/*" in zeile:
                im_kommentar = True
            if not im_kommentar:
                ohne_kommentare.append(zeile)
            if "*/" in zeile:
                im_kommentar = False
        rest = "\n".join(ohne_kommentare)
        assert "QSpinBox" not in rest, theme
        assert "QDoubleSpinBox" not in rest, theme


class _TrackBarFormular(Form):
    def create_components(self) -> None:
        self.width, self.height = 200, 60
        self.tb_regler = TrackBar(self)
        self.tb_regler.left, self.tb_regler.top = 10, 10
        self.tb_regler.maximum = 10
        self.tb_regler.position = 5


def _trackbar_bild(theme: str, frequency: int) -> QImage:
    formular = _TrackBarFormular()
    formular.theme = theme
    formular.tb_regler.frequency = frequency
    formular.show()
    return formular.tb_regler._qwidget.grab().toImage()


def test_trackbar_zeichnet_seine_teilstriche() -> None:
    """Real gefunden (Bildvergleich, Schritt 6): mit einer QSS-Regel für
    `QSlider::groove` zeichnet Qt den Schieber vollständig aus dem
    Stylesheet - und QSS kennt keine Teilstriche. `frequency` wäre damit
    in jedem pcl-Formular wirkungslos gewesen, denn jedes Formular setzt
    ein Stylesheet. Die Regel gilt seither nur noch dem Griff.

    Gemessen am gerenderten Bild statt an `tickInterval()`: genau das
    war ja der Punkt - die Eigenschaft kam korrekt am Widget an, nur zu
    sehen war sie nicht mehr.
    """
    for theme in ("light", "dark"):
        mit_strichen = _trackbar_bild(theme, 1)
        ohne_striche = _trackbar_bild(theme, 0)
        assert mit_strichen != ohne_striche, f"{theme}: frequency ändert das Bild nicht"


def test_trackbar_frequency_aendert_den_abstand_der_teilstriche() -> None:
    """Nicht nur „irgendwelche Striche", sondern wirklich der Abstand:
    zwei verschiedene `frequency`-Werte müssen zwei verschiedene Bilder
    ergeben."""
    for theme in ("light", "dark"):
        assert _trackbar_bild(theme, 1) != _trackbar_bild(theme, 5), theme


class _GesperrtFormular(Form):
    def create_components(self) -> None:
        self.width, self.height = 260, 90
        self.g_offen = GroupBox(self)
        self.g_offen.left, self.g_offen.top = 5, 5
        self.g_offen.width, self.g_offen.height = 120, 70
        self.g_offen.caption = "Zahlung"
        self.l_offen = Label(self.g_offen)
        self.l_offen.left, self.l_offen.top, self.l_offen.width = 10, 30, 100
        self.l_offen.caption = "Barzahlung"

        self.g_zu = GroupBox(self)
        self.g_zu.left, self.g_zu.top = 130, 5
        self.g_zu.width, self.g_zu.height = 120, 70
        self.g_zu.caption = "Zahlung"
        self.l_zu = Label(self.g_zu)
        self.l_zu.left, self.l_zu.top, self.l_zu.width = 10, 30, 100
        self.l_zu.caption = "Barzahlung"
        self.g_zu.enabled = False


def _schriftkontrast(formular: Form, beschriftung: Label) -> int:
    """Wie weit sich der auffälligste Punkt der Beschriftung in der
    Helligkeit vom Hintergrund des Formulars absetzt.

    Gemessen wird im Bild des ganzen Formulars, nicht in einem
    eigenen `grab()` des Labels: ein für sich gegriffenes Label bringt
    seinen eigenen Hintergrund mit, und der unterscheidet sich im
    gesperrten Zustand ebenfalls - der Test wäre dann grün, ohne etwas
    über die Schriftfarbe zu sagen.
    """
    bild = formular._qwidget.grab().toImage()
    ecke = beschriftung._qwidget.mapTo(formular._qwidget, beschriftung._qwidget.rect().topLeft())
    hintergrund = bild.pixelColor(1, 1).lightness()
    return max(
        abs(bild.pixelColor(ecke.x() + x, ecke.y() + y).lightness() - hintergrund)
        for y in range(beschriftung.height)
        for x in range(beschriftung.width)
    )


def test_gesperrter_behaelter_ist_auch_zu_sehen() -> None:
    """Real gefunden (Bildschirmfoto, Schritt 6): eine `GroupBox` mit
    `enabled = False` war zwar wirklich gesperrt, sah aber aus wie jede
    andere - Beschriftung und Inhalt standen in voller Schwärze da. Die
    Regel `QWidget { color: ... }` ganz oben im Theme-QSS schlug die
    Farbe, die Qt sonst für den Zustand „disabled" nimmt; es gab bis
    dahin nur `QPushButton:disabled`."""
    for theme in ("light", "dark"):
        formular = _GesperrtFormular()
        formular.theme = theme
        formular.show()
        # Gemessen an der Beschriftung *im* Behälter, nicht am Rahmen:
        # der Rahmen hat eine eigene `:disabled`-Regel und wäre auch
        # dann noch anders, wenn die Schrift voll schwarz bliebe.
        offen = _schriftkontrast(formular, formular.l_offen)
        zu = _schriftkontrast(formular, formular.l_zu)

        assert offen > zu + 30, f"{theme}: gesperrte Schrift ({zu}) wie offene ({offen})"
