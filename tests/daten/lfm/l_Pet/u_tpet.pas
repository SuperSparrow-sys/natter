unit u_TPet;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils;

type
  TPet = class

  private
    Name: string;
    art: string;
    liebe: integer;
    hunger: integer;
    tod: boolean;
    muede: integer;

  public
    constructor Create(n: string; a: string);
    function get_liebe: integer;
    function get_muede: integer;
    function get_hunger: integer;
    function get_name: string;
    function get_art: string;
    function get_tod: boolean;
    procedure streicheln();
    procedure aergern();
    procedure hungern();
    procedure fuettern();
    procedure isttod();
    procedure schlafen();
    procedure set_muede();
    procedure nameaendern(n:string);

  end;


implementation

constructor TPet.Create(n: string; a: string);
begin
  Name := n;
  art := a;
  liebe := 10;
  hunger := 0;
  tod := False;
end;


procedure TPet.isttod();
begin
  if liebe <= 0 then
    tod := True
  else if hunger >= 10 then
    tod := True
  else if muede >= 10 then
    tod := True
  else
    tod := False;

end;


procedure TPet.streicheln();
begin
  if Liebe < 10 then Liebe := Liebe + 1;
end;

procedure TPet.nameaendern(n:string);
begin
  name:=n;
end;

procedure TPet.schlafen();
begin
  muede:=0;
end;

procedure TPet.fuettern();
begin
  if (hunger - 5) < 0 then
    hunger := 0
  else
    hunger := hunger - 5;
end;

procedure TPet.aergern();
begin
  if Liebe > 0 then liebe := liebe - 1
  else
    liebe := 0;
end;

procedure TPet.hungern();
begin
  hunger := hunger + 1;
end;

procedure TPet.set_muede();
begin
  muede := muede + 1;
end;

function TPEt.get_liebe: integer;
begin
  Result := liebe;
end;

function TPEt.get_hunger: integer;
begin
  Result := hunger;
end;

function TPEt.get_name: string;
begin
  Result := Name;
end;

function TPEt.get_muede: integer;
begin
  Result := muede;
end;

function TPEt.get_art: string;
begin
  Result := art;
end;

function TPEt.get_tod: boolean;
begin
  Result := tod;
end;

end.
