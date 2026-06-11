---
name: travel-research-agent
description: Evidence-grounded travel research workflow bundled with this repository. Use when the user asks Codex to research whether a destination is worth visiting, generate a travel strategy, collect online travel notes with MediaCrawler, summarize pitfalls, compare suitability, or produce a report that must be grounded in collected sources rather than generic travel advice.
---

# Travel Research Agent

## Quick Start

Use the repository root that contains this skill as the project root. In this repository, the runnable backend script is `scripts/run_travel_research.py`.

Run the workflow without starting a web server:

```powershell
python scripts\run_travel_research.py "<user travel request>" --collection-mode auto --limit 5
```

Use `--collection-mode media_crawler` when the user explicitly wants real collection. Use `--collection-mode auto` when they want a working result even if MediaCrawler is missing or not logged in. Use `--collection-mode mock` only for demo or tests.

## Workflow

1. Work from the repository root.
2. Decide whether the user needs real collection or can use `auto`.
3. If real collection is requested, check that `external\MediaCrawler` exists. If it does not, run:

```powershell
.\scripts\setup_media_crawler.ps1
```

4. Run `scripts/run_travel_research.py` with the user's query.
5. Inspect the output metadata:
   - `collection_mode`
   - `llm_mode`
   - `collection_errors`
   - `collection_summary`
6. Treat the generated report as valid only when recommendations are backed by evidence and the report says it is based on collected sources.

## Output Expectations

Always surface the important result to the user:

- final judgement
- score
- collection mode and LLM mode
- whether MediaCrawler failed for any platform/query
- the Markdown report path or report body

If `llm_mode=fallback`, explicitly say evidence extraction used rule-based fallback because `OPENAI_API_KEY` was not configured.

If collection errors are present, do not hide them. Mention that the report may be based on partial sources.

## Safety Rules

- Do not bypass login, payment walls, CAPTCHA, or permission restrictions.
- Do not scrape private content.
- Keep platform limits small by default.
- Use manual platform login such as QR code when MediaCrawler asks for it.
- If sources are insufficient or contradictory, report that directly instead of inventing certainty.

## References

Read `references/media_crawler.md` when changing collection behavior, debugging MediaCrawler setup, or explaining why collection failed.

