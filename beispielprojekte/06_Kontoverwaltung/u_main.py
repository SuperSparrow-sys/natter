# Stufe 6 von 9 - eigene Klassen und eine Datenbank.
#
# Neu gegenüber Stufe 5:
#   Klasse         u_konto.py beschreibt, was ein Konto ist und darf
#   SQLite         eine echte Datenbank in einer Datei nebenan
#   SQL            SELECT, INSERT, UPDATE - die Sprache der Datenbanken
#   Parameter      :name statt Text zusammenkleben (SQL-Injection!)
#
# Warum überhaupt eine Datenbank? Weil das Programm beim nächsten Start
# noch weiß, was gestern war. Eine Python-Liste ist nach dem Schließen
# weg.
#
# Die Datenbank liegt nicht auf dem Formular, sondern wird hier
# geöffnet - sie hat nichts anzuzeigen.

from pathlib import Path

from pcl import SQLite3Connection
from u_konto import Konto, NichtGenugGeld
from u_main_design import Form1Design

# Die Datenbankdatei liegt neben dem Programm.
DATENBANK = Path(__file__).parent / "konten.sqlite"

SPALTEN = ("Nr.", "Inhaber", "Kontostand")


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        # Eine Zeile: Datei auf, fertig. Gibt es die Datei noch nicht,
        # legt SQLite sie an.
        self.db = SQLite3Connection(DATENBANK)

        self.tabelle_anlegen()
        self.konten_zeigen()

    # -- Datenbank -------------------------------------------------

    def tabelle_anlegen(self) -> None:
        """Legt die Tabelle an, falls es sie noch nicht gibt.

        `IF NOT EXISTS` heißt: beim zweiten Start passiert hier nichts -
        die Daten von gestern bleiben stehen.
        """
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS konto (
                nummer  INTEGER PRIMARY KEY AUTOINCREMENT,
                inhaber TEXT    NOT NULL,
                stand   REAL    NOT NULL DEFAULT 0
            )
        """)

    def konten_lesen(self, mindestens: float = 0.0) -> list[Konto]:
        """Holt die Konten aus der Datenbank und macht `Konto`-Objekte
        daraus.

        `:mindestens` ist ein **Parameter**. Den Wert in den Text zu
        kleben wäre die berühmteste Sicherheitslücke überhaupt: wer
        statt einer Zahl `0 OR 1=1; DROP TABLE konto` einträgt, löscht
        sonst die Tabelle.

        `query` gibt jede Zeile als `dict` zurück - `zeile["inhaber"]`
        also, genau wie bei jedem anderen Wörterbuch.
        """
        zeilen = self.db.query(
            "SELECT nummer, inhaber, stand FROM konto "
            "WHERE stand >= :mindestens ORDER BY nummer",
            mindestens=mindestens,
        )
        return [
            Konto(zeile["nummer"], zeile["inhaber"], zeile["stand"]) for zeile in zeilen
        ]

    def stand_schreiben(self, konto: Konto) -> None:
        self.db.execute(
            "UPDATE konto SET stand = :stand WHERE nummer = :nummer",
            stand=konto.stand,
            nummer=konto.nummer,
        )

    # -- Anzeige ---------------------------------------------------

    def konten_zeigen(self, mindestens: float = 0.0) -> None:
        konten = self.konten_lesen(mindestens)

        # Eine Zeile mehr als Konten: die erste ist die Überschrift.
        self.sg_konten.row_count = len(konten) + 1
        for spalte, titel in enumerate(SPALTEN):
            self.sg_konten.cells[spalte, 0] = titel

        for zeile, konto in enumerate(konten, start=1):
            self.sg_konten.cells[0, zeile] = str(konto.nummer)
            self.sg_konten.cells[1, zeile] = konto.inhaber
            self.sg_konten.cells[2, zeile] = f"{konto.stand:.2f}"

        # "1 Konten" liest sich falsch - dieselbe Stelle, an der sich
        # der Objektinspektor mit "(1 Einträge)" blamiert hat.
        wort = "Konto" if len(konten) == 1 else "Konten"
        self.l_meldung.caption = f"{len(konten)} {wort}."

    def konto_holen(self) -> Konto | None:
        """Das Konto zur eingetippten Nummer, oder None mit Meldung."""
        if not self.e_nummer.text.strip().isdigit():
            self.l_meldung.caption = "Bitte eine Kontonummer eintragen."
            return None

        nummer = int(self.e_nummer.text)
        # `query_one` liefert die erste Zeile - oder None, wenn es keine
        # gibt. Das erspart die Schleife über alle Konten.
        zeile = self.db.query_one(
            "SELECT nummer, inhaber, stand FROM konto WHERE nummer = :nummer",
            nummer=nummer,
        )
        if zeile is None:
            self.l_meldung.caption = f"Es gibt kein Konto mit der Nummer {nummer}."
            return None
        return Konto(zeile["nummer"], zeile["inhaber"], zeile["stand"])

    def betrag_holen(self) -> float | None:
        try:
            return float(self.e_betrag.text.replace(",", "."))
        except ValueError:
            self.l_meldung.caption = "Der Betrag muss eine Zahl sein."
            return None

    # -- Knöpfe ----------------------------------------------------

    def b_anlegen_click(self, sender) -> None:
        inhaber = self.e_inhaber.text.strip()
        if not inhaber:
            self.l_meldung.caption = "Ohne Namen geht kein Konto."
            return

        self.db.execute(
            "INSERT INTO konto (inhaber, stand) VALUES (:inhaber, 0)",
            inhaber=inhaber,
        )

        self.konten_zeigen()
        self.l_meldung.caption = f"Konto für {inhaber} angelegt."

    def b_einzahlen_click(self, sender) -> None:
        konto = self.konto_holen()
        betrag = self.betrag_holen()
        if konto is None or betrag is None:
            return

        try:
            konto.einzahlen(betrag)
        except ValueError as fehler:
            self.l_meldung.caption = str(fehler)
            return

        self.stand_schreiben(konto)
        self.konten_zeigen()
        self.l_meldung.caption = f"{betrag:.2f} Euro eingezahlt."

    def b_abheben_click(self, sender) -> None:
        konto = self.konto_holen()
        betrag = self.betrag_holen()
        if konto is None or betrag is None:
            return

        # Die Regel "nicht mehr abheben als da ist" steht in der Klasse
        # Konto, nicht hier. Das Formular fragt nur, ob es geklappt hat.
        try:
            konto.abheben(betrag)
        except (ValueError, NichtGenugGeld) as fehler:
            self.l_meldung.caption = str(fehler)
            return

        self.stand_schreiben(konto)
        self.konten_zeigen()
        self.l_meldung.caption = f"{betrag:.2f} Euro abgehoben."

    def b_filtern_click(self, sender) -> None:
        try:
            grenze = float(self.e_mindestens.text.replace(",", "."))
        except ValueError:
            self.l_meldung.caption = "Die Grenze muss eine Zahl sein."
            return

        self.konten_zeigen(grenze)
