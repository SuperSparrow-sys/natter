unit u_main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls, u_TAmpel;

type

  { TForm1 }

  TForm1 = class(TForm)
    b_einschalten: TButton;
    b_wechseln: TButton;
    b_Auschalten: TButton;
    Label1: TLabel;
    Shape1: TShape;
    s_rot: TShape;
    s_gelb: TShape;
    s_gruen: TShape;
    procedure b_AuschaltenClick(Sender: TObject);
    procedure b_einschaltenClick(Sender: TObject);
    procedure b_wechselnClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure ampel_zeichnen();
    procedure s_rotChangeBounds(Sender: TObject);
  private

  public

  end;

var
  Form1: TForm1;
  meineAmpel: TAmpel;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.ampel_zeichnen();
var
  phase: integer;
begin

  phase := meineAmpel.get_ampelphasen;

  if meineAmpel.get_aktiviert() then

  begin
    if phase = 1 then
    begin
      s_gruen.brush.color := clgreen;
      s_rot.brush.color := clblack;
      s_gelb.brush.color := clblack;
    end;

    if phase = 3 then
    begin
      s_gruen.brush.color := clblack;
      s_rot.brush.color := clred;
      s_gelb.brush.color := clblack;
    end;

    if (phase = 4) or (phase=2) then
    begin
      s_gruen.brush.color := clblack;
      s_rot.brush.color := clblack;
      s_gelb.brush.color := clyellow;
    end;
  end
  else
  begin
    s_gruen.brush.color := clblack;
    s_rot.brush.color := clblack;
    s_gelb.brush.color := clblack;
  end;

end;

procedure TForm1.s_rotChangeBounds(Sender: TObject);
begin

end;

procedure TForm1.FormCreate(Sender: TObject);
begin
  meineAmpel := TAmpel.Create(True, 1);
  ampel_zeichnen();
end;

procedure TForm1.b_einschaltenClick(Sender: TObject);
begin
  meineAmpel.anschalten();
  ampel_zeichnen();

end;

procedure TForm1.b_wechselnClick(Sender: TObject);
begin
  meineAmpel.umschalten;
  ampel_zeichnen();
end;

procedure TForm1.b_AuschaltenClick(Sender: TObject);
begin
  meineAmpel.ausschalten();
  ampel_zeichnen();
end;

end.
