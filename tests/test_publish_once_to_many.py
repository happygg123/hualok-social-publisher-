from pathlib import Path

import pytest

from publish_once_to_many import expand_master_rows, normalize_platforms, read_master_rows


def test_normalize_platforms_accepts_commas_and_chinese_aliases():
    assert normalize_platforms("视频号, 抖音，小红书") == ["tencent", "douyin", "xiaohongshu"]


def test_expand_master_rows_creates_one_row_per_platform_with_shared_metadata():
    rows = [
        {
            "id": "001",
            "account": "gavin",
            "video": r"D:\videos\001.mp4",
            "cover": r"D:\videos\001.jpg",
            "title": "标题",
            "desc": "简介",
            "tags": "标签1,标签2",
            "platforms": "tencent,douyin,xiaohongshu",
            "publish_time": "2026-05-25 20:00",
            "short_title": "短标题",
        }
    ]

    expanded = expand_master_rows(rows)

    assert [row["platform"] for row in expanded] == ["tencent", "douyin", "xiaohongshu"]
    assert all(row["file"] == r"D:\videos\001.mp4" for row in expanded)
    assert all(row["thumbnail"] == r"D:\videos\001.jpg" for row in expanded)
    assert all(row["title"] == "标题" for row in expanded)
    assert all(row["desc"] == "简介" for row in expanded)
    assert all(row["tags"] == "标签1,标签2" for row in expanded)
    assert all(row["schedule"] == "2026-05-25 20:00" for row in expanded)
    assert expanded[0]["short_title"] == "短标题"


def test_expand_master_rows_supports_platform_specific_overrides():
    rows = [
        {
            "id": "001",
            "account": "gavin",
            "video": r"D:\videos\001.mp4",
            "cover": r"D:\videos\001.jpg",
            "title": "通用标题",
            "desc": "通用简介",
            "tags": "通用标签",
            "platforms": "tencent,douyin",
            "tencent_title": "视频号标题",
            "douyin_desc": "抖音简介",
            "douyin_tags": "抖音标签",
        }
    ]

    expanded = expand_master_rows(rows)
    by_platform = {row["platform"]: row for row in expanded}

    assert by_platform["tencent"]["title"] == "视频号标题"
    assert by_platform["tencent"]["desc"] == "通用简介"
    assert by_platform["douyin"]["title"] == "通用标题"
    assert by_platform["douyin"]["desc"] == "抖音简介"
    assert by_platform["douyin"]["tags"] == "抖音标签"


def test_read_master_rows_requires_existing_csv(tmp_path: Path):
    with pytest.raises(SystemExit):
        read_master_rows(tmp_path / "missing.csv")
