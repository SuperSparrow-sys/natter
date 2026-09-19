unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ValEdit,
  Grids;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_berechnen: TButton;
    sg_tabelle: TStringGrid;
    procedure b_berechnenClick(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.b_berechnenClick(Sender: TObject);
var
  i, j: integer;
begin
  for i := 1 to 10 do
  begin
    for j := 1 to 10 do
    begin
      sg_tabelle.cells[i, j] := IntToStr(i * j);
    end;
  end;

end;

end.
