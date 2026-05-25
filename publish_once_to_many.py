from __future__ import annotations

import argparse
import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path

from publish_batch import read_rows as read_expanded_rows
from publish_batch import run_one

SUPPORTED_PLATFORMS = {"tencent", "douyin", "xiaohongshu"}
PLATFORM_ALIASES = {
    "视频号": "tencent",
    "微信视频号": "tencent",
    "tencent": "tencent",
    "wechat": "tencent",
    "channels": "tencent",
    "抖音": "douyin",
    "douyin": "douyin",
    "小红书": "xiaohongshu",
    "xhs": "xiaohongshu",
    "xiaohongshu": "xiaohongshu",
    "rednote": "xiaohongshu",
}
EXPANDED_FIELDS = [
    "platform",
    "account",
    "file",
    "title",
    "desc",
    "tags",
    "thumbnail",
    "schedule",
    "short_title",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_platforms(value: str) -> list[str]:
    raw_parts = str(value or "").replace("，", ",").replace(";", ",").replace("；", ",").split(",")
    platforms: list[str] = []
    for raw in raw_parts:
        key = raw.strip().lower()
        if not key:
            continue
        platform = PLATFORM_ALIASES.get(key) or PLATFORM_ALIASES.get(raw.strip())
        if not platform:
            raise ValueError(f"不支持的平台: {raw}")
        if platform not in platforms:
            platforms.append(platform)
    if not platforms:
        raise ValueError("platforms 不能为空，例如: tencent,douyin,xiaohongshu")
    return platforms


def _value(row: dict, platform: str, field: str, fallback: str = "") -> str:
    platform_value = (row.get(f"{platform}_{field}") or "").strip()
    if platform_value:
        return platform_value
    return (row.get(field) or row.get(fallback) or "").strip()


def expand_master_rows(rows: list[dict]) -> list[dict]:
    expanded: list[dict] = []
    for index, row in enumerate(rows, start=1):
        platforms = normalize_platforms(row.get("platforms") or row.get("platform") or "")
        video = (row.get("video") or row.get("file") or "").strip()
        if not video:
            raise ValueError(f"第 {index} 行缺少 video/file")
        title = (row.get("title") or "").strip()
        if not title and not any((row.get(f"{p}_title") or "").strip() for p in platforms):
            raise ValueError(f"第 {index} 行缺少 title")
        account_default = (row.get("account") or "hualok").strip()
        for platform in platforms:
            expanded.append(
                {
                    "platform": platform,
                    "account": _value(row, platform, "account") or account_default,
                    "file": video,
                    "title": _value(row, platform, "title"),
                    "desc": _value(row, platform, "desc"),
                    "tags": _value(row, platform, "tags"),
                    "thumbnail": _value(row, platform, "thumbnail", fallback="cover"),
                    "schedule": _value(row, platform, "schedule", fallback="publish_time"),
                    "short_title": _value(row, platform, "short_title"),
                }
            )
    return expanded


def read_master_rows(csv_path: Path) -> list[dict]:
    if not csv_path.is_file():
        raise SystemExit(f"CSV 文件不存在: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_expanded_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXPANDED_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in EXPANDED_FIELDS})


def run_expanded_rows(rows: list[dict], log_dir: Path, headed: bool, headless: bool, timeout_seconds: int) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    results = []
    success = 0
    failed = 0
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{total}] 分发 {row.get('platform')} - {row.get('file')}", flush=True)
        result = run_one(row, index, total, log_dir, headed=headed, headless=headless, timeout_seconds=timeout_seconds)
        results.append(result)
        if result["status"] == "success":
            success += 1
            print("  成功", flush=True)
        else:
            failed += 1
            print(f"  失败: {result['stderr'][-500:]}", flush=True)
    summary = {
        "time": now_str(),
        "total": total,
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
                "timed_out": item["timed_out"],
            }
            for item in results
        ],
    }
    (log_dir / "summary_once_to_many.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="一次设置视频信息，分发到多个平台")
    parser.add_argument("--csv", required=True, help="主任务 CSV，字段含 video/cover/title/desc/tags/platforms")
    parser.add_argument("--log-dir", default="publish_logs/once_to_many", help="日志目录")
    parser.add_argument("--expanded-csv", default="", help="只生成/保存拆分后的平台 CSV 到指定路径")
    parser.add_argument("--dry-run", action="store_true", help="只打印拆分结果，不执行发布")
    parser.add_argument("--headed", action="store_true", help="有头浏览器运行")
    parser.add_argument("--headless", action="store_true", help="无头浏览器运行")
    parser.add_argument("--timeout", type=int, default=1800, help="每个平台发布任务超时秒数")
    args = parser.parse_args()

    if args.headed and args.headless:
        raise SystemExit("--headed 和 --headless 不能同时传")

    master_rows = read_master_rows(Path(args.csv).expanduser())
    expanded = expand_master_rows(master_rows)

    if args.expanded_csv:
        write_expanded_csv(expanded, Path(args.expanded_csv).expanduser())

    if args.dry_run:
        print(json.dumps(expanded, ensure_ascii=False, indent=2), flush=True)
        return 0

    if not expanded:
        raise SystemExit("没有可发布的任务")

    summary = run_expanded_rows(
        expanded,
        Path(args.log_dir).expanduser(),
        headed=args.headed,
        headless=args.headless,
        timeout_seconds=args.timeout,
    )
    print(f"完成：成功 {summary['success']}，失败 {summary['failed']}。日志：{args.log_dir}", flush=True)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
