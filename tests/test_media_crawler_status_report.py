from __future__ import annotations

from pathlib import Path

from app.agents.graph import run_travel_agent
from app.config import Settings
from app.schemas import TravelPlanRequest


def test_media_crawler_without_initialization_writes_status_report(tmp_path: Path) -> None:
    media_root = tmp_path / "MediaCrawler"
    media_root.mkdir()
    settings = Settings(
        database_path=tmp_path / "travel.sqlite3",
        vector_store_path=tmp_path / "vectors",
        media_crawler_root=media_root,
        media_crawler_runs_path=tmp_path / "runs",
        media_crawler_init_status_path=tmp_path / "missing-status.json",
        media_crawler_require_initialized=True,
    )

    response = run_travel_agent(
        TravelPlanRequest(
            user_query="beijing weekend travel",
            platforms=["xhs"],
            collect_limit_per_query=1,
            collection_mode="media_crawler",
        ),
        settings=settings,
    )

    assert response.collection_summary.mode == "media_crawler"
    assert response.collection_summary.total_docs == 0
    assert response.collection_errors
    assert "MediaCrawler 未完成有效资料采集" in response.report
    assert "结论：" not in response.report
    assert "适配分：" not in response.report
