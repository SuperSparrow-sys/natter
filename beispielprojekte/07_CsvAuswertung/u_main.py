# Stufe 7 von 11 - echte Daten aus einer Datei.
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

from pcl import open_dialog, show_message, text, zahl
from u_main_design import Form1Design

DATEN = Path(__file__).parent / "daten" / "wetter.csv"
SPALTEN = ("Monat", "Temperatur", "Niederschlag")
# Ohne diese Spalten lässt sich nichts auswerten.
PFLICHT = ("Ort", *SPALTEN)


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.zeilen: list[dict[str, str]] = []
        self.sg_tabelle.col_titles = SPALTEN
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
        # aus Excel ist meist Semikolon-getrennt. Ältere Excel-Fassungen
        # speichern Umlaute nicht als UTF-8, sondern als cp1252.
        try:
            zeilen = self.zeilen_lesen(pfad, "utf-8-sig")
        except UnicodeDecodeError:
            zeilen = self.zeilen_lesen(pfad, "cp1252")

        # Eine fremde Datei kann alles enthalten. Erst prüfen, dann
        # übernehmen - sonst stünden halbe Daten in self.zeilen, und das
        # Programm bräche beim ersten fehlenden Wert ab.
        fehler = self.fehler_in(zeilen)
        if fehler:
            show_message(f"{pfad.name} lässt sich nicht auswerten: {fehler}")
            return
        self.zeilen = zeilen

        orte = sorted({zeile["Ort"] for zeile in self.zeilen})
        self.cb_ort.items = orte
        self.cb_ort.item_index = 0
        # Ausdrücklich neu anzeigen: stand vorher derselbe Ort an erster
        # Stelle, hat sich an der Auswahl nichts geändert, und
        # cb_ort_change käme nicht von allein.
        self.cb_ort_change(self.cb_ort)

    def zeilen_lesen(self, pfad: Path, zeichensatz: str) -> list[dict[str, str]]:
        with pfad.open(encoding=zeichensatz, newline="") as datei:
            return list(csv.DictReader(datei, delimiter=";"))

    def fehler_in(self, zeilen: list[dict[str, str]]) -> str:
        """Was an den Zeilen nicht stimmt, als Satz - oder "", wenn
        alles passt."""
        if not zeilen:
            return "Sie enthält keine Daten."
        fehlend = [name for name in PFLICHT if name not in zeilen[0]]
        if fehlend:
            wie = "fehlt die Spalte" if len(fehlend) == 1 else "fehlen die Spalten"
            return (
                f"Es {wie} {', '.join(fehlend)}. Gebraucht werden "
                f"{', '.join(PFLICHT)}, getrennt durch Semikolon."
            )
        for nummer, zeile in enumerate(zeilen, start=2):
            for name in ("Temperatur", "Niederschlag"):
                try:
                    zahl(zeile[name] or "")
                except ValueError:
                    return f"In Zeile {nummer} ist {name} keine Zahl."
        return ""

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
        self.sg_tabelle.row_count = len(daten)
        for zeile_nr, zeile in enumerate(daten):
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
            f"{self.cb_ort.text}:  Mittelwert {text(mittel, 1)} °C   |   "
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
        # Geschrieben wird in den Arbeitsordner, nicht neben
        # __file__: in der exportierten Exe ist das der Ordner der Exe,
        # und dort findet man die Datei auch wieder.
        ziel = Path("auswertung.csv")
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
                        "Mittelwert": text(sum(temperaturen) / len(temperaturen), 1),
                        "Niederschlag": text(
                            sum(zahl(z["Niederschlag"]) for z in werte), 0
                        ),
                    }
                )

        show_message(f"Gespeichert als {ziel.name}.")
