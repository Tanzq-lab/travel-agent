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

