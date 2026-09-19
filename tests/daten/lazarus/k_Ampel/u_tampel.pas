unit u_TAmpel;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils, dialogs, graphics;

type TAmpel = class

  private

    aktiviert: Boolean;
    Zustand: integer;

  public

    constructor create(a: boolean; z: integer);

    procedure anschalten();
    procedure ausschalten();
    procedure umschalten();

    function get_ampelphasen:integer;
    function get_aktiviert:boolean;

  end;


implementation

constructor TAmpel.create(a: boolean; z: integer);
begin
  aktiviert:=a;
  zustand:=z;
end;
                 aktiviert:=true
procedure TAmpel.anschalten();
begin
  aktiviert:=true;
end;

procedure TAmpel.ausschalten();
begin
  aktiviert:=false;
end;

procedure TAmpel.umschalten();
begin
  case zustand of
  1: zustand:=2;
  2: zustand:=3;
  3: zustand:=4;
  4: zustand:=1;
  end;
end;

function TAmpel.get_ampelphasen:integer;
begin
  result:=zustand;
end;

function TAmpel.get_aktiviert:boolean;
begin
  result:=aktiviert;
end;

end.
