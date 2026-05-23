#!/bin/bash
# Auto-restart wrapper for Kids Points
# Usage: ./run.sh &
cd "$(dirname "$0")"

while true; do
    echo "[$(date)] Starting Kids Points..."
    /opt/hermes/.venv/bin/python3 app.py
    code=$?
    echo "[$(date)] Process exited (code=$code). Restarting in 3s..."
    sleep 3
done
