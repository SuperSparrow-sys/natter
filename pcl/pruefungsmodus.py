"""Prüfungsmodus (M11, Abschnitt 6).

Vom Nutzer gefordert: Natter wird im Unterricht auch
in Leistungssituationen benutzt, und dann darf das Programm nicht die
halbe Aufgabe lösen.

Was er tut. Für vier Stunden ab dem Einschalten

* werden keine Lösungsvorschläge angezeigt. Die Fehlermeldung sagt
 weiterhin, *was* falsch ist – nur nicht mehr, woran es liegen könnte
* ist die Quelltexterzeugung aus dem Klassendiagramm und aus dem
 Struktogramm nicht möglich

Was er nicht tut. Alles andere bleibt. Die Diagramme lassen sich
weiter zeichnen, das Programm weiter starten und schrittweise
ausführen, die Meldungen bleiben deutsch und verständlich. Der Modus
nimmt Werkzeug weg, keine Bedienbarkeit.

Warum ein Endzeitpunkt und kein Schalter. Zwei Dinge sind
entscheidend, und beide folgen daraus:

1. Er muss einen Neustart von Natter überstehen. Ein Schalter im
 Speicher wäre mit einem Schließen und Öffnen ausgehebelt, und der
 Modus damit wertlos.
2. Er muss von selbst auslaufen. Niemand soll daran denken müssen,
 ihn wieder abzuschalten, und ein vergessener Modus darf keinen
 Schulrechner auf Dauer sperren.

Gespeichert wird deshalb, wann er vorbei ist – nicht, dass er an
ist.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QSettings

#: Wie lange der Modus läuft. Vier Stunden decken auch eine lange
#: Klausur ab, ohne den Rechner über den Schultag hinaus zu binden.
DAUER = timedelta(hours=4)

#: Schlüssel in den Einstellungen: der Zeitpunkt, an dem es vorbei ist.
ENDE_SCHLUESSEL = "pruefung/ende"


def einstellungen() -> QSettings:
    """Dieselbe Ini wie der Rest der IDE – der Modus muss einen
    Neustart überstehen."""
    return QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )


def ende(werte: QSettings | None = None) -> datetime | None:
    """Wann der Prüfungsmodus ausläuft, oder `None`.

    Ein unlesbarer Wert zählt wie „kein Prüfungsmodus“: lieber die
    Werkzeuge freigeben als eine kaputte Einstellungsdatei zu einer
    Dauersperre werden zu lassen.
    """
    werte = werte or einstellungen()
    roh = werte.value(ENDE_SCHLUESSEL, "", type=str)
    if not roh:
        return None
    try:
        return datetime.fromisoformat(roh)
    except ValueError:
        return None


def laeuft(werte: QSettings | None = None, jetzt: datetime | None = None) -> bool:
    """Ob gerade eine Prüfung läuft."""
    zeitpunkt = ende(werte)
    return zeitpunkt is not None and (jetzt or datetime.now()) < zeitpunkt


def restzeit(
    werte: QSettings | None = None, jetzt: datetime | None = None
) -> timedelta | None:
    """Wie lange noch – `None`, wenn kein Prüfungsmodus läuft."""
    zeitpunkt = ende(werte)
    if zeitpunkt is None:
        return None
    verbleibend = zeitpunkt - (jetzt or datetime.now())
    return verbleibend if verbleibend > timedelta(0) else None


def starten(
    werte: QSettings | None = None,
    dauer: timedelta = DAUER,
    jetzt: datetime | None = None,
) -> datetime:
    """Startet den Prüfungsmodus und gibt seinen Endzeitpunkt zurück."""
    werte = werte or einstellungen()
    zeitpunkt = (jetzt or datetime.now()) + dauer
    werte.setValue(ENDE_SCHLUESSEL, zeitpunkt.isoformat(timespec="seconds"))
    return zeitpunkt


def beenden(werte: QSettings | None = None) -> None:
    """Beendet ihn vorzeitig."""
    werte = werte or einstellungen()
    werte.remove(ENDE_SCHLUESSEL)


def restzeit_text(
    werte: QSettings | None = None, jetzt: datetime | None = None
) -> str:
    """Für die Statusleiste: „Prüfungsmodus – noch 2:45 h“.

    Leer, wenn keine Prüfung läuft. Wer nicht sieht, dass der Modus an
    ist, sucht den Fehler bei sich.
    """
    verbleibend = restzeit(werte, jetzt)
    if verbleibend is None:
        return ""
    minuten = int(verbleibend.total_seconds() // 60)
    return f"Prüfungsmodus – noch {minuten // 60}:{minuten % 60:02d} h"


#: Einheitlicher Hinweis an allem, was der Prüfungsmodus sperrt. Ein
#: spurlos verschwundener Menüeintrag wäre verwirrender als ein
#: erklärter.
GESPERRT_HINWEIS = (
    "Während des Prüfungsmodus nicht verfügbar. Er läuft nach vier "
    "Stunden von selbst aus."
)
