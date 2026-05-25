from __future__ import annotations

import unittest

from app.publisher_engines.multipost_payload import build_multipost_video_payload, parse_schedule_ms, split_tags


class MultipostPayloadTests(unittest.TestCase):
    def test_split_tags_accepts_chinese_and_english_commas(self):
        self.assertEqual(split_tags("采购, 工厂，供应链,,"), ["采购", "工厂", "供应链"])

    def test_parse_schedule_ms_uses_local_naive_time(self):
        self.assertEqual(parse_schedule_ms("1970-01-01 08:00:01"), 1000)

    def test_build_video_payload_maps_hualok_job_to_multipost_schema(self):
        job = {
            "id": 12,
            "title": "标题",
            "desc": "简介",
            "tags": "采购,工厂",
            "video": r"D:\videos\001.mp4",
            "cover": r"D:\videos\001.png",
            "platforms": "tencent,douyin,xiaohongshu",
            "schedule_time": "1970-01-01 08:00:01",
            "tencent_declare_original": 1,
        }

        payload = build_multipost_video_payload(job, base_url="http://127.0.0.1:8765")

        self.assertEqual(
            [platform["name"] for platform in payload["platforms"]],
            ["VIDEO_WEIXINCHANNEL", "VIDEO_DOUYIN", "VIDEO_REDNOTE"],
        )
        self.assertTrue(payload["isAutoPublish"])
        self.assertEqual(payload["data"]["title"], "标题")
        self.assertEqual(payload["data"]["content"], "简介")
        self.assertEqual(payload["data"]["tags"], ["采购", "工厂"])
        self.assertEqual(payload["data"]["scheduledPublishTime"], 1000)
        self.assertTrue(payload["data"]["original"])
        self.assertEqual(payload["data"]["video"]["url"], "http://127.0.0.1:8765/media/job/12/video")
        self.assertEqual(payload["data"]["cover"]["url"], "http://127.0.0.1:8765/media/job/12/cover")


if __name__ == "__main__":
    unittest.main()
