"""Fehlerkatalog: fester, von Hand gepflegter Katalog für Wo/Was/Prüfe-
Meldungen bei unbehandelten Ausnahmen (Abschnitt 8.3–8.5). Deterministisch,
keine KI – jede Meldung kommt aus einer festen Zuordnung Exception-Typ →
Erklärungstext.

„Was“ wird bewusst nie aus `traceback.format_exception_only()` gebaut,
sondern immer aus `str(exc)`/strukturierten Attributen (`exc.name`,
`exc.filename`, …) – dort hängt Python (ab 3.12) keine „Did you mean …?“-
Vorschläge an, die Abschnitt 8.4 verbietet. `SyntaxError.msg` führt
solche Vorschläge trotzdem mit sich („Maybe you meant '==' …“); sie
werden von `_vorschlaege_entfernen()` abgeschnitten.

Alles, was Python selbst formuliert, ist englisch. Seit M11
(Abschnitt 4) steht es deshalb nicht mehr unverändert im „Was“:
`_STANDARDMELDUNGEN` übersetzt die Meldungen, die im Unterricht
vorkommen, und gibt jeder ihre eigene Leitfrage. Greift keines der
Muster, steht ein deutscher Satz vorn und die englische Originalmeldung
dahinter als gekennzeichnetes Zitat – lieber ein erkennbares Zitat als
eine Meldung, der die entscheidende Einzelheit fehlt.

`Wo`/Quelltext/Karett-Markierung kommen dagegen aus
`traceback.StackSummary.format_frame_summary()` für genau den tiefsten
Frame, der zu eigenem Code gehört (nicht `pcl`/Qt/Standardbibliothek) –
das liefert die Spaltenmarkierung ab Python 3.11 automatisch korrekt
ausgerichtet, ohne sie selbst nachzubauen.
"""

from __future__ import annotations

import builtins
import importlib
import re
import string
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

from pcl.eigener_code import ist_eigener_code
from pcl.errors import NatterDatenbankError, NatterPropertyError

_STAPEL_ZEILE_MUSTER = re.compile(
    r'^  File "(?P<datei>[^"]+)", line (?P<zeile>\d+), in (?P<name>.+)$'
)


@dataclass(frozen=True)
class Fehlermeldung:
    ueberschrift: str
    wo: str
    quelltext: str | None
    markierung: str | None
    was: str
    pruefe: str

    def als_text(self) -> str:
        """Die Meldung in drei Teilen: Wo, Was, Prüfe.

        Im **Prüfungsmodus** (M11, Abschnitt 6) entfällt der Teil
        „Prüfe“. Er ist genau der, der weiterhilft – und genau deshalb
        gehört er in einer Leistungssituation nicht dazu. „Wo“ und
        „Was“ bleiben: eine Schülerin soll sehen, dass und wo etwas
        schiefgegangen ist, nur nicht, woran es liegen könnte.
        """
        from pcl.pruefungsmodus import laeuft

        zeilen = [self.ueberschrift, "", f"Wo:   {self.wo}"]
        if self.quelltext is not None:
            zeilen.append(f"          {self.quelltext}")
        if self.markierung is not None:
            zeilen.append(f"          {self.markierung}")
        zeilen.append(f"Was:  {self.was}")
        if not laeuft():
            zeilen.append(f"Prüfe: {self.pruefe}")
        return "\n".join(zeilen)


def _name_ermitteln(exc: BaseException) -> str | None:
    name = getattr(exc, "name", None)
    if name:
        return name
    treffer = re.search(r"'([^']+)'", str(exc))
    return treffer.group(1) if treffer else None


# -- Deutsche Fassung der Standardmeldungen von Python ----------------------
#
# Python formuliert seine Fehlermeldungen englisch („list index out of
# range“). Bis M11 standen sie unverändert im „Was“ – gegen AGENTS.md
# („alle sichtbaren Texte sind Deutsch“) und gegen die Zielgruppe, die
# Englisch erst lernt. `_STANDARDMELDUNGEN` übersetzt die Meldungen, die
# im Unterricht tatsächlich vorkommen, und gibt jeder ihre eigene
# Leitfrage statt der allgemeinen ihrer Fehlerklasse (M11, Abschnitt 4:
# „jede Meldung mit Lösungen“).
#
# Die Leitfrage bleibt eine Frage: der Fehlerkatalog nennt Fehlerart,
# Ort und Werte, aber nie den korrigierten Code (docs/fehlerkatalog.yaml,
# Kopf).

#: Kenntlich gemachtes Zitat für die Fälle, in denen keine Übersetzung
#: greift. Ohne diese Kennzeichnung wäre nicht zu erkennen, dass der
#: englische Rest von Python stammt und nicht von Natter.
ORIGINALMELDUNG_PRAEFIX = "Python meldet dazu wörtlich: "

#: Typnamen von Python als deutsche Nominativ-Wortgruppe. Bewusst
#: unvollständig: ein hier nicht eingetragener Typ erscheint mit seinem
#: Python-Namen in Anführungszeichen, was für seltene Typen (`Decimal`,
#: eigene Klassen) auch richtig ist.
_TYPNAMEN = {
    "int": "eine ganze Zahl",
    "float": "eine Kommazahl",
    "complex": "eine komplexe Zahl",
    "str": "ein Text",
    "bool": "ein Wahrheitswert",
    "list": "eine Liste",
    "tuple": "ein Tupel",
    "dict": "ein Wörterbuch",
    "set": "eine Menge",
    "range": "ein Zahlenbereich",
    "bytes": "eine Folge von Bytes",
    "NoneType": "None, also gar kein Wert",
    "function": "eine Funktion",
    "method": "eine Methode",
    "module": "ein Modul",
    "type": "eine Klasse",
}

#: „Did you mean …?“/„Maybe you meant …“ – Pythons Namensvorschläge, die
#: Abschnitt 8.4 verbietet. Sie kommen über `SyntaxError.msg` und
#: `str(exc)` herein, nicht nur über `format_exception_only()`.
_VORSCHLAG_MUSTER = re.compile(
    r"[.,;]?\s*(?:Did you mean|Maybe you meant|Perhaps you forgot|"
    r"Did you forget)\b.*$",
    re.IGNORECASE | re.DOTALL,
)


#: Womit Python einen fehlenden eingerückten Block einleitet
#: („expected an indented block after 'if' statement on line 3“).
_EINLEITUNGEN = {
    "'if' statement": "der if-Zeile",
    "'else' statement": "der else-Zeile",
    "'elif' statement": "der elif-Zeile",
    "'for' statement": "der for-Zeile",
    "'while' statement": "der while-Zeile",
    "'try' statement": "der try-Zeile",
    "'except' statement": "der except-Zeile",
    "'finally' statement": "der finally-Zeile",
    "'with' statement": "der with-Zeile",
    "function definition": "der Funktionsdefinition",
    "class definition": "der Klassendefinition",
}


class _Zahlwortformat(string.Formatter):
    """Format-Erweiterung für Ein- und Mehrzahl: `{anzahl:Wert|Werte}`
    setzt bei 1 den ersten, sonst den zweiten Teil ein.

    Ohne sie stand in den Meldungen die Klammerform („1 Wert(e)“) oder
    schlicht die falsche Zahlform („es fehlen 1 Angaben“). Beides liest
    sich für die Zielgruppe schlechter als ein ganzer Satz (M11,
    Abschnitt 4).
    """

    def format_field(self, wert: Any, spezifikation: str) -> str:
        if "|" in spezifikation:
            einzahl, _, mehrzahl = spezifikation.partition("|")
            return einzahl if str(wert).strip() == "1" else mehrzahl
        return format(wert, spezifikation)


_FORMAT = _Zahlwortformat()


def _typname(python_name: str) -> str:
    """Deutscher Nominativ zu einem Python-Typnamen."""
    return _TYPNAMEN.get(python_name, f"ein Objekt der Art „{python_name}“")


def _in_deutsche_anfuehrungszeichen(wert: str) -> str:
    """Python zitiert Werte mit `'…'`; in einer deutschen Meldung stehen
    sie in „…“."""
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "'\"":
        return f"„{wert[1:-1]}“"
    return wert


def _gross(wortgruppe: str) -> str:
    """Wortgruppe als Satzanfang."""
    return wortgruppe[:1].upper() + wortgruppe[1:]


def _vorschlaege_entfernen(text: str) -> str:
    return _VORSCHLAG_MUSTER.sub("", text).strip()


@dataclass(frozen=True)
class _Standardmeldung:
    """Eine Standardmeldung von Python mit ihrer deutschen Fassung.

    `was` und `pruefe` sind Vorlagen, in denen die benannten Gruppen von
    `muster` als `{gruppe}` stehen. Gruppen, deren Name mit `typ`
    beginnt, werden vorher durch `_typname()` geschickt, Gruppen mit
    `gross_` davor zusätzlich großgeschrieben.
    """

    muster: re.Pattern[str]
    was: str
    pruefe: str


def _m(muster: str, was: str, pruefe: str) -> _Standardmeldung:
    return _Standardmeldung(re.compile(muster), was, pruefe)


# Eine Zahl ist im Deutschen „der Index“; die Frage nach dem ersten Platz
# steht bewusst dabei, weil die Zählung ab 0 der häufigste Grund für
# diesen Fehler im ersten Lernjahr ist.
_SAMMLUNG_AUF_DEUTSCH = {
    "list": "der Liste",
    "string": "des Textes",
    "tuple": "des Tupels",
    "bytearray": "der Bytefolge",
    "bytes": "der Bytefolge",
}

_STANDARDMELDUNGEN: tuple[_Standardmeldung, ...] = (
    # -- IndexError --------------------------------------------------------
    _m(
        r"^(?P<sammlung>list|string|tuple|bytearray|bytes) index out of range$",
        "Es wurde ein Platz angesprochen, den es innerhalb {sammlung} nicht gibt.",
        "Wie viele Einträge hat die Sammlung an dieser Stelle wirklich? Der erste "
        "Platz trägt die Nummer 0, der letzte also eine weniger als die Anzahl.",
    ),
    _m(
        r"^list assignment index out of range$",
        "Es sollte auf einen Platz geschrieben werden, den es in der Liste noch nicht gibt.",
        "Wie lang ist die Liste zu diesem Zeitpunkt? Muss der Eintrag angehängt "
        "werden, statt einen vorhandenen zu überschreiben?",
    ),
    _m(
        r"^pop from empty (?P<sammlung>list|set)$",
        "Aus einer leeren Sammlung sollte ein Eintrag entnommen werden.",
        "Wird vorher geprüft, ob überhaupt noch etwas darin ist?",
    ),
    # -- TypeError ---------------------------------------------------------
    _m(
        r"^unsupported operand type\(s\) for (?P<zeichen>.+?): "
        r"'(?P<typ_links>.+?)' and '(?P<typ_rechts>.+?)'$",
        "Die Rechenart „{zeichen}“ ist zwischen diesen beiden Werten nicht "
        "möglich: links steht {typ_links}, rechts {typ_rechts}.",
        "Soll hier gerechnet oder sollen Texte aneinandergehängt werden? Welcher "
        "der beiden Werte müsste dafür in die Art des anderen umgewandelt werden?",
    ),
    _m(
        r"^can only concatenate (?P<typ_links>\w+) \(not \"(?P<typ_rechts>\w+)\"\) "
        r"to \w+$",
        "An einen Text lässt sich nur wieder ein Text anhängen, hier kam aber {typ_rechts} dazu.",
        "Soll der Wert als Text erscheinen oder soll gerechnet werden?",
    ),
    _m(
        r"^'(?P<typ>.+?)' object is not subscriptable$",
        "Hier steht {typ}; mit eckigen Klammern lassen sich nur Sammlungen wie "
        "Listen, Texte und Wörterbücher ansprechen.",
        "Welchen Wert trägt der Name an dieser Stelle wirklich? Ist versehentlich "
        "ein Komma verlorengegangen?",
    ),
    _m(
        r"^'(?P<typ>.+?)' object is not callable$",
        "Hier steht {typ}; mit runden Klammern dahinter lassen sich nur "
        "Funktionen und Methoden aufrufen.",
        "Wird hier wirklich eine Funktion angesprochen? Trägt eine Variable "
        "denselben Namen wie eine Funktion?",
    ),
    _m(
        r"^'(?P<typ>.+?)' object is not iterable$",
        "Über {typ} lässt sich nicht Stück für Stück laufen.",
        "Was soll die Schleife durchlaufen – eine Liste, einen Text oder einen Zahlenbereich?",
    ),
    _m(
        r"^cannot unpack non-iterable (?P<typ>.+?) object$",
        "{gross_typ} lässt sich nicht auf mehrere Namen verteilen.",
        "Wie viele Werte liefert die rechte Seite wirklich?",
    ),
    _m(
        r"^object of type '(?P<typ>.+?)' has no len\(\)$",
        "{gross_typ} hat keine Länge.",
        "Soll die Länge einer Liste oder eines Textes bestimmt werden – und "
        "steht in der Variablen wirklich eine solche Sammlung?",
    ),
    _m(
        r"^'(?P<zeichen>.+?)' not supported between instances of "
        r"'(?P<typ_links>.+?)' and '(?P<typ_rechts>.+?)'$",
        "Ein Vergleich mit „{zeichen}“ ist hier nicht möglich: links steht "
        "{typ_links}, rechts {typ_rechts}.",
        "Sollen zwei Zahlen verglichen werden? Liefert ein Eingabefeld seinen "
        "Inhalt vielleicht als Text?",
    ),
    _m(
        r"^(?P<funktion>[\w.]+)\(\) missing (?P<anzahl>\d+) required positional "
        r"arguments?: (?P<namen>.+)$",
        "Beim Aufruf von {funktion}() {anzahl:fehlt|fehlen} {anzahl} "
        "{anzahl:Angabe|Angaben}: {namen}.",
        "Welche Werte erwartet {funktion}() laut ihrer Definition, und welche "
        "davon stehen im Aufruf schon?",
    ),
    _m(
        r"^(?P<funktion>[\w.]+)\(\) takes (?:from \d+ to )?(?P<erwartet>\d+) "
        r"positional arguments? but (?P<uebergeben>\d+) (?:was|were) given$",
        "{funktion}() nimmt {erwartet} {erwartet:Angabe|Angaben} entgegen, "
        "übergeben {uebergeben:wurde|wurden} {uebergeben}.",
        "Wurde die Methode über das Objekt aufgerufen (dann zählt `self` nicht "
        "mit) oder über die Klasse? Passt die Zahl der Werte zur Definition?",
    ),
    _m(
        r"^(?P<funktion>[\w.]+)\(\) got an unexpected keyword argument "
        r"'(?P<name>.+?)'$",
        "{funktion}() kennt keine Angabe namens „{name}“.",
        "Wie heißen die Parameter in der Definition von {funktion}() wirklich?",
    ),
    _m(
        r"^'(?P<typ>.+?)' object does not support item assignment$",
        "In {typ} lässt sich kein einzelner Platz überschreiben.",
        "Texte und Tupel bleiben, wie sie sind – soll stattdessen ein neuer Wert entstehen?",
    ),
    _m(
        r"^(?P<typ>\w+) indices must be integers.*$",
        "Der Platz in einer Sammlung wird über eine ganze Zahl angesprochen.",
        "Welchen Typ hat der Ausdruck in den eckigen Klammern? Steht dort "
        "vielleicht ein Text aus einem Eingabefeld?",
    ),
    _m(
        r"^unhashable type: '(?P<typ>.+?)'$",
        "{gross_typ} kann nicht als Schlüssel eines Wörterbuchs oder als Eintrag "
        "einer Menge dienen.",
        "Welcher Wert soll hier der Schlüssel sein? Schlüssel müssen unveränderlich sein.",
    ),
    _m(
        r"^can't multiply sequence by non-int of type '(?P<typ>.+?)'$",
        "Ein Text oder eine Liste lässt sich nur mit einer ganzen Zahl "
        "vervielfachen, hier stand {typ} daneben.",
        "Soll wirklich vervielfacht werden, oder sollten zwei Zahlen multipliziert werden?",
    ),
    # -- ValueError --------------------------------------------------------
    _m(
        r"^invalid literal for int\(\) with base \d+: (?P<wert>.+)$",
        "Der Text {wert} lässt sich nicht als ganze Zahl lesen.",
        "Steht in dem Text wirklich nur eine ganze Zahl – ohne Leerzeichen, "
        "Einheit oder Nachkommastelle?",
    ),
    _m(
        r"^could not convert string to float: (?P<wert>.+)$",
        "Der Text {wert} lässt sich nicht als Kommazahl lesen.",
        "Python schreibt Kommazahlen mit einem Dezimalpunkt statt eines "
        "Dezimalkommas – ist das hier der Fall? Stehen noch Leerzeichen oder "
        "eine Einheit im Text?",
    ),
    _m(
        r"^not enough values to unpack \(expected (?P<erwartet>\d+), "
        r"got (?P<erhalten>\d+)\)$",
        "Links vom Gleichheitszeichen stehen {erwartet} Namen, rechts "
        "{erhalten:kommt|kommen} aber nur {erhalten} {erhalten:Wert|Werte} an.",
        "Wie viele Werte liefert die rechte Seite an dieser Stelle wirklich?",
    ),
    _m(
        r"^too many values to unpack \(expected (?P<erwartet>\d+)\)$",
        "Links vom Gleichheitszeichen stehen {erwartet} Namen, rechts kommen mehr Werte an.",
        "Wie viele Werte liefert die rechte Seite an dieser Stelle wirklich?",
    ),
    _m(
        r"^list\.remove\(x\): x not in list$",
        "Der Wert, der entfernt werden sollte, kommt in der Liste nicht vor.",
        "Steht der gesuchte Wert wirklich in der Liste – und in derselben Schreibweise?",
    ),
    _m(
        r"^substring not found$",
        "Der gesuchte Textteil kommt in der Zeichenkette nicht vor.",
        "Stimmen Schreibweise und Groß-/Kleinschreibung des gesuchten Textes?",
    ),
    _m(
        r"^(?P<wert>.+) is not in list$",
        "{wert} kommt in der Liste nicht vor.",
        "Steht der gesuchte Wert wirklich in der Liste – und in derselben Schreibweise?",
    ),
    _m(
        r"^math domain error$",
        "Die Rechnung ist für diesen Wert nicht festgelegt – etwa die Wurzel "
        "oder der Logarithmus einer negativen Zahl.",
        "Welchen Wert hat der Ausdruck unter der Wurzel bzw. im Logarithmus "
        "hier? Wird der Fall vorher abgefangen?",
    ),
    _m(
        r"^time data (?P<wert>.+?) does not match format (?P<format>.+?)$",
        "Die Zeitangabe {wert} passt nicht zum angegebenen Muster {format}.",
        "In welcher Reihenfolge stehen Tag, Monat und Jahr im Text, und welche "
        "Trennzeichen benutzt er?",
    ),
    # -- SyntaxError -------------------------------------------------------
    _m(
        r"^expected ':'$",
        "Am Ende dieser Zeile fehlt der Doppelpunkt.",
        "Jede Zeile, die einen Block eröffnet (if, else, while, for, def, "
        "class), endet mit einem Doppelpunkt – ist er hier gesetzt?",
    ),
    _m(
        r"^invalid syntax$",
        "Python kann diese Zeile nicht lesen.",
        "Fehlt ein Doppelpunkt, eine Klammer oder ein Anführungszeichen? Steht "
        "der Fehler vielleicht schon in der Zeile darüber?",
    ),
    _m(
        r"^unterminated string literal.*$",
        "Ein Text wurde geöffnet, aber in derselben Zeile nicht wieder geschlossen.",
        "Stehen am Anfang und am Ende des Textes dieselben Anführungszeichen?",
    ),
    _m(
        r"^unterminated triple-quoted string literal.*$",
        "Ein mehrzeiliger Text wurde geöffnet und nie wieder geschlossen.",
        "Wo sollte der Text enden, und stehen dort dieselben drei Anführungszeichen wie am Anfang?",
    ),
    _m(
        r"^'(?P<klammer>.)' was never closed$",
        "Die Klammer „{klammer}“ wurde geöffnet und nie wieder geschlossen.",
        "Gehört zu jeder öffnenden Klammer eine schließende? Der Fehler wird "
        "erst dort gemeldet, wo Python nicht weiterkommt.",
    ),
    _m(
        r"^unmatched '(?P<klammer>.)'$",
        "Die Klammer „{klammer}“ schließt etwas, das nie geöffnet wurde.",
        "Steht eine Klammer zu viel da, oder fehlt die zugehörige öffnende?",
    ),
    _m(
        r"^closing parenthesis '(?P<zu>.)' does not match opening parenthesis "
        r"'(?P<auf>.)'.*$",
        "Geschlossen wurde mit „{zu}“, geöffnet wurde aber mit „{auf}“.",
        "Welche Klammernart gehört hier zusammen?",
    ),
    _m(
        r"^cannot assign to .*$",
        "Links vom Gleichheitszeichen steht etwas, dem sich kein Wert zuweisen lässt.",
        "Sollte hier ein Wert zugewiesen oder zwei Werte verglichen werden? "
        "Zuweisung und Vergleich sind in Python zwei verschiedene Zeichen.",
    ),
    _m(
        r"^expected an indented block after (?P<einleitung>.+?) "
        r"on line (?P<zeile>\d+)$",
        "Nach {einleitung} (Zeile {zeile}) muss der zugehörige Block eingerückt "
        "sein; hier steht nichts Eingerücktes.",
        "Ist die Zeile darunter eingerückt? Python nutzt die Einrückung anstelle von begin/end.",
    ),
    _m(
        r"^unexpected indent$",
        "Diese Zeile ist eingerückt, obwohl davor kein Block eröffnet wurde.",
        "Gehört die Zeile wirklich in einen Block, und endet die Zeile darüber "
        "mit einem Doppelpunkt?",
    ),
    _m(
        r"^unindent does not match any outer indentation level$",
        "Die Einrückung dieser Zeile passt zu keiner der Ebenen darüber.",
        "Sind alle Zeilen des Blocks gleich weit eingerückt? Ein gemischter "
        "Gebrauch von Leerzeichen und Tabulatoren sieht im Editor gleich aus – "
        "„Ansicht → Leerzeichen anzeigen“ macht den Unterschied sichtbar.",
    ),
    # Die Meldung zu `TabError`. Ohne eigenen Eintrag fiel sie auf den
    # allgemeinen Text der Syntaxfehler zurück, der die Ursache gar nicht
    # nennt - dabei ist sie die eine, die man im Editor nicht sehen kann
    # (M12). Der Hinweis zeigt auf die Ansicht, die Natter seit M11 dafür
    # hat.
    _m(
        r"^inconsistent use of tabs and spaces in indentation$",
        "In der Einrückung sind Leerzeichen und Tabulatoren gemischt.",
        "Wird in dieser Datei überall mit Leerzeichen eingerückt – oder überall "
        "mit Tabulatoren? Beides sieht im Editor gleich aus; „Ansicht → "
        "Leerzeichen anzeigen“ macht den Unterschied sichtbar.",
    ),
    _m(
        r"^expected an indented block$",
        "Hier fehlt der eingerückte Block.",
        "Ist die Zeile darunter eingerückt? Python nutzt die Einrückung anstelle von begin/end.",
    ),
    _m(
        r"^invalid decimal literal$",
        "Eine Zahl steht hier in einer Form, die Python nicht lesen kann.",
        "Beginnt ein Name mit einer Ziffer? Steht in einer Zahl ein Komma statt eines Punktes?",
    ),
    _m(
        r"^leading zeros in decimal integer literals are not permitted.*$",
        "Eine ganze Zahl darf nicht mit einer 0 beginnen.",
        "Soll die führende Null nur der Darstellung dienen? Dann gehört die Zahl in einen Text.",
    ),
    _m(
        r"^Missing parentheses in call to '(?P<funktion>\w+)'.*$",
        "Beim Aufruf von {funktion} fehlen die runden Klammern.",
        "In Python steht hinter jedem Funktionsaufruf ein Klammerpaar, auch "
        "bei einer Ausgabe – ist es hier gesetzt?",
    ),
    # -- json.JSONDecodeError, eine Unterklasse von ValueError -------------
    _m(
        r"^Expecting value: line (?P<zeile>\d+) column (?P<spalte>\d+).*$",
        "In Zeile {zeile}, Spalte {spalte} wurde ein Wert erwartet; dort steht kein gültiges JSON.",
        "Ist die Datei wirklich im JSON-Format, und ist sie vollständig?",
    ),
    _m(
        r"^Expecting ',' delimiter: line (?P<zeile>\d+) column (?P<spalte>\d+).*$",
        "In Zeile {zeile}, Spalte {spalte} fehlt ein Komma zwischen zwei Einträgen.",
        "Steht zwischen allen Einträgen ein Komma – und hinter dem letzten keines?",
    ),
    _m(
        r"^Expecting property name enclosed in double quotes: "
        r"line (?P<zeile>\d+) column (?P<spalte>\d+).*$",
        "In Zeile {zeile}, Spalte {spalte} wurde ein Schlüsselname in doppelten "
        "Anführungszeichen erwartet.",
        "Stehen alle Schlüssel in doppelten Anführungszeichen? JSON kennt keine einfachen.",
    ),
    _m(
        r"^Unterminated string starting at: line (?P<zeile>\d+) "
        r"column (?P<spalte>\d+).*$",
        "Der Text, der in Zeile {zeile}, Spalte {spalte} beginnt, wurde nie geschlossen.",
        "Steht am Ende des Textes wieder ein doppeltes Anführungszeichen?",
    ),
    _m(
        r"^Extra data: line (?P<zeile>\d+) column (?P<spalte>\d+).*$",
        "Ab Zeile {zeile}, Spalte {spalte} steht noch etwas hinter dem Ende der JSON-Daten.",
        "Enthält die Datei mehr als ein JSON-Objekt hintereinander?",
    ),
    _m(
        r"^invalid character '(?P<zeichen>.)' \(U\+[0-9A-Fa-f]+\)$",
        "Das Zeichen „{zeichen}“ gehört nicht zu Python.",
        "Wurde die Zeile aus einem Textprogramm oder einer Webseite kopiert? "
        "Dabei geraten leicht typografische Anführungszeichen oder ein "
        "geschütztes Leerzeichen mit hinein.",
    ),
    _m(
        r"^EOL while scanning string literal$",
        "Ein Text wurde geöffnet, aber in derselben Zeile nicht wieder geschlossen.",
        "Stehen am Anfang und am Ende des Textes dieselben Anführungszeichen?",
    ),
)


#: Meldungen der Datenbanktreiber (sqlite3, MySQL). `pcl` reicht sie in
#: `NatterDatenbankError` unverändert durch – dort sind sie englisch und
#: stammen aus einer Bibliothek, die Schülerinnen und Schüler nicht
#: kennen müssen (Abschnitt 8.5). Ersetzt wird nur der Treiberteil, der
#: deutsche Satz von `pcl` davor bleibt stehen.
_DATENBANKMELDUNGEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"no such table:\s*(?P<name>\S+)"),
        "eine Tabelle namens „{name}“ gibt es in der Datenbank nicht",
    ),
    (
        re.compile(r"no such column:\s*(?P<name>\S+)"),
        "eine Spalte namens „{name}“ gibt es in der Datenbank nicht",
    ),
    (
        re.compile(r"table\s+(?P<tabelle>\S+)\s+has no column named\s+(?P<spalte>\S+)"),
        "die Tabelle „{tabelle}“ hat keine Spalte „{spalte}“",
    ),
    (
        re.compile(r"UNIQUE constraint failed:\s*(?P<feld>\S+)"),
        "der Wert für „{feld}“ kommt schon einmal vor, muss dort aber eindeutig sein",
    ),
    (
        re.compile(r"NOT NULL constraint failed:\s*(?P<feld>\S+)"),
        "für „{feld}“ muss ein Wert angegeben werden",
    ),
    (
        re.compile(r"FOREIGN KEY constraint failed"),
        "der verknüpfte Datensatz in der anderen Tabelle fehlt",
    ),
    (
        re.compile(r'near "(?P<wort>[^"]*)": syntax error'),
        "die SQL-Anweisung lässt sich ab „{wort}“ nicht mehr lesen",
    ),
    (
        re.compile(r"incomplete input"),
        "die SQL-Anweisung bricht mitten im Satz ab",
    ),
    (
        re.compile(r"unable to open database file"),
        "die Datenbankdatei ließ sich nicht öffnen",
    ),
    (
        re.compile(r"database is locked"),
        "die Datenbank ist gerade von einem anderen Programm gesperrt",
    ),
    (
        re.compile(r"file is not a database"),
        "die angegebene Datei ist keine Datenbank",
    ),
)


def _datenbankmeldung_eindeutschen(text: str) -> str:
    for muster, vorlage in _DATENBANKMELDUNGEN:
        treffer = muster.search(text)
        if treffer is not None:
            ersatz = vorlage.format(**treffer.groupdict())
            return text[: treffer.start()] + ersatz + text[treffer.end() :]
    return text


def _standardmeldung_uebersetzen(text: str) -> tuple[str, str] | None:
    """Deutsche (Was, Prüfe)-Fassung einer Standardmeldung von Python,
    oder `None`, wenn keines der Muster greift."""
    text = _vorschlaege_entfernen(text)
    for eintrag in _STANDARDMELDUNGEN:
        treffer = eintrag.muster.match(text)
        if treffer is None:
            continue
        werte: dict[str, str] = {}
        for name, wert in treffer.groupdict().items():
            wert = wert or ""
            if name == "sammlung":
                wert = _SAMMLUNG_AUF_DEUTSCH.get(wert, "der Sammlung")
            elif name == "einleitung":
                wert = _EINLEITUNGEN.get(wert, "der Zeile davor")
            elif name.startswith("typ"):
                wert = _typname(wert)
            elif name in ("wert", "namen"):
                wert = _in_deutsche_anfuehrungszeichen(wert)
            werte[name] = wert
            werte[f"gross_{name}"] = _gross(wert)
        return _FORMAT.vformat(eintrag.was, (), werte), _FORMAT.vformat(eintrag.pruefe, (), werte)
    return None


def _quellklasse(exc: BaseException | Any) -> type:
    """Die Ausnahmeklasse, um die es wirklich geht. Bei der DAP-Attrappe
    (`_DapAusnahme`) ist das nicht ihr eigener Typ, sondern die Klasse
    aus der `exceptionId`."""
    klasse = getattr(exc, "natter_klasse", None)
    return klasse if isinstance(klasse, type) else type(exc)


def _ist_natter_meldung(exc: BaseException | Any) -> bool:
    """Ob `str(exc)` schon eine deutsche Meldung aus `pcl` ist. Die wird
    unverändert übernommen – sie ist genauer als alles, was der Katalog
    aus dem Exception-Typ allein ableiten könnte."""
    klasse = _quellklasse(exc)
    return klasse.__module__.split(".")[0] == "pcl" or klasse.__name__.startswith("Natter")


def _was_und_pruefe(
    exc: BaseException | Any, rueckfall_was: str, rueckfall_pruefe: str
) -> tuple[str, str]:
    """Gemeinsamer Weg aller Katalogeinträge, die sonst `str(exc)`
    unübersetzt ins „Was“ gestellt hätten.

    Reihenfolge: deutsche `pcl`-Meldung → Übersetzungstabelle →
    Rückfall. Im Rückfall steht der deutsche Satz vorn und die
    englische Originalmeldung dahinter als gekennzeichnetes Zitat –
    ohne sie wäre bei einer unbekannten Meldung jede Einzelheit weg.
    """
    text = _vorschlaege_entfernen(str(exc))
    if _ist_natter_meldung(exc):
        return text or rueckfall_was, rueckfall_pruefe
    uebersetzt = _standardmeldung_uebersetzen(text)
    if uebersetzt is not None:
        return uebersetzt
    if not text:
        return rueckfall_was, rueckfall_pruefe
    return f"{rueckfall_was} {ORIGINALMELDUNG_PRAEFIX}„{text}“.", rueckfall_pruefe


# Jeder Katalogeintrag liefert (Kurzbeschreibung für die Überschrift, Was,
# Prüfe) – siehe Abschnitt 8.3: "Laufzeitfehler: <Kurz> (<Exception-Typ>)".


def _zero_division(exc: ZeroDivisionError) -> tuple[str, str, str]:
    return (
        "Division durch 0",
        "Es wurde durch 0 geteilt.",
        "Welche Werte kann der Teiler annehmen? Wird der Fall 0 vorher abgefangen?",
    )


def _unbound_local(exc: UnboundLocalError) -> tuple[str, str, str]:
    name = _name_ermitteln(exc)
    ziel = f"„{name}“" if name else "Die Variable"
    return (
        "Lokale Variable vor Zuweisung verwendet",
        f"{ziel} wurde in dieser Funktion verändert, bevor ihr ein Wert zugewiesen "
        "wurde – lokale und globale Variablen mit demselben Namen sind unterschiedliche "
        "Variablen.",
        "Soll an dieser Stelle wirklich eine neue lokale Variable entstehen, oder "
        "war die gleichnamige globale gemeint?",
    )


def _name_error(exc: NameError) -> tuple[str, str, str]:
    name = _name_ermitteln(exc)
    ziel = f"„{name}“" if name else "Der verwendete Name"
    return (
        "Unbekannter Name",
        f"{ziel} ist an dieser Stelle nicht bekannt.",
        "Ist die Schreibweise korrekt? Wurde die Variable vorher zugewiesen? Ist die "
        "Unit eingebunden?",
    )


def _attribute_error(exc: AttributeError) -> tuple[str, str, str]:
    name = _name_ermitteln(exc)
    if name and name.startswith("__") and not name.endswith("__"):
        return (
            "Zugriff auf gekapseltes Attribut",
            f"„{name}“ beginnt mit zwei Unterstrichen und ist damit von außerhalb der "
            "Klasse nicht direkt zugreifbar (Namensumbildung/Kapselung).",
            "Gibt es eine öffentliche Methode oder Eigenschaft, die stattdessen "
            "genutzt werden sollte?",
        )
    ziel = f"„{name}“" if name else "Die verwendete Eigenschaft"
    return (
        "Unbekannte Eigenschaft",
        f"{ziel} existiert bei diesem Objekt nicht.",
        "Ist der Name richtig geschrieben? Ist es wirklich der erwartete Objekttyp?",
    )


def _type_error(exc: TypeError) -> tuple[str, str, str]:
    was, pruefe = _was_und_pruefe(
        exc,
        "Die verwendeten Datentypen passen an dieser Stelle nicht zusammen.",
        "Passen die verwendeten Datentypen zueinander? Stimmt die Anzahl der Argumente?",
    )
    return ("Unpassender Datentyp", was, pruefe)


def _value_error(exc: ValueError) -> tuple[str, str, str]:
    was, pruefe = _was_und_pruefe(
        exc,
        "Der übergebene Wert passt nicht zu dem, was hier erwartet wird.",
        "Welcher Wert wurde tatsächlich übergeben, und passt er zum erwarteten Typ?",
    )
    return ("Ungültiger Wert", was, pruefe)


def _index_error(exc: IndexError) -> tuple[str, str, str]:
    was, pruefe = _was_und_pruefe(
        exc,
        "Es wurde ein Platz angesprochen, den es in der Sammlung nicht gibt.",
        "Welcher Index wurde verwendet, und wie viele Einträge hat die Liste bzw. "
        "die Tabelle wirklich? Gezählt wird ab 0.",
    )
    return ("Index außerhalb des gültigen Bereichs", was, pruefe)


def _key_error(exc: KeyError) -> tuple[str, str, str]:
    schluessel = exc.args[0] if exc.args else "?"
    return (
        "Unbekannter Schlüssel",
        f"Der Schlüssel {schluessel!r} kommt in diesem Wörterbuch nicht vor.",
        "Welche Schlüssel enthält das Wörterbuch an dieser Stelle wirklich? Steckt "
        "ein Tippfehler oder eine andere Groß-/Kleinschreibung dahinter?",
    )


def _file_not_found(exc: FileNotFoundError) -> tuple[str, str, str]:
    # exc.filename ist nur gesetzt, wenn Python die Ausnahme selbst
    # erzeugt hat - beim DAP-Nachbau (fehlermeldung_aus_dap_erzeugen())
    # fehlt es, str(exc) enthält den Pfad aber ohnehin schon als Text.
    pruefe = (
        "Stimmt der Pfad, und ist er relativ zum aktuellen Arbeitsverzeichnis "
        "gemeint? Liegt die Datei wirklich im Projektordner?"
    )
    if exc.filename:
        return (
            "Datei nicht gefunden",
            f"Die Datei {_in_deutsche_anfuehrungszeichen(repr(exc.filename))} "
            "wurde nicht gefunden.",
            pruefe,
        )
    was, pruefe = _was_und_pruefe(exc, "Die angegebene Datei wurde nicht gefunden.", pruefe)
    return ("Datei nicht gefunden", was, pruefe)


def _permission_error(exc: PermissionError) -> tuple[str, str, str]:
    pruefe = (
        "Ist die Datei noch in einem anderen Programm (z. B. Excel) geöffnet? "
        "Bestehen Schreibrechte für diesen Ordner?"
    )
    if exc.filename:
        return (
            "Kein Zugriff auf die Datei",
            f"Auf {_in_deutsche_anfuehrungszeichen(repr(exc.filename))} besteht kein "
            "Zugriff.",
            pruefe,
        )
    was, pruefe = _was_und_pruefe(exc, "Auf die Datei besteht kein Zugriff.", pruefe)
    return ("Kein Zugriff auf die Datei", was, pruefe)


def _unicode_decode_error(exc: UnicodeDecodeError) -> tuple[str, str, str]:
    pruefe = (
        "Welchen Zeichensatz hat die Datei wirklich? Aus Excel exportierte "
        "CSV-Dateien tragen häufig Windows-1252 statt UTF-8."
    )
    if exc.encoding:
        return (
            "Datei mit falschem Zeichensatz gelesen",
            f"Die Datei lässt sich nicht als {exc.encoding} lesen.",
            pruefe,
        )
    was, pruefe = _was_und_pruefe(
        exc, "Die Datei lässt sich mit dem angegebenen Zeichensatz nicht lesen.", pruefe
    )
    return ("Datei mit falschem Zeichensatz gelesen", was, pruefe)


class _NurMeldung:
    """Hilfsobjekt, damit `_was_und_pruefe()` auch einen bloßen Text
    übersetzen kann – `SyntaxError.msg` trägt die eigentliche Meldung,
    `str(exc)` hängt Datei und Zeile an."""

    def __init__(self, text: str, klasse: type) -> None:
        self._text = text
        self.natter_klasse = klasse

    def __str__(self) -> str:
        return self._text


def _syntax_error(exc: SyntaxError) -> tuple[str, str, str]:
    was, pruefe = _was_und_pruefe(
        _NurMeldung(exc.msg or str(exc), _quellklasse(exc)),
        "Der Quelltext an der markierten Stelle ist kein gültiges Python.",
        "Fehlt ein Doppelpunkt am Blockanfang? Stimmt die Einrückung? Python nutzt "
        "Einrückung statt begin…end.",
    )
    return ("Ungültige Quelltextstruktur", was, pruefe)


def _import_error(exc: BaseException) -> tuple[str, str, str]:
    """`ModuleNotFoundError`/`ImportError` (M12).

    Der häufigste Fehler beim Aufteilen auf mehrere Units: die Unit
    heißt `u_Ampel.py`, im Import steht `u_ampel` – unter Windows fällt
    das beim Dateinamen nicht auf, beim Import schon. Der zweite Fall
    ist ein Paket, das gar nicht installiert ist.
    """
    name = getattr(exc, "name", None) or _name_ermitteln(exc)
    # Bewusst ohne `_gross()`: der Name ist ein Bezeichner. Aus
    # `u_ampel` würde sonst `U_ampel` – und genau um Groß- und
    # Kleinschreibung geht es hier.
    ziel = (
        f"Die Unit oder das Paket {_in_deutsche_anfuehrungszeichen(repr(name))}"
        if name
        else "Die angeforderte Unit bzw. das Paket"
    )
    return (
        "Unit oder Paket nicht gefunden",
        f"{ziel} konnte nicht geladen werden.",
        "Heißt die Unit wirklich so, mit derselben Groß- und Kleinschreibung, und "
        "liegt sie im Projektordner? Falls es ein Paket sein soll: ist es über "
        "„Pakete → Paket installieren …“ eingerichtet?",
    )


def _recursion_error(exc: BaseException) -> tuple[str, str, str]:
    """`RecursionError` (M12). Rekursion steht auf dem Lehrplan, und der
    erste Versuch endet fast immer hier."""
    return (
        "Rekursion ohne Ende",
        "Die Funktion hat sich so oft selbst aufgerufen, dass kein Platz mehr da "
        "war. Meistens fehlt der Fall, der die Rekursion beendet.",
        "Welcher Fall soll die Rekursion abbrechen, und wird er überhaupt erreicht? "
        "Kommt der Aufruf dem Abbruchfall mit jedem Schritt näher?",
    )


def _assertion_error(exc: BaseException) -> tuple[str, str, str]:
    """`AssertionError` (M12). Kommt aus einem `assert` im eigenen Code
    und aus jeder fehlgeschlagenen Prüfung in einer Test-Unit."""
    text = _vorschlaege_entfernen(str(exc))
    was = "Eine Behauptung (`assert`) hat nicht gestimmt."
    if text:
        was += f" Dazu steht da: {_in_deutsche_anfuehrungszeichen(repr(text))}."
    return (
        "Behauptung nicht erfüllt",
        was,
        "Welche Werte haben die Namen in der Behauptung an dieser Stelle wirklich? "
        "Ist die Behauptung falsch – oder das, was vorher berechnet wurde?",
    )


def _os_error(exc: BaseException) -> tuple[str, str, str]:
    """Rückfall für alle `OSError`, die keinen eigenen Eintrag haben
    (`FileExistsError`, `IsADirectoryError`, volle Platte …). Ohne ihn
    fiel die Suche über die MRO ins Leere und das Schülerprogramm zeigte
    den rohen Traceback (M12)."""
    pfad = getattr(exc, "filename", None)
    was, pruefe = _was_und_pruefe(
        exc,
        f"Der Zugriff auf {_in_deutsche_anfuehrungszeichen(repr(str(pfad)))} ist "
        "fehlgeschlagen."
        if pfad
        else "Ein Zugriff auf eine Datei oder einen Ordner ist fehlgeschlagen.",
        "Stimmt der Pfad, und gibt es die Datei bzw. den Ordner schon? Ist sie "
        "gerade in einem anderen Programm geöffnet?",
    )
    return ("Dateizugriff fehlgeschlagen", was, pruefe)


def _arithmetic_error(exc: BaseException) -> tuple[str, str, str]:
    """Rückfall für `OverflowError` und die übrigen Rechenfehler neben
    der Division durch 0 (M12)."""
    was, pruefe = _was_und_pruefe(
        exc,
        "Die Rechnung ließ sich nicht ausführen.",
        "Welche Werte haben die beteiligten Zahlen an dieser Stelle? Wird eine "
        "Zahl in einer Schleife immer weiter vergrößert?",
    )
    return ("Rechnung nicht ausführbar", was, pruefe)


def _natter_property_error(exc: BaseException) -> tuple[str, str, str]:
    """`pcl.errors.NatterPropertyError`: einer Eigenschaft wurde ein Wert
    falschen Typs zugewiesen. Die Meldung aus `pcl` ist bereits deutsch
    und nennt erwarteten und erhaltenen Typ – hier kommt nur die
    Leitfrage dazu."""
    return (
        "Eigenschaft mit unpassendem Wert belegt",
        str(exc),
        "Welchen Typ liefert der zugewiesene Ausdruck wirklich? Kommt der Wert aus "
        "einem Eingabefeld und ist damit ein Text?",
    )


def _natter_datenbank_error(exc: BaseException) -> tuple[str, str, str]:
    """`pcl.errors.NatterDatenbankError`. Ohne eigenen Eintrag fiel die
    Suche über die MRO bis `RuntimeError` durch und lieferte gar keine
    Meldung – der Schüler sah dann den rohen Traceback (M11,
    Abschnitt 4)."""
    return (
        "Datenbank nicht erreichbar oder SQL-Fehler",
        _datenbankmeldung_eindeutschen(str(exc)),
        "Steht die Verbindung zur Datenbank? Heißen Tabelle und Spalten wirklich "
        "so, und stimmt die Reihenfolge der SQL-Schlüsselwörter?",
    )


# Nachschlagen läuft über die MRO der tatsächlichen Ausnahme (siehe
# _katalog_eintrag), die Reihenfolge hier ist deshalb ohne Bedeutung.
_KATALOG: dict[type[BaseException], Callable[[BaseException], tuple[str, str, str]]] = {
    ZeroDivisionError: _zero_division,
    UnboundLocalError: _unbound_local,
    NameError: _name_error,
    AttributeError: _attribute_error,
    TypeError: _type_error,
    ValueError: _value_error,
    IndexError: _index_error,
    KeyError: _key_error,
    FileNotFoundError: _file_not_found,
    PermissionError: _permission_error,
    UnicodeDecodeError: _unicode_decode_error,
    IndentationError: _syntax_error,
    SyntaxError: _syntax_error,
    # M12: Fehler, die im Unterricht vorkommen und bis dahin gar keine
    # Meldung bekamen - das Schülerprogramm zeigte den englischen
    # Traceback. `ImportError` deckt auch `ModuleNotFoundError` ab,
    # `OSError` und `ArithmeticError` fangen ihre übrigen Unterklassen
    # auf (FileExistsError, IsADirectoryError, OverflowError …).
    ImportError: _import_error,
    RecursionError: _recursion_error,
    AssertionError: _assertion_error,
    OSError: _os_error,
    ArithmeticError: _arithmetic_error,
    # `pcl`-eigene Ausnahmen: NatterPropertyError und
    # NatterDatenbankError stehen hier, weil ihre Basisklassen den
    # Fehler nicht treffen bzw. gar nicht im Katalog stehen
    # (RuntimeError). Die übrigen (NatterDatenError, NatterDatenDateiError,
    # NatterUnbekannteEigenschaftError) finden über ihre Basisklasse
    # schon den richtigen Eintrag, siehe tests/test_analyse_fehlerkatalog.py.
    NatterPropertyError: _natter_property_error,
    NatterDatenbankError: _natter_datenbank_error,
}


def _katalog_eintrag_fuer_klasse(
    klasse: type[BaseException],
) -> Callable[[BaseException], tuple[str, str, str]] | None:
    for basisklasse in klasse.__mro__:
        if basisklasse in _KATALOG:
            return _KATALOG[basisklasse]
    return None


def _katalog_eintrag(
    exc: BaseException,
) -> Callable[[BaseException], tuple[str, str, str]] | None:
    return _katalog_eintrag_fuer_klasse(type(exc))


def _wo_quelltext_markierung(tb: TracebackType | None) -> tuple[str, str | None, str | None]:
    stack = traceback.extract_tb(tb)
    eigene = [fs for fs in stack if ist_eigener_code(fs.filename)]
    ziel = eigene[-1] if eigene else (stack[-1] if stack else None)
    if ziel is None:
        return "?", None, None

    formatiert = stack.format_frame_summary(ziel).rstrip("\n").split("\n")
    quelltext = formatiert[1].strip() if len(formatiert) > 1 else None
    markierung = formatiert[2] if len(formatiert) > 2 else None

    wo = f"{Path(ziel.filename).name}, Zeile {ziel.lineno}, in {ziel.name}"
    return wo, quelltext, markierung


def fehlermeldung_erzeugen(exc: BaseException) -> Fehlermeldung | None:
    """Baut die Wo/Was/Prüfe-Meldung für `exc` (Abschnitt 8.3). `None`,
    wenn kein Katalogeintrag zum Exception-Typ passt (Abschnitt 8.5 ist
    ein MVP-Auszug, kein vollständiger Katalog)."""
    eintrag = _katalog_eintrag(exc)
    if eintrag is None:
        return None

    kurz, was, pruefe = eintrag(exc)
    wo, quelltext, markierung = _wo_quelltext_markierung(exc.__traceback__)

    art = "Syntaxfehler" if isinstance(exc, SyntaxError) else "Laufzeitfehler"
    ueberschrift = f"{art}: {kurz} ({type(exc).__name__})"

    return Fehlermeldung(
        ueberschrift=ueberschrift,
        wo=wo,
        quelltext=quelltext,
        markierung=markierung,
        was=was,
        pruefe=pruefe,
    )


class _DapAusnahme:
    """Attrappe für eine Ausnahme aus einer DAP-`exceptionInfo`-Antwort
    (Abschnitt 8.1: unbehandelte Ausnahme im per DAP verbundenen
    Schülerprogramm-Prozess – dort gibt es kein lokales Exception-Objekt,
    nur Text). Trägt nur die Felder, die die Katalogfunktionen oben
    tatsächlich lesen (`str(exc)`, `.name`, `.filename`, `.encoding`,
    `.args`, `.msg`), ohne über den – bei manchen Typen wie
    `UnicodeDecodeError` mehrargumentigen – echten Exception-Konstruktor
    zu gehen."""

    def __init__(self, nachricht: str, klasse: type | None = None) -> None:
        self._nachricht = nachricht
        #: Die echte Ausnahmeklasse aus der `exceptionId`. Ohne sie
        #: hielte `_ist_natter_meldung()` eine bereits deutsche
        #: `pcl`-Meldung für eine englische Standardmeldung und stellte
        #: ihr den Rückfalltext voran.
        self.natter_klasse = klasse
        self.name: str | None = None
        self.filename: str | None = None
        self.encoding: str | None = None
        self.args = (nachricht,)
        self.msg = nachricht

    def __str__(self) -> str:
        return self._nachricht


def _exception_klasse_aufloesen(exception_id: str) -> type[BaseException] | None:
    """Löst einen DAP-`exceptionId`-String (z. B. `"ZeroDivisionError"`
    oder `"json.decoder.JSONDecodeError"`) auf die tatsächliche Klasse
    auf, damit dieselbe MRO-Katalogsuche wie bei echten Ausnahmen greift
    (auch unregistrierte Unterklassen finden über ihre Basisklasse einen
    Eintrag, siehe `fehlermeldung_erzeugen`)."""
    eingebaut = getattr(builtins, exception_id, None)
    if isinstance(eingebaut, type) and issubclass(eingebaut, BaseException):
        return eingebaut
    if "." not in exception_id:
        return None
    modulname, _, klassenname = exception_id.rpartition(".")
    try:
        modul = importlib.import_module(modulname)
    except ImportError:
        return None
    klasse = getattr(modul, klassenname, None)
    return klasse if isinstance(klasse, type) and issubclass(klasse, BaseException) else None


def _dap_stapel_parsen(
    text: str,
) -> list[tuple[str, int, str, str | None, str | None]]:
    """Zerlegt den von `debugpy` gelieferten Text-Stacktrace
    (`exceptionInfo`-Antwort, `details.stackTrace`) in (Datei, Zeile,
    Methode, Quelltext, Karett-Markierung)-Tupel – dasselbe, was
    `traceback.extract_tb()`/`format_frame_summary()` für eine lokale
    Ausnahme liefern, nur aus reinem Text statt einem echten Traceback-
    Objekt gewonnen. Jeder „File …“-Zeile folgt im selben Format wie
    Pythons eigene Ausgabe die Quellzeile, optional darunter eine
    `^`/`~`-Karett-Zeile (Python 3.11+)."""
    zeilen = text.split("\n")
    frames: list[tuple[str, int, str, str | None, str | None]] = []
    i = 0
    while i < len(zeilen):
        treffer = _STAPEL_ZEILE_MUSTER.match(zeilen[i])
        if treffer is None:
            i += 1
            continue
        quelltext = zeilen[i + 1].strip() if i + 1 < len(zeilen) else None
        markierung = None
        naechste = zeilen[i + 2] if i + 2 < len(zeilen) else ""
        if naechste.strip() and set(naechste.strip()) <= set("^~"):
            markierung = naechste
        frames.append(
            (
                treffer.group("datei"),
                int(treffer.group("zeile")),
                treffer.group("name"),
                quelltext,
                markierung,
            )
        )
        i += 3 if markierung else 2
    return frames


def fehlermeldung_aus_dap_erzeugen(exception_info: dict[str, Any]) -> Fehlermeldung | None:
    """Wie `fehlermeldung_erzeugen()`, aber für eine unbehandelte Ausnahme
    im per DAP verbundenen Schülerprogramm-Prozess: `exception_info` ist
    die Antwort auf den DAP-`exceptionInfo`-Request (Abschnitt 8.1).
    `None`, wenn `exceptionId` keiner bekannten Klasse zugeordnet werden
    kann oder kein Katalogeintrag passt."""
    exception_id = exception_info.get("exceptionId", "")
    klasse = _exception_klasse_aufloesen(exception_id)
    if klasse is None:
        return None
    eintrag = _katalog_eintrag_fuer_klasse(klasse)
    if eintrag is None:
        return None

    details = exception_info.get("details") or {}
    nachricht = details.get("message") or exception_info.get("description") or ""
    kurz, was, pruefe = eintrag(_DapAusnahme(nachricht, klasse))

    # Achtung, anders herum als traceback.extract_tb(): debugpys
    # exceptionInfo-Stacktrace listet den tiefsten (innersten) Frame
    # zuerst, nicht zuletzt - "eigener Code" ist deshalb der erste
    # Treffer, nicht der letzte.
    stapel = _dap_stapel_parsen(details.get("stackTrace") or "")
    eigene = [f for f in stapel if ist_eigener_code(f[0])]
    ziel = eigene[0] if eigene else (stapel[0] if stapel else None)
    if ziel is not None:
        datei, zeile, methode, quelltext, markierung = ziel
        wo = f"{Path(datei).name}, Zeile {zeile}, in {methode}"
    else:
        wo, quelltext, markierung = "?", None, None

    art = "Syntaxfehler" if issubclass(klasse, SyntaxError) else "Laufzeitfehler"
    ueberschrift = f"{art}: {kurz} ({klasse.__name__})"

    return Fehlermeldung(
        ueberschrift=ueberschrift,
        wo=wo,
        quelltext=quelltext,
        markierung=markierung,
        was=was,
        pruefe=pruefe,
    )
