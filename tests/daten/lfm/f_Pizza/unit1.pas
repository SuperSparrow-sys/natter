unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_hinzufuegen: TButton;
    b_zettelLeer: TButton;
    cb_mws: TComboBox;
    c_kaese: TCheckBox;
    c_knoblauch: TCheckBox;
    e_eingabeSorte: TEdit;
    e_Grundpreis: TEdit;
    Label1: TLabel;
    Label2: TLabel;
    lb_KurzWahl: TListBox;
    l_Kassenzettel: TLabel;
    l_eingabeSorte: TLabel;
    l_grundpreis: TLabel;
    m_zettel: TMemo;
    rb_small: TRadioButton;
    rb_normal: TRadioButton;
    rb_XL: TRadioButton;
    rb_XXL: TRadioButton;
    rb_XXXL: TRadioButton;
    RadioGroup1: TRadioGroup;
    sb_behinderung: TScrollBar;

    procedure b_hinzufuegenClick(Sender: TObject);
    procedure b_zettelLeerClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure sb_behinderungChange(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  kurzName: array[1..10] of string;
  kurzPreis: array[1..10] of real;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.b_hinzufuegenClick(Sender: TObject);
var
  preis: real;
  pizzaname, groesse: string;


begin


  case lb_KurzWahl.itemindex of
    0: pizzaname:=KurzName[1];
    1: pizzaname:=KurzName[2];
    2: pizzaname:=KurzName[3];
    3: pizzaname:=KurzName[4];
    4: pizzaname:=KurzName[5];
    5: pizzaname:=KurzName[6];
    6: pizzaname:=KurzName[7];
    7: pizzaname:=KurzName[8];
    8: pizzaname:=KurzName[9];
    9: pizzaname:=KurzName[10];
  end;

  case lb_KurzWahl.itemindex of
    0: Preis:=KurzPreis[1];
    1: Preis:=KurzPreis[2];
    2: Preis:=KurzPreis[3];
    3: Preis:=KurzPreis[4];
    4: Preis:=KurzPreis[5];
    5: Preis:=KurzPreis[6];
    6: Preis:=KurzPreis[7];
    7: Preis:=KurzPreis[8];
    8: Preis:=KurzPreis[9];
    9: Preis:=KurzPreis[10];
  end;



  if rb_small.Checked then
  begin
    preis := preis * 0.8;
    groesse := 'Small';
  end;
  if rb_normal.Checked then
  begin
    groesse := 'Normal';
  end;
  if rb_xl.Checked then
  begin
    preis := preis * 1.2;
    groesse := 'XL';
  end;
  if rb_xxl.Checked then
  begin
    preis := preis * 1.4;
    groesse := 'XXL';
  end;
  if rb_xxxl.Checked then
  begin
    preis := preis * 1.5;
    groesse := 'XXXL';
  end;

  if c_kaese.Checked = True then
    preis := preis + 1.99;
  if c_knoblauch.Checked = True then
    preis := preis + 0.50;

  case cb_mws.itemindex of
    0: preis:=preis*1.07;
    1: preis:=preis*1.19;
  end;


  m_zettel.Lines.Add('Pizza ' + pizzaname + ' ' + groesse + ' - ' + floattostrF(preis, ffFixed, 0, 2) + ' EUR');

  m_zettel.Font.size:=12;


  end;

procedure TForm1.b_zettelLeerClick(Sender: TObject);
begin
  m_zettel.Lines.Clear;
end;

procedure TForm1.FormCreate(Sender: TObject);
var
  i: integer;
begin

  KurzName[1]:='Hawaii';
  KurzName[2]:='Napoli';
  KurzName[3]:='Spinatta';
  KurzName[4]:='Quadro';
  KurzName[5]:='Fugi';
  KurzName[6]:='Stabilo';
  KurzName[7]:='L`Figgo';
  KurzName[8]:='Crinto Romana';
  KurzName[9]:='Quadro Fromaggi';
  KurzName[10]:='Spinno';

  KurzPreis[1]:=8.50;
  KurzPreis[2]:=8.50;
  KurzPreis[3]:=8.50;
  KurzPreis[4]:=8.50;
  KurzPreis[5]:=8.50;
  KurzPreis[6]:=8.50;
  KurzPreis[7]:=8.50;
  KurzPreis[8]:=8.50;
  KurzPreis[9]:=8.50;
  KurzPreis[10]:=8.50;

  for i:=1 to 10 do
  lb_KurzWahl.items.add(KurzName[i] + ' (' + floattostr(KurzPreis[i]) + ' EUR)' );
end;



procedure TForm1.sb_behinderungChange(Sender: TObject);
begin
  m_zettel.Font.size:= sb_behinderung.position;
end;

end.
