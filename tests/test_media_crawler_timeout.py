from __future__ import annotations

import sys
from pathlib import Path

from app.collectors.media_crawler_adapter import MediaCrawlerAdapter
from app.collectors.media_crawler_adapter import MediaCrawlerRunConfig


def test_media_crawler_adapter_reports_timeout(tmp_path: Path) -> None:
    media_root = tmp_path / "MediaCrawler"
    media_root.mkdir()
    (media_root / "main.py").write_text(
        """
import time

time.sleep(10)
""",
        encoding="utf-8",
    )

    adapter = MediaCrawlerAdapter(
        config=MediaCrawlerRunConfig(
            root=media_root,
            runner=sys.executable,
            runs_path=tmp_path / "runs",
            sleep_seconds=0,
            rate_limit_per_minute=1000,
            timeout_seconds=1,
        ),
        platforms=["xhs"],
        request_id="req-timeout",
    )

    docs = adapter.search("beijing weekend travel", limit=1)

    assert docs == []
    assert len(adapter.errors) == 1
    assert "timed out after 1 seconds" in adapter.errors[0].error
