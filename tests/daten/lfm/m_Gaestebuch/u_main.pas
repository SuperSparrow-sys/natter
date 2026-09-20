unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, u_TSeite;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_zurueck: TButton;
    b_eintragen: TButton;
    b_vor: TButton;
    e_eingabe_username: TEdit;
    e_eingabe_mail: TEdit;
    l_username: TLabel;
    l_ueberschrift: TLabel;
    l_mail: TLabel;
    l_kommentar: TLabel;
    m_anzeige: TMemo;
    m_anzeige1: TMemo;
    procedure b_eintragenClick(Sender: TObject);
    procedure anzeigen(z:integer);
    procedure b_vorClick(Sender: TObject);
    procedure b_zurueckClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);

  private

  public

  end;

var
  Form1: TForm1;
  seiten: array of TSeite;
  z,m:integer;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.anzeigen(z:integer);
begin
  m_anzeige.Lines.clear;
  m_anzeige.Lines.add('Username: ' + seiten[z].get_username);
  m_anzeige.Lines.add('E-Mail: ' + seiten[z].get_email);
  m_anzeige.Lines.add('Datum: ' + seiten[z].get_datum);
  m_anzeige.Lines.add('Kommentar: ');
  m_anzeige.Lines.add(seiten[z].get_kommentar);
end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  z:=0;
  m:=0;
end;

procedure TForm1.b_eintragenClick(Sender: TObject);
var e,u,d,k: string;
begin
  e:=e_eingabe_mail.text;
  u:=e_eingabe_username.text;
  d:=FormatDateTime('dd.mm.yyyy, hh:nn:ss', now);
  k:=m_anzeige1.text;

  setlength(seiten,length(seiten)+1);

  seiten[m]:=TSeite.create(u,e,d,k);

  z:=m;

  anzeigen(z);

  m:=m+1;
end;

procedure TForm1.b_vorClick(Sender: TObject);
begin
  if z = 0 then showMessage('Ende')
  else z:=z+1;

  anzeigen(z);
end;

procedure TForm1.b_zurueckClick(Sender: TObject);
begin
  if z = 0 then showMessage('Anfang')
  else z:=z-1;

  anzeigen(z);
end;

end.

