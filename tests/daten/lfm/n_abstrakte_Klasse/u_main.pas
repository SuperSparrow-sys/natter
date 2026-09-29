unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, u_haustiere;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_Haustier_erzeugen: TButton;
    b_Geraeusch_machen: TButton;
    cb_typ: TComboBox;
    e_name: TEdit;
    Label1: TLabel;
    Label2: TLabel;
    m_ausgabe: TMemo;
    procedure b_Geraeusch_machenClick(Sender: TObject);
    procedure b_Haustier_erzeugenClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
 meinHaustier : THaustier;

implementation

{$R *.lfm}

{ TForm1 }


procedure TForm1.b_Haustier_erzeugenClick(Sender: TObject);
begin

  if cb_typ.Text = 'Hund' then
    meinHaustier := THund.Create('Moddin')
  else if cb_typ.Text = 'Katze' then
    meinHaustier := TKatze.Create('Moritz');

end;

procedure TForm1.b_Geraeusch_machenClick(Sender: TObject);
begin
  if cb_typ.Text = 'Hund' then
  begin
    m_ausgabe.Lines.Clear;
    m_ausgabe.Lines.add('Moddin');
    m_ausgabe.Lines.add(meinHaustier.geraeuch_machen);
  end

  else if cb_typ.Text = 'Katze' then
  begin
    m_ausgabe.Lines.Clear;
    m_ausgabe.Lines.add('Moritz');
    m_ausgabe.Lines.add(meinHaustier.geraeuch_machen);
  end;
end;

procedure TForm1.FormCreate(Sender: TObject);
begin

end;

end.
