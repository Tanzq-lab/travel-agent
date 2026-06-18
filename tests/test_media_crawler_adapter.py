from __future__ import annotations

import json
import sys
from pathlib import Path

from app.collectors.media_crawler_adapter import (
    MediaCrawlerAdapter,
    MediaCrawlerOutputParser,
    MediaCrawlerRunConfig,
)


def test_media_crawler_command_uses_real_cli_arguments(tmp_path: Path) -> None:
    adapter = MediaCrawlerAdapter(
        config=MediaCrawlerRunConfig(
            root=tmp_path,
            runner="uv run",
            login_type="qrcode",
            save_option="jsonl",
            headless=False,
            runs_path=tmp_path / "runs",
        ),
        platforms=["bilibili", "weibo"],
        request_id="req-1",
    )

    command = adapter.build_command(
        platform="bili",
        query="重庆 避坑",
        limit=5,
        run_dir=tmp_path / "runs" / "req-1",
    )

    assert command[:2] == ["uv", "run"]
    assert "--platform" in command
    assert command[command.index("--platform") + 1] == "bili"
    assert command[command.index("--lt") + 1] == "qrcode"
    assert command[command.index("--type") + 1] == "search"
    assert command[command.index("--keywords") + 1] == "重庆 避坑"
    assert command[command.index("--crawler_max_notes_count") + 1] == "5"
    assert command[command.index("--save_data_option") + 1] == "jsonl"
    assert command[command.index("--get_comment") + 1] == "false"
    assert command[command.index("--get_sub_comment") + 1] == "false"


def test_media_crawler_command_uses_absolute_save_data_path(tmp_path: Path) -> None:
    adapter = MediaCrawlerAdapter(
        config=MediaCrawlerRunConfig(
            root=tmp_path,
            runner="uv run",
            runs_path=Path("data/media_crawler_runs"),
        ),
        platforms=["xhs"],
        request_id="req-relative",
    )

    command = adapter.build_command(
        platform="xhs",
        query="北京 攻略",
        limit=1,
        run_dir=Path("data/media_crawler_runs/req-relative"),
    )

    save_path = Path(command[command.index("--save_data_path") + 1])

    assert save_path.is_absolute()
    assert save_path.name == "req-relative"


def test_media_crawler_output_parser_maps_jsonl_fields(tmp_path: Path) -> None:
    path = tmp_path / "xhs.jsonl"
    path.write_text(
        json.dumps(
            {
                "note_id": "abc",
                "note_title": "重庆三天攻略",
                "note_desc": "7月重庆白天很热，建议晚上看夜景。",
                "note_url": "https://example.test/note",
                "nickname": "tester",
                "liked_count": "12",
                "comment_count": 3,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    docs = MediaCrawlerOutputParser.parse_directory(tmp_path, query="重庆 攻略", platform="xhs")

    assert len(docs) == 1
    assert docs[0].id == "xhs:abc"
    assert docs[0].title == "重庆三天攻略"
    assert "白天很热" in docs[0].content
    assert docs[0].url == "https://example.test/note"
    assert docs[0].like_count == 12
    assert docs[0].comment_count == 3


def test_media_crawler_adapter_reads_fake_cli_output(tmp_path: Path) -> None:
    media_root = tmp_path / "MediaCrawler"
    media_root.mkdir()
    fake_main = media_root / "main.py"
    fake_main.write_text(
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
    'id': 'fake-1',
    'title': args.keywords,
    'content': '根据采集资料，重庆夜景好看但7月白天热。',
    'url': 'https://example.test/fake'
}, ensure_ascii=False) + '\\n', encoding='utf-8')
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
        ),
        platforms=["xhs"],
        request_id="req-fake",
    )

    docs = adapter.search("重庆 夜景", limit=2)

    assert not adapter.errors
    assert len(docs) == 1
    assert docs[0].platform == "xhs"
    assert docs[0].query == "重庆 夜景"
    assert "夜景好看" in docs[0].content
