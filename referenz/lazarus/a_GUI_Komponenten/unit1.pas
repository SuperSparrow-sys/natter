unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls;

type

  { TForm1 }

  TForm1 = class(TForm)
    Button1: TButton;
    Button2: TButton;
    Button3: TButton;
    Button4: TButton;
    b_Schliessen: TButton;
    b_Begruessung: TButton;
    e_Namenseingabe: TEdit;
    Label1: TLabel;
    l_Ueberschrift: TLabel;
    l_Ausgabe: TLabel;
    procedure Button1Click(Sender: TObject);
    procedure b_BegruessungClick(Sender: TObject);
    procedure b_SchliessenClick(Sender: TObject);
    procedure e_NamenseingabeChange(Sender: TObject);
    procedure l_AusgabeClick(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.e_NamenseingabeChange(Sender: TObject);
begin

end;

procedure TForm1.b_BegruessungClick(Sender: TObject);
var
  vorname: string;
begin
  vorname := e_Namenseingabe.Text;
  if e_Namenseingabe.Text = '' then
  l_ausgabe.Caption := 'Bitte Name eingeben';
  l_ausgabe.Caption := 'Sei gegrüßt, ' + vorname;
end;

procedure TForm1.b_SchliessenClick(Sender: TObject);
begin
  close;
end;

procedure TForm1.Button1Click(Sender: TObject);
begin

end;

procedure TForm1.l_AusgabeClick(Sender: TObject);
begin

end;

end.
