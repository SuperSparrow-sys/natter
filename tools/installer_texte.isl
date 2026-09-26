; Natters Fassung der Setup-Texte (Punkt 30 der offenen Punkte).
;
; Wird in tools/natter.iss hinter compiler:Languages\German.isl geladen
; und überschreibt dort jede Meldung, die mit „Sie“ oder „Ihr“
; anspricht. Natter spricht niemanden direkt an, auch der Installer
; nicht (AGENTS.md, „Sichtbare Texte und Kommentare“). Geprüft wird das
; in tests/test_textstil.py: keine Meldung aus German.isl mit Anrede
; bleibt ohne Gegenstück hier.

[Messages]
SetupLdrStartupMessage=%1 wird jetzt installiert. Fortfahren?
SetupFileMissing=Die Datei %1 fehlt im Installationsordner. Das Problem beheben oder eine neue Kopie des Programms besorgen.
SetupFileCorrupt=Die Setup-Dateien sind beschädigt. Eine neue Kopie des Programms besorgen.
SetupFileCorruptOrWrongVer=Die Setup-Dateien sind beschädigt oder passen nicht zu dieser Version des Setups. Das Problem beheben oder eine neue Kopie des Programms besorgen.
WindowsVersionNotSupported=Dieses Programm unterstützt die auf diesem Computer installierte Windows-Version nicht.
AdminPrivilegesRequired=Für diese Installation ist eine Anmeldung als Administrator nötig.
PowerUserPrivilegesRequired=Für diese Installation ist eine Anmeldung als Administrator oder als Mitglied der Gruppe Hauptbenutzer nötig.
SetupAppRunningError=%1 läuft gerade.%n%nAlle laufenden Fenster von %1 schließen und dann „OK“ wählen, oder „Abbrechen“, um das Setup zu beenden.
UninstallAppRunningError=%1 läuft gerade.%n%nAlle laufenden Fenster von %1 schließen und dann „OK“ wählen, oder „Abbrechen“, um die Deinstallation zu beenden.
PrivilegesRequiredOverrideInstruction=Installationsart wählen
PrivilegesRequiredOverrideText1=%1 lässt sich für alle Benutzer (mit Administratorrechten) oder nur für das angemeldete Konto installieren.
PrivilegesRequiredOverrideText2=%1 lässt sich nur für das angemeldete Konto oder für alle Benutzer (mit Administratorrechten) installieren.
PrivilegesRequiredOverrideCurrentUser=Nur für das angemeldete &Konto
PrivilegesRequiredOverrideCurrentUserRecommended=Nur für das angemeldete &Konto (empfohlen)
ExitSetupMessage=Das Setup ist noch nicht abgeschlossen. Wird es jetzt beendet, ist das Programm nicht installiert.%n%nDas Setup lässt sich später erneut ausführen, um die Installation abzuschließen.%n%nSetup verlassen?
SelectLanguageLabel=Sprache für die Installation:
BrowseDialogLabel=Einen Ordner auswählen und dann „OK“ wählen.
WelcomeLabel2=[name/ver] wird jetzt auf diesem Computer installiert.%n%nAndere Programme vorher zu schließen, erspart Rückfragen während der Installation.
PasswordLabel3=Das Passwort eingeben und dann „Weiter“ wählen. Groß- und Kleinschreibung zählt.
IncorrectPassword=Das Passwort stimmt nicht. Bitte erneut versuchen.
LicenseLabel=Vor dem Fortfahren die folgenden wichtigen Informationen lesen.
LicenseLabel3=Die folgenden Lizenzbedingungen lesen. Mit der Bildlaufleiste oder der Taste „Bild ab“ geht es weiter nach unten.
InfoBeforeLabel=Vor dem Fortfahren die folgenden wichtigen Informationen lesen.
InfoBeforeClickLabel=Mit „Weiter“ geht es mit dem Setup weiter.
InfoAfterLabel=Vor dem Fortfahren die folgenden wichtigen Informationen lesen.
InfoAfterClickLabel=Mit „Weiter“ geht es mit dem Setup weiter.
UserInfoDesc=Die Benutzerdaten eintragen.
UserInfoNameRequired=Ein Name muss eingetragen sein.
SelectDirBrowseLabel=Mit „Weiter“ geht es weiter. Über „Durchsuchen“ lässt sich ein anderer Ordner wählen.
CannotInstallToUNCPath=Das Setup kann nicht in einen UNC-Pfad installieren. Für ein Netzlaufwerk dem Netzwerkpfad vorher einen Laufwerksbuchstaben zuordnen.
InvalidPath=Nötig ist ein vollständiger Pfad mit Laufwerksbuchstaben, z. B.:%n%nC:\Beispiel%n%noder ein UNC-Pfad in der Form:%n%n\\Server\Freigabe
InvalidDrive=Das Laufwerk bzw. der UNC-Pfad existiert nicht oder ist nicht erreichbar. Einen anderen Ordner wählen.
DiskSpaceWarning=Das Setup braucht mindestens %1 KB freien Speicherplatz, auf dem gewählten Laufwerk sind aber nur %2 KB frei.%n%nTrotzdem fortfahren?
DirExists=Der Ordner:%n%n%1%n%nexistiert bereits. Trotzdem in diesen Ordner installieren?
SelectComponentsLabel2=Die Komponenten auswählen, die installiert werden sollen, dann „Weiter“ wählen.
NoUninstallWarning=Die folgenden Komponenten sind auf diesem Computer bereits installiert:%n%n%1%n%nWerden sie hier abgewählt, bleiben sie trotzdem auf dem Computer.%n%nTrotzdem fortfahren?
SelectTasksLabel2=Die zusätzlichen Aufgaben auswählen, die das Setup bei der Installation von [name] ausführen soll, dann „Weiter“ wählen.
SelectStartMenuFolderBrowseLabel=Mit „Weiter“ geht es weiter. Über „Durchsuchen“ lässt sich ein anderer Ordner wählen.
MustEnterGroupName=Ein Ordnername muss eingetragen sein.
ReadyLabel1=Das Setup ist bereit, [name] auf diesem Computer zu installieren.
ReadyLabel2a=„Installieren“ beginnt mit der Installation, „Zurück“ führt zu den Einstellungen.
ReadyLabel2b=„Installieren“ beginnt mit der Installation.
StopDownload=Den Download wirklich abbrechen?
StopExtraction=Das Entpacken wirklich abbrechen?
PreviousInstallNotCompleted=Eine frühere Installation oder Deinstallation ist nicht abgeschlossen. Der Computer muss dafür neu starten.%n%nNach dem Neustart das Setup erneut ausführen, um [name] zu installieren.
CannotContinue=Das Setup kann nicht fortfahren. „Abbrechen“ beendet es.
PrepareToInstallNeedsRestart=Das Setup muss den Computer neu starten. Danach das Setup erneut ausführen, um die Installation von [name] abzuschließen.%n%nJetzt neu starten?
InstallingLabel=[name] wird auf diesem Computer installiert.
FinishedLabelNoIcons=[name] ist auf diesem Computer installiert.
FinishedLabel=[name] ist auf diesem Computer installiert. Gestartet wird es über die angelegten Verknüpfungen.
ClickFinish=„Fertigstellen“ beendet das Setup.
FinishedRestartLabel=Um die Installation von [name] abzuschließen, muss der Computer neu starten. Jetzt neu starten?
FinishedRestartMessage=Um die Installation von [name] abzuschließen, muss der Computer neu starten.%n%nJetzt neu starten?
SelectDiskLabel2=Datenträger %1 einlegen und „OK“ wählen.%n%nLiegen die Dateien dieses Datenträgers in einem anderen als dem angezeigten Ordner, den richtigen Pfad eingeben oder „Durchsuchen“ wählen.
SelectDirectoryLabel=Angeben, wo der nächste Datenträger liegt.
SetupAborted=Das Setup ließ sich nicht abschließen.%n%nDas Problem beheben und das Setup erneut starten.
ErrorRestartingComputer=Das Setup konnte den Computer nicht neu starten. Den Neustart von Hand ausführen.
ConfirmUninstall=%1 und alle zugehörigen Komponenten wirklich entfernen?
UninstallStatusLabel=%1 wird von diesem Computer entfernt.
UninstalledAll=%1 ist von diesem Computer entfernt.
UninstalledMost=Entfernen von %1 beendet.%n%nEinige Komponenten ließen sich nicht entfernen und können von Hand gelöscht werden.
UninstalledAndNeedsRestart=Um die Deinstallation von %1 abzuschließen, muss der Computer neu starten.%n%nJetzt neu starten?
ConfirmDeleteSharedFile2=Laut System benutzt kein anderes Programm mehr die folgende gemeinsame Datei. Soll sie entfernt werden?%nBenutzt doch noch ein Programm diese Datei, funktioniert es danach vielleicht nicht mehr. Im Zweifel „Nein“ wählen; die Datei zu behalten, schadet dem System nicht.
AddonHostProgramNotFound=%1 ließ sich im gewählten Ordner nicht finden.%n%nTrotzdem fortfahren?
