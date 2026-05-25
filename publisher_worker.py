from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from publish_once_to_many import expand_master_rows, run_expanded_rows
from publisher_db import due_jobs, get_job, init_db, insert_attempt, job_to_master_row, set_job_status


def run_job(job_id: int, headed: bool = True, timeout_seconds: int = 1800) -> dict:
    job = get_job(job_id)
    if not job:
        raise SystemExit(f"任务不存在: {job_id}")

    set_job_status(job_id, "running")
    expanded = expand_master_rows([job_to_master_row(job)])
    log_dir = Path("publish_logs") / "jobs" / str(job_id)
    summary = run_expanded_rows(expanded, log_dir, headed=headed, headless=False, timeout_seconds=timeout_seconds)

    for item in summary.get("results", []):
        record_path = log_dir / "records" / f"{item['index']:04d}_{item['platform']}_{item['status']}.json"
        if record_path.is_file():
            result = json.loads(record_path.read_text(encoding="utf-8"))
            insert_attempt(job_id, result)

    if summary["failed"]:
        set_job_status(job_id, "failed", f"失败 {summary['failed']} 个平台")
    elif job.get("tencent_declare_original"):
        set_job_status(job_id, "published_pending_original")
    else:
        set_job_status(job_id, "success")
    return summary


def run_loop(interval_seconds: int, headed: bool, timeout_seconds: int) -> None:
    init_db()
    print(f"worker started, interval={interval_seconds}s, mode=platform-schedule-upload", flush=True)
    while True:
        jobs = due_jobs()
        for job in jobs:
            print(f"run job {job['id']}: {job['title']}", flush=True)
            try:
                run_job(int(job["id"]), headed=headed, timeout_seconds=timeout_seconds)
            except Exception as exc:
                set_job_status(int(job["id"]), "failed", str(exc))
                print(f"job {job['id']} failed: {exc}", flush=True)
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="HuaLok social publisher worker")
    parser.add_argument("--once", action="store_true", help="只扫描并执行一次到期任务")
    parser.add_argument("--job-id", type=int, default=0, help="直接执行指定任务")
    parser.add_argument("--interval", type=int, default=30, help="循环扫描间隔秒数")
    parser.add_argument("--headed", action="store_true", default=True, help="有头浏览器运行")
    parser.add_argument("--timeout", type=int, default=1800, help="每个平台发布超时秒数")
    args = parser.parse_args()

    init_db()
    if args.job_id:
        run_job(args.job_id, headed=args.headed, timeout_seconds=args.timeout)
        return 0
    if args.once:
        for job in due_jobs():
            run_job(int(job["id"]), headed=args.headed, timeout_seconds=args.timeout)
        return 0
    run_loop(args.interval, headed=args.headed, timeout_seconds=args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
