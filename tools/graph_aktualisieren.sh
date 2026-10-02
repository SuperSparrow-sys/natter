#!/usr/bin/env bash
# Hält den Wissensgraphen in graphify-out/ auf dem Stand des
# Arbeitsbaums (siehe AGENTS.md, Abschnitt „Wissensgraph").
#
#     bash tools/graph_aktualisieren.sh              nur wenn nötig
#     bash tools/graph_aktualisieren.sh --einrichten Git-Hooks anlegen
#
# Aufgerufen wird es am Ende jeder Antwort von Claude Code (Hook
# „Stop" in .claude/settings.json) und von den Git-Hooks nach Commit,
# Checkout und Merge. Beide Wege kehren sofort zurück:
#
# - Ob sich etwas geändert hat, entscheidet ein Fingerabdruck aller
#   Python-Dateien im Arbeitsbaum, eingecheckt oder nicht. Git
#   berechnet ihn über einen eigenen Index und hasht dabei nur
#   Dateien neu, deren Zeitstempel sich geändert hat - das dauert
#   Sekundenbruchteile. `graphify update .` dagegen braucht auch ohne
#   jede Änderung gut zehn Sekunden.
# - Der Fingerabdruck hängt nur am Inhalt, nicht am Commit. Ein
#   Commit dessen, was schon im Graphen steht, löst deshalb keinen
#   zweiten Lauf aus.
# - Graphify läuft im Hintergrund, und immer nur einer. Ändert sich
#   während des Laufs etwas, holt der nächste Aufruf es nach.
#
# Ohne graphify oder ohne graphify-out/ (etwa in den Arbeitsbäumen
# unter .claude/worktrees) tut das Skript nichts.

set -u

wurzel=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$wurzel" || exit 0

if [ "${1:-}" = "--einrichten" ]; then
    hooks=$(git rev-parse --git-path hooks)
    mkdir -p "$hooks"
    for name in post-commit post-checkout post-merge; do
        printf '%s\n' '#!/bin/sh' \
            '# Angelegt von tools/graph_aktualisieren.sh --einrichten' \
            'bash tools/graph_aktualisieren.sh >/dev/null 2>&1 || true' \
            > "$hooks/$name"
        chmod +x "$hooks/$name"
    done
    echo "Git-Hooks angelegt in $hooks"
    exit 0
fi

command -v graphify >/dev/null 2>&1 || exit 0
[ -d graphify-out ] || exit 0

sperre=graphify-out/.laeuft
stempel=graphify-out/.stand
index=graphify-out/.index

# Eine Sperre, die älter als eine Viertelstunde ist, stammt von einem
# abgebrochenen Lauf.
if [ -d "$sperre" ] && [ -n "$(find "$sperre" -maxdepth 0 -mmin +15)" ]; then
    rmdir "$sperre" 2>/dev/null
fi
mkdir "$sperre" 2>/dev/null || exit 0

cp "$(git rev-parse --git-path index)" "$index" 2>/dev/null
# Ohne tests/: die stehen nicht im Graphen (.graphifyignore), eine
# Änderung dort braucht keinen Lauf.
stand=$(GIT_INDEX_FILE=$index git add -A -- '*.py' ':!tests/' \
        2>/dev/null &&
    GIT_INDEX_FILE=$index git write-tree 2>/dev/null)
if [ -z "$stand" ] || [ "$stand" = "$(cat "$stempel" 2>/dev/null)" ]; then
    rmdir "$sperre"
    exit 0
fi

# GRAPHIFY_FORCE: Ohne den Schalter behält graphify den alten Graphen,
# sobald der neue weniger Knoten hat - nach jedem Löschen von Code.
# Der Schutz gilt Knoten, die ein Sprachmodell aus Dokumenten gewonnen
# hat; hier entsteht der Graph allein aus dem Code.
(
    if GRAPHIFY_FORCE=1 graphify update . \
        >graphify-out/letzter_lauf.log 2>&1; then
        printf '%s\n' "$stand" >"$stempel"
    fi
    rmdir "$sperre"
) </dev/null >/dev/null 2>&1 &
exit 0
