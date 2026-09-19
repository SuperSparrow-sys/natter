# Umstieg Pascal → Python

Du kannst schon programmieren. Was sich ändert, ist die Schreibweise –
und an ein paar Stellen die Denkweise. Diese Seite stellt beides
nebeneinander.

## Das Wichtigste zuerst

| Pascal | Python |
|---|---|
| `begin … end` | **Einrückung**. Der Doppelpunkt eröffnet den Block, die Einrückung hält ihn zusammen |
| `x := 5;` | `x = 5` – ein Gleichheitszeichen, kein Semikolon |
| `if a = b then` | `if a == b:` – zum **Vergleichen** zwei Gleichheitszeichen |
| `var x: Integer;` | gar nichts. `x = 5` legt die Variable an und merkt sich den Typ |
| `{ Kommentar }` | `# Kommentar` bis zum Zeilenende |
| `and`, `or`, `not` | `and`, `or`, `not` – gleich geblieben |
| `<>` | `!=` |

Die Einrückung ist keine Formsache, sondern die Syntax. Im Editor
zeigen dir die senkrechten Linien die Ebenen; unter **Ansicht →
Leerzeichen anzeigen** siehst du jedes einzelne Zeichen.

## Datentypen

| Pascal | Python | Hinweis |
|---|---|---|
| `Integer`, `LongInt` | `int` | beliebig groß, kein Überlauf |
| `Real`, `Double` | `float` | Dezimal**punkt**: `3.5`, nicht `3,5` |
| `Boolean` | `bool` | `True` und `False`, groß geschrieben |
| `Char` | `str` der Länge 1 | einen eigenen Typ gibt es nicht |
| `String` | `str` | |
| `array of Integer` | `list` | `zahlen = [1, 2, 3]` |
| `record` | `class` oder `dataclass` | |
| `TDateTime` | `datetime` aus der Standardbibliothek | |

Umwandeln geht mit dem Typnamen selbst: `int("42")`, `float("3.5")`,
`str(42)`. Das ist das Gegenstück zu `StrToInt` und `FloatToStr`.

**Die häufigste Stolperstelle:** `input()` liefert **immer** einen Text,
auch wenn eine Zahl eingetippt wurde. `readln(zahl)` mit
`zahl: Integer` hat das früher selbst erledigt.

```python
zahl = int(input("Zahl: "))   # ohne int() steht in zahl der Text "7"
```

Dasselbe gilt für Eingabefelder: `self.e_zahl.text` ist ein Text.

## Kontrollstrukturen

| Pascal | Python |
|---|---|
| `if … then … else …` | `if …: … else: …`, dazwischen `elif` statt `else if` |
| `case x of 1: …; 2: …; end;` | `match x: case 1: … case 2: …` oder eine Kette aus `elif` |
| `for i := 1 to 10 do` | `for i in range(1, 11):` – die Obergrenze gehört **nicht** dazu |
| `for i := 10 downto 1 do` | `for i in range(10, 0, -1):` |
| `while b do` | `while b:` |
| `repeat … until b;` | `while True: …` mit `if b: break` am Ende |

```pascal
for i := 1 to 3 do
begin
  writeln(i);
end;
```

```python
for i in range(1, 4):
    print(i)
```

## Strings

| Pascal | Python |
|---|---|
| `Length(s)` | `len(s)` |
| `Copy(s, 2, 3)` | `s[1:4]` – gezählt wird **ab 0** |
| `Pos('a', s)` | `s.find("a")`, liefert -1 statt 0, wenn nichts da ist |
| `s1 + s2` | `s1 + s2` |
| `UpperCase(s)` | `s.upper()` |
| `Trim(s)` | `s.strip()` |
| `IntToStr(i) + ' Stück'` | `f"{i} Stück"` |

## Listen statt Arrays

```pascal
var zahlen: array[0..2] of Integer;
zahlen[0] := 7;
```

```python
zahlen = [0, 0, 0]
zahlen[0] = 7

zahlen.append(9)     # waechst von selbst, kein SetLength
len(zahlen)          # Laenge
for z in zahlen:     # direkt ueber die Werte, ohne Index
    print(z)
```

Ein `record` wird zu einer Klasse:

```python
class Schueler:
    def __init__(self, name: str, note: int) -> None:
        self.name = name
        self.note = note
```

## Prozeduren und Funktionen

| Pascal | Python |
|---|---|
| `procedure Tu(a: Integer);` | `def tu(a):` |
| `function Rechne(a: Integer): Integer;` | `def rechne(a):` mit `return` |
| `Result := 5;` | `return 5` |
| `var`-Parameter (Rückgabe über den Parameter) | mehrere Werte zurückgeben: `return a, b` |

```python
def rechne(a, b):
    return a + b, a - b


summe, differenz = rechne(3, 2)
```

Eine Variable, die in einer Funktion zugewiesen wird, ist dort
**lokal** – auch wenn es draußen eine gleichnamige gibt. Soll die
äußere gemeint sein, schreibt man `global name` in die erste Zeile der
Funktion. In der Regel ist ein `return` die bessere Lösung.

## Units

| Pascal | Python |
|---|---|
| `unit u_ampel;` | die Datei heißt `u_ampel.py`, mehr braucht es nicht |
| `interface` / `implementation` | gibt es nicht – alles steht einmal da |
| `uses u_ampel;` | `from u_ampel import Ampel` |

Groß- und Kleinschreibung zählt: `u_Ampel.py` und `u_ampel` sind
verschieden. Unter Windows fällt das beim Dateinamen nicht auf, beim
Import schon.

## Klassen und Vererbung

```pascal
type
  TAmpel = class
  private
    FZustand: Integer;
  public
    procedure Umschalten;
  end;
```

```python
class Ampel:
    def __init__(self, zustand: int) -> None:
        self.__zustand = zustand

    def umschalten(self) -> None:
        self.__zustand = self.__zustand % 4 + 1
```

| Pascal | Python |
|---|---|
| `constructor Create;` | `def __init__(self):` |
| `private` | zwei Unterstriche davor: `self.__zustand` |
| `public` | der Normalfall, nichts davor |
| `Self` | `self` – und es steht als **erster Parameter** in jeder Methode |
| `class TB = class(TA)` | `class B(A):` |
| `inherited Create;` | `super().__init__()` |

## Dateien

```pascal
AssignFile(f, 'daten.txt');
Reset(f);
ReadLn(f, zeile);
CloseFile(f);
```

```python
with open("daten.txt", encoding="utf-8") as datei:
    for zeile in datei:
        print(zeile.strip())
```

`with` schließt die Datei von selbst – ein vergessenes `CloseFile` kann
es nicht mehr geben. Zum Schreiben: `open("daten.txt", "w",
encoding="utf-8")`.

## Konsole

| Pascal | Python |
|---|---|
| `writeln('Hallo')` | `print("Hallo")` |
| `write('ohne Umbruch')` | `print("ohne Umbruch", end="")` |
| `readln(s)` | `s = input()` |
| `readln(i)` mit `i: Integer` | `i = int(input())` |

Aus der Unit `crt` gibt es in `pcl.crt` dasselbe wieder:

```python
from pcl.crt import clr_scr, goto_xy, text_color, delay, read_key, key_pressed, beep
```

## Oberfläche

Der Designer arbeitet wie in Lazarus: Komponente aus der Palette
wählen, auf das Formular klicken, im Objektinspektor die Eigenschaften
setzen.

| Lazarus | Natter |
|---|---|
| `Button1.Caption := 'OK';` | `self.b_ok.caption = "OK"` |
| `Edit1.Text` | `self.e_name.text` |
| `Memo1.Lines.Add('x')` | `self.m_log.lines.append("x")` |
| `ListBox1.Items` | `self.l_auswahl.items` |
| `Image1.Picture.LoadFromFile(…)` | `self.i_bild.picture.load_from_file("assets/bild.png")` |
| `ShowMessage('Hallo')` | `show_message("Hallo")` |
| `InputBox('Titel', 'Frage', '')` | `input_box("Titel", "Frage", "")` |

Die Ereignismethode legt Natter beim **Doppelklick auf die Komponente**
an – wie in Lazarus:

```python
def b_ok_click(self, sender):
    self.l_ausgabe.caption = "Hallo!"
```

`sender` ist die Komponente, von der das Ereignis kam – das Gegenstück
zu `Sender: TObject`.

## Was Python nicht hat

* **Kein `begin`/`end`** und kein Semikolon am Zeilenende.
* **Keine Typangabe nötig.** Man darf sie hinschreiben (`a: int`), und
  in diesem Unterricht ist das erwünscht – Python prüft sie aber nicht.
* **Kein `var`-Parameter.** Mehrere Rückgabewerte lösen das.
* **Keine Zeiger.** Jede Variable verweist ohnehin auf ein Objekt.
