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
#define MyAppVersion "0.3.0"
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
DisableProgramGroupPage=no
DisableDirPage=no
DisableReadyPage=no
; Lizenzseite, die angenommen werden muss.
LicenseFile=lizenz_vorlagen\INSTALLER_LIZENZ.txt
; Kurzer Hinweis vor der Installation, wie viel Platz gebraucht wird.
InfoBeforeFile=lizenz_vorlagen\INSTALLER_HINWEIS.txt
OutputDir=..\dist\installer
OutputBaseFilename=Natter-Setup
SetupIconFile={#MyAppIcon}
Compression=lzma2
SolidCompression=yes
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
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

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
; Gelöscht wird nur, was Natter selbst mitbringt und vollständig
; ersetzt. "beispielprojekte" gehört dazu, weil die IDE ein
; Beispiel vor dem Öffnen ins Heimverzeichnis kopiert
; (ide/shell/startbild.py, beispiel_kopieren) - in der Installation
; arbeitet niemand darin. Der übrige Inhalt von site-packages
; (PySide6, numpy, ...) bleibt unangetastet; den verwaltet pip.
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\ide"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\pcl"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\docs"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\design"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\schemas"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\templates"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages\beispielprojekte"

[Files]
Source: "..\dist\Natter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

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

[UninstallDelete]
; Der Uninstaller entfernt von sich aus nur, was der Installer gelegt
; hat. In python\ entsteht danach aber noch einiges: __pycache__ zu
; jedem Modul und alles, was über das Menü "Pakete" nachinstalliert
; wird. Ohne diese Zeile bliebe nach dem Deinstallieren ein Ordner mit
; hunderten Megabyte stehen (M13).
Type: filesandordirs; Name: "{app}\python"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
