"""
Kids Points System — 小朋友积分系统
Animal Crossing style, FastAPI + SQLite

Tap task → PIN → +N points. Simple as that.
"""

import os
import sqlite3
from datetime import date
from pathlib import Path
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── Config ──────────────────────────────────────────
DB_PATH = Path(__file__).parent / "data" / "points.db"
PIN = os.environ.get("KIDS_PIN", "159357")
KID_NAME = os.environ.get("KID_NAME", "招铭")
PORT = int(os.environ.get("KIDS_PORT", "2020"))

app = FastAPI(title="Kids Points")


# ── Database ────────────────────────────────────────
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                emoji       TEXT    DEFAULT '⭐',
                points      INTEGER DEFAULT 1,
                active      INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS point_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,
                delta       INTEGER NOT NULL,
                note        TEXT,
                created_at  TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
            CREATE INDEX IF NOT EXISTS idx_logs_created
                ON point_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_logs_task
                ON point_logs(task_id, created_at);
        """)
        # Seed default task
        if db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 0:
            db.execute(
                "INSERT INTO tasks (name, emoji, points, sort_order) VALUES (?,?,?,?)",
                ("吃菜 10 条", "🥬", 1, 0),
            )


# ── Models ──────────────────────────────────────────
class AddReq(BaseModel):
    pin: str
    note: str | None = None


# ── API ─────────────────────────────────────────────
@app.get("/api/summary")
def get_summary():
    today = date.today().isoformat()
    with get_db() as db:
        # Tasks + today's count
        rows = db.execute("""
            SELECT t.id, t.name, t.emoji, t.points,
                   count(pl.id) as done_today
            FROM tasks t
            LEFT JOIN point_logs pl
              ON pl.task_id = t.id AND date(pl.created_at) = ?
            WHERE t.active = 1
            GROUP BY t.id
            ORDER BY t.sort_order, t.id
        """, (today,)).fetchall()

        tasks = [dict(r) for r in rows]

        # Total points
        total = db.execute(
            "SELECT coalesce(sum(delta), 0) FROM point_logs"
        ).fetchone()[0]

        # Recent logs
        logs = db.execute("""
            SELECT pl.id, t.name as task_name, t.emoji,
                   pl.delta, pl.note, pl.created_at
            FROM point_logs pl
            JOIN tasks t ON t.id = pl.task_id
            ORDER BY pl.created_at DESC
            LIMIT 20
        """).fetchall()

        return {
            "kid_name": KID_NAME,
            "total_points": total,
            "tasks": tasks,
            "recent_logs": [dict(r) for r in logs],
        }


@app.post("/api/tasks/{task_id}/add")
def add_point(task_id: int, req: AddReq):
    if req.pin != PIN:
        raise HTTPException(status_code=403, detail="PIN 有误")

    with get_db() as db:
        task = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND active = 1", (task_id,)
        ).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        pts = task["points"]

        # Check: each task can only be done once per day
        today = date.today().isoformat()
        done_today = db.execute(
            "SELECT count(*) FROM point_logs WHERE task_id = ? AND date(created_at) = ?",
            (task_id, today),
        ).fetchone()[0]
        if done_today >= 1:
            raise HTTPException(status_code=409, detail="今日已完成该任务")

        db.execute(
            "INSERT INTO point_logs (task_id, delta, note) VALUES (?,?,?)",
            (task_id, pts, req.note),
        )

        # Today's count
        today = date.today().isoformat()
        done_today = db.execute(
            "SELECT count(*) FROM point_logs WHERE task_id = ? AND date(created_at) = ?",
            (task_id, today),
        ).fetchone()[0]

        # New total
        total = db.execute(
            "SELECT coalesce(sum(delta), 0) FROM point_logs"
        ).fetchone()[0]

        return {
            "ok": True,
            "points_earned": pts,
            "done_today": done_today,
            "total_points": total,
        }


# ── Static ──────────────────────────────────────────
static_dir = Path(__file__).parent / "static"

@app.get("/")
def serve_index():
    return FileResponse(static_dir / "index.html")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Main ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    init_db()
    print(f"🏝️  Kids Points running on http://0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
