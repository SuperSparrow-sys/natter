# Stufe 7 von 9 - echte Daten aus einer Datei.
#
# Neu gegenüber Stufe 6:
#   csv            liest Tabellen, die aus Excel oder dem Netz kommen
#   Trennzeichen   deutsche Dateien nutzen ; und Komma statt , und Punkt
#   Auswerten      Mittelwert, Größtes, Kleinstes über eine Spalte
#   Chart          dieselben Zahlen als Kurve statt als Tabelle
#   Schreiben      das Ergebnis landet wieder in einer CSV
#
# CSV ist das Format, in dem draußen die meisten Daten liegen:
# Wetterdienst, Statistisches Bundesamt, jede Tabellenkalkulation.
# Wer es lesen kann, kann mit echten Daten arbeiten.

import csv
from pathlib import Path

from pcl import open_dialog, show_message
from u_main_design import Form1Design

DATEN = Path(__file__).parent / "daten" / "wetter.csv"
SPALTEN = ("Monat", "Temperatur", "Niederschlag")


def zahl(text: str) -> float:
    """Macht aus deutschem Zahlentext eine Zahl: "2,4" -> 2.4."""
    return float(text.replace(",", "."))


def text(wert: float, stellen: int = 1) -> str:
    """Und zurück: 2.4 -> "2,4". Die Gegenrichtung zu `zahl`."""
    return f"{wert:.{stellen}f}".replace(".", ",")


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.zeilen: list[dict[str, str]] = []
        self.datei_lesen(DATEN)

    # -- Lesen -----------------------------------------------------

    def datei_lesen(self, pfad: Path) -> None:
        """Liest die CSV in `self.zeilen`.

        `DictReader` gibt jede Zeile als Wörterbuch zurück - man
        schreibt dann `zeile["Temperatur"]` statt `zeile[2]` und muss
        beim Umsortieren der Spalten nichts ändern.
        """
        if not pfad.is_file():
            show_message(f"Die Datei {pfad.name} gibt es nicht.")
            return

        # encoding und delimiter gehören beide dazu: eine deutsche CSV
        # aus Excel ist meist Semikolon-getrennt.
        with pfad.open(encoding="utf-8", newline="") as datei:
            self.zeilen = list(csv.DictReader(datei, delimiter=";"))

        if not self.zeilen:
            show_message("Die Datei enthält keine Daten.")
            return

        orte = sorted({zeile["Ort"] for zeile in self.zeilen})
        self.cb_ort.items = orte
        self.cb_ort.item_index = 0  # löst cb_ort_change aus

    def zeilen_fuer_ort(self) -> list[dict[str, str]]:
        ort = self.cb_ort.text
        return [zeile for zeile in self.zeilen if zeile["Ort"] == ort]

    # -- Anzeigen --------------------------------------------------

    def cb_ort_change(self, sender) -> None:
        daten = self.zeilen_fuer_ort()
        if not daten:
            return

        self.tabelle_fuellen(daten)
        self.diagramm_zeichnen(daten)
        self.auswerten(daten)

    def tabelle_fuellen(self, daten: list[dict[str, str]]) -> None:
        self.sg_tabelle.row_count = len(daten) + 1
        for spalte, titel in enumerate(SPALTEN):
            self.sg_tabelle.cells[spalte, 0] = titel

        for zeile_nr, zeile in enumerate(daten, start=1):
            for spalte, titel in enumerate(SPALTEN):
                self.sg_tabelle.cells[spalte, zeile_nr] = zeile[titel]

    def diagramm_zeichnen(self, daten: list[dict[str, str]]) -> None:
        self.ch_verlauf.clear()
        self.ch_verlauf.add_line_series(
            [zeile["Monat"][:3] for zeile in daten],
            [zahl(zeile["Temperatur"]) for zeile in daten],
            title=self.cb_ort.text,
        )

    def auswerten(self, daten: list[dict[str, str]]) -> None:
        """Mittelwert, wärmster und kältester Monat."""
        temperaturen = [zahl(zeile["Temperatur"]) for zeile in daten]
        mittel = sum(temperaturen) / len(temperaturen)

        # max() mit key: das Größte nach einem selbst gewählten Maßstab -
        # hier die Temperatur, zurück kommt aber die ganze Zeile.
        waermster = max(daten, key=lambda zeile: zahl(zeile["Temperatur"]))
        kaeltester = min(daten, key=lambda zeile: zahl(zeile["Temperatur"]))
        regen = sum(zahl(zeile["Niederschlag"]) for zeile in daten)

        self.l_ergebnis.caption = (
            f"{self.cb_ort.text}:  Mittelwert {text(mittel)} °C   |   "
            f"wärmster Monat {waermster['Monat']} ({waermster['Temperatur']} °C)   |   "
            f"kältester Monat {kaeltester['Monat']} ({kaeltester['Temperatur']} °C)   |   "
            f"Niederschlag im Jahr {text(regen, 0)} mm"
        )

    # -- Knöpfe ----------------------------------------------------

    def b_laden_click(self, sender) -> None:
        pfad = open_dialog("CSV-Datei wählen", "Tabellen (*.csv);;Alle Dateien (*.*)")
        if pfad:
            self.datei_lesen(Path(pfad))

    def b_speichern_click(self, sender) -> None:
        """Schreibt die Auswertung aller Orte als neue CSV.

        Lesen und Schreiben sind fast dasselbe - nur `DictWriter`
        statt `DictReader`.
        """
        ziel = Path(__file__).parent / "auswertung.csv"
        orte = sorted({zeile["Ort"] for zeile in self.zeilen})

        with ziel.open("w", encoding="utf-8", newline="") as datei:
            schreiber = csv.DictWriter(
                datei, fieldnames=["Ort", "Mittelwert", "Niederschlag"], delimiter=";"
            )
            schreiber.writeheader()
            for ort in orte:
                werte = [zeile for zeile in self.zeilen if zeile["Ort"] == ort]
                temperaturen = [zahl(zeile["Temperatur"]) for zeile in werte]
                schreiber.writerow(
                    {
                        "Ort": ort,
                        "Mittelwert": text(sum(temperaturen) / len(temperaturen)),
                        "Niederschlag": text(
                            sum(zahl(z["Niederschlag"]) for z in werte), 0
                        ),
                    }
                )

        show_message(f"Gespeichert als {ziel.name}.")
