"""`Zertifikat-entfernen.ps1` findet die Zertifikate des Exe-Exports.

Punkt 318: nach dem Deinstallieren blieb in jedem Konto, das einmal
als Exe exportiert hatte, ein selbst ausgestelltes Stammzertifikat
„Natter Programme dieses Rechners“ stehen, und das Skript im Paket
für die Schule suchte nur den Fingerabdruck des Natter-Zertifikats.

Geprüft wird die Auswahl im Skript, nicht das Entfernen selbst: das
Skript gegen die echten Speicher laufen zu lassen, hieße, am
Zertifikatspeicher des Rechners etwas zu ändern. Die Probezertifikate
sind deshalb Objekte mit den Eigenschaften eines Zertifikats.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from ide.export.signatur import ZERT_NAME

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "tools" / "paket" / "Zertifikat-entfernen.ps1"

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows PowerShell gibt es nur unter Windows"
)


def test_das_skript_findet_das_zertifikat_des_exports() -> None:
    # Die Funktion aus dem Skript holen, ohne das Skript auszuführen:
    # dessen Hauptteil verlangt Administratorrechte und schreibt in
    # die Speicher.
    befehl = (
        "$ast = [System.Management.Automation.Language.Parser]::ParseFile("
        "$env:NATTER_SKRIPT, [ref]$null, [ref]$null); "
        "$zuweisung = $ast.FindAll({ param($k) "
        "$k -is [System.Management.Automation.Language.AssignmentStatementAst] "
        "-and $k.Left.Extent.Text -eq '$EXPORT_NAME' }, $true) | "
        "Select-Object -First 1; "
        "$funktion = $ast.FindAll({ param($k) "
        "$k -is [System.Management.Automation.Language.FunctionDefinitionAst] "
        "-and $k.Name -eq 'Test-Exportzertifikat' }, $true) | "
        "Select-Object -First 1; "
        "Invoke-Expression $zuweisung.Extent.Text; "
        "Invoke-Expression $funktion.Extent.Text; "
        "foreach ($name in $env:NATTER_EXPORT, 'CN=Natter Codesignatur', "
        "'CN=Anderes Programm') { "
        "  $probe = [pscustomobject]@{ Subject = $name; Thumbprint = 'AB12' }; "
        "  Write-Output ($name + '=' + (Test-Exportzertifikat $probe)) }"
    )
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", befehl],
        capture_output=True, text=True, timeout=60,
        env={
            **os.environ,
            "NATTER_SKRIPT": str(SKRIPT),
            "NATTER_EXPORT": f"CN={ZERT_NAME}",
        },
    )

    zeilen = dict(
        z.rsplit("=", 1) for z in ergebnis.stdout.splitlines() if "=" in z
    )
    assert zeilen == {
        f"CN={ZERT_NAME}": "True",
        "CN=Natter Codesignatur": "False",
        "CN=Anderes Programm": "False",
    }, ergebnis.stderr


def test_der_schalter_kommt_vom_doppelklick_starter_an() -> None:
    """Ohne `%*` bliebe `-Exportzertifikate` am `.cmd` hängen."""
    starter = SKRIPT.with_suffix(".cmd").read_text(encoding="utf-8")
    skript = SKRIPT.read_text(encoding="utf-8")

    assert "[switch]$Exportzertifikate" in skript
    assert starter.rstrip().endswith("%*")
    # Die Konto-Speicher werden vor dem Wechsel zum Administrator
    # bearbeitet; danach wären es die eines anderen Kontos.
    assert skript.index("if ($Exportzertifikate)") < skript.index("-Verb RunAs")
