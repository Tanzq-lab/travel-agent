# Amap / Gaode Map Import Workflow

Use this workflow when the user wants the travel result to live in Gaode Map rather than in a long guide document.

## Key Rules

- The standard Gaode map mini-program Excel import template imports marked locations only.
- Importing markers does not automatically draw route lines or create route resources.
- If the user wants route lines, use a route-specific Gaode template/tool if they provide one. Otherwise state that the user must create routes in Gaode with "制作路线" or an equivalent UI after marker import.
- Put the actionable travel guidance into each marker's `描述` field so the map itself carries the plan. The companion note is not enough.
- If the route note contains citations, links, or recommendation sources, the workbook must contain them too.
- Do not keep redundant Markdown/HTML guide documents when the user asks for a map-first deliverable.
- Provide a concise companion note for map-first deliverables. It should explain import steps and evidence-based route decisions, not duplicate a long guide article.
- Keep the final output directory user-facing. Remove or move intermediate CSV, JSON point plans, raw response JSON, sqlite/vector-store files, crawler scratch runs, screenshots, and other debug artifacts before the final answer unless the user asked for them.

## Preferred Artifact Set

For a map-first travel output, produce:

- A Gaode-compatible marker import workbook (`.xlsx`) generated from the user's template.
- A short companion note such as `导入说明与决策依据.txt` or `map_import_notes.md` covering import steps, route rationale, source confidence, pitfalls, weather/time tradeoffs, and known limitations.
- A processed point-plan JSON and evidence/source summary under `data/processed/`, not in the final output directory.
- Optionally a same-schema CSV for review/debugging, but keep it outside the final delivery directory or delete it before final response unless requested.
- Optionally a route-order JSON for future automation or manual route creation, but keep it as scratch/debug output unless requested.

Avoid producing:

- Long Markdown/HTML guide documents unless the user explicitly asks for them.
- Decorative cover images or route thumbnails unless the user explicitly asks for social-media style output.
- A final directory cluttered with internal evidence dumps, raw workflow JSON, local databases, or vector stores.

## Companion Decision Note

For map-first outputs, the companion note should be concise but decision-complete. Include:

- the exact workbook path and step-by-step import instructions
- a clear statement that this import creates markers only, not route lines
- the evidence corpus summary: platforms requested, platforms that succeeded, document counts if available, `collection_mode`, `llm_mode`, and collection errors
- confidence by source/platform, especially when one requested platform failed, hit CAPTCHA, or only has initialization/sample data
- why the selected day-by-day route was chosen over plausible alternatives
- why backup or not-recommended points were not put in the main route
- weather, train/flight times, lodging assumptions, and other hard constraints that changed the plan
- concrete pitfalls from sources: rushed itineraries, long transfers, queue/booking risks, food/transport caveats, commercialized stops, and skip conditions
- a statement that the marker workbook itself includes daily route guidance and the source-link folder

If the user provides an exact outline, follow it. Put the operational details into the requested sections instead of adding new top-level sections.

Do not make the note a generic travel article. It should explain the map package and the choices encoded in the markers.

## Marker Workbook Fields

For the common Gaode marker template, preserve these columns exactly:

```text
名称
*经度
*纬度
*地址
颜色
图标(外轮廓)
图标(填充物)
描述
文件夹
```

If the template differs, inspect the workbook and follow its actual header row.

## Point Naming

Use ordered names to preserve route order inside Gaode:

```text
D1-01 Place Name
D1-02 Place Name
D2-01 Place Name
B1 Optional Place
X1 Avoid / Not Recommended
```

Use folder hierarchy to make route groups obvious:

```text
Trip Name/Day1 Route Theme
Trip Name/Day2 Route Theme
Trip Name/Backup Route
Trip Name/Not Recommended
Trip Name/引用链接
```

Recommended folder categories:

- `Day1...`, `Day2...`, `Day3...` for ordered main route markers.
- `餐饮备选` for credible but non-binding food options.
- `换日备选节点` for worthwhile places that should replace, not add to, a day.
- `规则提醒和慎去` for constraints, volatile checks, and avoid conditions.
- `引用链接` for source IDs and full URLs used by marker descriptions.

## Description Field Pattern

Keep each marker description under Gaode's 600-character limit. Use compact action-oriented text:

```text
Day1 09:00 起点。定位：...。动作：...。下一站：...。避坑：...。
```

Recommended description components:

- day-level route context for day-start markers
- time slot or role in the day
- why this stop exists under the user's weights
- what to see at scenic/city markers
- what to eat at dining markers
- next stop
- reservation or ticket caveat
- food/transport caveat
- skip condition
- source IDs such as `[U1][U3]` that map to `引用链接` rows

For routes that include weighted preferences, reflect the weights directly:

```text
Day1全线：北站->酒店->中山广场->东港喷泉->水城->晚餐。权重：拍照40/好吃35/顺路15/不累10。下一站D1-02。完整来源见“引用链接”文件夹。
```

For scenic markers:

```text
Day1 18:40-20:05。看什么：喷泉、海边夜景、广场灯光。样本有19:40-20:00场次记录；以现场/高德/当天公告为准。下一站D1-07。来源[U1][U2]。
```

For dining markers:

```text
Day1 20:35后吃什么：首选WHERE·WHERE东港店，海胆披萨/肥佬肉酱意面；次选日月昇但评价分歧。排队>20分钟换店。来源[U5][U7]。
```

## Source Links In Workbook

When using citations:

1. Assign stable source IDs such as `U1`, `U2`, `O1` (official), or `W1` (web).
2. Put short IDs in route marker descriptions.
3. Add one marker per source in `Trip Name/引用链接`.
4. In each source marker's description, include:
   - what the source supports
   - the full URL
   - uncertainty if the source is only a sample, not an official schedule

Example:

```json
{
  "name": "U1 来源 大连三日休闲游行程记录",
  "address": "辽宁省大连市",
  "color": "6",
  "description": "支撑：港东五街->东港音乐喷泉->威尼斯水城；样本记录19:40-20:00喷泉场次，也提醒水城人多/登船排队。链接：https://www.xiaohongshu.com/explore/...",
  "folder": "Trip Name/引用链接"
}
```

Do not rely on the companion note alone for links. The user should be able to import the workbook and still inspect the sources inside Gaode.

## Route Decision Heuristics

For iterative travel planning, encode these heuristics in both the point plan and companion note:

- User-provided weights are route-scoring criteria, not decoration.
- Popular platform routes are evidence, not templates to copy.
- If the user says only same-day overlap matters, do not globally blacklist worthwhile classics. Move them to another day, short-stop them, or make them optional.
- All transport assumptions such as "全程打车" must be reflected in marker descriptions and skip conditions.
- Keep volatile items explicit: "sample says X; confirm via official/current source or onsite." Do not present unstable fountain/opening/weather times as guaranteed.
- Food recommendations need confidence handling. If sources conflict, mark the item as optional or "排队短再吃" instead of mandatory.

## Intermediate Files

Keep intermediate state outside the final delivery directory:

- Point plans: `data/processed/<destination>_points_<date>.json`
- Evidence summaries: `data/processed/<destination>_evidence_summary_<date>.md`
- Source maps or weighted-route notes: `data/processed/<destination>_source_map_<date>.md`
- Link status tables: `data/processed/<destination>_link_status_<date>.tsv`

Use these files to continue later revisions without recollecting sources unnecessarily.

## JSON Input Shape For The Helper Script

Use `.codex/skills/travel-research-agent/scripts/build_amap_marker_workbook.py`.

Input can be either a list of point objects or an object with `points`, `markers`, or `rows`.

```json
{
  "points": [
    {
      "name": "D1-01 Example Place",
      "address": "City District Street",
      "color": "1",
      "description": "Day1 09:00 起点。定位：...。下一站：D1-02 ...。",
      "folder": "Trip Name/Day1 Route"
    }
  ]
}
```

Supported aliases:

- `name`, `title`, `名称`
- `lng`, `longitude`, `经度`, `*经度`
- `lat`, `latitude`, `纬度`, `*纬度`
- `address`, `地址`, `*地址`
- `description`, `desc`, `notes`, `描述`
- `folder`, `文件夹`
- `outline_icon`, `icon_outline`, `图标(外轮廓)`
- `fill_icon`, `icon_fill`, `图标(填充物)`

Save the point-plan JSON under `data/processed/` before generating the workbook. For iterative revisions, keep the previous raw MediaCrawler runs under `data/media_crawler_runs/` and write a new concise decision/source summary under `data/processed/`.

Command:

```powershell
python .codex\skills\travel-research-agent\scripts\build_amap_marker_workbook.py `
  --template <gaode-template.xlsx> `
  --input <points.json> `
  --out-xlsx <map-import.xlsx> `
  --out-csv <map-import.csv>
```

## Validation Checklist

After generating the workbook:

- Open the `.xlsx` as a zip and verify `xl/worksheets/...` is valid XML.
- Confirm the marker sheet dimension covers all generated rows.
- Confirm row 1 contains the template headers.
- Confirm point descriptions carry the itinerary guidance, including what to see/eat, next stop, skip conditions, and source IDs.
- Confirm the workbook has a `引用链接` folder when citations are used, and that every source ID referenced in route descriptions has a corresponding source row with a full URL.
- Confirm the companion decision note exists when the output is map-first.
- Confirm the final delivery directory contains only user-facing files unless the user requested debug artifacts.
- Tell the user clearly whether the output imports markers only or also creates routes.
