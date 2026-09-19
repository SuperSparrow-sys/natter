"""Tests für den Pascal-Rumpf-Extraktor (`ide/import_lfm/pascal.py`,
docs/arbeitspakete/M8.md, Schritt 3). Reine Textumwandlung, kein Qt.
"""

from __future__ import annotations

from pathlib import Path

from ide.import_lfm.pascal import (
    pas_text_lesen,
    prozedur_ruempfe_lesen,
    rumpf_als_kommentar,
)

_REFERENZ = Path(__file__).resolve().parent / "daten" / "lazarus"

_PAS = """\
unit u_main;

interface

type
  TForm1 = class(TForm)
    procedure b_startClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  end;

implementation

{$R *.lfm}

procedure TForm1.b_startClick(Sender: TObject);
var
  i: Integer;
begin
  for i := 1 to 3 do
  begin
    Memo1.Lines.Add('Zahl: ' + IntToStr(i));
  end;
end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  Caption := 'Start';
end;

end.
"""


def test_ruempfe_werden_je_methode_gefunden() -> None:
    ruempfe = prozedur_ruempfe_lesen(_PAS)

    assert set(ruempfe) == {"b_startClick", "FormCreate"}
    assert ruempfe["FormCreate"] == ["begin", "  Caption := 'Start';", "end;"]


def test_verschachteltes_begin_end_beendet_den_rumpf_nicht_zu_frueh() -> None:
    rumpf = prozedur_ruempfe_lesen(_PAS)["b_startClick"]

    assert rumpf[0] == "var"
    assert rumpf[-1] == "end;"
    # das innere `end;` der for-Schleife gehört noch dazu
    assert rumpf.count("end;") == 1
    assert "  end;" in rumpf


def test_begin_in_zeichenkette_oder_kommentar_wird_nicht_gezaehlt() -> None:
    quelltext = """\
implementation

procedure TForm1.b_aClick(Sender: TObject);
begin
  ShowMessage('hier steht begin und end');  // und hier: begin
  { begin }
  Caption := 'fertig';
end;

procedure TForm1.b_bClick(Sender: TObject);
begin
  Caption := 'b';
end;
"""
    ruempfe = prozedur_ruempfe_lesen(quelltext)

    assert set(ruempfe) == {"b_aClick", "b_bClick"}
    assert ruempfe["b_aClick"][-1] == "end;"
    assert ruempfe["b_bClick"] == ["begin", "  Caption := 'b';", "end;"]


def test_case_und_try_zaehlen_als_eigene_ebene() -> None:
    quelltext = """\
implementation

procedure TForm1.b_aClick(Sender: TObject);
begin
  case x of
    1: Caption := 'eins';
    2: Caption := 'zwei';
  end;
  try
    y := 1 div 0;
  except
    Caption := 'Fehler';
  end;
end;
"""
    rumpf = prozedur_ruempfe_lesen(quelltext)["b_aClick"]

    assert rumpf[-1] == "end;"
    assert "  try" in rumpf


def test_gemeinsame_einrueckung_wird_entfernt() -> None:
    quelltext = """\
implementation

    procedure TForm1.b_aClick(Sender: TObject);
    begin
      Caption := 'a';
    end;
"""
    assert prozedur_ruempfe_lesen(quelltext)["b_aClick"] == [
        "begin",
        "  Caption := 'a';",
        "end;",
    ]


def test_ohne_implementation_abschnitt_keine_ruempfe() -> None:
    assert prozedur_ruempfe_lesen("unit u; interface end.") == {}


def test_rumpf_als_kommentar_ruecken_ein_und_lassen_leerzeilen_ohne_leerzeichen() -> None:
    zeilen = rumpf_als_kommentar(["begin", "", "end;"], einrueckung="    ")

    assert zeilen == ["    # begin", "    #", "    # end;"]


def test_echte_referenzdatei_l_pet() -> None:
    """Gegen eine echte Lazarus-Unit aus `tests/daten/lazarus/` statt nur
    gegen ein Fixture (nur lesend)."""
    pfad = _REFERENZ / "l_Pet" / "u_main.pas"
    ruempfe = prozedur_ruempfe_lesen(pas_text_lesen(pfad))

    assert "b_nameClick" in ruempfe
    assert ruempfe["b_nameClick"] == [
        "begin",
        "  meinPet.nameaendern(e_name.text);",
        "  Statuswerte();",
        "end;",
    ]
    # jede Methode endet auf `end;` - kein Rumpf läuft über sein Ende hinaus
    for rumpf in ruempfe.values():
        assert [zeile for zeile in rumpf if zeile.strip()][-1].strip().startswith("end")
