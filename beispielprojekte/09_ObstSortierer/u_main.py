# Stufe 9 von 11 - der Rechner lernt selbst eine Regel.
#
# Neu gegenüber Stufe 8:
#   scikit-learn       die Bibliothek für maschinelles Lernen
#   Random Forest      viele Entscheidungsbäume, die gemeinsam abstimmen
#   Trainingsdaten /   getrennte Daten zum Lernen und zum Prüfen
#     Testdaten
#   Wahrscheinlichkeit wie sicher sich das Modell ist
#   Merkmalswichtigkeit  welche Angabe die Entscheidung trägt
#
# Der Unterschied zu Stufe 8 ist der entscheidende:
#   Regression  -> wir geben die Form der Kurve vor, der Rechner sucht
#                  nur noch die Zahlen dazu.
#   Random Forest -> wir geben gar keine Form vor. Der Rechner baut
#                  sich seine Regeln aus den Beispielen selbst.
#
# Ein Entscheidungsbaum stellt Ja/Nein-Fragen: "Länge über 120 mm?"
# Ein Random Forest besteht aus vielen solchen Bäumen, die jeweils
# nur einen Teil der Daten gesehen haben. Die Sorte, für die sich die
# meisten entscheiden, ist die Antwort. Das ist zuverlässiger als ein
# einzelner Baum, der sich an Zufälligkeiten in den Lerndaten
# festhält.

import csv
from pathlib import Path

from u_main_design import Form1Design

DATEN = Path(__file__).parent / "daten" / "obst.csv"

MERKMALE = ("Gewicht", "Laenge", "Breite")
BESCHRIFTUNG = {"Gewicht": "Gewicht", "Laenge": "Länge", "Breite": "Breite"}


def prozent(anteil: float) -> str:
    """0.59 -> "59 %". Auf Deutsch steht vor dem Prozentzeichen ein
    Leerzeichen; Pythons `:.0%` schreibt es ohne."""
    return f"{round(anteil * 100)} %"


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.wald = None
        self.daten_lesen()
        self.streuung_zeichnen()
        # Das Lernen braucht beim ersten Mal einige Sekunden, schon weil
        # scikit-learn groß ist. Hier im form_create stünde so lange gar
        # kein Fenster da. Deshalb erscheint zuerst das Fenster, und der
        # Zeitgeber t_lernen startet das Lernen gleich danach.
        self.l_training.caption = "Das Modell lernt gerade ..."
        self.l_antwort.caption = ""

    def t_lernen_timer(self, sender) -> None:
        # Nur einmal: der Zeitgeber hält sich gleich selbst an.
        self.t_lernen.enabled = False
        self.wald_trainieren()
        self.sortieren()

    # -- Daten -----------------------------------------------------

    def daten_lesen(self) -> None:
        with DATEN.open(encoding="utf-8", newline="") as datei:
            self.zeilen = list(csv.DictReader(datei, delimiter=";"))

        # X sind die Merkmale, y ist die richtige Antwort. Diese beiden
        # Namen sind in scikit-learn überall gleich.
        self.X = [[float(zeile[name]) for name in MERKMALE] for zeile in self.zeilen]
        self.y = [zeile["Sorte"] for zeile in self.zeilen]

    def streuung_zeichnen(self) -> None:
        """Eine Punktwolke je Sorte - so sieht man sofort, ob sich die
        Sorten überhaupt unterscheiden lassen."""
        self.ch_streuung.clear()
        for sorte in sorted(set(self.y)):
            passend = [z for z in self.zeilen if z["Sorte"] == sorte]
            self.ch_streuung.add_scatter_series(
                [float(z["Laenge"]) for z in passend],
                [float(z["Breite"]) for z in passend],
                title=sorte,
            )

    # -- Lernen ----------------------------------------------------

    def wald_trainieren(self) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split

        # Ein Teil der Beispiele wird zurückgehalten. Nur an Daten, die
        # das Modell nie gesehen hat, lässt sich ehrlich messen, ob es
        # etwas gelernt oder nur auswendig gelernt hat.
        x_lernen, x_pruefen, y_lernen, y_pruefen = train_test_split(
            self.X, self.y, test_size=0.25, random_state=42, stratify=self.y
        )

        # n_estimators = Anzahl der Entscheidungsbäume.
        # random_state sorgt dafür, dass bei jedem Start dasselbe
        # herauskommt - sonst wäre der Unterricht schwer zu besprechen.
        self.wald = RandomForestClassifier(n_estimators=100, random_state=42)
        self.wald.fit(x_lernen, y_lernen)

        treffer = self.wald.score(x_pruefen, y_pruefen)
        self.l_training.caption = (
            f"Gelernt an {len(x_lernen)} Früchten,\n"
            f"geprüft an {len(x_pruefen)} zurückgehaltenen.\n"
            f"Davon richtig erkannt: {prozent(treffer)}"
        )

        self.wichtigkeit_zeigen()

    def wichtigkeit_zeigen(self) -> None:
        """Welches Merkmal trägt die Entscheidung?

        Das kann ein Random Forest von sich aus sagen - einer der
        Gründe, warum er im Unterricht so dankbar ist.
        """
        anteile = sorted(
            zip(MERKMALE, self.wald.feature_importances_, strict=True),
            key=lambda paar: paar[1],
            reverse=True,
        )
        zeilen = [f"{BESCHRIFTUNG[name]}: {prozent(anteil)}" for name, anteil in anteile]
        self.l_wichtigkeit.caption = "Worauf das Modell achtet:\n" + "\n".join(zeilen)

    # -- Vorhersagen -----------------------------------------------

    def se_wert_change(self, sender) -> None:
        self.sortieren()

    def sortieren(self) -> None:
        # Vor dem Ende des Lernens gibt es noch kein Modell, das fragen
        # könnte.
        if self.wald is None:
            return
        frucht = [
            float(self.se_gewicht.value),
            float(self.se_laenge.value),
            float(self.se_breite.value),
        ]

        # predict gibt die Antwort, predict_proba die Sicherheit je
        # Sorte. Beide erwarten eine Liste von Früchten, deshalb die
        # doppelte Klammer.
        antwort = self.wald.predict([frucht])[0]
        anteile = self.wald.predict_proba([frucht])[0]
        sicherheit = max(anteile)

        self.l_antwort.caption = f"Das ist:  {antwort}\nSicherheit: {prozent(sicherheit)}"

        # Aus den Anteilen wird wieder die Anzahl der Bäume: "59 von
        # 100" sagt mehr darüber, wie die Antwort zustande kommt, als
        # "59 %".
        stimmen = ", ".join(
            f"{sorte} {round(anteil * self.wald.n_estimators)}"
            for sorte, anteil in zip(self.wald.classes_, anteile, strict=True)
        )
        self.l_erklaerung.caption = (
            f"So haben die {self.wald.n_estimators} Entscheidungsbäume "
            f"entschieden: {stimmen}.\n"
            "Probiere eine Frucht aus, die es so nicht gibt - etwa 300 g schwer, "
            "250 mm lang und 30 mm breit. Auch dann kommt eine Antwort heraus, "
            "und zwar die ähnlichste Sorte: ein Modell sagt nie „kenne ich "
            "nicht“, es sagt immer etwas."
        )
