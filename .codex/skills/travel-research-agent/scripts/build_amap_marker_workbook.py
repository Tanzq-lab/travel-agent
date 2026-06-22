from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("", MAIN_NS)

REQUIRED_COLUMNS = ["名称", "*经度", "*纬度", "*地址", "颜色", "图标(外轮廓)", "图标(填充物)", "描述", "文件夹"]

FIELD_ALIASES = {
    "名称": ("名称", "name", "title"),
    "*经度": ("*经度", "经度", "lng", "longitude"),
    "*纬度": ("*纬度", "纬度", "lat", "latitude"),
    "*地址": ("*地址", "地址", "address"),
    "颜色": ("颜色", "color"),
    "图标(外轮廓)": ("图标(外轮廓)", "outline_icon", "icon_outline"),
    "图标(填充物)": ("图标(填充物)", "fill_icon", "icon_fill"),
    "描述": ("描述", "description", "desc", "notes"),
    "文件夹": ("文件夹", "folder"),
}


def column_letter(index: int) -> str:
    out = ""
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def load_points(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        raw_points = data
    elif isinstance(data, dict):
        raw_points = data.get("points") or data.get("markers") or data.get("rows")
    else:
        raw_points = None

    if not isinstance(raw_points, list) or not raw_points:
        raise ValueError("Input JSON must contain a non-empty `points`, `markers`, or `rows` array.")

    points: list[dict[str, str]] = []
    for index, item in enumerate(raw_points, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Point #{index} is not an object.")
        row: dict[str, str] = {}
        for column, aliases in FIELD_ALIASES.items():
            value = ""
            for alias in aliases:
                if alias in item and item[alias] is not None:
                    value = str(item[alias])
                    break
            row[column] = value
        if not row["名称"]:
            raise ValueError(f"Point #{index} is missing `名称`/`name`.")
        if not row["*地址"] and not (row["*经度"] and row["*纬度"]):
            raise ValueError(f"Point #{index} must provide either address or longitude+latitude.")
        if len(row["描述"]) > 600:
            raise ValueError(f"Point #{index} description exceeds Gaode's 600-character limit.")
        points.append(row)
    return points


def inline_text(cell: ET.Element) -> str:
    inline = cell.find(f"{{{MAIN_NS}}}is")
    if inline is None:
        return ""
    return "".join(node.text or "" for node in inline.iter() if node.tag == f"{{{MAIN_NS}}}t")


def find_marker_sheet(zip_file: ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))

    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
    }

    sheets = workbook.find(f"{{{MAIN_NS}}}sheets")
    if sheets is None:
        raise RuntimeError("Workbook has no sheets.")

    first_sheet_target = None
    for sheet in sheets.findall(f"{{{MAIN_NS}}}sheet"):
        rid = sheet.attrib.get(f"{{{REL_NS}}}id")
        target = rel_targets.get(rid or "")
        if not target:
            continue
        if target.startswith("/"):
            normalized = target.lstrip("/")
        elif target.startswith("xl/"):
            normalized = target
        else:
            normalized = "xl/" + target
        if first_sheet_target is None:
            first_sheet_target = normalized
        if sheet.attrib.get("name") == sheet_name:
            return normalized

    if first_sheet_target:
        return first_sheet_target
    raise RuntimeError(f"Could not locate worksheet `{sheet_name}`.")


def cell(ref: str, value: str, style: str | None = None) -> ET.Element:
    result = ET.Element(f"{{{MAIN_NS}}}c", {"r": ref, "t": "inlineStr"})
    if style is not None:
        result.set("s", style)
    inline = ET.SubElement(result, f"{{{MAIN_NS}}}is")
    text = ET.SubElement(inline, f"{{{MAIN_NS}}}t")
    text.text = value
    if value.startswith(" ") or value.endswith(" "):
        text.set(f"{{{XML_NS}}}space", "preserve")
    return result


def row(row_num: int, values: list[str], styles: list[str | None]) -> ET.Element:
    result = ET.Element(f"{{{MAIN_NS}}}row", {"r": str(row_num)})
    for index, value in enumerate(values, start=1):
        result.append(cell(f"{column_letter(index)}{row_num}", value, styles[index - 1] if index - 1 < len(styles) else None))
    return result


def extract_row_styles(sheet_data: ET.Element, row_number: str) -> list[str | None]:
    target = sheet_data.find(f"{{{MAIN_NS}}}row[@r='{row_number}']")
    if target is None:
        return []
    return [c.attrib.get("s") for c in target.findall(f"{{{MAIN_NS}}}c")]


def replace_sheet(sheet_xml: bytes, points: list[dict[str, str]]) -> bytes:
    root = ET.fromstring(sheet_xml)
    sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
    if sheet_data is None:
        raise RuntimeError("Target worksheet does not contain sheetData.")

    header_styles = extract_row_styles(sheet_data, "1")
    data_styles = extract_row_styles(sheet_data, "2")
    if not header_styles:
        header_styles = [None] * len(REQUIRED_COLUMNS)
    if not data_styles:
        data_styles = [None] * len(REQUIRED_COLUMNS)

    for child in list(sheet_data):
        sheet_data.remove(child)

    sheet_data.append(row(1, REQUIRED_COLUMNS, header_styles))
    for row_num, point in enumerate(points, start=2):
        sheet_data.append(row(row_num, [point.get(column, "") for column in REQUIRED_COLUMNS], data_styles))

    dimension = root.find(f"{{{MAIN_NS}}}dimension")
    if dimension is not None:
        dimension.set("ref", f"A1:I{len(points) + 1}")

    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return re.sub(br"<\?xml version='1.0' encoding='utf-8'\?>", b'<?xml version="1.0" encoding="UTF-8"?>', xml, count=1)


def write_workbook(template: Path, output: Path, points: list[dict[str, str]], sheet_name: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(template, "r") as zin:
        sheet_path = find_marker_sheet(zin, sheet_name)
        with ZipFile(output, "w", ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == sheet_path:
                    data = replace_sheet(data, points)
                zout.writestr(info, data)


def write_csv(output: Path, points: list[dict[str, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(points)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Gaode/Amap marker import workbook from a JSON point plan.")
    parser.add_argument("--template", required=True, type=Path, help="Gaode marker import .xlsx template.")
    parser.add_argument("--input", required=True, type=Path, help="JSON file containing points/markers/rows.")
    parser.add_argument("--out-xlsx", required=True, type=Path, help="Output .xlsx path.")
    parser.add_argument("--out-csv", type=Path, help="Optional same-schema CSV output path.")
    parser.add_argument("--sheet-name", default="标记位置", help="Marker worksheet name in the template.")
    args = parser.parse_args()

    points = load_points(args.input)
    write_workbook(args.template, args.out_xlsx, points, args.sheet_name)
    if args.out_csv:
        write_csv(args.out_csv, points)

    print(args.out_xlsx)
    if args.out_csv:
        print(args.out_csv)


if __name__ == "__main__":
    main()
