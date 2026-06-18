# Amap / Gaode Map Import Workflow

Use this workflow when the user wants the travel result to live in Gaode Map rather than in a long guide document.

## Key Rules

- The standard Gaode map mini-program Excel import template imports marked locations only.
- Importing markers does not automatically draw route lines or create route resources.
- If the user wants route lines, use a route-specific Gaode template/tool if they provide one. Otherwise state that the user must create routes in Gaode with "制作路线" or an equivalent UI after marker import.
- Put the actionable travel guidance into each marker's `描述` field so the map itself carries the plan.
- Do not keep redundant Markdown/HTML guide documents when the user asks for a map-first deliverable.

## Preferred Artifact Set

For a map-first travel output, produce:

- A Gaode-compatible marker import workbook (`.xlsx`) generated from the user's template.
- Optionally a same-schema CSV for review/debugging.
- Optionally a route-order JSON for future automation or manual route creation.

Avoid producing:

- Long Markdown/HTML guide documents unless the user explicitly asks for them.
- Decorative cover images or route thumbnails unless the user explicitly asks for social-media style output.

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
```

## Description Field Pattern

Keep each marker description under Gaode's 600-character limit. Use compact action-oriented text:

```text
Day1 09:00 起点。定位：...。动作：...。下一站：...。避坑：...。
```

Recommended description components:

- time slot or role in the day
- why this stop exists
- what to do at the stop
- next stop
- reservation or ticket caveat
- food/transport caveat
- skip condition

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
- Confirm point descriptions carry the itinerary guidance.
- Tell the user clearly whether the output imports markers only or also creates routes.
