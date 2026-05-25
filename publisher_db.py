from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("publisher_state.sqlite3")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS publish_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL DEFAULT 'hualok',
                video TEXT NOT NULL,
                cover TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                desc TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                platforms TEXT NOT NULL,
                schedule_time TEXT NOT NULL DEFAULT '',
                short_title TEXT NOT NULL DEFAULT '',
                tencent_declare_original INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_error TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS publish_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                status TEXT NOT NULL,
                command TEXT NOT NULL DEFAULT '',
                stdout TEXT NOT NULL DEFAULT '',
                stderr TEXT NOT NULL DEFAULT '',
                screenshot TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(job_id) REFERENCES publish_jobs(id)
            );

            CREATE TABLE IF NOT EXISTS post_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                stdout TEXT NOT NULL DEFAULT '',
                stderr TEXT NOT NULL DEFAULT '',
                screenshot TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL DEFAULT '',
                finished_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(job_id) REFERENCES publish_jobs(id)
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def create_job(data: dict[str, Any], db_path: Path | str = DB_PATH) -> int:
    init_db(db_path)
    timestamp = now_str()
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO publish_jobs
            (account, video, cover, title, desc, tags, platforms, schedule_time, short_title,
             tencent_declare_original, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)
            """,
            (
                data.get("account") or "hualok",
                data.get("video") or "",
                data.get("cover") or "",
                data.get("title") or "",
                data.get("desc") or "",
                data.get("tags") or "",
                data.get("platforms") or "",
                data.get("schedule_time") or "",
                data.get("short_title") or "",
                1 if data.get("tencent_declare_original") else 0,
                timestamp,
                timestamp,
            ),
        )
        return int(cur.lastrowid)


def list_jobs(db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM publish_jobs ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def get_job(job_id: int, db_path: Path | str = DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)
    with connect(db_path) as conn:
        return row_to_dict(conn.execute("SELECT * FROM publish_jobs WHERE id = ?", (job_id,)).fetchone())


def list_attempts(job_id: int, db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM publish_attempts WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()
        return [dict(row) for row in rows]


def set_job_status(job_id: int, status: str, last_error: str = "", db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE publish_jobs SET status = ?, last_error = ?, updated_at = ? WHERE id = ?",
            (status, last_error, now_str(), job_id),
        )


def queue_job(job_id: int, schedule_time: str = "", db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE publish_jobs
            SET status = 'queued', schedule_time = ?, last_error = '', updated_at = ?
            WHERE id = ?
            """,
            (schedule_time, now_str(), job_id),
        )


def cancel_job(job_id: int, db_path: Path | str = DB_PATH) -> None:
    set_job_status(job_id, "cancelled", db_path=db_path)


def due_jobs(db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)
    now = now_str()
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM publish_jobs
            WHERE status = 'queued'
              AND (schedule_time = '' OR schedule_time <= ?)
            ORDER BY id ASC
            """,
            (now,),
        ).fetchall()
        return [dict(row) for row in rows]


def insert_attempt(job_id: int, result: dict[str, Any], db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO publish_attempts
            (job_id, platform, status, command, stdout, stderr, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                result.get("platform") or "",
                result.get("status") or "",
                json.dumps(result.get("command") or [], ensure_ascii=False),
                result.get("stdout") or "",
                result.get("stderr") or "",
                result.get("time") or now_str(),
                now_str(),
            ),
        )


def job_to_master_row(job: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(job["id"]),
        "account": job.get("account", "hualok"),
        "video": job.get("video", ""),
        "cover": job.get("cover", ""),
        "title": job.get("title", ""),
        "desc": job.get("desc", ""),
        "tags": job.get("tags", ""),
        "platforms": job.get("platforms", ""),
        "publish_time": "",
        "short_title": job.get("short_title", ""),
    }
