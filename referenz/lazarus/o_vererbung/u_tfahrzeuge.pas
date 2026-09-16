unit u_TFahrzeuge;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils;

type
  TFahrzeuge = class
  private
    geschwindikeit:real;
    anzahlRaeder:integer;
  public
    function get_Geschwindikeit():real;
    function get_AnzahlRaeder():integer;
  end;

type
  TFahrrad = class(TFahrzeuge)
  private
    rahmengroesse: real;
    hatGepaecktraeger: boolean;
  public
    constructor create(v:real; r:integer; rg:real; gt:boolean);
    function get_hatGepaecktraeger: boolean;
    function get_rahmengroesse: real;
    procedure gepaecktraeger;
  end;

implementation

constructor TFahrrad.create(v:real; r:integer; rg:real; gt:boolean);
begin
  geschwindikeit:=v;
  anzahlRaeder:=r;
  rahmengroesse:=rg;
  hatGepaecktraeger:=gt;
end;

function TFahrzeuge.get_Geschwindikeit():real;
begin
  result:=geschwindikeit;
end;

function TFahrzeuge.get_AnzahlRaeder():integer;
begin
  result:=anzahlRaeder;
end;

function TFahrrad.get_hatGepaecktraeger():boolean;
begin
  result:=hatGepaecktraeger;
end;

function TFahrrad.get_rahmengroesse: real;
begin
 result:=rahmengroesse;
end;

procedure TFahrrad.gepaecktraeger;
begin
  hatGepaecktraeger:=true;
end;

end.

