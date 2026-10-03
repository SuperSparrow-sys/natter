"""Zahlen mit Dezimalkomma lesen und schreiben: `zahl` und `text`.

Python kennt nur den Dezimalpunkt: `float("2,5")` bricht ab, und
`str(2.5)` ergibt „2.5“. Getippt und gelesen wird im Unterricht aber
mit Komma. Bis Punkt 91 schrieb sich jedes Projekt dafür zwei kleine
Funktionen selbst; das Taschenrechner-Beispiel hatte sie als Methoden
des Formulars.

    from pcl import text, zahl

    preis = zahl(self.e_preis.text)          # "2,5" -> 2.5
    self.l_summe.caption = text(preis * 3)   # 7.5 -> "7,5"
    self.l_euro.caption = text(preis, 2)     # 2.5 -> "2,50"
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Context, Decimal

from pcl.errors import NatterPropertyError, NatterZahlError

#: Eine ganze Zahl mit Punkten zwischen Dreiergruppen, wie man im
#: Deutschen große Zahlen schreibt: „1.000“, „-1.234.567“.
_TAUSENDERPUNKTE = re.compile(r"[+-]?[1-9]\d{0,2}(\.\d{3})+")


def zahl(eingabe: str) -> float:
    """Liest eine Zahl aus einem Text, mit Komma oder Punkt.

    Leerzeichen am Rand zählen nicht. Stehen Punkt und Komma
    zugleich darin, ist der Punkt die Tausendertrennung: „1.234,5“
    ergibt 1234.5. Steht ein Punkt hinter dem Komma, wie im
    englischen „1,234.5“, ist das keine Zahl. Ohne Komma gilt der Punkt ebenfalls als
    Tausendertrennung, wenn er Dreiergruppen abteilt und die Zahl
    vorn nicht mit 0 beginnt: „1.000“ ergibt 1000, „1.234.567“
    1234567. Sonst ist er ein Dezimalpunkt: „2.5“ ergibt 2.5,
    „0.500“ 0.5 und „1.0005“ 1.0005. Das Ergebnis ist immer eine
    Kommazahl (`float`), auch bei „3“.

    Ein Text, der keine Zahl ist, löst einen `ValueError` mit
    deutscher Meldung aus. Das gilt auch für „nan“ und „inf“, die
    `float()` annähme: mit ihnen lässt sich nicht rechnen::

        try:
            a = zahl(self.e_zahl1.text)
        except ValueError:
            self.l_ergebnis.caption = "Bitte eine Zahl eintragen."
            return
    """
    if not isinstance(eingabe, str):
        raise NatterZahlError(
            f"zahl() erwartet einen Text, erhalten wurde {eingabe!r}."
        )
    bereinigt = eingabe.strip().replace(" ", "")
    if "," in bereinigt and "." in bereinigt:
        if bereinigt.rfind(".") > bereinigt.rfind(","):
            # „1,234.5“ ist englisch geschrieben: Komma als
            # Tausendertrennung, Punkt als Dezimalzeichen. Gelesen
            # wurde daraus still 1,2345 (Punkt 479).
            raise NatterZahlError(
                f"„{eingabe.strip()}“ ist keine Zahl in deutscher "
                "Schreibweise. Das Komma trennt die Nachkommastellen, "
                "zum Beispiel 1234,5 oder 1.234,5."
            )
        bereinigt = bereinigt.replace(".", "")
    elif _TAUSENDERPUNKTE.fullmatch(bereinigt):
        bereinigt = bereinigt.replace(".", "")
    bereinigt = bereinigt.replace(",", ".")
    try:
        wert = float(bereinigt)
    except ValueError:
        wert = math.nan
    if not bereinigt or not math.isfinite(wert):
        if not eingabe.strip():
            raise NatterZahlError("Das Feld ist leer, erwartet wird eine Zahl.")
        raise NatterZahlError(
            f"„{eingabe.strip()}“ ist keine Zahl. Erwartet wird zum Beispiel "
            "2,5 oder -3."
        )
    return wert


class PunktInSpalte:
    """Entscheidet für eine ganze Spalte (CSV-Import, `StringGrid`),
    was ein Punkt bedeutet - nicht Zelle für Zelle wie `zahl`.

    Für eine einzelne Eingabe ist „1.250“ die Zahl 1250. In einer
    Spalte, in der auch „2.49“ oder „0.125“ steht, ist der Punkt aber
    erkennbar das Dezimalzeichen, wie in Dateien aus englischem Excel
    oder `pandas.to_csv`. Zelle für Zelle gelesen wurde dort aus jedem
    Wert mit genau drei Nachkommastellen still eine Tausenderzahl.

    Die Werte kommen einzeln über `sehen`, damit große Dateien nicht
    ganz im Speicher liegen müssen. `ergebnis` ist danach:

    - ``True``: der Punkt ist das Dezimalzeichen; die Spalte wird mit
      `zahl_mit_dezimalpunkt` gelesen.
    - ``False``: nichts spricht dafür; es gilt `zahl`.
    - ``None``: widersprüchlich („2.5“ neben „1.234.567“); die Spalte
      bleibt Text, statt geraten zu werden.
    """

    def __init__(self) -> None:
        self._komma = False
        self._dezimal = False
        self._mehrere = False

    def sehen(self, wert: str) -> None:
        bereinigt = wert.strip().replace(" ", "")
        if "," in bereinigt:
            self._komma = True
        if bereinigt.count(".") > 1:
            self._mehrere = True
        elif "." in bereinigt and not _TAUSENDERPUNKTE.fullmatch(bereinigt):
            self._dezimal = True

    @property
    def ergebnis(self) -> bool | None:
        if not self._dezimal or self._komma:
            return False
        return None if self._mehrere else True


def zahl_mit_dezimalpunkt(eingabe: str) -> float:
    """Wie `zahl`, aber jeder Punkt ist ein Dezimalpunkt: „1.250“
    ergibt 1.25. Nur für Spalten, für die `PunktInSpalte` das so
    entschieden hat."""
    return zahl(eingabe.replace(".", ","))


def text(wert: float, stellen: int | None = None) -> str:
    """Schreibt eine Zahl als Text mit Dezimalkomma.

    Ohne `stellen` so kurz wie möglich: 3.0 wird „3“, 0.1 + 0.2 wird
    „0,3“ und nicht „0,30000000000000004“. Mit `stellen` genau so
    viele Nachkommastellen: ``text(2.5, 2)`` ergibt „2,50“.

    Gerundet wird wie im Mathematikunterricht, bei einer 5 aufwärts:
    ``text(2.5, 0)`` ergibt „3“, ``text(0.125, 2)`` „0,13“. Pythons
    eigenes Runden ergäbe „2“ und „0,12“, weil es eine 5 zur geraden
    Ziffer rundet. Außerdem rechnet es mit dem Binärwert, und der
    liegt bei 1.005 knapp unter der Zahl im Programm. Gerundet wird
    deshalb die Zahl, wie sie im Programm steht (`repr`).

    Ohne `stellen` erscheint keine Schreibweise mit „e“:
    ``text(0.00001)`` ergibt „0,00001“, ``text(1e16)``
    „10000000000000000“. Erst ab einem Betrag von 10^21 und unter
    10^-10 wird die Zahl als Zehnerpotenz geschrieben,
    ``text(2.5e21)`` ergibt „2,5 · 10^21“; ausgeschrieben wäre sie
    nicht mehr lesbar.
    """
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        raise NatterZahlError(
            f"text() erwartet eine Zahl, erhalten wurde {wert!r}."
        )
    if stellen is None:
        if isinstance(wert, int):
            ergebnis = str(wert)
        else:
            ergebnis = _ohne_exponent(wert)
    else:
        if isinstance(stellen, bool) or not isinstance(stellen, int) or stellen < 0:
            raise NatterPropertyError(
                "text() erwartet bei den Nachkommastellen eine ganze Zahl "
                f"ab 0, erhalten wurde {stellen!r}."
            )
        if isinstance(wert, float) and not math.isfinite(wert):
            ergebnis = f"{wert:.{stellen}f}"
        else:
            dezimal = Decimal(repr(wert))
            # Genug Stellen für große Zahlen; die Vorgabe von 28
            # reichte für 1e30 mit zwei Nachkommastellen nicht.
            kontext = Context(
                prec=max(28, dezimal.adjusted() + stellen + 2),
                rounding=ROUND_HALF_UP,
            )
            genau = dezimal.quantize(Decimal(1).scaleb(-stellen), context=kontext)
            ergebnis = format(genau, "f")
    if ergebnis.startswith("-") and not ergebnis.strip("-0."):
        ergebnis = ergebnis[1:]
    return ergebnis.replace(".", ",")


#: Ab hier und darunter wird eine Zahl ohne `stellen` als Zehnerpotenz
#: geschrieben.
_GROSS = Decimal("1e21")
_KLEIN = Decimal("1e-10")

def _ohne_exponent(wert: float) -> str:
    """Eine Kommazahl so kurz wie möglich, aber ohne „e“."""
    if not math.isfinite(wert):
        return format(wert, ".15g")
    # 15 Stellen: mehr kann `float` nicht verlässlich, und die
    # Rundungsreste dahinter will niemand sehen.
    kurz = Decimal(format(wert, ".15g"))
    if kurz == 0 or _KLEIN <= abs(kurz) < _GROSS:
        ergebnis = format(kurz, "f")
        if "." in ergebnis:
            ergebnis = ergebnis.rstrip("0").rstrip(".")
        return ergebnis
    exponent = kurz.adjusted()
    mantisse = format(kurz.scaleb(-exponent), "f")
    if "." in mantisse:
        mantisse = mantisse.rstrip("0").rstrip(".")
    # „^“ statt hochgestellter Ziffern: die meisten davon kennt die
    # Windows-Konsole nicht, und `print` bräche dort ab.
    return f"{mantisse} · 10^{exponent}"
