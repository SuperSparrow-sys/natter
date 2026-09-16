unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_start: TButton;
    b_Beenden: TButton;
    e_zahl1: TEdit;
    e_Zahl2: TEdit;
    l_ueberschrift: TLabel;
    l_Zahl1: TLabel;
    l_zahl2: TLabel;
    l_Ergebniss: TLabel;
    procedure b_BeendenClick(Sender: TObject);
    procedure b_startClick(Sender: TObject);
    procedure e_zahl1Change(Sender: TObject);
    procedure l_ErgebnissClick(Sender: TObject);
    procedure l_ueberschriftClick(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;

implementation

{$R *.lfm}

{ TForm1 }


procedure TForm1.b_startClick(Sender: TObject);
var
  a,b, erg: real;
begin
  a:=StrToFloat(e_zahl1.text);
  b:=StrToFloat(e_zahl2.text);
  erg:=a+b;


  erg:=a+b;

  l_ergebniss.caption:=('Ergebniss: '+ FloatToStr(erg));

end;

procedure TForm1.b_BeendenClick(Sender: TObject);
begin
  close;
end;

procedure TForm1.e_zahl1Change(Sender: TObject);
begin

end;

procedure TForm1.l_ErgebnissClick(Sender: TObject);
begin

end;

procedure TForm1.l_ueberschriftClick(Sender: TObject);
begin

end;

end.

