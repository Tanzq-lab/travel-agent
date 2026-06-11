from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.graph import run_travel_agent
from app.schemas import TravelPlanRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the evidence-grounded travel research workflow without starting FastAPI."
    )
    parser.add_argument("query", help="Natural-language travel request, e.g. 我要7月去重庆玩3天")
    parser.add_argument(
        "--platforms",
        default="xhs,zhihu,bilibili,weibo,tieba",
        help="Comma-separated platforms: xhs,zhihu,bilibili,weibo,tieba",
    )
    parser.add_argument("--limit", type=int, default=5, help="Per-query collection limit")
    parser.add_argument(
        "--collection-mode",
        choices=["media_crawler", "mock", "auto"],
        default="media_crawler",
        help="Collection backend. Use auto to fall back to mock if MediaCrawler is missing.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = TravelPlanRequest(
        user_query=args.query,
        platforms=[item.strip() for item in args.platforms.split(",") if item.strip()],
        collect_limit_per_query=args.limit,
        collection_mode=args.collection_mode,
        use_mock=None,
    )
    response = run_travel_agent(payload)
    if args.format == "json":
        print(response.model_dump_json(indent=2))
    else:
        print(f"request_id: {response.request_id}")
        print(f"collection_mode: {response.collection_summary.mode}")
        print(f"llm_mode: {response.llm_mode}")
        print(f"collection_errors: {len(response.collection_errors)}")
        print()
        print(response.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

