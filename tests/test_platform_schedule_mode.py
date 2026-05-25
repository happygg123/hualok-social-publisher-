from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from publisher_db import create_job, due_jobs, job_to_master_row, get_job


class PlatformScheduleModeTests(unittest.TestCase):
    def test_future_schedule_time_is_still_queued_for_immediate_upload(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "publisher.sqlite3"
            job_id = create_job(
                {
                    "account": "hualok",
                    "video": r"D:\videos\001.mp4",
                    "cover": r"D:\videos\001.jpg",
                    "title": "标题",
                    "platforms": "tencent,douyin,xiaohongshu",
                    "schedule_time": "2099-01-01 20:00:00",
                },
                db_path=db_path,
            )

            jobs = due_jobs(db_path=db_path)

            self.assertEqual([job["id"] for job in jobs], [job_id])

    def test_schedule_time_is_preserved_as_platform_publish_time(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "publisher.sqlite3"
            job_id = create_job(
                {
                    "account": "hualok",
                    "video": r"D:\videos\001.mp4",
                    "title": "标题",
                    "platforms": "douyin",
                    "schedule_time": "2099-01-01 20:00:00",
                },
                db_path=db_path,
            )
            job = get_job(job_id, db_path=db_path)

            row = job_to_master_row(job)

            self.assertEqual(row["publish_time"], "2099-01-01 20:00:00")


if __name__ == "__main__":
    unittest.main()
