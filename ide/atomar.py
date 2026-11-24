"""Projektdateien so schreiben, dass nach einem Abbruch die alte
Fassung noch da ist.

`Path.write_text` kürzt die Datei zuerst auf null Bytes und füllt sie
dann neu. Fällt dazwischen der Strom aus, bricht die Verbindung zum
Netzlaufwerk ab oder wird der USB-Stick gezogen, bleibt eine leere
oder abgeschnittene Datei zurück, und eine Vorfassung gibt es nicht
(Punkt 236). Den Designer trifft das am stärksten: er schreibt die
`.pfm` bei jeder einzelnen Änderung neu.

`atomar_schreiben` schreibt deshalb zuerst in eine Nachbardatei im
selben Ordner, bringt sie mit `os.fsync` auf die Platte und setzt sie
erst dann mit `os.replace` an die Stelle der alten. `os.replace`
tauscht in einem Schritt: danach liegt entweder die alte oder die
neue Datei vollständig da. Im selben Ordner muss die Zwischendatei
liegen, weil ein Tausch über Laufwerksgrenzen hinweg nicht in einem
Schritt geht.
"""

from __future__ import annotations

import contextlib
import errno
import os
import time
from pathlib import Path

#: So oft wird der Tausch versucht, wenn Windows ihn verweigert. Ein
#: Virenscanner öffnet eine gerade geschriebene Datei gern für einen
#: Augenblick, und solange er sie hält, scheitert `os.replace`.
_VERSUCHE = 5
_PAUSE = 0.05


def atomar_schreiben(
    pfad: Path | str,
    inhalt: str | bytes,
    *,
    encoding: str = "utf-8",
) -> None:
    """Schreibt `inhalt` nach `pfad`, ohne dass ein Abbruch mitten im
    Schreiben die alte Datei beschädigt.

    Ein Text wird wie bei `Path.write_text` geschrieben, auch mit
    denselben Zeilenenden. Scheitert das Schreiben, löst die Funktion
    denselben `OSError` aus wie `write_text`; die alte Datei bleibt
    unverändert, und die Zwischendatei wird entfernt.
    """
    pfad = Path(pfad)
    # Eine schreibgeschützte Datei ließe sich über den Tausch trotzdem
    # ersetzen, jedenfalls außerhalb von Windows. Der Schreibschutz soll
    # aber gelten wie bisher.
    if pfad.exists() and not os.access(pfad, os.W_OK):
        raise PermissionError(
            13, "Die Datei ist schreibgeschützt", str(pfad)
        )
    zwischen = pfad.with_name(f".{pfad.name}.{os.getpid()}.tmp")
    try:
        if isinstance(inhalt, bytes):
            datei = zwischen.open("wb")
        else:
            datei = zwischen.open("w", encoding=encoding)
        with datei:
            datei.write(inhalt)
            datei.flush()
            os.fsync(datei.fileno())
        _ersetzen(zwischen, pfad)
    except BaseException:
        with contextlib.suppress(OSError):
            zwischen.unlink(missing_ok=True)
        raise


#: Windows-Fehlernummern für einen Ort, den es nicht mehr gibt: Pfad
#: oder Laufwerk fehlt, Laufwerk nicht bereit, Netzpfad weg.
_ORT_FEHLT = {2, 3, 15, 21, 53, 64, 67, 1231}
#: Windows-Fehlernummern für einen vollen Datenträger.
_VOLL = {39, 112}


def schreibfehler_grund(fehler: OSError, pfad: Path | str) -> str | None:
    """Ein deutscher Satz zu einem Schreibfehler, den jemand ohne
    Kenntnis von Fehlernummern versteht, oder `None`, wenn der Fehler
    keiner der bekannten Fälle ist.

    Der Text von Windows nannte die Zwischendatei aus
    `atomar_schreiben`, die niemand kennt, und war englisch („[Errno 28]
    No space left on device“, Punkt 675).
    """
    ordner = Path(pfad).parent
    winerror = getattr(fehler, "winerror", None)
    if fehler.errno == errno.ENOSPC or winerror in _VOLL:
        return f"Auf dem Datenträger von\n{ordner}\nist kein Platz mehr frei."
    if fehler.errno == errno.ENOENT or winerror in _ORT_FEHLT:
        return (
            f"Den Ordner\n{ordner}\ngibt es nicht mehr. Vermutlich ist "
            "der USB-Stick abgezogen oder die Verbindung zum "
            "Netzlaufwerk unterbrochen."
        )
    return None


def ordner_beschreibbar(ordner: Path | str) -> bool:
    """Ob sich in `ordner` eine Datei anlegen und wieder löschen lässt.

    Ausprobiert statt über `os.access` gefragt: das sieht unter
    Windows nur das Attribut „Schreibgeschützt“ an und meldet einen
    Ordner, dessen Freigabe nur Lesen erlaubt, als beschreibbar
    (Punkt 321). Die Probedatei ist versteckt benannt, damit sie im
    Explorer von Natter nicht auftaucht, falls das Löschen scheitert.
    """
    import tempfile

    try:
        kennung, name = tempfile.mkstemp(
            prefix=".natter-probe-", dir=str(ordner)
        )
    except OSError:
        return False
    os.close(kennung)
    with contextlib.suppress(OSError):
        os.unlink(name)
    return True


def _ersetzen(zwischen: Path, pfad: Path) -> None:
    for versuch in range(_VERSUCHE):
        try:
            os.replace(zwischen, pfad)
            return
        except PermissionError:
            if versuch == _VERSUCHE - 1:
                raise
            time.sleep(_PAUSE)
