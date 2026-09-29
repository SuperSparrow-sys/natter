unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, Grids;

type

  { TForm1 }

  TForm1 = class(TForm)
    Button1: TButton;
    b_wurfeln: TButton;
    Label1: TLabel;
    l_zahl: TLabel;
    l_punkte: TLabel;
    l_leben: TLabel;
    sg_tabelle: TStringGrid;
    procedure Button1Click(Sender: TObject);
    procedure b_wurfelnClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    function wuerfeln: integer;
  private

  public

  end;

var
  Form1: TForm1;
  punkte, leben, zahl: integer;

implementation

{$R *.lfm}

{ TForm1 }

function TForm1.wuerfeln: integer;
begin
  Result := random(6) + 1;
end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  leben := 3;
  punkte := 0;
  zahl := 0;

  l_zahl.Caption := ('Gewürfelte Zahl: ' + IntToStr(zahl));
  l_punkte.Caption := ('Punkte: ' + IntToStr(punkte));
  l_leben.Caption := ('Leben: ' + IntToStr(leben));

  randomize;
end;

procedure TForm1.b_wurfelnClick(Sender: TObject);
begin
  zahl := wuerfeln;
  if zahl = 6 then leben := leben - 1
  else
    punkte := punkte + zahl;

  l_zahl.Caption := ('Gewürfelte Zahl: ' + IntToStr(zahl));
  l_punkte.Caption := ('Punkte: ' + IntToStr(punkte));
  l_leben.Caption := ('Leben: ' + IntToStr(leben));

  if leben = 0 then
  begin
    Name := inputbox('VERLOREN', 'Bitte gib deinen Namen ein', '');
    b_wurfeln.Enabled := False;
    sg_tabelle.RowCount := sg_tabelle.RowCount + 1;
    sg_tabelle.Cells[0, sg_tabelle.RowCount - 1] := Name;
    sg_tabelle.Cells[1, sg_tabelle.RowCount - 1] := IntToStr(punkte);
    punkte := 0;
    Name := '';
    leben := 3;
    l_zahl.Caption := ('Gewürfelte Zahl: ' + IntToStr(zahl));
    l_punkte.Caption := ('Punkte: ' + IntToStr(punkte));
    l_leben.Caption := ('Leben: ' + IntToStr(leben));
    b_wurfeln.Enabled := True;

  end;

end;

procedure TForm1.Button1Click(Sender: TObject);
begin

end;



end.
