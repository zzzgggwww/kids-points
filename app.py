"""
Kids Points System — 小朋友积分打卡系统

动森风格界面，FastAPI + SQLite 零依赖部署。
每次完成任务 → 大人输 PIN → 直接加星。

数据表:
  tasks      - 任务定义（名称、emoji、积分值）
  point_logs - 积分记录（每次加星一条记录）
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

# ── 配置 ──────────────────────────────────────────
# 数据库路径、PIN码、小朋友名字、端口均可通过环境变量覆盖
DB_PATH = Path(__file__).parent / "data" / "points.db"
PIN = os.environ.get("KIDS_PIN", "159357")
KID_NAME = os.environ.get("KID_NAME", "招铭")
PORT = int(os.environ.get("KIDS_PORT", "2020"))

app = FastAPI(title="Kids Points")


# ── 数据库 ────────────────────────────────────────
# SQLite 上下文管理器，自动提交/关闭连接
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 返回字典格式的行
    conn.execute("PRAGMA journal_mode=WAL")  # WAL 模式提升并发性能
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# 初始化数据库表结构，首次启动时自动创建
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.executescript("""
            -- 任务表：定义可完成的任务
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,          -- 任务名称
                emoji       TEXT    DEFAULT '⭐',       -- 显示图标
                points      INTEGER DEFAULT 1,         -- 完成可得星数
                active      INTEGER DEFAULT 1,         -- 是否启用
                sort_order  INTEGER DEFAULT 0,         -- 排序权重
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );
            -- 积分记录表：每次加星记录一条
            CREATE TABLE IF NOT EXISTS point_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,           -- 关联任务
                delta       INTEGER NOT NULL,           -- 加减星数
                note        TEXT,                       -- 备注
                created_at  TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
            -- 索引：加速日期查询和任务统计
            CREATE INDEX IF NOT EXISTS idx_logs_created
                ON point_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_logs_task
                ON point_logs(task_id, created_at);
        """)
        # 首次启动插入默认任务
        if db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 0:
            defaults = [
                ("吃菜 10 条", "🥬", 1, 0),
                ("睡午觉", "😴", 1, 1),
            ]
            for name, emoji, pts, order in defaults:
                db.execute(
                    "INSERT INTO tasks (name, emoji, points, sort_order) VALUES (?,?,?,?)",
                    (name, emoji, pts, order),
                )


# ── 请求模型 ──────────────────────────────────────
class AddReq(BaseModel):
    pin: str              # 6位 PIN 码
    note: str | None = None  # 可选备注


# ── API 路由 ──────────────────────────────────────

# 获取首页数据：任务列表 + 今日完成情况 + 总积分 + 最近记录
@app.get("/api/summary")
def get_summary():
    today = date.today().isoformat()
    with get_db() as db:
        # 查询所有启用的任务，附带今日完成次数
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

        # 汇总历史总积分
        total = db.execute(
            "SELECT coalesce(sum(delta), 0) FROM point_logs"
        ).fetchone()[0]

        # 最近 20 条积分记录
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
