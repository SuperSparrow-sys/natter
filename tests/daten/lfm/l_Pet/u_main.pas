unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls,
  u_TPet;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_neuStarten: TButton;
    b_fuettern: TButton;
    b_schlafen: TButton;
    b_name: TButton;
    b_streicheln: TButton;
    b_aergern: TButton;
    e_name: TEdit;
    Image1: TImage;
    Label1: TLabel;
    l_muede: TLabel;
    l_tod: TLabel;
    l_name: TLabel;
    l_art: TLabel;
    l_liebe: TLabel;
    Label6: TLabel;
    l_hunger: TLabel;
    s_muede: TShape;
    s_liebe: TShape;
    s_hunger: TShape;
    t_hunger: TTimer;
    procedure b_nameClick(Sender: TObject);
    procedure b_fuetternClick(Sender: TObject);
    procedure b_aergernClick(Sender: TObject);
    procedure b_neuStartenClick(Sender: TObject);
    procedure b_schlafenClick(Sender: TObject);
    procedure b_streichelnClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure statuswerte();
    procedure t_hungerTimer(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  meinPet: TPet;
  n, x: integer;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.statuswerte();
begin

  if meinPet.get_tod then
  begin
    Form1.color := $008080FF;
    t_hunger.enabled := false;
    showMessage('Deinem Tier geht es nicht gut, neu Starten um weiter zu machen');
  end
    else Form1.color:= $009CD1AD;

  l_name.Caption := ('Name: ' + meinPet.get_name);
  l_art.Caption := ('Art: ' + meinPet.get_art);
  l_liebe.Caption := ('Liebe: ' + IntToStr(meinPet.get_liebe));
  l_hunger.Caption := ('Hunger: ' + IntToStr(meinPet.get_hunger));
  l_muede.Caption := ('Müede: ' + IntToStr(meinPet.get_muede));

  if ((n + 5) mod 10) = 0 then meinPet.hungern;
  if ((n + 8) mod 5) = 0 then meinPet.set_muede;

  meinPet.isttod;

  if meinPet.get_tod then l_tod.Caption := ('Tod: True')
  else
    l_tod.Caption := ('Tod: False');

 if meinPet.get_liebe > 0 then
  s_liebe.width := round((200 / (10/meinPet.get_liebe )))
  else
    s_liebe.width :=0;

 if meinPet.get_hunger > 0 then
  s_hunger.width := round((200 / (10/meinPet.get_hunger )))
  else
    s_hunger.width :=0;

 if meinPet.get_muede > 0 then
  s_muede.width := round((200 / (10/meinPet.get_muede )))
  else
    s_muede.width :=0;

if meinPet.get_liebe < 3 then x:=3
  else if meinPet.get_liebe < 5 then x:=2
    else if meinPet.get_liebe < 8 then x:=1;

 if meinPet.get_muede > 7 then x:=7
   else if meinPet.get_muede > 5 then x:=0;

  case x of
    0: Image1.Picture.LoadFromFile('frosch_muede1.png');
    1: Image1.Picture.LoadFromFile('frosch_aerger1.png');
    2: Image1.Picture.LoadFromFile('frosch_aerger2.png');
    3: Image1.Picture.LoadFromFile('frosch_aerger3.png');
    4: Image1.Picture.LoadFromFile('frosch_durst.png');
    7: Image1.Picture.LoadFromFile('frosch_muede2.png');
    8: Image1.Picture.LoadFromFile('frosch_start.png');
  end;



end;

procedure TForm1.t_hungerTimer(Sender: TObject);
begin
  n := 1 + n;
  Statuswerte();
end;

procedure TForm1.b_streichelnClick(Sender: TObject);
begin
  meinPet.streicheln();
  Statuswerte();
end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  t_hunger.enabled := true;
  x:= 8;
  n := 1;
  Image1.Picture.LoadFromFile('frosch_start.png');
  meinPet := TPet.Create('Jonny', 'Frosch');
  Statuswerte();
end;

procedure TForm1.b_aergernClick(Sender: TObject);
begin
  meinPet.aergern();
  Statuswerte();
end;

procedure TForm1.b_neuStartenClick(Sender: TObject);
begin
 t_hunger.enabled := true;
  x:= 8;
  n := 1;
  Image1.Picture.LoadFromFile('frosch_start.png');
  meinPet := TPet.Create('Jonny', 'Frosch');
  Statuswerte();
end;

procedure TForm1.b_schlafenClick(Sender: TObject);
begin
  meinPet.schlafen;
  Statuswerte();
end;

procedure TForm1.b_fuetternClick(Sender: TObject);
begin
  meinPet.fuettern;
  Statuswerte();
end;

procedure TForm1.b_nameClick(Sender: TObject);
begin
  meinPet.nameaendern(e_name.text);
  Statuswerte();
end;

end.
