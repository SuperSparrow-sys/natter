@echo off
rem Startet Natter-pruefen.ps1 per Doppelklick.
rem
rem Der Umweg ueber diese Datei ist noetig, weil Windows das
rem Ausfuehren von PowerShell-Skripten in zwei Faellen verweigert:
rem auf einem frisch aufgesetzten Rechner steht die
rem Ausfuehrungsrichtlinie auf "Restricted", und Dateien aus einem
rem entpackten ZIP tragen die Markierung "aus dem Internet". Beides
rem fuehrt beim Rechtsklick auf die .ps1 zu einer roten Meldung
rem statt zum Ergebnis.
rem
rem -ExecutionPolicy Bypass gilt nur fuer diesen einen Aufruf. An den
rem Einstellungen des Rechners aendert sich nichts.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Natter-pruefen.ps1"
