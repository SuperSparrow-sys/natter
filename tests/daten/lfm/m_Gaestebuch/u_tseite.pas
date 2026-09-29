unit u_TSeite;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils;

type TSeite = class

  private
  username:string;
  email:string;
  datum:string;
  kommentar:string;

  public

  constructor create(u:string;e:string;d:string;k:string);
  function get_username:string;
  function get_email:string;
  function get_datum:string;
  function get_kommentar:string;

  end;



implementation

constructor TSeite.create(u:string;e:string;d:string;k:string);
begin
  username:=u;
  email:=e;
  datum:=d;
  kommentar:=k;
end;

function TSeite.get_username:string;
begin
  result:=username;
end;

function TSeite.get_email:string;
begin
  result:=email;
end;

function TSeite.get_datum:string;
begin
  result:=datum;
end;

function TSeite.get_kommentar:string;
begin
  result:=kommentar;
end;

end.

