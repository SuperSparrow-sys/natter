; Installer für Natter selbst (nicht ein Schülerprojekt) - Nutzer-
; Feedback September 2026: "Programm als exe nur zum Download auf z. B.
; einer Website, man installiert die exe und kann dann auch eine
; .natter-Datei einfach öffnen". Baut auf dem Ordner auf, den
; tools/ide_paketieren.py erzeugt (dist\Natter): Natter.exe, daneben
; eine vollständige, eigene Python-Installation im Ordner python\.
;
; Voraussetzung: dist\Natter muss bereits existieren, siehe
;   uv run python -m tools.ide_paketieren
;
; Kompilieren (Inno Setup 6):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" tools\natter.iss
; Ergebnis: dist\installer\Natter-Setup.exe (noch unsigniert - Natter.exe
; darin ist bereits signiert, weil tools/ide_paketieren.py das vor dem
; Kompilieren erledigt). Den Installer selbst danach separat signieren:
;   powershell -NoProfile -ExecutionPolicy Bypass -File tools\signieren\datei_signieren.ps1 -Datei dist\installer\Natter-Setup.exe
; (Beides zusammen automatisiert tools/signieren/README.md, Abschnitt
; "Kompletter Bau".)

#define MyAppName "Natter"
#define MyAppVersion "0.3.5"
#define MyAppPublisher "Natter-Projekt"
#define MyAppExeName "Natter.exe"
#define MyAppIcon "..\ide\assets\icons\app.ico"

[Setup]
; Feste, projekteigene AppId (nicht neu würfeln - sonst behandelt
; Windows spätere Versionen als komplett neue Anwendung statt als
; Update, siehe Inno-Setup-Dokumentation zu AppId).
AppId={{961DA420-CA63-4436-9023-9CA411B620DA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Die klassischen Schritte einer Windows-Installation (M13):
; Willkommen, Lizenz, Zielordner, Startmenü-Ordner, Zusatzaufgaben,
; Zusammenfassung, Fortschritt, Fertigstellen.
;
; Inno Setup 6 blendet die Willkommensseite in der modernen Darstellung
; standardmäßig aus - hier ausdrücklich wieder eingeschaltet.
DisableWelcomePage=no
; "auto": bei einer Erstinstallation erscheinen Zielordner und
; Startmenü-Ordner, bei einem Update nicht - dann gelten die der
; vorhandenen Installation, und die Willkommensseite nennt, was
; aktualisiert wird (Punkt 26; [Code] unten).
DisableProgramGroupPage=auto
DisableDirPage=auto
DisableReadyPage=no
; Eine laufende Natter hält Dateien in python\ offen; vor dem
; Ersetzen wird sie über den Neustart-Manager von Windows geschlossen.
CloseApplications=yes
RestartApplications=no
; Lizenzseite, die angenommen werden muss.
LicenseFile=lizenz_vorlagen\INSTALLER_LIZENZ.txt
; Kurzer Hinweis vor der Installation, wie viel Platz gebraucht wird.
InfoBeforeFile=lizenz_vorlagen\INSTALLER_HINWEIS.txt
; Der Uninstaller entsteht erst beim Installieren, also lange nach
; dem Bau - ohne diese beiden Zeilen bliebe er als einzige unsignierte
; Datei auf dem Rechner zurueck, und Smart App Control liesse sich
; Natter dann nicht mehr deinstallieren. "natter" ist der Name, den
; der Compiler-Aufruf mit /Snatter=... belegt (siehe
; tools/auslieferung_bauen.py).
#ifndef OhneProgramm
SignTool=natter
SignedUninstaller=yes
#endif
OutputDir=..\dist\installer
OutputBaseFilename=Natter-Setup
SetupIconFile={#MyAppIcon}
Compression=lzma2
SolidCompression=yes
; Komprimiert auf acht Kernen statt auf einem. Gemessen an 30.161
; Dateien (1,2 GB): 185 statt 691 Sekunden, die Setup-Datei wird dafür
; 0,7 % größer. Das Format bleibt LZMA2, das Inno beim Installieren
; ohnehin entpackt - nur in acht Blöcken statt in einem.
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=8
WizardStyle=modern
; PySide6 liefert nur 64-Bit-DLLs.
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
; Steht in "Apps & Features" neben der Anwendung.
AppPublisherURL=https://github.com/SuperSparrow-sys/natter
AppSupportURL=https://github.com/SuperSparrow-sys/natter
AppUpdatesURL=https://github.com/SuperSparrow-sys/natter
; Windows 10 oder neuer - PySide6 setzt das ohnehin voraus.
MinVersion=10.0
; Damit der Explorer die neue .natter-Verknüpfung sofort übernimmt.
ChangesAssociations=yes
; HKA statt HKLM/HKCU: installiert je nach Adminrechten passend
; systemweit oder nur für den aktuellen Nutzer - praktisch für
; Schulrechner mit unterschiedlichen Berechtigungen.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
; Nur Deutsch, ohne Frage nach der Setup-Sprache: Natter ist
; durchgehend deutsch. installer_texte.isl überschreibt jede Meldung
; aus German.isl, die mit "Sie" oder "Ihr" anspricht (Punkt 30).
Name: "german"; MessagesFile: "compiler:Languages\German.isl,installer_texte.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
; Die Dateiverknüpfung als Zusatzaufgabe statt stillschweigend: auf
; einem Schulrechner kann daneben eine andere Umgebung liegen, die
; .natter ebenfalls beansprucht.
Name: "natterverknuepfung"; Description: "{cm:AssocFileExtension,{#MyAppName},.natter}"

[InstallDelete]
; Inno Setup überschreibt und ergänzt, löscht aber nichts, was in
; der neuen Fassung fehlt. Ohne diesen Abschnitt bleiben bei jedem
; Update die Dateien der vorigen Fassung liegen. Gefunden beim Bau
; 0.2.0: die Planungsunterlagen in "docs" standen nach dem Update
; weiter da, obwohl die neue Fassung nur noch zwei Hilfeseiten
; mitbringt. Bei Python-Paketen wäre das schlimmer als unsauber -
; ein entferntes Modul bliebe importierbar und könnte das neue
; verdecken.
;
; Bis 0.3.3 wurden nur Natters eigene Ordner in site-packages
; geleert. Beim Update von 0.3.2 blieben dadurch 148 Dateien liegen:
; die Qt-Module unter GPL, die 0.3.3 gar nicht mehr ausliefert, und
; eine zweite natter-0.3.2.dist-info, nach der pip die Fassung als
; 0.3.2 meldete (Punkt 28). Deshalb wird die mitgelieferte Python
; jetzt vollständig ersetzt. Was über "Pakete" nachinstalliert war,
; merkt sich [Code] vorher und installiert es danach wieder.
; Alles, was einem Benutzer gehört, liegt ohnehin außerhalb:
; Projekte unter Dokumente\Natter, Einstellungen unter
; %APPDATA%\Natter.
Type: filesandordirs; Name: "{app}\python"

[Files]
; "OhneProgramm" übersetzt das Skript ohne Programmdateien und ohne
; Signatur - für tests/test_installer_update.py, der Texte und [Code]
; prüft, ohne einen Bau zu brauchen.
#ifndef OhneProgramm
Source: "..\dist\Natter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif
; Nur für das Update, landet nicht in der Installation ([Code]).
Source: "installer_pakete_merken.py"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; .natter-Dateiendung mit Natter verknüpfen - Doppelklick im Explorer
; öffnet das Projekt direkt (gemeldet: "kann dann auch eine
; .natter Datei auch einfach öffnen"). ide/main.py liest den Pfad aus
; sys.argv[1] (siehe _projekt_aus_argv_oeffnen).
; uninsdeletevalue *und* uninsdeletekeyifempty: der Wert allein darf
; nicht stehenbleiben (eine andere Anwendung könnte .natter inzwischen
; für sich beansprucht haben), der leere Schlüssel aber auch nicht -
; nach dem Deinstallieren blieb sonst ein verwaister
; HKCU\Software\Classes\.natter zurück (M13, nachgesehen).
Root: HKA; Subkey: "Software\Classes\.natter"; ValueType: string; ValueName: ""; ValueData: "NatterProjekt"; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: natterverknuepfung
Root: HKA; Subkey: "Software\Classes\NatterProjekt"; ValueType: string; ValueName: ""; ValueData: "Natter-Projekt"; Flags: uninsdeletekey; Tasks: natterverknuepfung
Root: HKA; Subkey: "Software\Classes\NatterProjekt\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: natterverknuepfung
Root: HKA; Subkey: "Software\Classes\NatterProjekt\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: natterverknuepfung
; Reste älterer Fassungen: bis 0.3.3 speicherte der Diagramm-Editor
; Lineale und Minimap unter HKCU\Software\Natter\Diagramm, und nach dem
; Deinstallieren blieb der Schlüssel stehen, dazu ein leerer
; ...\Natter-IDE. Heute steht alles in der INI unter %APPDATA%\Natter.
; dontcreatekey: angelegt wird hier nichts, der Uninstaller entfernt
; nur, was eine ältere Fassung hinterlassen hat.
Root: HKCU; Subkey: "Software\Natter\Diagramm"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Natter\Natter-IDE"; Flags: uninsdeletekeyifempty dontcreatekey
Root: HKCU; Subkey: "Software\Natter"; Flags: uninsdeletekeyifempty dontcreatekey

[UninstallDelete]
; Der Uninstaller entfernt von sich aus nur, was der Installer gelegt
; hat. In python\ entsteht danach aber noch einiges: __pycache__ zu
; jedem Modul und alles, was über das Menü "Pakete" nachinstalliert
; wird. Ohne diese Zeile bliebe nach dem Deinstallieren ein Ordner mit
; hunderten Megabyte stehen (M13).
Type: filesandordirs; Name: "{app}\python"
; Der Cache der Prüfung vor dem Start. Seit ruff mit --no-cache läuft,
; entsteht er nicht mehr; eine ältere Fassung kann ihn aber
; hinterlassen haben. Nicht "{app}" selbst: wählt jemand beim
; Installieren einen Ordner wie "Dokumente", würde eine solche Regel
; ihn beim Entfernen leeren.
Type: filesandordirs; Name: "{app}\.ruff_cache"
Type: dirifempty; Name: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// Update erkennen und nachinstallierte Pakete mitnehmen (Punkte 26
// und 28). Der Eintrag unter ...\Uninstall\<AppId>_is1 ist derselbe,
// den "Apps & Features" liest; DisplayVersion schreibt Inno Setup
// selbst aus AppVersion.
const
  UNINSTALL_SCHLUESSEL =
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{961DA420-CA63-4436-9023-9CA411B620DA}_is1';

var
  AlteFassung: String;
  PaketListe: String;

function InstallierteFassung(): String;
begin
  Result := '';
  if not RegQueryStringValue(HKCU, UNINSTALL_SCHLUESSEL, 'DisplayVersion', Result) then
    RegQueryStringValue(HKLM, UNINSTALL_SCHLUESSEL, 'DisplayVersion', Result);
end;

// Nimmt die nächste Zahl vor dem Punkt aus S heraus.
function NaechsteZahl(var S: String): Integer;
var
  P: Integer;
begin
  P := Pos('.', S);
  if P = 0 then
  begin
    Result := StrToIntDef(S, 0);
    S := '';
  end
  else
  begin
    Result := StrToIntDef(Copy(S, 1, P - 1), 0);
    Delete(S, 1, P);
  end;
end;

// -1, 0 oder 1, je nachdem ob A älter, gleich oder neuer ist als B.
function FassungVergleichen(A, B: String): Integer;
var
  I, X, Y: Integer;
begin
  Result := 0;
  for I := 1 to 3 do
  begin
    X := NaechsteZahl(A);
    Y := NaechsteZahl(B);
    if X < Y then
    begin
      Result := -1;
      Exit;
    end;
    if X > Y then
    begin
      Result := 1;
      Exit;
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  AlteFassung := InstallierteFassung();
  if (AlteFassung <> '') and (FassungVergleichen(AlteFassung, '{#MyAppVersion}') > 0) then
  begin
    SuppressibleMsgBox(
      'Auf diesem Computer ist Natter ' + AlteFassung + ' installiert, eine neuere ' +
      'Fassung als {#MyAppVersion}. Eine ältere Fassung wird nicht darüber installiert.',
      mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

procedure InitializeWizard();
begin
  if AlteFassung = '' then
    Exit;
  if AlteFassung = '{#MyAppVersion}' then
    WizardForm.WelcomeLabel2.Caption :=
      'Natter {#MyAppVersion} ist bereits installiert und wird erneut installiert.'
  else
    WizardForm.WelcomeLabel2.Caption :=
      'Natter ' + AlteFassung + ' ist installiert und wird auf {#MyAppVersion} aktualisiert.';
  WizardForm.WelcomeLabel2.Caption := WizardForm.WelcomeLabel2.Caption + #13#10#13#10 +
    'Projekte und Einstellungen bleiben erhalten. Die mitgelieferten Bibliotheken ' +
    'werden vollständig ersetzt; Pakete, die über "Pakete" nachinstalliert wurden, ' +
    'installiert das Setup danach wieder. Dafür ist eine Internetverbindung nötig.';
end;

// Vor dem Kopieren: mit der Python der alten Installation aufschreiben,
// was nicht mitgeliefert wurde (tools/installer_pakete_merken.py).
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  AltePython: String;
  Code: Integer;
begin
  Result := '';
  PaketListe := ExpandConstant('{userappdata}\Natter\pakete_vor_update.txt');
  AltePython := ExpandConstant('{app}\python\python.exe');
  if (AlteFassung <> '') and FileExists(AltePython) then
  begin
    ExtractTemporaryFile('installer_pakete_merken.py');
    if not Exec(AltePython,
        '"' + ExpandConstant('{tmp}\installer_pakete_merken.py') + '" "' + PaketListe + '"',
        '', SW_HIDE, ewWaitUntilTerminated, Code) then
      Log('Nachinstallierte Pakete ließen sich nicht ermitteln.');
  end;
end;

// Nach dem Kopieren: die gemerkten Pakete mit der neuen Python wieder
// installieren. Klappt das nicht (etwa ohne Netz), bleibt die Liste
// stehen, und die Meldung sagt, wo.
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  Pakete: AnsiString;
begin
  if (CurStep <> ssPostInstall) or (PaketListe = '') or not FileExists(PaketListe) then
    Exit;
  WizardForm.StatusLabel.Caption := 'Nachinstallierte Pakete werden wieder installiert ...';
  if Exec(ExpandConstant('{app}\python\python.exe'),
      '-m pip install --disable-pip-version-check --no-warn-script-location ' +
      '--retries 1 --timeout 15 -r "' + PaketListe + '"',
      '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0) then
    DeleteFile(PaketListe)
  else
  begin
    LoadStringFromFile(PaketListe, Pakete);
    Log('Pakete nicht wieder installiert: ' + String(Pakete));
    SuppressibleMsgBox(
      'Diese über "Pakete" nachinstallierten Pakete ließen sich nicht wieder ' +
      'installieren, vermutlich fehlt die Internetverbindung:' + #13#10#13#10 +
      String(Pakete) + #13#10 +
      'In Natter lassen sich die Pakete später über "Pakete -> Paket installieren ..." ' +
      'erneut installieren. Die Liste steht in ' + PaketListe + '.',
      mbInformation, MB_OK, IDOK);
  end;
end;
