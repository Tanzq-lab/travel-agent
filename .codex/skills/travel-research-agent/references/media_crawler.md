# MediaCrawler Notes

The repository integrates MediaCrawler through a subprocess boundary. It does not import or modify MediaCrawler source code.

Default local location relative to the repository root:

```text
external/MediaCrawler
```

Setup:

```powershell
.\scripts\setup_media_crawler.ps1
```

The project command uses this pattern per platform/query:

```powershell
uv run main.py --platform <platform> --lt qrcode --type search --keywords <query> --crawler_max_notes_count <limit> --save_data_option jsonl --save_data_path <request_run_dir> --get_comment false --get_sub_comment false --headless false
```

Platform aliases:

- `bilibili` -> `bili`
- `weibo` -> `wb`
- `xhs`, `zhihu`, `tieba` stay unchanged

Common failure causes:

- MediaCrawler has not been cloned.
- `uv` is not installed.
- Playwright browsers are not installed.
- The platform requires login or QR-code confirmation.
- Platform anti-abuse or permission rules prevent access.
- Network access to GitHub or a platform is unavailable.

Do not bypass login, CAPTCHA, paywalls, or permission restrictions.

## User-Supplied Platform Links

When the user provides Xiaohongshu or other platform links as required evidence:

- Treat them as part of the evidence corpus, not as optional examples.
- Resolve shortlinks when needed and save link status under `data/processed/`, for example `*_link_status_YYYYMMDD.tsv`.
- Use detail collection when available so the full note text, `note_id`, title, `note_url`, author metadata, and engagement counts are preserved.
- If network is unstable, retry a small number of times and record which attempts failed or succeeded.
- If a link cannot be opened, keep its original URL in the status file and mark it unavailable instead of silently dropping it.
- When extracting recommendations, keep the source URL or `note_url` so final deliverables can cite it.

## Evidence Hygiene

- Save raw crawler JSONL under `data/media_crawler_runs/`.
- Save processed summaries, point plans, link-status TSVs, and source maps under `data/processed/`.
- Do not mix raw crawler output into final user-facing output folders.
- If a source looks like an ad, low-information repost, or affiliate bait, downgrade confidence or exclude it from recommendations.
- Prefer recommendations supported by multiple independent personal notes, cross-platform agreement, or official/current context.
- For conflicting food reviews, preserve the disagreement and make the restaurant optional rather than mandatory.
- For volatile event times such as fountains, fireworks, night shows, openings, or weather-dependent items, distinguish "sample evidence says" from "official/current source confirms".
