from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

STATUS_META = {
    "queued": ("待上传", "queued", "⏱"),
    "running": ("上传中", "running", "●"),
    "success": ("已成功", "success", "✓"),
    "partial_success": ("部分成功", "warning", "!"),
    "published_pending_original": ("待原创声明", "warning", "!"),
    "failed": ("失败", "failed", "×"),
    "cancelled": ("已取消", "cancelled", "–"),
}
PLATFORM_LABELS = {"tencent": "视频号", "douyin": "抖音", "xiaohongshu": "小红书"}
SCREENSHOT_RE = re.compile(r"([A-Za-z]:\\[^\n\r\t<>|]+?\.(?:png|jpg|jpeg|webp)|/[^\n\r\t<>|]+?\.(?:png|jpg|jpeg|webp))", re.I)


def win_path(value: str) -> str:
    if not value:
        return ""
    if value.startswith("/mnt/d/"):
        return value.replace("/mnt/d/", "D:\\").replace("/", "\\")
    if value.startswith("/mnt/c/"):
        return value.replace("/mnt/c/", "C:\\").replace("/", "\\")
    return value


def status_meta(status: str) -> dict[str, str]:
    label, css, icon = STATUS_META.get(status or "", (status or "未知", "neutral", "•"))
    return {"label": label, "css": css, "icon": icon, "raw": status or ""}


def platform_items(platforms: str) -> list[dict[str, str]]:
    names = [p.strip() for p in (platforms or "").split(",") if p.strip()]
    return [{"key": p, "label": PLATFORM_LABELS.get(p, p)} for p in names]


def truncate(value: str, length: int = 120) -> str:
    value = str(value or "")
    return value if len(value) <= length else value[:length] + "…"


def normalize_screenshot_path(path: str) -> str:
    path = path.strip().strip('"\'').replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", path):
        path = "/mnt/" + path[0].lower() + path[2:]
    return path


def file_url(path: str) -> str:
    return "/file?path=" + quote(path)


def extract_screenshots(*texts: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for text in texts:
        for match in SCREENSHOT_RE.finditer(text or ""):
            path = normalize_screenshot_path(match.group(1))
            if path not in seen and Path(path).exists():
                seen.add(path)
                out.append({"path": path, "name": Path(path).name, "url": file_url(path)})
    return out


def build_dashboard_context(jobs: list[dict], active_filter: str) -> dict:
    counts = {"total": len(jobs), "queued": 0, "running": 0, "success": 0, "failed": 0, "partial_success": 0}
    for job in jobs:
        status = job.get("status")
        if status in counts:
            counts[status] += 1
    filtered = jobs if active_filter == "all" else [job for job in jobs if job.get("status") == active_filter]
    cards = []
    for job in filtered:
        cards.append(
            {
                **job,
                "status_view": status_meta(job.get("status", "")),
                "platform_items": platform_items(job.get("platforms", "")),
                "video_view": win_path(job.get("video", "")),
                "schedule_view": job.get("schedule_time") or "立即发布",
                "error_view": truncate(job.get("last_error", ""), 90),
            }
        )
    filters = [
        ("all", "全部"),
        ("queued", "待上传"),
        ("running", "上传中"),
        ("success", "成功"),
        ("failed", "失败"),
        ("partial_success", "部分成功"),
        ("published_pending_original", "待原创声明"),
        ("cancelled", "已取消"),
    ]
    return {"jobs": cards, "counts": counts, "filters": filters, "active_filter": active_filter}


def build_job_detail_context(job: dict, attempts: list[dict]) -> dict:
    shots: list[dict[str, str]] = []
    for item in attempts:
        direct = item.get("screenshot") or ""
        if direct and Path(direct).exists():
            shots.append({"path": direct, "name": Path(direct).name, "url": file_url(direct)})
        shots.extend(extract_screenshots(item.get("stdout", ""), item.get("stderr", "")))
    deduped = []
    seen = set()
    for shot in shots:
        if shot["path"] not in seen:
            seen.add(shot["path"])
            deduped.append(shot)
    return {
        "job": {
            **job,
            "status_view": status_meta(job.get("status", "")),
            "platform_items": platform_items(job.get("platforms", "")),
            "video_view": win_path(job.get("video", "")),
            "cover_view": win_path(job.get("cover", "")),
            "schedule_view": job.get("schedule_time") or "立即发布",
        },
        "attempts": [
            {
                **item,
                "platform_items": platform_items(item.get("platform", "")),
                "status_view": status_meta(item.get("status", "")),
                "stderr_tail": (item.get("stderr") or "")[-3000:] or "无",
                "stdout_tail": (item.get("stdout") or "")[-3000:] or "无",
            }
            for item in attempts
        ],
        "screenshots": deduped,
    }
