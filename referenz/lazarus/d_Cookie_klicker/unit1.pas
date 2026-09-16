unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Crt, Classes, SysUtils, Forms, Controls, Graphics, Dialogs, ExtCtrls, StdCtrls;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_risk: TButton;
    b_reset: TButton;
    b_schliessen: TButton;
    i_cookie4: TImage;
    i_cookie2: TImage;
    i_cookie3: TImage;
    i_Cookie1: TImage;
    l_Rang: TLabel;
    l_Punktestand: TLabel;
    procedure b_resetClick(Sender: TObject);
    procedure b_riskClick(Sender: TObject);
    procedure b_schliessenClick(Sender: TObject);
    procedure i_Cookie1Click(Sender: TObject);
    procedure i_cookie2Click(Sender: TObject);
    procedure i_cookie3Click(Sender: TObject);
    procedure i_cookie4Click(Sender: TObject);
    procedure i_CookieClick(Sender: TObject);
    procedure Image3Click(Sender: TObject);
    procedure l_RangClick(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  cookies, a: integer;
  monster:boolean;


implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.i_CookieClick(Sender: TObject);
begin

end;

procedure TForm1.b_schliessenClick(Sender: TObject);
begin
  Close;
end;

procedure TForm1.i_Cookie1Click(Sender: TObject);
begin
monster:=false;
randomize;
cookies := cookies+a;
l_Punktestand.Caption := IntToStr(cookies);
if cookies > 10 then
  Form1.color := clskyblue;
if cookies < 10 then
  l_Rang.Caption := 'Rang: Anfaenger';
if cookies > 20 then
  l_Rang.Caption := 'Rang: Fortgeschritten';
if cookies > 30 then
  l_Rang.Caption := 'Rang: Profi';
if cookies > 40 then
  l_Rang.Caption := 'Rang: Du Geiler';
if cookies > 50 then
  l_Rang.Caption := 'Rang: Weltmeister';

if cookies = random(10) then
  monster:=true;

if monster = true then
  begin
    i_Cookie1.picture.LoadFromFile('H:\Jonathan\InfoSys\Lazarus\GUI\d_Cookie_klicker\boesercookie.jpg');
    cookies:=0;
    l_Punktestand.Caption := IntToStr(cookies);
  end;


if cookies < 19 then
  a:=1;
if cookies > 39 then
  a:=2;
if cookies > 59 then
  a:=3;
if cookies > 79 then
  a:=4;

sound(700);
delay(90);
nosound;
end;

procedure TForm1.i_cookie2Click(Sender: TObject);
begin
  i_Cookie1.picture.LoadFromFile('H:\Jonathan\InfoSys\Lazarus\GUI\d_Cookie_klicker\Cookie2.jpg');
end;

procedure TForm1.i_cookie3Click(Sender: TObject);
begin
  i_Cookie1.picture.LoadFromFile('H:\Jonathan\InfoSys\Lazarus\GUI\d_Cookie_klicker\Cookie3.jpg')
end;

procedure TForm1.i_cookie4Click(Sender: TObject);
begin
  i_Cookie1.picture.LoadFromFile('H:\Jonathan\InfoSys\Lazarus\GUI\d_Cookie_klicker\Cookie1.jpg')
end;



procedure TForm1.b_resetClick(Sender: TObject);
begin
  cookies := 0;
  a:=1;
  l_Punktestand.Caption := IntToStr(cookies);
  Form1.color := clwhite;
end;

procedure TForm1.b_riskClick(Sender: TObject);
begin
randomize;
  if random(2)+1 = 1 then
    cookies:= cookies*2
  else
    cookies:=0;
  l_Punktestand.Caption := IntToStr(cookies);

end;

procedure TForm1.Image3Click(Sender: TObject);
begin

end;

procedure TForm1.l_RangClick(Sender: TObject);
begin

end;

end.
