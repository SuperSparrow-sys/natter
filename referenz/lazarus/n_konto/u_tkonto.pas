unit u_TKonto;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, dialogs, SysUtils;


type TKonto=class

  private

    KontoNr: string;
    Besitzer: string;
    KontoStand: single;

  public

    constructor create(KNr:string; B:string; KSt:single);

    function get_besitzer: string;
    function get_KontoNr: string;
    function get_Kontostand: single;

    procedure abheben(betrag:single);
    procedure einzahlen (betrag:single);
    procedure set_besitzer (b: string);
    procedure ueberweisen(Betrag: single; Zielkonto:TKonto);
end;

implementation

constructor TKonto.create(KNr:string; B:string; KSt:single);
begin
KontoNr:=KNr;
Besitzer:=B;
Kontostand:=Kst;
end;

function TKonto.get_besitzer: string;
begin
  result:=besitzer;
end;


function TKonto.get_KontoNr: string;
begin
  result:=KontoNr;
end;


function TKonto.get_Kontostand: single;
begin
  result:=Kontostand;
end;

procedure TKonto.set_besitzer (b: string);
begin
  besitzer:=b;
end;

procedure TKonto.einzahlen (betrag:single);
begin
  Kontostand:=Kontostand+betrag;
end;

procedure TKonto.abheben(betrag:single);
begin
  if betrag<kontostand then kontostand:=kontostand-betrag
  else showMessage('Nicht genügend Geld vorhanden!');
end;

procedure TKonto.ueberweisen(Betrag: single; Zielkonto:TKonto);
begin
  abheben(Betrag);
  Zielkonto.einzahlen(Betrag);
end;

end.

