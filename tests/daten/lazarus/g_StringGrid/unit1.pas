unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, Grids, StdCtrls,
  ActnList;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_schliessen: TButton;
    b_uebernehmen: TButton;
    b_zurueksetzen: TButton;
    e_name: TEdit;
    e_Vorname: TEdit;
    e_datum: TEdit;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    sg_Tabelle: TStringGrid;
    procedure b_schliessenClick(Sender: TObject);
    procedure b_uebernehmenClick(Sender: TObject);
    procedure b_zurueksetzenClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  Name, datum, vorname: string;
  zeile: integer;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.FormCreate(Sender: TObject);
begin
  zeile := 1;

end;

procedure TForm1.b_uebernehmenClick(Sender: TObject);
begin
  Name := e_name.Text;
  vorname := e_vorname.Text;
  datum := e_datum.Text;

  sg_tabelle.rowcount := zeile + 1;

  if (length(Name) > 10) or (length(Vorname) > 10) then
    begin
      ShowMessage('Deinen Eingaben sind zu Lang');
      zeile := zeile - 1;
    end

  else
  begin
    sg_tabelle.cells[0, zeile] := IntToStr(zeile);
    sg_tabelle.cells[1, zeile] := Name;
    sg_tabelle.cells[2, zeile] := Vorname;
    sg_tabelle.cells[3, zeile] := Datum;
  end;
  zeile := zeile + 1;

end;

procedure TForm1.b_schliessenClick(Sender: TObject);
begin
  Close;
end;

procedure TForm1.b_zurueksetzenClick(Sender: TObject);
begin
  zeile := 1;
  sg_tabelle.rowcount := zeile + 1;

  sg_tabelle.cells[0, zeile] := '';
  sg_tabelle.cells[1, zeile] := '';
  sg_tabelle.cells[2, zeile] := '';
  sg_tabelle.cells[3, zeile] := '';
end;

end.
