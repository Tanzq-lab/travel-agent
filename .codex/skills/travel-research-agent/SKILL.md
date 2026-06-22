---
name: travel-research-agent
description: Evidence-grounded travel research workflow bundled with this repository. Use when the user asks Codex to research whether a destination is worth visiting, generate or iteratively revise a travel strategy, collect online travel notes with MediaCrawler, summarize pitfalls, compare suitability, apply route-scoring weights, produce cited recommendations, or create a map-first itinerary/import package such as Gaode/Amap whose markers carry the actionable plan and source links.
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

## Operating Standard

Use this project as an evidence-to-itinerary system, not a generic guide writer.

- Preserve intermediate research and decisions under `data/processed/` so later optimization can resume from the current state.
- When the user iterates on an existing route, update the source point plan and regenerate the final artifact; do not only edit the prose note.
- Treat the user's constraints as scoring rules. If they give weights such as `拍照 40% + 好吃 35% + 顺路 15% + 不累 10%`, reflect those weights in route selection, marker descriptions, and the rationale.
- Do not blindly copy popular platform routes. Use platform notes as an evidence pool, then route by the user's weights, lodging, arrival/departure times, weather, transport mode, and fatigue tolerance.
- Avoid blacklisting good places solely because they appear in a reference route. If the user only wants to avoid same-day overlap, move worthwhile nodes to another day or make them optional.
- If recommending food, views, events, or pitfalls, include citation IDs and source links in the deliverable, not only in the final chat response.
- For volatile items such as fountain shows, weather, opening hours, ferry schedules, or ticketed events, verify when possible. If a stable source is unavailable, mark the time as sample-based/uncertain and tell the user how to confirm.

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

## Iterative Route Revision

When refining an already-generated itinerary:

1. Read the current point plan, companion note, and processed evidence summaries.
2. Apply the latest user message as the controlling constraint.
3. Save an updated point plan under `data/processed/`.
4. Save or update a concise evidence/decision summary under `data/processed/`.
5. Regenerate the map/import artifact and companion note.
6. Validate the workbook, final folder cleanliness, and source-link presence before responding.

## Output Target Handling

Confirm the requested delivery shape before creating heavy artifacts. If the user asks for a map-first output, an import file, or says they do not need a guide document, do not generate a long Markdown/HTML travel article by default. Put the actionable travel information into the destination artifact itself.

For Gaode/Amap map outputs:

- Read `references/amap_map_import.md` before generating the artifact.
- If the user provides an Excel import template, read the actual workbook structure first and preserve its worksheet names, headers, styles, and auxiliary instruction/color sheets. Do not invent a CSV-only schema when a template is available.
- The Gaode map mini-program marker import template imports marked locations only. It does not automatically draw route lines or create "制作路线" resources. Make this limitation explicit.
- For the standard Gaode marker template, write concise actionable guidance into each point's `描述` field: daily route context, time slot, what to see, what to eat, next stop, skip/avoid advice, booking notes, food/transport caveats, and source IDs such as `[U1]`.
- If the companion note contains citation links, the workbook must contain them too. Add a `引用链接` folder with `U1 ...` marker rows whose descriptions include full source URLs and what each source supports.
- Use ordered names such as `D1-01 ...`, `D2-01 ...` and hierarchical `文件夹` values to preserve itinerary order inside the map.
- Always pair the marker workbook with a concise user-facing decision/rationale note, unless the user explicitly asks for the workbook only. This note is not a generic guide: it must explain how to import the workbook, why this route was chosen over plausible alternatives, which source themes support the choices, what pitfalls were found, how weather/time constraints changed the plan, and what confidence level each source/platform supports. If the user gives an exact outline, preserve that outline.
- If the user needs actual route lines, ask for or use a route-specific template/tool. Otherwise provide the marker import file plus route order metadata, and state that route creation still requires Gaode's "制作路线" or equivalent UI.
- Avoid keeping redundant Markdown/HTML guide documents when the map import file is the requested final deliverable. A short `.txt`/`.md` decision note is acceptable and expected for map-first outputs when it explains operation and evidence-based tradeoffs.
- Keep the final delivery directory clean. Do not leave debug CSV, point-plan JSON, raw response JSON, sqlite databases, vector stores, crawler scratch folders, screenshots, or other intermediate files next to the user-facing artifact unless the user explicitly requests them. Store intermediate research artifacts under `data/` or a separate scratch path, or remove them before the final response.
- Prefer `.codex/skills/travel-research-agent/scripts/build_amap_marker_workbook.py` for generating a marker import workbook from a JSON point plan and the user's Excel template.

## Output Expectations

Always surface the important result to the user:

- collection mode and LLM mode
- whether MediaCrawler failed for any platform/query
- the final artifact path: Markdown/HTML report, map import workbook, route data, or another user-requested deliverable
- for map/import deliverables, the path to the companion decision/rationale note and the fact that the final folder has been cleaned of intermediate files
- whether route details and source links were embedded in the import workbook itself
- where intermediate point plans and evidence summaries were saved

Only surface final judgement and score when MediaCrawler collection succeeded and produced usable source documents. If collection did not succeed, explicitly say no conclusion is provided because MediaCrawler research was not completed.

If `llm_mode=fallback`, explicitly say evidence extraction used rule-based fallback because `OPENAI_API_KEY` was not configured.

If collection errors are present, do not hide them. If usable MediaCrawler documents were still collected, mention that the report may be based on partial sources. For requested platforms that failed or produced only initialization/sample data, mark their confidence separately instead of implying full coverage. If no usable MediaCrawler documents were collected, do not provide conclusions or recommendations.

If the error says MediaCrawler is not initialized, the correct next step is `.\scripts\initialize_media_crawler.ps1`; do not run platform login inside the research task.

## Safety Rules

- Do not bypass login, payment walls, CAPTCHA, or permission restrictions.
- Do not scrape private content.
- Keep platform limits small by default.
- Use manual platform login such as QR code when MediaCrawler asks for it.
- If sources are insufficient or contradictory, report that directly instead of inventing certainty.

## References

Read `references/media_crawler.md` when changing collection behavior, processing user-supplied platform links, debugging MediaCrawler setup, or explaining why collection failed.

Read `references/amap_map_import.md` when the requested output is a Gaode/Amap import workbook or map-first travel plan.
