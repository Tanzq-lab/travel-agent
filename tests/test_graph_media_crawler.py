from __future__ import annotations

import sys
from pathlib import Path

from app.agents.graph import run_travel_agent
from app.config import Settings
from app.schemas import TravelPlanRequest


def make_settings(tmp_path: Path, media_root: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "travel.sqlite3",
        vector_store_path=tmp_path / "vectors",
        media_crawler_root=media_root,
        media_crawler_runner=sys.executable,
        media_crawler_runs_path=tmp_path / "runs",
        media_crawler_sleep_seconds=0,
        media_crawler_rate_limit_per_minute=1000,
        media_crawler_timeout_seconds=20,
        media_crawler_require_initialized=False,
    )


def write_fake_media_crawler(media_root: Path) -> None:
    media_root.mkdir()
    (media_root / "main.py").write_text(
        """
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--platform')
parser.add_argument('--lt')
parser.add_argument('--type')
parser.add_argument('--keywords')
parser.add_argument('--crawler_max_notes_count')
parser.add_argument('--save_data_option')
parser.add_argument('--save_data_path')
parser.add_argument('--get_comment')
parser.add_argument('--get_sub_comment')
parser.add_argument('--headless')
args = parser.parse_args()
out = Path(args.save_data_path)
out.mkdir(parents=True, exist_ok=True)
(out / 'result.jsonl').write_text(json.dumps({
    'id': args.platform + '-1',
    'title': args.keywords,
    'content': '7月重庆白天很热，不建议一直户外走；晚上夜景好看，适合低强度安排。',
    'url': 'https://example.test/' + args.platform
}, ensure_ascii=False) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )


def test_graph_uses_media_crawler_path_with_fake_cli(tmp_path: Path) -> None:
    media_root = tmp_path / "MediaCrawler"
    write_fake_media_crawler(media_root)
    settings = make_settings(tmp_path, media_root)

    response = run_travel_agent(
        TravelPlanRequest(
            user_query="我要 7 月去重庆，玩 3 天，怕热。",
            platforms=["xhs"],
            collect_limit_per_query=1,
            collection_mode="media_crawler",
        ),
        settings=settings,
    )

    assert response.collection_summary.mode == "media_crawler"
    assert response.collection_summary.total_docs > 0
    assert not response.collection_errors
    assert response.llm_mode == "fallback"
    assert "根据本次收集到的资料" in response.report


def test_graph_reports_collection_errors_when_media_crawler_missing(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, tmp_path / "missing")

    response = run_travel_agent(
        TravelPlanRequest(
            user_query="我要去重庆。",
            platforms=["xhs"],
            collect_limit_per_query=1,
            collection_mode="media_crawler",
        ),
        settings=settings,
    )

    assert response.collection_summary.mode == "media_crawler"
    assert response.collection_summary.total_docs == 0
    assert response.collection_errors
    assert response.judgement.final_judgement == "资料不足，暂不能判断"
