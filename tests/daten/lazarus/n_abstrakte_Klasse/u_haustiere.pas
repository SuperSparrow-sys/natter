unit u_haustiere;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils;

type
  THaustier = class
    private
      name: string;
    public
      function geraeuch_machen: string; virtual; abstract;
  end;

type
  TKatze = class (THaustier)
    private
    public
      function geraeuch_machen: string; override;
      constructor create(n:string);
  end;

type
  THund = class (THaustier)
    private
    public
      function geraeuch_machen: string; override;
      constructor create(n:string);
  end;

implementation

function TKatze.geraeuch_machen: string;
begin
  result:= 'MiauMiau'
end;

constructor TKatze.create(n:string);
begin
 name:=n;
end;

function THund.geraeuch_machen: string;
begin
  result:= 'WauWau'
end;
constructor THund.create(n:string);
begin
name:=n
end;
end.

