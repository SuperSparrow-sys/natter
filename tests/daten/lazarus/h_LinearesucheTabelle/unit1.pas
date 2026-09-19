unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, Grids, StdCtrls;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_werteberechnen: TButton;
    b_zufallszahlen: TButton;
    m_Werte: TMemo;
    sg_tabelle: TStringGrid;
    procedure b_werteberechnenClick(Sender: TObject);
    procedure b_zufallszahlenClick(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  zahl: array[1..1000] of integer;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.b_zufallszahlenClick(Sender: TObject);
var
  i: integer;
begin
  randomize;
  m_werte.Lines.Clear;
  for i := 1 to 1000 do
  begin
    zahl[i] := random(10000) + 1;

    sg_tabelle.cells[i - 1, 0] := IntToStr(i);
    sg_tabelle.Cells[i - 1, 1] := IntToStr(zahl[i]);

  end;
end;

procedure TForm1.b_werteberechnenClick(Sender: TObject);
var
  min, max, sum, i, a, b: integer;
begin

  //minimum
  min := 10000;
  for i := 1 to 1000 do
  begin
    if zahl[i] < min then
      begin
      min := zahl[i];
      a:=i;
      end;
  end;

  //maximum
  max := 0;
  for i := 1 to 1000 do
  begin
    if zahl[i] > max then
      begin
      max := zahl[i];
      b:=i;
      end;
  end;

  //summe
  sum := 0;
  for i := 1 to 1000 do
  begin
    sum := sum + zahl[i];
  end;

  m_werte.Lines.add('Das Maximum ist: ' + IntToStr(max) + ' und ist an ' + IntToStr(b) + '. Stelle.');
  m_werte.Lines.add('Das Minimum ist: ' + IntToStr(min) + ' und ist an ' + IntToStr(a) + '. Stelle.');
  m_werte.Lines.add('Die Summe aller Zahlen ist: ' + IntToStr(sum) + '.');
end;

end.
