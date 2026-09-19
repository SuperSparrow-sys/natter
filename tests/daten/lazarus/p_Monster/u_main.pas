unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls,
  u_Monster;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_naechsteRunde: TButton;
    b_feuerangriff: TButton;
    b_energiebooster: TButton;
    b_wasserangriff: TButton;
    b_heilung: TButton;
    i_wassermonster: TImage;
    i_feuermonster: TImage;
    m_statusanzeige1: TMemo;
    m_statusanzeige2: TMemo;
    procedure b_energieboosterClick(Sender: TObject);
    procedure b_feuerangriffClick(Sender: TObject);
    procedure b_heilungClick(Sender: TObject);
    procedure b_naechsteRundeClick(Sender: TObject);
    procedure b_wasserangriffClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  monster1: TFeuermonster;
  monster2: TWassermonster;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.FormCreate(Sender: TObject);
begin
  randomize;

  monster1 := TFeuermonster.create('Feurmonster');
  m_statusanzeige1.text := monster1.infos_ausgeben;
  monster2 := TWassermonster.create('Wassermosnter');
  m_statusanzeige2.text := monster2.infos_ausgeben;
end;

procedure TForm1.b_feuerangriffClick(Sender: TObject);
begin
  monster1.feuerangriff(monster2);
  m_statusanzeige2.text := monster2.infos_ausgeben;
  m_statusanzeige1.text := monster1.infos_ausgeben;

end;

procedure TForm1.b_heilungClick(Sender: TObject);
begin
  monster2.heilung;
  m_statusanzeige2.text := monster2.infos_ausgeben;
  m_statusanzeige1.text := monster1.infos_ausgeben;
end;

procedure TForm1.b_naechsteRundeClick(Sender: TObject);
begin
  monster1.energie_erhalten;
  monster2.energie_erhalten;
  m_statusanzeige2.text := monster2.infos_ausgeben;
  m_statusanzeige1.text := monster1.infos_ausgeben;
end;

procedure TForm1.b_wasserangriffClick(Sender: TObject);
begin
  monster2.wasserangriff(monster1);
  m_statusanzeige2.text := monster2.infos_ausgeben;
  m_statusanzeige1.text := monster1.infos_ausgeben;
end;

procedure TForm1.b_energieboosterClick(Sender: TObject);
begin
  monster1.energieboost;
  m_statusanzeige2.text := monster2.infos_ausgeben;
  m_statusanzeige1.text := monster1.infos_ausgeben;
end;


end.

