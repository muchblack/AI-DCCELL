#!/bin/bash
# ccb-headless.sh — Toggle CCB headless mode.
# When active, /ask gemini uses CLI subprocess instead of tmux pane (codex retired 2026-05-05).
FLAG="/tmp/.ccb-headless"

if [ -f "$FLAG" ]; then
    rm -f "$FLAG"
    echo "Headless mode OFF (pane mode)"
else
    touch "$FLAG"
    echo "Headless mode ON (subprocess mode)"
fi
