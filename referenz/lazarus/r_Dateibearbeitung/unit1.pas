unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_hinzufuegen: TButton;
    b_speichern: TButton;
    b_auslesen: TButton;
    m_name: TEdit;
    m_ausgabe: TMemo;
    procedure b_auslesenClick(Sender: TObject);
    procedure b_hinzufuegenClick(Sender: TObject);
    procedure b_speichernClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  textdatei: text;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.FormCreate(Sender: TObject);
begin
  assignFile(textdatei, 'namensliste.txt');
end;

procedure TForm1.b_auslesenClick(Sender: TObject);
var
  inhalt: string;
begin
  m_ausgabe.Lines.Clear;
  Reset(textdatei);
  repeat
    ReadLn(textdatei, inhalt);
    m_ausgabe.Lines.Add(inhalt);
  until EOF(textdatei);
  CloseFile(textdatei);
end;

procedure TForm1.b_hinzufuegenClick(Sender: TObject);
begin

end;

procedure TForm1.b_speichernClick(Sender: TObject);
begin

end;

end.

