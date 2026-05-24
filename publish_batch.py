from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path


SUPPORTED_PLATFORMS = {"tencent", "douyin", "xiaohongshu"}
DEFAULT_ACTION = "upload-video"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_path(value: str) -> str:
    if not value:
        return ""
    return str(Path(value).expanduser())


def require(row: dict, key: str, index: int) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise ValueError(f"第 {index} 行缺少必填字段: {key}")
    return value


def build_command(row: dict, index: int, headed: bool, headless: bool) -> list[str]:
    platform = require(row, "platform", index).lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"第 {index} 行不支持的平台: {platform}")

    cmd = [
        "sau",
        platform,
        DEFAULT_ACTION,
        "--account",
        require(row, "account", index),
        "--file",
        normalize_path(require(row, "file", index)),
        "--title",
        require(row, "title", index),
    ]

    optional_fields = {
        "desc": "--desc",
        "tags": "--tags",
        "schedule": "--schedule",
    }
    for csv_key, cli_flag in optional_fields.items():
        value = (row.get(csv_key) or "").strip()
        if value:
            cmd.extend([cli_flag, value])

    thumbnail = (row.get("thumbnail") or "").strip()
    if thumbnail:
        cmd.extend(["--thumbnail", normalize_path(thumbnail)])

    short_title = (row.get("short_title") or row.get("short-title") or "").strip()
    if platform == "tencent" and short_title:
        cmd.extend(["--short-title", short_title])

    if headed and headless:
        raise ValueError("--headed 和 --headless 不能同时传")
    if headed:
        cmd.append("--headed")
    if headless:
        cmd.append("--headless")

    return cmd


def run_one(row: dict, index: int, total: int, log_dir: Path, headed: bool, headless: bool) -> dict:
    platform = (row.get("platform") or "unknown").strip().lower()
    result = {
        "index": index,
        "total": total,
        "time": now_str(),
        "platform": platform,
        "account": (row.get("account") or "").strip(),
        "file": (row.get("file") or "").strip(),
        "title": (row.get("title") or "").strip(),
        "status": "pending",
        "command": [],
        "stdout": "",
        "stderr": "",
        "returncode": None,
    }

    try:
        cmd = build_command(row, index, headed=headed, headless=headless)
        result["command"] = cmd
        completed = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        result["returncode"] = completed.returncode
        result["stdout"] = completed.stdout
        result["stderr"] = completed.stderr
        result["status"] = "success" if completed.returncode == 0 else "failed"
    except Exception as exc:
        result["status"] = "failed"
        result["stderr"] = str(exc)

    safe_platform = platform or "unknown"
    log_file = log_dir / "records" / f"{index:04d}_{safe_platform}_{result['status']}.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def read_rows(csv_path: Path) -> list[dict]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch publish videos via sau CLI")
    parser.add_argument("--csv", required=True, help="CSV 发布任务文件")
    parser.add_argument("--log-dir", default="publish_logs", help="日志目录")
    parser.add_argument("--headed", action="store_true", help="有头浏览器运行，适合首次联调")
    parser.add_argument("--headless", action="store_true", help="无头运行")
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser()
    if not csv_path.is_file():
        raise SystemExit(f"CSV 文件不存在: {csv_path}")

    log_dir = Path(args.log_dir).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(csv_path)
    success = 0
    failed = 0
    results = []

    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] 发布 {row.get('platform')} - {row.get('file')}")
        result = run_one(row, index, len(rows), log_dir, headed=args.headed, headless=args.headless)
        results.append(result)
        if result["status"] == "success":
            success += 1
            print("  成功")
        else:
            failed += 1
            print(f"  失败: {result['stderr'][-500:]}")

    summary = {
        "time": now_str(),
        "csv": str(csv_path),
        "total": len(rows),
        "success": success,
        "failed": failed,
        "results": [
            {
                "index": item["index"],
                "platform": item["platform"],
                "file": item["file"],
                "title": item["title"],
                "status": item["status"],
                "returncode": item["returncode"],
            }
            for item in results
        ],
    }
    (log_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：成功 {success}，失败 {failed}。日志：{log_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
