unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, u_TFahrzeuge;

type

  { TForm1 }

  TForm1 = class(TForm)
    m_anzeige: TMemo;
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  Fahrrad: TFahrrad;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.FormCreate(Sender: TObject);
begin
 fahrrad:= TFahrrad.create(0,2,29,false);

 m_anzeige.Lines.clear;
 m_anzeige.Lines.add('Geschwindigkeit: ' + floattostr(fahrrad.get_Geschwindikeit));
 m_anzeige.Lines.add('Räder: ' + floattostr(fahrrad.get_AnzahlRaeder));
 m_anzeige.Lines.add('Rahmengröße: ' + floattostr(fahrrad.get_rahmengroesse));

 if fahrrad.get_hatGepaecktraeger then
 m_anzeige.Lines.add('Gepäckträder:  Ja')
 else m_anzeige.Lines.add('Gepäckträder:  Nein');

end;

end.

