from __future__ import annotations

import json
import sys
from pathlib import Path

from app.collectors.media_crawler_adapter import MediaCrawlerAdapter
from app.collectors.media_crawler_adapter import MediaCrawlerRunConfig


def test_media_crawler_adapter_requires_initialization_status(tmp_path: Path) -> None:
    media_root = tmp_path / "MediaCrawler"
    media_root.mkdir()

    adapter = MediaCrawlerAdapter(
        config=MediaCrawlerRunConfig(
            root=media_root,
            runner=sys.executable,
            runs_path=tmp_path / "runs",
            require_initialized=True,
            init_status_path=tmp_path / "missing-status.json",
        ),
        platforms=["xhs"],
        request_id="req-init-missing",
    )

    docs = adapter.search("beijing weekend travel", limit=1)

    assert docs == []
    assert len(adapter.errors) == 1
    assert "initialize_media_crawler.ps1" in adapter.errors[0].error


def test_media_crawler_adapter_rejects_uninitialized_platform(tmp_path: Path) -> None:
    media_root = tmp_path / "MediaCrawler"
    media_root.mkdir()
    status_path = tmp_path / "status.json"
    status_path.write_text(
        json.dumps(
            {
                "initialized": True,
                "ready_platforms": ["xhs"],
                "cdp_port": None,
            }
        ),
        encoding="utf-8",
    )

    adapter = MediaCrawlerAdapter(
        config=MediaCrawlerRunConfig(
            root=media_root,
            runner=sys.executable,
            runs_path=tmp_path / "runs",
            require_initialized=True,
            init_status_path=status_path,
        ),
        platforms=["bilibili"],
        request_id="req-init-platform",
    )

    docs = adapter.search("beijing weekend travel", limit=1)

    assert docs == []
    assert len(adapter.errors) == 1
    assert "bili" in adapter.errors[0].error
