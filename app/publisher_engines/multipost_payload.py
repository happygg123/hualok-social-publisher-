from __future__ import annotations

import mimetypes
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

PLATFORM_TO_MULTIPOST = {
    "tencent": "VIDEO_WEIXINCHANNEL",
    "weixinchannel": "VIDEO_WEIXINCHANNEL",
    "douyin": "VIDEO_DOUYIN",
    "xiaohongshu": "VIDEO_REDNOTE",
    "rednote": "VIDEO_REDNOTE",
}
CHINA_TZ = timezone(timedelta(hours=8))


def split_tags(value: str) -> list[str]:
    parts = str(value or "").replace("，", ",").replace(";", ",").replace("；", ",").split(",")
    return [part.strip().lstrip("#") for part in parts if part.strip().lstrip("#")]


def parse_schedule_ms(value: str) -> int | None:
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=CHINA_TZ)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"不支持的定时时间格式: {value}")


def _platforms(value: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for raw in str(value or "").replace("，", ",").split(","):
        key = raw.strip().lower()
        if not key:
            continue
        name = PLATFORM_TO_MULTIPOST.get(key)
        if name and {"name": name} not in out:
            out.append({"name": name})
    return out


def _file_data(job_id: int, field: str, path_value: str, base_url: str) -> dict[str, str | int]:
    path = Path(str(path_value or ""))
    mime = mimetypes.guess_type(path.name)[0] or ("video/mp4" if field == "video" else "application/octet-stream")
    return {
        "name": path.name or field,
        "url": urljoin(base_url.rstrip("/") + "/", f"media/job/{job_id}/{field}"),
        "type": mime,
    }


def build_multipost_video_payload(job: dict, base_url: str) -> dict:
    job_id = int(job["id"])
    data = {
        "title": job.get("title", ""),
        "content": job.get("desc", ""),
        "video": _file_data(job_id, "video", job.get("video", ""), base_url),
        "tags": split_tags(job.get("tags", "")),
        "original": bool(job.get("tencent_declare_original")),
    }
    if job.get("cover"):
        data["cover"] = _file_data(job_id, "cover", job.get("cover", ""), base_url)
    schedule_ms = parse_schedule_ms(job.get("schedule_time", ""))
    if schedule_ms is not None:
        data["scheduledPublishTime"] = schedule_ms
    return {
        "platforms": _platforms(job.get("platforms", "")),
        "isAutoPublish": True,
        "data": data,
    }
