from __future__ import annotations

import unittest

from uploader.douyin_uploader.main import DOUYIN_SCHEDULE_INPUT_SELECTORS, DOUYIN_SCHEDULE_TOGGLE_SELECTORS
from uploader.xiaohongshu_uploader.main import XHS_SCHEDULE_INPUT_SELECTORS, XHS_SCHEDULE_TOGGLE_SELECTORS


class MultiPostSelectorMigrationTests(unittest.TestCase):
    def test_douyin_schedule_selectors_include_multipost_fallbacks(self):
        self.assertIn('label:has-text("定时发布")', DOUYIN_SCHEDULE_TOGGLE_SELECTORS)
        self.assertIn('input[format="yyyy-MM-dd HH:mm"]', DOUYIN_SCHEDULE_INPUT_SELECTORS)

    def test_xhs_schedule_selectors_include_multipost_fallbacks(self):
        self.assertIn('label:has-text("定时发布")', XHS_SCHEDULE_TOGGLE_SELECTORS)
        self.assertIn('input[placeholder="选择日期和时间"]', XHS_SCHEDULE_INPUT_SELECTORS)


if __name__ == "__main__":
    unittest.main()
