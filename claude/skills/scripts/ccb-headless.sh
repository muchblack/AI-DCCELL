#!/bin/bash
# ccb-headless.sh — Toggle CCB headless mode.
# When active, /ask gemini and /ask codex use CLI subprocess instead of tmux pane.
FLAG="/tmp/.ccb-headless"

if [ -f "$FLAG" ]; then
    rm -f "$FLAG"
    echo "Headless mode OFF (pane mode)"
else
    touch "$FLAG"
    echo "Headless mode ON (subprocess mode)"
fi
