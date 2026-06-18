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

Platform UGC rule: for Xiaohongshu, Bilibili, Zhihu, Weibo, Tieba, and similar travel-note platforms, treat MediaCrawler as the primary collection path because public web search only exposes partial and unstable platform data. Public web or official sources may be used only as context or citation supplements; they do not replace the required MediaCrawler corpus when the requested research is supposed to include these UGC platforms.

Initialization rule: installation, CDP browser preparation, platform login, QR-code login, cookie preparation, and platform readiness checks belong to a user-approved initialization flow, not the research flow. Do not start ad-hoc login, launch/control the user's browser, or perform platform setup while answering a research request.

## Workflow

1. Work from the repository root.
2. Use real MediaCrawler collection unless the user explicitly asks for a fallback/demo mode.
3. Check that MediaCrawler has already been initialized. Initialization is done with:

```powershell
.\scripts\initialize_media_crawler.ps1
```

   This script installs MediaCrawler if needed, uses an already-running CDP browser or a browser explicitly allowed with `-StartCdpBrowser`, asks the user to complete any platform login, runs small readiness checks, and writes `data/media_crawler_init/status.json`.
4. If initialization status is missing, incomplete, stale, or does not cover the requested platforms, stop and tell the user to run the initialization script. Do not proceed to research collection.
5. Run `scripts/run_travel_research.py` with the user's query.
6. Inspect the output metadata:
   - `collection_mode`
   - `llm_mode`
   - `collection_errors`
   - `collection_summary`
7. Treat the generated report as valid only when all of these are true:
   - `collection_summary.mode` is `media_crawler`
   - `collection_summary.total_docs` is greater than `0`
   - recommendations are backed by MediaCrawler-collected evidence
   - the report says it is based on collected sources
8. If the validity checks fail, stop at a collection status report. Surface the metadata and errors, then state that no travel conclusion can be given until MediaCrawler collection succeeds.

## Output Target Handling

Confirm the requested delivery shape before creating heavy artifacts. If the user asks for a map-first output, an import file, or says they do not need a guide document, do not generate a long Markdown/HTML travel article by default. Put the actionable travel information into the destination artifact itself.

For Gaode/Amap map outputs:

- Read `references/amap_map_import.md` before generating the artifact.
- If the user provides an Excel import template, read the actual workbook structure first and preserve its worksheet names, headers, styles, and auxiliary instruction/color sheets. Do not invent a CSV-only schema when a template is available.
- The Gaode map mini-program marker import template imports marked locations only. It does not automatically draw route lines or create "制作路线" resources. Make this limitation explicit.
- For the standard Gaode marker template, write concise actionable guidance into each point's `描述` field: time slot, role in the route, next stop, skip/avoid advice, booking notes, and food/transport caveats.
- Use ordered names such as `D1-01 ...`, `D2-01 ...` and hierarchical `文件夹` values to preserve itinerary order inside the map.
- If the user needs actual route lines, ask for or use a route-specific template/tool. Otherwise provide the marker import file plus route order metadata, and state that route creation still requires Gaode's "制作路线" or equivalent UI.
- Avoid keeping redundant guide documents when the map import file is the requested final deliverable.
- Prefer `.codex/skills/travel-research-agent/scripts/build_amap_marker_workbook.py` for generating a marker import workbook from a JSON point plan and the user's Excel template.

## Output Expectations

Always surface the important result to the user:

- collection mode and LLM mode
- whether MediaCrawler failed for any platform/query
- the final artifact path: Markdown/HTML report, map import workbook, route data, or another user-requested deliverable

Only surface final judgement and score when MediaCrawler collection succeeded and produced usable source documents. If collection did not succeed, explicitly say no conclusion is provided because MediaCrawler research was not completed.

If `llm_mode=fallback`, explicitly say evidence extraction used rule-based fallback because `OPENAI_API_KEY` was not configured.

If collection errors are present, do not hide them. If usable MediaCrawler documents were still collected, mention that the report may be based on partial sources. If no usable MediaCrawler documents were collected, do not provide conclusions or recommendations.

If the error says MediaCrawler is not initialized, the correct next step is `.\scripts\initialize_media_crawler.ps1`; do not run platform login inside the research task.

## Safety Rules

- Do not bypass login, payment walls, CAPTCHA, or permission restrictions.
- Do not scrape private content.
- Keep platform limits small by default.
- Use manual platform login such as QR code when MediaCrawler asks for it.
- If sources are insufficient or contradictory, report that directly instead of inventing certainty.

## References

Read `references/media_crawler.md` when changing collection behavior, debugging MediaCrawler setup, or explaining why collection failed.

Read `references/amap_map_import.md` when the requested output is a Gaode/Amap import workbook or map-first travel plan.
