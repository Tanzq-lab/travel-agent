---
name: travel-research-agent
description: Evidence-grounded travel research workflow bundled with this repository. Use when the user asks Codex to research whether a destination is worth visiting, generate a travel strategy, collect online travel notes with MediaCrawler, summarize pitfalls, compare suitability, or produce a report that must be grounded in collected sources rather than generic travel advice.
---

# Travel Research Agent

## Quick Start

Use the repository root that contains this skill as the project root. In this repository, the runnable backend script is `scripts/run_travel_research.py`.

Run the workflow without starting a web server:

```powershell
python scripts\run_travel_research.py "<user travel request>" --collection-mode media_crawler --limit 5
```

Use `--collection-mode media_crawler` by default for research tasks. Use `--collection-mode auto` only when the user explicitly accepts fallback behavior. Use `--collection-mode mock` only for demo or tests.

Hard rule: if MediaCrawler research did not actually run and collect usable source documents, do not give a travel conclusion, score, itinerary, suitability judgement, or recommendations. Do not substitute model knowledge, generic travel advice, official website browsing, or `mock` data for the MediaCrawler evidence corpus.

## Workflow

1. Work from the repository root.
2. Use real MediaCrawler collection unless the user explicitly asks for a fallback/demo mode.
3. Check that `external\MediaCrawler` exists. If it does not, run:

```powershell
.\scripts\setup_media_crawler.ps1
```

4. Run `scripts/run_travel_research.py` with the user's query.
5. Inspect the output metadata:
   - `collection_mode`
   - `llm_mode`
   - `collection_errors`
   - `collection_summary`
6. Treat the generated report as valid only when all of these are true:
   - `collection_summary.mode` is `media_crawler`
   - `collection_summary.total_docs` is greater than `0`
   - recommendations are backed by MediaCrawler-collected evidence
   - the report says it is based on collected sources
7. If the validity checks fail, stop at a collection status report. Surface the metadata and errors, then state that no travel conclusion can be given until MediaCrawler collection succeeds.

## Output Expectations

Always surface the important result to the user:

- collection mode and LLM mode
- whether MediaCrawler failed for any platform/query
- the Markdown report path or report body

Only surface final judgement and score when MediaCrawler collection succeeded and produced usable source documents. If collection did not succeed, explicitly say no conclusion is provided because MediaCrawler research was not completed.

If `llm_mode=fallback`, explicitly say evidence extraction used rule-based fallback because `OPENAI_API_KEY` was not configured.

If collection errors are present, do not hide them. If usable MediaCrawler documents were still collected, mention that the report may be based on partial sources. If no usable MediaCrawler documents were collected, do not provide conclusions or recommendations.

## Safety Rules

- Do not bypass login, payment walls, CAPTCHA, or permission restrictions.
- Do not scrape private content.
- Keep platform limits small by default.
- Use manual platform login such as QR code when MediaCrawler asks for it.
- If sources are insufficient or contradictory, report that directly instead of inventing certainty.

## References

Read `references/media_crawler.md` when changing collection behavior, debugging MediaCrawler setup, or explaining why collection failed.
