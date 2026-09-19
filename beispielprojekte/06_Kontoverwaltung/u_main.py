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
# Die Datenbank-Komponenten liegen nicht auf dem Formular, sondern
# werden hier erzeugt - sie haben nichts anzuzeigen.

from pathlib import Path

from pcl import SQLite3Connection, SQLQuery, SQLTransaction
from u_konto import Konto, NichtGenugGeld
from u_main_design import Form1Design

# Die Datenbankdatei liegt neben dem Programm.
DATENBANK = Path(__file__).parent / "konten.sqlite"

SPALTEN = ("Nr.", "Inhaber", "Kontostand")


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.verbindung = SQLite3Connection()
        self.verbindung.database_name = str(DATENBANK)
        self.verbindung.connected = True

        self.transaktion = SQLTransaction(self.verbindung)
        self.abfrage = SQLQuery(self.verbindung)

        self.tabelle_anlegen()
        self.konten_zeigen()

    # -- Datenbank -------------------------------------------------

    def tabelle_anlegen(self) -> None:
        """Legt die Tabelle an, falls es sie noch nicht gibt.

        `IF NOT EXISTS` heißt: beim zweiten Start passiert hier nichts -
        die Daten von gestern bleiben stehen.
        """
        self.abfrage.sql = """
            CREATE TABLE IF NOT EXISTS konto (
                nummer  INTEGER PRIMARY KEY AUTOINCREMENT,
                inhaber TEXT    NOT NULL,
                stand   REAL    NOT NULL DEFAULT 0
            )
        """
        self.abfrage.exec_sql()
        self.transaktion.commit()

    def konten_lesen(self, mindestens: float = 0.0) -> list[Konto]:
        """Holt die Konten aus der Datenbank und macht `Konto`-Objekte
        daraus.

        `:mindestens` ist ein **Parameter**. Den Wert in den Text zu
        kleben wäre die berühmteste Sicherheitslücke überhaupt: wer
        statt einer Zahl `0 OR 1=1; DROP TABLE konto` einträgt, löscht
        sonst die Tabelle.
        """
        self.abfrage.sql = (
            "SELECT nummer, inhaber, stand FROM konto "
            "WHERE stand >= :mindestens ORDER BY nummer"
        )
        self.abfrage.params = {"mindestens": mindestens}
        self.abfrage.open()

        konten = []
        while not self.abfrage.eof:
            konten.append(
                Konto(
                    self.abfrage.field_by_name("nummer").as_integer,
                    self.abfrage.field_by_name("inhaber").as_string,
                    self.abfrage.field_by_name("stand").as_float,
                )
            )
            self.abfrage.next()
        self.abfrage.close()
        return konten

    def stand_schreiben(self, konto: Konto) -> None:
        self.abfrage.sql = "UPDATE konto SET stand = :stand WHERE nummer = :nummer"
        self.abfrage.params = {"stand": konto.stand, "nummer": konto.nummer}
        self.abfrage.exec_sql()
        self.transaktion.commit()

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

        self.l_meldung.caption = f"{len(konten)} Konten."

    def konto_holen(self) -> Konto | None:
        """Das Konto zur eingetippten Nummer, oder None mit Meldung."""
        if not self.e_nummer.text.strip().isdigit():
            self.l_meldung.caption = "Bitte eine Kontonummer eintragen."
            return None

        nummer = int(self.e_nummer.text)
        for konto in self.konten_lesen():
            if konto.nummer == nummer:
                return konto

        self.l_meldung.caption = f"Es gibt kein Konto mit der Nummer {nummer}."
        return None

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

        self.abfrage.sql = "INSERT INTO konto (inhaber, stand) VALUES (:inhaber, 0)"
        self.abfrage.params = {"inhaber": inhaber}
        self.abfrage.exec_sql()
        self.transaktion.commit()

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
