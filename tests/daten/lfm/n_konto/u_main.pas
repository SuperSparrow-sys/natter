unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, u_TKonto;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_ueberweisen: TButton;
    b_runter: TButton;
    b_hoch: TButton;
    b_neuesKonto: TButton;
    e_uB: TEdit;
    e_uKNr: TEdit;
    e_kontostand: TEdit;
    e_besitzer: TEdit;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    Label4: TLabel;
    Label5: TLabel;
    Label6: TLabel;
    Label7: TLabel;
    Label8: TLabel;
    m_anzeige: TMemo;
    procedure b_hochClick(Sender: TObject);
    procedure b_neuesKontoClick(Sender: TObject);
    procedure b_runterClick(Sender: TObject);
    procedure b_ueberweisenClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure anzeigen(n:integer);
  private

  public

  end;

var
  Form1: TForm1;
  z,m: integer;
  konten: array of TKonto;

implementation

{$R *.lfm}

{ TForm1 }
procedure TForm1.anzeigen(n:integer);
begin
  m_anzeige.lines.Clear;
  m_anzeige.lines.add('Besitzer: ' + konten[n].get_besitzer);
  m_anzeige.lines.add('Kontonummer: ' + konten[n].get_kontoNr);
  m_anzeige.lines.add('Betrag: ' + floattostrf(konten[n].get_kontostand,fffixed,0,2) + '€');


  m:=high(konten);

end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  z:=0;
  m:=0;

  setlength(konten,3);
  konten[0] := TKonto.create('1234.0000', 'Dr. Martina Meiermilch', 4783.20);
  konten[1] := TKonto.create('1234.0001', 'Sebastian Säumlich', 3222.99);
  konten[2] := TKonto.create('1234.0002', 'Sina Säumlich', 9234.20);

  m:=length(konten);
  anzeigen(z);
end;

procedure TForm1.b_neuesKontoClick(Sender: TObject);
var
  b,k: string;
  btr: single;
begin
  b:= e_besitzer.text;
  btr:= strtofloat(e_kontostand.text);

  k:=('1234.' + Format('%.4d',[m+1]));

  setlength(konten,length(konten)+1);

  m:=m+1;

  konten[m]:= TKonto.create(k, b, btr);

  z:=m;

  anzeigen(z);

  m:=high(konten);

end;

procedure TForm1.b_hochClick(Sender: TObject);
begin
  if z = m then z:=0 else
  z:=z+1;
  anzeigen(z);
end;

procedure TForm1.b_runterClick(Sender: TObject);
begin
  if z = 0 then z:=m else
  z:=z-1;
  anzeigen(z)
end;

procedure TForm1.b_ueberweisenClick(Sender: TObject);
begin
  konten[z].ueberweisen(strtofloat(e_uB.text),konten[strtoint(e_uKNr.text)]);
  anzeigen(z);
end;

end.

