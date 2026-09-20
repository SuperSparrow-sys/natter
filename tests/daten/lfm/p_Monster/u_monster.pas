unit u_monster;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, Dialogs, SysUtils;

type
  Tmonster = class
  private
    monstername: string;
    max_gesundheit: integer;
    gesundheit: integer;
    energie: integer;
    tot: boolean;
  public
    procedure getroffen(schaden: integer);
    procedure energie_erhalten;
    function infos_ausgeben: string;

  end;

type
  TWassermonster = class(Tmonster)
  public
    constructor Create(n: string);
    procedure wasserangriff(ziel: TMonster);
    procedure heilung;
  end;

type
  TFeuermonster = class(Tmonster)
  public
    constructor Create(n: string);
    procedure feuerangriff(ziel: TMonster);
    procedure energieboost;
  end;


implementation

procedure TMonster.getroffen(schaden: integer);
begin
  if (gesundheit - schaden) <= 0 then
    ShowMessage('Das Monster: ' + monstername + ' ist gestorben.')
  else
  begin
    gesundheit := gesundheit - schaden;
    tot := True;
  end;
end;

procedure TMonster.energie_erhalten();
begin
  energie := energie + 5;
end;

function TMonster.infos_ausgeben: string;
begin
  if tot = False then
  begin
    Result := 'Monstername: ' + monstername + sLineBreak + 'Gesundheit: ' +
      IntToStr(gesundheit) + '/' + IntToStr(max_gesundheit) +
      sLineBreak + 'Energie: ' + IntToStr(energie);
  end
  else
    Result := monstername + ' ist leider gestorben.';
end;

constructor TWassermonster.Create(n: string);
begin
  monstername := n;
  max_gesundheit := 75;
  gesundheit := 75;
  energie := 15;
  tot := False;
end;

procedure TWassermonster.wasserangriff(ziel: TMonster);
begin
  if (energie - 10) <= 0 then
  ShowMessage('Das Monster: ' + monstername + ' hat zu wenig Energie')
  else
  begin
  energie := energie - 10;
  ziel.getroffen(12);
  end;

end;

procedure TWassermonster.heilung;
begin
  if (gesundheit + 7) > max_gesundheit then
    gesundheit := max_gesundheit
  else
    gesundheit := gesundheit + 7;
end;


constructor TFeuermonster.Create(n: string);
begin
  monstername := n;
  max_gesundheit := 90;
  gesundheit := 90;
  energie := 20;
  tot := False;
end;

procedure TFeuermonster.feuerangriff(ziel: TMonster);
begin
  if (energie - 8) <= 0 then
  ShowMessage('Das Monster: ' + monstername + ' hat zu wenig Energie')
  else
  begin
  energie := energie - 8;
  ziel.getroffen(9);
  end;

end;

procedure TFeuermonster.energieboost;
begin
  if energie >= max_gesundheit then
  energie := energie + 3 + random(8);
end;

end.
