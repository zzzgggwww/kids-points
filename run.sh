#!/bin/bash
# Kids Points — 守护进程脚本
# 自动重启 Python 服务，崩溃后 3 秒重新拉起
# 用法: ./run.sh &

cd "$(dirname "$0")"

# 如果已有进程在跑，先杀掉
pkill -f "python.*app.py" 2>/dev/null
sleep 1

while true; do
    echo "[$(date)] 🏝️ Starting Kids Points..."
    /opt/hermes/.venv/bin/python3 app.py
    code=$?
    echo "[$(date)] Process exited (code=$code). Restarting in 3s..."
    sleep 3
done
