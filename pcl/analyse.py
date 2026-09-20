"""Regression für den Unterricht (M10, Punkt 5).

Bewusst klein: keine Modellauswahl, kein Hyperparameter-Tuning, keine
Kreuzvalidierung. Vier Arten, eine Funktion, ein Ergebnisobjekt mit
deutschen Namen.

Gerechnet wird mit `numpy.polyfit`, nicht mit scikit-learn (M10,
Abschnitt 7: „numpy rechnet, scikit-learn liegt bei“). `numpy.polyfit`
deckt linear und polynomial direkt ab; exponentiell und logarithmisch
entstehen über die im Unterricht übliche Linearisierung:

* exponentiell ``y = a·e^(b·x)``  →  ``ln(y) = ln(a) + b·x``
* logarithmisch ``y = a·ln(x) + b``  →  Gerade über ``ln(x)``

Das Bestimmtheitsmaß wird in beiden Fällen auf der ursprünglichen
Skala gerechnet (gemessenes y gegen vorhergesagtes y), nicht auf der
linearisierten – sonst stünde dort ein Wert, der zu einer anderen Kurve
gehört als der angezeigten. Eine Reihe, die exakt auf der Kurve liegt,
ergibt so R² = 1; eine Kurve, die schlechter ist als der bloße
Mittelwert, darf dagegen ein negatives R² ergeben. Das ist bei
linearisierten Anpassungen normal und wird nicht auf 0 geschönt.

`numpy` wird lokal in den Funktionen importiert, wie `pandas` in
`pcl/dataframe.py` – `import pcl` soll für Projekte ohne Datenauswertung
nichts nachladen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pcl.errors import NatterDatenError

#: Erlaubte Werte von ``art``.
ARTEN = ("linear", "polynomial", "exponentiell", "logarithmisch")

#: Erlaubte Werte von ``grad`` bei ``art="polynomial"`` (M10, Punkt 5:
#: „mit wählbarem Grad (2 und 3 reichen)“). Grad 1 ist die lineare
#: Regression und hat mit ``art="linear"`` einen eigenen Namen.
GRADE = (2, 3)

#: Hochgestellte Ziffern für die Formel – ``x²`` liest sich in einer
#: Legende deutlich besser als ``x**2``.
_POTENZEN = {0: "", 1: "·x", 2: "·x²", 3: "·x³"}


def _zahl(wert: float) -> str:
    """Formatiert eine Zahl deutsch, mit Dezimalkomma.

    Zwei Nachkommastellen wie im Arbeitspaket (``y = 2,31·x + 4,07``);
    bei sehr kleinen oder sehr großen Beträgen stattdessen drei
    signifikante Stellen, sonst stünde in der Formel ein nichtssagendes
    ``0,00``.
    """
    if wert == 0:
        return "0"
    if abs(wert) < 0.01 or abs(wert) >= 100000:
        text = f"{wert:.3g}"
    else:
        text = f"{wert:.2f}"
    return text.replace(".", ",")


def _summand(koeffizient: float, term: str, *, erster: bool) -> str:
    """Ein Glied der Formel samt Vorzeichen. Ein negativer Koeffizient
    ergibt ``- 4,07`` statt ``+ -4,07``."""
    zahl = _zahl(abs(koeffizient))
    if erster:
        return f"-{zahl}{term}" if koeffizient < 0 else f"{zahl}{term}"
    zeichen = "-" if koeffizient < 0 else "+"
    return f" {zeichen} {zahl}{term}"


def _formel(glieder: list[tuple[float, str]]) -> str:
    """Baut ``y = 0,50·x² + 1,20·x + 3,00`` aus (Koeffizient, Term)-Paaren.

    Glieder mit Koeffizient 0 fallen weg – nach `_geglaettet()` sind das
    genau die, die nur aus Rundungsrauschen bestehen. Sind alle Glieder
    0, bleibt ``y = 0`` stehen statt einer leeren rechten Seite.
    """
    teile: list[str] = []
    for koeffizient, term in glieder:
        if koeffizient == 0.0:
            continue
        teile.append(_summand(koeffizient, term, erster=not teile))
    return "y = " + ("".join(teile) if teile else "0")


def _polynomformel(koeffizienten: tuple[float, ...]) -> str:
    """``y = 0,50·x² + 1,20·x + 3,00`` aus den Koeffizienten in der
    Reihenfolge von `numpy.polyfit` (höchste Potenz zuerst)."""
    grad = len(koeffizienten) - 1
    return _formel(
        [
            (koeffizient, _POTENZEN[grad - nummer])
            for nummer, koeffizient in enumerate(koeffizienten)
        ]
    )


def _geglaettet(koeffizienten: tuple[float, ...]) -> tuple[float, ...]:
    """Setzt Koeffizienten auf glatte 0, die gegenüber dem größten
    Koeffizienten verschwinden.

    Eine Parabel durch (1|1), (2|4), (3|9) ist ``y = x²``; `numpy.polyfit`
    liefert dafür aber ``1,0·x² - 1,21e-14·x + 2,37e-14``. Ungeglättet
    stünde dieses Rechenrauschen in der Formel in der Legende und in
    `achsenabschnitt` – für den Unterricht unbrauchbar. Die Schranke ist
    mit dem 1e-10-fachen des größten Koeffizienten so klein gewählt, dass
    sie nur Rauschen trifft und nie einen echten Wert.
    """
    groesste = max(abs(koeffizient) for koeffizient in koeffizienten)
    grenze = groesste * 1e-10
    return tuple(0.0 if abs(k) <= grenze else k for k in koeffizienten)


@dataclass(frozen=True)
class Regressionsergebnis:
    """Ergebnis von `regression()` – absichtlich ein kleines, lesbares
    Objekt statt der scikit-learn-API.

    `steigung` und `achsenabschnitt` gibt es bei jeder Art, bedeuten aber
    je nach Art etwas anderes:

    * linear: ``y = steigung·x + achsenabschnitt``
    * polynomial: `achsenabschnitt` ist der Wert bei ``x = 0``,
      `steigung` der Koeffizient des linearen Glieds ``·x``
    * exponentiell ``y = achsenabschnitt·e^(steigung·x)``: der
      Achsenabschnitt ist der Startwert bei ``x = 0``, die Steigung die
      Wachstumsrate im Exponenten
    * logarithmisch: ``y = steigung·ln(x) + achsenabschnitt``
    """

    art: str
    grad: int
    koeffizienten: tuple[float, ...]
    steigung: float
    achsenabschnitt: float
    bestimmtheitsmass: float
    formel: str

    def vorhersage(self, x: Any) -> Any:
        """Der vorhergesagte y-Wert zu `x`. Nimmt eine einzelne Zahl
        (dann kommt eine Zahl zurück) oder eine Reihe von Zahlen (dann
        kommt eine Liste zurück – keine numpy-Reihe, die sich für
        Schüler ungewohnt ausgibt)."""
        import numpy as np

        einzeln = np.ndim(x) == 0
        werte = np.asarray(_zahlenreihe(x, "x"), dtype=float)

        if self.art in ("linear", "polynomial"):
            ergebnis = np.polyval(self.koeffizienten, werte)
        elif self.art == "exponentiell":
            faktor, rate = self.koeffizienten
            ergebnis = faktor * np.exp(rate * werte)
        else:
            faktor, verschiebung = self.koeffizienten
            if np.any(werte <= 0):
                raise NatterDatenError(
                    "Eine logarithmische Regression ist nur für x-Werte größer als 0 "
                    "definiert. Für die Vorhersage wurde ein x-Wert kleiner oder "
                    "gleich 0 übergeben."
                )
            ergebnis = faktor * np.log(werte) + verschiebung

        if einzeln:
            # `_zahlenreihe` hat die einzelne Zahl in eine Reihe verpackt,
            # deshalb steckt das Ergebnis hier in einem Eintrag.
            return float(ergebnis[0])
        return [float(wert) for wert in ergebnis]


def _zahlenreihe(werte: Any, name: str) -> list[float]:
    """Wandelt `werte` in eine Liste von Kommazahlen um. Alles, was keine
    Zahl ist, ergibt eine deutsche Meldung statt eines Tracebacks."""
    if _ist_skalar(werte):
        werte = [werte]
    reihe: list[float] = []
    for wert in werte:
        try:
            zahl = float(wert)
        except (TypeError, ValueError) as fehler:
            raise NatterDatenError(
                f"Die Werte für {name} müssen Zahlen sein. Gefunden wurde {wert!r}. "
                "Hinweis: Python erkennt 3.5 als Zahl, 3,5 dagegen nicht."
            ) from fehler
        reihe.append(zahl)
    return reihe


def _ist_skalar(werte: Any) -> bool:
    import numpy as np

    return np.ndim(werte) == 0


def _bestimmtheitsmass(gemessen: Any, vorhergesagt: Any) -> float:
    """R² auf der ursprünglichen Skala.

    Liegen alle gemessenen y-Werte auf derselben Höhe, ist die Streuung 0
    und der Bruch nicht definiert – dann zählt nur, ob die Kurve durch sie
    hindurchgeht. „Genau“ heißt dabei „bis auf Rechenungenauigkeit“: für
    y = 5, 5, 5 liefert `numpy.polyfit` den Achsenabschnitt als
    4,999999999999999, ein Vergleich auf exakt 0 ergäbe dort fälschlich
    R² = 0.
    """
    import numpy as np

    rest = float(np.sum((gemessen - vorhergesagt) ** 2))
    streuung = float(np.sum((gemessen - gemessen.mean()) ** 2))
    if streuung == 0.0:
        groessenordnung = float(np.sum(gemessen**2))
        return 1.0 if rest <= 1e-20 + 1e-18 * groessenordnung else 0.0
    return 1.0 - rest / streuung


def _pruefe_eingaben(x: list[float], y: list[float], art: str, ordnung: int) -> None:
    import numpy as np

    mindestpunkte = ordnung + 1
    if len(x) != len(y):
        raise NatterDatenError(
            f"Zu jedem x-Wert gehört ein y-Wert. Übergeben wurden {len(x)} x-Werte "
            f"und {len(y)} y-Werte."
        )
    if len(x) < mindestpunkte:
        raise NatterDatenError(
            f"Eine Regression der Art „{art}“ braucht mindestens {mindestpunkte} "
            f"Punkte. Übergeben wurden {len(x)}."
        )
    felder = (("x", np.asarray(x)), ("y", np.asarray(y)))
    for name, werte in felder:
        if not np.all(np.isfinite(werte)):
            raise NatterDatenError(
                f"Die Werte für {name} enthalten einen fehlenden oder unendlichen "
                "Wert. Eine Regression braucht überall echte Zahlen."
            )
    verschiedene = len(set(x))
    if verschiedene == 1:
        raise NatterDatenError(
            f"Alle x-Werte sind gleich ({_zahl(x[0])}). Durch eine senkrechte "
            "Punktwolke lässt sich keine Regression legen – dafür braucht es "
            "Punkte mit verschiedenen x-Werten."
        )
    if verschiedene < mindestpunkte:
        # Ohne diese Prüfung liefert numpy.polyfit eine Kurve, die zwar
        # exakt durch die wenigen x-Stellen geht, zwischen ihnen aber
        # beliebig ausschlägt - und warnt nur (RankWarning), statt zu
        # scheitern.
        raise NatterDatenError(
            f"Eine Regression der Art „{art}“ braucht mindestens {mindestpunkte} "
            f"verschiedene x-Werte. Gefunden wurden nur {verschiedene}."
        )


def regression(x: Any, y: Any, art: str = "linear", *, grad: int = 2) -> Regressionsergebnis:
    """Legt eine Ausgleichskurve durch die Punkte (`x`, `y`).

    `art` ist ``"linear"``, ``"polynomial"``, ``"exponentiell"`` oder
    ``"logarithmisch"``; `grad` gilt nur für ``"polynomial"`` und ist 2
    oder 3. Nimmt Listen, pandas-Spalten oder numpy-Reihen entgegen.

    Beispiel::

        ergebnis = regression(Größe, schuhgroesse)
        print(ergebnis.formel)              # y = 0,25·x - 5,00
        print(ergebnis.bestimmtheitsmass)   # 0.97
        print(ergebnis.vorhersage(180))     # 40.0
    """
    import numpy as np

    if art not in ARTEN:
        raise NatterDatenError(
            f"„{art}“ ist keine bekannte Regressionsart. Möglich sind: {' / '.join(ARTEN)}."
        )
    if art == "polynomial" and grad not in GRADE:
        raise NatterDatenError(
            f"Für eine polynomiale Regression ist der Grad {' oder '.join(str(g) for g in GRADE)} "
            f"vorgesehen. Übergeben wurde {grad!r}."
        )

    x_werte = _zahlenreihe(x, "x")
    y_werte = _zahlenreihe(y, "y")
    ordnung = grad if art == "polynomial" else 1
    _pruefe_eingaben(x_werte, y_werte, art, ordnung)

    x_reihe = np.asarray(x_werte, dtype=float)
    y_reihe = np.asarray(y_werte, dtype=float)

    if art == "linear":
        ergebnis = _linear(x_reihe, y_reihe)
    elif art == "polynomial":
        ergebnis = _polynomial(x_reihe, y_reihe, grad)
    elif art == "exponentiell":
        ergebnis = _exponentiell(x_reihe, y_reihe)
    else:
        ergebnis = _logarithmisch(x_reihe, y_reihe)
    return ergebnis


def _linear(x: Any, y: Any) -> Regressionsergebnis:
    import numpy as np

    koeffizienten = _geglaettet(tuple(float(wert) for wert in np.polyfit(x, y, 1)))
    steigung, achsenabschnitt = koeffizienten
    return Regressionsergebnis(
        art="linear",
        grad=1,
        koeffizienten=koeffizienten,
        steigung=steigung,
        achsenabschnitt=achsenabschnitt,
        bestimmtheitsmass=_bestimmtheitsmass(y, np.polyval(koeffizienten, x)),
        formel=_polynomformel(koeffizienten),
    )


def _polynomial(x: Any, y: Any, grad: int) -> Regressionsergebnis:
    import numpy as np

    koeffizienten = _geglaettet(tuple(float(wert) for wert in np.polyfit(x, y, grad)))
    return Regressionsergebnis(
        art="polynomial",
        grad=grad,
        koeffizienten=koeffizienten,
        # Vorletzter Koeffizient ist der des linearen Glieds, letzter der
        # konstante – siehe Klassendokumentation von Regressionsergebnis.
        steigung=koeffizienten[-2],
        achsenabschnitt=koeffizienten[-1],
        bestimmtheitsmass=_bestimmtheitsmass(y, np.polyval(koeffizienten, x)),
        formel=_polynomformel(koeffizienten),
    )


def _exponentiell(x: Any, y: Any) -> Regressionsergebnis:
    import numpy as np

    if np.any(y <= 0):
        raise NatterDatenError(
            "Für eine exponentielle Regression müssen alle y-Werte größer als 0 "
            "sein – der Logarithmus aus 0 oder einer negativen Zahl ist nicht "
            "definiert. Gefunden wurde der y-Wert "
            f"{_zahl(float(np.min(y)))}."
        )
    rate, log_faktor = (float(wert) for wert in np.polyfit(x, np.log(y), 1))
    faktor = float(np.exp(log_faktor))
    vorhergesagt = faktor * np.exp(rate * x)
    formel = f"y = {_zahl(faktor)}·e^({_zahl(rate)}·x)"
    return Regressionsergebnis(
        art="exponentiell",
        grad=1,
        koeffizienten=(faktor, rate),
        steigung=rate,
        achsenabschnitt=faktor,
        bestimmtheitsmass=_bestimmtheitsmass(y, vorhergesagt),
        formel=formel,
    )


def _logarithmisch(x: Any, y: Any) -> Regressionsergebnis:
    import numpy as np

    if np.any(x <= 0):
        raise NatterDatenError(
            "Für eine logarithmische Regression müssen alle x-Werte größer als 0 "
            "sein – der Logarithmus aus 0 oder einer negativen Zahl ist nicht "
            "definiert. Gefunden wurde der x-Wert "
            f"{_zahl(float(np.min(x)))}."
        )
    faktor, verschiebung = _geglaettet(tuple(float(wert) for wert in np.polyfit(np.log(x), y, 1)))
    vorhergesagt = faktor * np.log(x) + verschiebung
    formel = _formel([(faktor, "·ln(x)"), (verschiebung, "")])
    return Regressionsergebnis(
        art="logarithmisch",
        grad=1,
        koeffizienten=(faktor, verschiebung),
        steigung=faktor,
        achsenabschnitt=verschiebung,
        bestimmtheitsmass=_bestimmtheitsmass(y, vorhergesagt),
        formel=formel,
    )
