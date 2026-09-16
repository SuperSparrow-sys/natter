unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, Grids;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_guthabena: TButton;
    b_Tipp: TButton;
    b_ziehung: TButton;
    b_auswertung: TButton;
    b_neuesSpiel: TButton;
    l_titel: TLabel;
    l_GuthabenAusgabe: TLabel;
    m_auswertungMemo: TMemo;
    sg_TippTabelle: TStringGrid;
    sg_ZiehungTabelle: TStringGrid;
    procedure b_auswertungClick(Sender: TObject);
    procedure b_guthabenaClick(Sender: TObject);
    procedure b_neuesSpielClick(Sender: TObject);
    procedure b_TippClick(Sender: TObject);
    procedure b_ziehungClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  guthaben: integer;
  tippZahlen: array[0..5] of integer;
  zahlZiehung: array[0..5] of integer;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.FormCreate(Sender: TObject);
begin
  randomize;
  guthaben := 100;
  l_guthabenAusgabe.Caption :=
    'Dein aktuelles Guthaben ist ' + IntToStr(guthaben) + ' €.';
  b_ziehung.Enabled := False;
  b_auswertung.Enabled := False;
end;

procedure TForm1.b_TippClick(Sender: TObject);
var
  i: integer;
begin
  guthaben := guthaben - 5;

  for i := 0 to 5 do
    tippZahlen[i] := StrToInt(sg_TippTabelle.cells[i, 1]);

  b_ziehung.Enabled := True;

  sg_TippTabelle.Enabled := False;

  l_guthabenAusgabe.Caption :=
    'Dein aktuelles Guthaben ist ' + IntToStr(guthaben) + ' €.';

  b_Tipp.Enabled := False;

end;

procedure TForm1.b_ziehungClick(Sender: TObject);
var
  i: integer;
begin
  for i := 0 to 5 do
  begin
    sg_ziehungTabelle.cells[i, 1] := IntToStr(random(49) + 1);
    zahlZiehung[i] := StrToInt(sg_TippTabelle.cells[i, 1]);
  end;

  b_ziehung.Enabled := False;
  b_auswertung.Enabled := True;
  b_Tipp.Enabled := False;

end;

procedure TForm1.b_neuesSpielClick(Sender: TObject);
var
  i: integer;
begin
  for i := 0 to 5 do
  begin
    sg_ziehungTabelle.cells[i, 1] := '';
    sg_TippTabelle.cells[i, 1] := '';
  end;


  b_auswertung.Enabled := false;
  b_Tipp.Enabled := true;
  sg_TippTabelle.Enabled := true;

end;

procedure TForm1.b_auswertungClick(Sender: TObject);
var
  anzahlg, gewinn, i, j: integer;
begin
  anzahlg := 0;

  for i := 0 to 5 do
  begin
    for j := 0 to 5 do
    begin
      if tippZahlen[i] = zahlZiehung[j] then
        anzahlg := anzahlg + 1;

    end;

  end;



  case anzahlg of
    0: gewinn := 0;
    1: gewinn := 1;
    2: gewinn := 10;
    3: gewinn := 100;
    4: gewinn := 1000;
    5: gewinn := 10000;
  end;

  m_auswertungMemo.Lines.add('Du hast ' + inttostr(gewinn) + '€ gewonnen.');
  m_auswertungMemo.Lines.add('Du hast ' + inttostr(anzahlg) + '€ gewonnen.');

  guthaben := guthaben + gewinn;

  l_guthabenAusgabe.Caption :=
    'Dein aktuelles Guthaben ist ' + IntToStr(guthaben) + ' €.';

  b_auswertung.Enabled := false;

  if guthaben <= 1 then
    ShowMessage('Dein Guthaben ist unter 0. Bitte gehe auf PayPal um dein Guthaben wieder aufzufüllen.');


end;

procedure TForm1.b_guthabenaClick(Sender: TObject);
begin

  guthaben:=100;
end;




end.
