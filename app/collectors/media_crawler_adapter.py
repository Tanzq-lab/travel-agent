from __future__ import annotations

import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any

from app.collectors.base import SourceCollector
from app.schemas import CollectionError, RawDocument


PLATFORM_ALIASES = {
    "xhs": "xhs",
    "zhihu": "zhihu",
    "bilibili": "bili",
    "bili": "bili",
    "weibo": "wb",
    "wb": "wb",
    "tieba": "tieba",
}


@dataclass
class MediaCrawlerRunConfig:
    root: Path
    runner: str = "uv run"
    login_type: str = "qrcode"
    save_option: str = "jsonl"
    headless: bool = False
    runs_path: Path = Path("data/media_crawler_runs")
    sleep_seconds: float = 1.0
    rate_limit_per_minute: int = 10
    timeout_seconds: int = 120
    require_initialized: bool = False
    init_status_path: Path | None = Path("data/media_crawler_init/status.json")


@dataclass
class MediaCrawlerAdapter(SourceCollector):
    """Run MediaCrawler through CLI and normalize saved outputs into RawDocument."""

    config: MediaCrawlerRunConfig
    platforms: list[str]
    request_id: str
    errors: list[CollectionError] = field(default_factory=list)
    _query_counter: int = 0
    _init_error_reported: bool = False

    def search(self, query: str, limit: int) -> list[RawDocument]:
        """Search all configured platforms through MediaCrawler for one query."""

        root = self.config.root.resolve()
        if not root.exists():
            self.errors.append(
                CollectionError(
                    platform=None,
                    query=query,
                    error=f"MediaCrawler root not found: {root}. Run scripts/setup_media_crawler.ps1 first.",
                )
            )
            return []

        init_error = self._initialization_error()
        if init_error:
            if not self._init_error_reported:
                self.errors.append(CollectionError(platform=None, query=query, error=init_error))
                self._init_error_reported = True
            return []

        self._query_counter += 1
        results: list[RawDocument] = []
        interval = 60.0 / max(self.config.rate_limit_per_minute, 1)

        for platform in self._normalized_platforms():
            started_at = time.monotonic()
            run_dir = self._run_dir(platform, query).resolve()
            run_dir.mkdir(parents=True, exist_ok=True)
            cmd = self.build_command(platform=platform, query=query, limit=limit, run_dir=run_dir)
            completed = _run_command(
                cmd,
                cwd=str(root),
                timeout_seconds=self.config.timeout_seconds,
            )
            if completed.returncode != 0:
                self.errors.append(
                    CollectionError(
                        platform=platform,
                        query=query,
                        error=_trim_error(completed.stderr or completed.stdout),
                    )
                )
            else:
                parsed = MediaCrawlerOutputParser.parse_directory(run_dir, query=query, platform=platform)
                if not parsed:
                    self.errors.append(
                        CollectionError(
                            platform=platform,
                            query=query,
                            error=f"MediaCrawler completed but no {self.config.save_option} records were found in {run_dir}.",
                        )
                    )
                results.extend(parsed)

            elapsed = time.monotonic() - started_at
            time.sleep(max(self.config.sleep_seconds, interval - elapsed, 0.0))

        return results

    def build_command(self, platform: str, query: str, limit: int, run_dir: Path) -> list[str]:
        """Build the MediaCrawler CLI command for a single platform/query."""

        return [
            *shlex.split(self.config.runner, posix=False),
            "main.py",
            "--platform",
            platform,
            "--lt",
            self.config.login_type,
            "--type",
            "search",
            "--keywords",
            query,
            "--crawler_max_notes_count",
            str(limit),
            "--save_data_option",
            self.config.save_option,
            "--save_data_path",
            str(run_dir.resolve()),
            "--get_comment",
            "false",
            "--get_sub_comment",
            "false",
            "--headless",
            "true" if self.config.headless else "false",
        ]

    def run_root(self) -> Path:
        """Return the top-level run directory for this request."""

        return self.config.runs_path / self.request_id

    def _normalized_platforms(self) -> list[str]:
        normalized: list[str] = []
        for platform in self.platforms:
            mapped = PLATFORM_ALIASES.get(platform.lower())
            if mapped and mapped not in normalized:
                normalized.append(mapped)
        return normalized

    def _run_dir(self, platform: str, query: str) -> Path:
        query_hash = sha1(query.encode("utf-8")).hexdigest()[:10]
        return self.run_root() / platform / f"{self._query_counter:03d}-{query_hash}"

    def _initialization_error(self) -> str | None:
        if not self.config.require_initialized:
            return None

        status_path = self.config.init_status_path
        if status_path is None:
            return None

        if not status_path.exists():
            return (
                "MediaCrawler is not initialized. Run "
                "scripts\\initialize_media_crawler.ps1 before media_crawler research."
            )

        try:
            status = json.loads(status_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            return f"MediaCrawler initialization status is unreadable: {status_path} ({exc})."

        if not status.get("initialized"):
            return (
                "MediaCrawler initialization is incomplete. Run "
                "scripts\\initialize_media_crawler.ps1 and complete platform login before research."
            )

        ready_platforms = {str(item).lower() for item in status.get("ready_platforms", [])}
        requested_platforms = set(self._normalized_platforms())
        missing_platforms = sorted(requested_platforms - ready_platforms)
        if missing_platforms:
            return (
                "MediaCrawler is not initialized for requested platform(s): "
                f"{', '.join(missing_platforms)}. Run scripts\\initialize_media_crawler.ps1 "
                f"-Platforms {','.join(missing_platforms)} first."
            )

        cdp_port = status.get("cdp_port")
        if cdp_port is not None:
            try:
                port = int(cdp_port)
            except (TypeError, ValueError):
                return f"MediaCrawler initialization status has an invalid cdp_port: {cdp_port!r}."
            if not _is_tcp_port_open("127.0.0.1", port):
                return (
                    f"MediaCrawler CDP browser is not running on port {port}. Run "
                    "scripts\\initialize_media_crawler.ps1 again before research."
                )

        return None


class MediaCrawlerOutputParser:
    """Parse MediaCrawler JSON/JSONL output files into the app RawDocument schema."""

    @classmethod
    def parse_directory(cls, directory: Path, *, query: str, platform: str) -> list[RawDocument]:
        """Parse all JSON and JSONL files under a run directory."""

        documents: list[RawDocument] = []
        for path in sorted(directory.rglob("*")):
            if path.suffix.lower() == ".jsonl":
                documents.extend(cls._parse_jsonl(path, query=query, platform=platform))
            elif path.suffix.lower() == ".json":
                documents.extend(cls._parse_json(path, query=query, platform=platform))
        return documents

    @classmethod
    def _parse_jsonl(cls, path: Path, *, query: str, platform: str) -> list[RawDocument]:
        documents: list[RawDocument] = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                doc = cls._to_raw_document(item, query=query, platform=platform)
                if doc:
                    documents.append(doc)
        return documents

    @classmethod
    def _parse_json(cls, path: Path, *, query: str, platform: str) -> list[RawDocument]:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return []
        items = parsed if isinstance(parsed, list) else [parsed]
        documents: list[RawDocument] = []
        for item in items:
            if isinstance(item, dict):
                doc = cls._to_raw_document(item, query=query, platform=platform)
                if doc:
                    documents.append(doc)
        return documents

    @staticmethod
    def _to_raw_document(item: dict[str, Any], *, query: str, platform: str) -> RawDocument | None:
        content = _first_text(
            item,
            [
                "content",
                "desc",
                "note_desc",
                "description",
                "text",
                "answer_content",
                "article_content",
                "video_desc",
                "brief",
            ],
        )
        title = _first_text(
            item,
            [
                "title",
                "note_title",
                "display_title",
                "question_title",
                "article_title",
                "video_title",
                "desc",
            ],
        )
        if not content:
            content = title
        if not content:
            return None

        doc_id = _first_text(
            item,
            [
                "id",
                "note_id",
                "aweme_id",
                "article_id",
                "question_id",
                "answer_id",
                "video_id",
                "bvid",
                "mblogid",
                "post_id",
            ],
        )
        if not doc_id:
            doc_id = sha1(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]

        return RawDocument(
            id=f"{platform}:{doc_id}",
            platform=platform,
            query=query,
            title=title,
            content=content,
            url=_first_text(item, ["url", "note_url", "source_url", "web_url", "video_url", "article_url"]),
            author=_first_text(item, ["author", "nickname", "user_name", "user_nickname", "nick_name", "screen_name"]),
            publish_time=_first_text(item, ["publish_time", "time", "created_time", "create_time", "last_modify_ts"]),
            like_count=_first_int(item, ["like_count", "liked_count", "liked_num", "digg_count", "attitudes_count"]),
            collect_count=_first_int(item, ["collect_count", "collected_count", "fav_count", "favorite_count"]),
            comment_count=_first_int(item, ["comment_count", "comments_count", "reply_count"]),
            raw=item,
        )


def _first_text(item: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_int(item: dict[str, Any], keys: list[str]) -> int | None:
    for key in keys:
        value = item.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _run_command(cmd: list[str], *, cwd: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    popen_kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **popen_kwargs,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        timeout_message = f"MediaCrawler timed out after {timeout_seconds} seconds and was terminated."
        stderr = "\n".join(part for part in [timeout_message, stderr] if part)
        return subprocess.CompletedProcess(cmd, 124, stdout, stderr)

    return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _is_tcp_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def _trim_error(text: str, limit: int = 500) -> str:
    stripped = " ".join(text.split())
    return stripped[:limit] if stripped else "unknown MediaCrawler error"
