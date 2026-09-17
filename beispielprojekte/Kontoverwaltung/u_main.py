"""Kontoverwaltung (M5, Schritt 9 - Abnahme): erweitert
`referenz/lazarus/n_konto` um echte SQLite-Persistenz (Abschnitt 10) -
Konten werden in `konten.sqlite` gespeichert statt nur im Speicher zu
leben wie im Original.

Kein `u_main_design.py`: `DBGrid`/`DBEdit`/`DBNavigator` brauchen eine
`DataSource` beim Erzeugen (Abschnitt 10.1), was der `.pfm`-Generator aus
M3 bisher nicht unterstützt (siehe docs/arbeitspakete/M5.md, Schritt 5,
„Zurückgestellt“: Designzeit-Aktivierung nicht-visueller SQLdb-
Komponenten fehlt noch) - die Oberfläche wird deshalb hier von Hand in
`create_components()` aufgebaut, wie bei den allerersten Übungsprojekten
vor Einführung des Designers.

Einzahlen/Abheben nutzen absichtlich direktes SQL (Abschnitt 10.1:
`self.query.sql = ...` / `exec_sql()`) statt der reinen `Konto`-Klasse
aus `u_konto.py` - die Geschäftsregel „nicht genug Geld“ bleibt aber
dieselbe (siehe `Konto.abheben`).
"""

from __future__ import annotations

from pcl import (
    Button,
    DataSource,
    DBEdit,
    DBGrid,
    DBNavigator,
    Edit,
    Form,
    Label,
    SQLite3Connection,
    SQLQuery,
    SQLTransaction,
    input_box,
)


class Form1(Form):
    caption = "Kontoverwaltung"
    width = 660
    height = 400

    def create_components(self) -> None:
        self.verbindung = SQLite3Connection()
        self.verbindung.database_name = "konten.sqlite"
        self.verbindung.connected = True
        self.transaktion = SQLTransaction(self.verbindung)
        self._tabelle_vorbereiten()

        self.abfrage = SQLQuery(self.verbindung)
        self.abfrage.sql = "SELECT kontonr, besitzer, kontostand FROM konten ORDER BY kontonr"
        self.abfrage.open()
        self.ds_konten = DataSource(self.abfrage)

        self.l_titel = Label(self)
        self.l_titel.caption = "Kontoverwaltung"
        self.l_titel.left = 16
        self.l_titel.top = 12
        self.l_titel.width = 200

        self.dbg_konten = DBGrid(self, self.ds_konten)
        self.dbg_konten.left = 16
        self.dbg_konten.top = 44
        self.dbg_konten.width = 620
        self.dbg_konten.height = 140

        self.dbn_konten = DBNavigator(self, self.ds_konten)
        self.dbn_konten.left = 16
        self.dbn_konten.top = 192
        self.dbn_konten.width = 620
        self.dbn_konten.height = 28
        self.dbn_konten.on_insert = self.dbn_konten_on_insert
        self.dbn_konten.on_delete = self.dbn_konten_on_delete
        self.dbn_konten.on_save = self.dbn_konten_on_save

        self.l_besitzer = Label(self)
        self.l_besitzer.caption = "Besitzer:"
        self.l_besitzer.left = 16
        self.l_besitzer.top = 236
        self.l_besitzer.width = 80

        self.dbe_besitzer = DBEdit(self, self.ds_konten)
        self.dbe_besitzer.field = "besitzer"
        self.dbe_besitzer.left = 100
        self.dbe_besitzer.top = 232
        self.dbe_besitzer.width = 200

        self.l_betrag = Label(self)
        self.l_betrag.caption = "Betrag:"
        self.l_betrag.left = 16
        self.l_betrag.top = 276
        self.l_betrag.width = 80

        self.e_betrag = Edit(self)
        self.e_betrag.left = 100
        self.e_betrag.top = 272
        self.e_betrag.width = 100
        self.e_betrag.text = "0"

        self.b_einzahlen = Button(self)
        self.b_einzahlen.caption = "Einzahlen"
        self.b_einzahlen.left = 210
        self.b_einzahlen.top = 272
        self.b_einzahlen.width = 90
        self.b_einzahlen.on_click = self.b_einzahlen_click

        self.b_abheben = Button(self)
        self.b_abheben.caption = "Abheben"
        self.b_abheben.left = 310
        self.b_abheben.top = 272
        self.b_abheben.width = 90
        self.b_abheben.on_click = self.b_abheben_click

        self.l_meldung = Label(self)
        self.l_meldung.caption = ""
        self.l_meldung.left = 16
        self.l_meldung.top = 316
        self.l_meldung.width = 480

    def _tabelle_vorbereiten(self) -> None:
        anlegen = SQLQuery(self.verbindung)
        anlegen.sql = (
            "CREATE TABLE IF NOT EXISTS konten ("
            "kontonr TEXT PRIMARY KEY, besitzer TEXT, kontostand REAL)"
        )
        anlegen.exec_sql()

        pruefen = SQLQuery(self.verbindung)
        pruefen.sql = "SELECT COUNT(*) AS anzahl FROM konten"
        pruefen.open()
        if pruefen.field_by_name("anzahl").as_integer == 0:
            for kontonr, besitzer, kontostand in (
                ("1001", "Anna Beispiel", 500.0),
                ("1002", "Bo Beispiel", 250.0),
            ):
                einfuegen = SQLQuery(self.verbindung)
                einfuegen.sql = (
                    "INSERT INTO konten (kontonr, besitzer, kontostand) "
                    "VALUES (:kontonr, :besitzer, :kontostand)"
                )
                einfuegen.params["kontonr"] = kontonr
                einfuegen.params["besitzer"] = besitzer
                einfuegen.params["kontostand"] = kontostand
                einfuegen.exec_sql()
        self.transaktion.commit()

    def _betrag_lesen(self) -> float | None:
        try:
            return float(self.e_betrag.text.replace(",", "."))
        except ValueError:
            self.l_meldung.caption = "Ungültiger Betrag."
            return None

    def _aktuelles_konto_neu_laden(self, kontonr: str) -> None:
        self.abfrage.open()
        while not self.abfrage.eof:
            if self.abfrage.field_by_name("kontonr").as_string == kontonr:
                break
            self.abfrage.next()
        self.ds_konten.aktualisieren()

    def b_einzahlen_click(self, sender) -> None:
        if self.abfrage.eof:
            self.l_meldung.caption = "Kein Konto ausgewählt."
            return
        betrag = self._betrag_lesen()
        if betrag is None:
            return
        kontonr = self.abfrage.field_by_name("kontonr").as_string
        aendern = SQLQuery(self.verbindung)
        aendern.sql = "UPDATE konten SET kontostand = kontostand + :betrag WHERE kontonr = :kontonr"
        aendern.params["betrag"] = betrag
        aendern.params["kontonr"] = kontonr
        aendern.exec_sql()
        self.transaktion.commit()
        self._aktuelles_konto_neu_laden(kontonr)
        self.l_meldung.caption = ""

    def b_abheben_click(self, sender) -> None:
        if self.abfrage.eof:
            self.l_meldung.caption = "Kein Konto ausgewählt."
            return
        betrag = self._betrag_lesen()
        if betrag is None:
            return
        kontostand = self.abfrage.field_by_name("kontostand").as_float
        if betrag > kontostand:
            self.l_meldung.caption = "Nicht genügend Geld vorhanden!"
            return
        kontonr = self.abfrage.field_by_name("kontonr").as_string
        aendern = SQLQuery(self.verbindung)
        aendern.sql = "UPDATE konten SET kontostand = kontostand - :betrag WHERE kontonr = :kontonr"
        aendern.params["betrag"] = betrag
        aendern.params["kontonr"] = kontonr
        aendern.exec_sql()
        self.transaktion.commit()
        self._aktuelles_konto_neu_laden(kontonr)
        self.l_meldung.caption = ""

    def dbn_konten_on_insert(self, sender) -> None:
        """„+" im DBNavigator (Nutzer-Feedback: „Person neu anlegen"
        funktionierte nicht - `on_insert` war bisher gar nicht
        verknüpft, der Knopf tat nichts). Anders als in Lazarus erzeugt
        `DBNavigator` keinen automatischen Leerdatensatz (Abschnitt
        10.1) - die Kontonummer wird deshalb direkt erfragt und die
        neue Zeile sofort in die Datenbank geschrieben; „Speichern"
        editiert sie danach ganz normal weiter."""
        kontonr = input_box("Neues Konto", "Kontonummer:")
        if not kontonr:
            return

        pruefen = SQLQuery(self.verbindung)
        pruefen.sql = "SELECT COUNT(*) AS anzahl FROM konten WHERE kontonr = :kontonr"
        pruefen.params["kontonr"] = kontonr
        pruefen.open()
        if pruefen.field_by_name("anzahl").as_integer > 0:
            self.l_meldung.caption = f"Kontonummer {kontonr} gibt es schon."
            return

        einfuegen = SQLQuery(self.verbindung)
        einfuegen.sql = (
            "INSERT INTO konten (kontonr, besitzer, kontostand) "
            "VALUES (:kontonr, :besitzer, :kontostand)"
        )
        einfuegen.params["kontonr"] = kontonr
        einfuegen.params["besitzer"] = ""
        einfuegen.params["kontostand"] = 0.0
        einfuegen.exec_sql()
        self.transaktion.commit()
        self._aktuelles_konto_neu_laden(kontonr)
        self.l_meldung.caption = f"Konto {kontonr} angelegt."

    def dbn_konten_on_delete(self, sender) -> None:
        """„-" im DBNavigator - war wie „+" bisher unverknüpft."""
        if self.abfrage.eof:
            self.l_meldung.caption = "Kein Konto ausgewählt."
            return
        kontonr = self.abfrage.field_by_name("kontonr").as_string
        loeschen = SQLQuery(self.verbindung)
        loeschen.sql = "DELETE FROM konten WHERE kontonr = :kontonr"
        loeschen.params["kontonr"] = kontonr
        loeschen.exec_sql()
        self.transaktion.commit()
        self.abfrage.open()
        self.ds_konten.aktualisieren()
        self.l_meldung.caption = f"Konto {kontonr} gelöscht."

    def dbn_konten_on_save(self, sender) -> None:
        if self.abfrage.eof:
            return
        kontonr = self.abfrage.field_by_name("kontonr").as_string
        besitzer = self.abfrage.field_by_name("besitzer").as_string
        aendern = SQLQuery(self.verbindung)
        aendern.sql = "UPDATE konten SET besitzer = :besitzer WHERE kontonr = :kontonr"
        aendern.params["besitzer"] = besitzer
        aendern.params["kontonr"] = kontonr
        aendern.exec_sql()
        self.transaktion.commit()
        self._aktuelles_konto_neu_laden(kontonr)
        self.l_meldung.caption = "Gespeichert."
