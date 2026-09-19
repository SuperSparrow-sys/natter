"""System-Komponenten: Timer.

Siehe konzept-natter.md, Abschnitt 5.2 (Palette „System“). Anders als
alles in `standard.py`/`additional.py` ist ein `Timer` **nicht
sichtbar** und deshalb keine `Control`-, sondern eine reine
`Komponente` - genau wie die Datenbank-Komponenten in `data_access.py`.
Er hat folglich weder `left`/`top` noch eine Kachel in der Palette,
sondern entsteht im Quelltext:

    def create_components(self):
        self.t_ampel = Timer()
        self.t_ampel.interval = 2000
        self.t_ampel.on_timer = self.t_ampel_timer

Was fehlt, damit der Designer ihn wie Lazarus als Entwurfszeit-Symbol
auf dem Formular zeigen könnte, steht in `docs/komponenten.md` unter
„Offene Punkte“.

Vorbild ist `TTimer` aus `referenz/lazarus/l_Pet/u_main.lfm`
(`t_hunger: TTimer` mit `OnTimer = t_hungerTimer`, im Quelltext über
`t_hunger.enabled := true` geschaltet) - deshalb dieselben beiden
Eigenschaften `enabled`/`interval` und dasselbe eine Ereignis.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer

from pcl.properties import Event, Komponente, Prop


class Timer(Komponente):
    """Zeitgeber, der in festem Abstand `on_timer` auslöst. Qt-Basis:
    `QTimer`.

    Wie `TTimer` in Lazarus läuft ein frisch erzeugter `Timer` sofort
    (`enabled` ist standardmäßig wahr) und wird über `enabled` an- und
    abgeschaltet - ein `start()`/`stop()` gibt es bewusst nicht, damit es
    nur einen Schalter gibt.
    """

    enabled = Prop(bool, True, kategorie="Verhalten", doc="Legt fest, ob der Zeitgeber läuft")
    interval = Prop(
        int,
        1000,
        kategorie="Verhalten",
        doc="Abstand zwischen zwei Auslösungen in Millisekunden",
    )

    on_timer = Event(doc="Wird nach jeweils `interval` Millisekunden ausgelöst")

    def __init__(self) -> None:
        self._qtimer = QTimer()
        self._qtimer.setInterval(self.interval)
        self._qtimer.timeout.connect(self._bei_zeitpunkt)
        if self.enabled:
            self._qtimer.start()

    def _bei_zeitpunkt(self) -> None:
        if self.on_timer is not None:
            self.on_timer(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name == "interval":
            # setInterval wirkt auch bei laufendem QTimer sofort; ein
            # Neustart wäre nicht nötig und würde die bereits verstrichene
            # Zeit verwerfen.
            self._qtimer.setInterval(wert)
        elif name == "enabled":
            if wert:
                self._qtimer.start()
            else:
                self._qtimer.stop()
