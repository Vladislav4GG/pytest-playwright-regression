#!/usr/bin/env python3
"""Extract regression checklist cases from an .xlsx sheet without external deps."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {"m": NS_MAIN, "r": NS_REL}


@dataclass(frozen=True)
class CaseRow:
    case_id: int
    priority: str
    area: str
    function: str
    action: str
    test_data: str
    source_row: int


def col_to_index(col_letters: str) -> int:
    value = 0
    for ch in col_letters:
        value = value * 26 + (ord(ch) - 64)
    return value


def parse_shared_strings(zipf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zipf.namelist():
        return []

    sst = ET.fromstring(zipf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in sst.findall("m:si", NS):
        text = "".join(t.text or "" for t in si.findall(".//m:t", NS))
        values.append(text.strip())
    return values


def workbook_sheet_targets(zipf: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zipf.read("xl/workbook.xml"))
    rels = ET.fromstring(zipf.read("xl/_rels/workbook.xml.rels"))

    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{NS_PKG_REL}}}Relationship")
    }

    result: dict[str, str] = {}
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        sheet_name = sheet.attrib["name"]
        rid = sheet.attrib[f"{{{NS_REL}}}id"]
        target = rid_to_target[rid]
        path = target if target.startswith("xl/") else f"xl/{target}"
        result[sheet_name] = path

    return result


def parse_sheet_rows(
    zipf: ZipFile,
    sheet_xml_path: str,
    shared_strings: list[str],
) -> dict[int, dict[int, str]]:
    root = ET.fromstring(zipf.read(sheet_xml_path))
    rows: dict[int, dict[int, str]] = defaultdict(dict)

    for cell in root.findall(".//m:sheetData/m:row/m:c", NS):
        ref = cell.attrib.get("r", "")
        match = re.match(r"([A-Z]+)(\d+)$", ref)
        if not match:
            continue

        col_letters, row_str = match.groups()
        col = col_to_index(col_letters)
        row = int(row_str)

        value = ""
        cell_type = cell.attrib.get("t")
        v = cell.find("m:v", NS)

        if cell_type == "s" and v is not None and v.text is not None:
            idx = int(v.text)
            value = shared_strings[idx] if 0 <= idx < len(shared_strings) else v.text
        elif cell_type == "inlineStr":
            inline = cell.find("m:is", NS)
            if inline is not None:
                value = "".join(t.text or "" for t in inline.findall(".//m:t", NS))
        elif v is not None and v.text is not None:
            value = v.text

        rows[row][col] = value.strip()

    return rows


def normalize_header(text: str) -> str:
    return " ".join(text.strip().lower().split())


def find_header_row(rows: dict[int, dict[int, str]]) -> int:
    for row_number in sorted(rows):
        first_cell = normalize_header(rows[row_number].get(1, ""))
        if first_cell == "no.":
            return row_number
    raise ValueError("Header row was not found (expected first header cell to be 'No.').")


def resolve_columns(header_row: dict[int, str]) -> dict[str, int]:
    by_name = {normalize_header(v): k for k, v in header_row.items() if v}

    def pick(*candidates: str) -> int:
        for name in candidates:
            index = by_name.get(normalize_header(name))
            if index:
                return index
        raise ValueError(f"Missing required column. Tried: {candidates}")

    return {
        "no": pick("No."),
        "priority": pick("Priority"),
        "area": pick("Area/Page"),
        "function": pick("Function", "Function "),
        "action": pick("Action"),
        "test_data": pick("Test Data"),
    }


def extract_cases(rows: dict[int, dict[int, str]], columns: dict[str, int], header_row_num: int) -> list[CaseRow]:
    cases: list[CaseRow] = []

    for row_num in sorted(rows):
        if row_num <= header_row_num:
            continue

        no_value = rows[row_num].get(columns["no"], "")
        if not re.fullmatch(r"\d+", str(no_value)):
            continue

        cases.append(
            CaseRow(
                case_id=int(no_value),
                priority=rows[row_num].get(columns["priority"], ""),
                area=rows[row_num].get(columns["area"], ""),
                function=rows[row_num].get(columns["function"], ""),
                action=rows[row_num].get(columns["action"], ""),
                test_data=rows[row_num].get(columns["test_data"], ""),
                source_row=row_num,
            )
        )

    return sorted(cases, key=lambda c: c.case_id)


def write_json(path: Path, xlsx: Path, sheet: str, header_row_num: int, cases: list[CaseRow]) -> None:
    payload = {
        "source_file": str(xlsx),
        "sheet": sheet,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "header_row": header_row_num,
        "case_count": len(cases),
        "cases": [
            {
                "id": c.case_id,
                "priority": c.priority,
                "area": c.area,
                "function": c.function,
                "action": c.action,
                "test_data": c.test_data,
                "source_row": c.source_row,
            }
            for c in cases
        ],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_csv(path: Path, cases: list[CaseRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "priority", "area", "function", "action", "test_data", "source_row"])
        for c in cases:
            writer.writerow(
                [c.case_id, c.priority, c.area, c.function, c.action, c.test_data, c.source_row]
            )


def print_summary(cases: list[CaseRow]) -> None:
    priority_counts = Counter(c.priority or "(empty)" for c in cases)
    area_counts = Counter(c.area or "(empty)" for c in cases)

    print(f"Extracted {len(cases)} cases")
    print("Priority:")
    for key, count in priority_counts.most_common():
        print(f"  - {key}: {count}")

    print("Top areas:")
    for key, count in area_counts.most_common(12):
        print(f"  - {key}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract test checklist rows from an Excel sheet into JSON/CSV."
    )
    parser.add_argument("--xlsx", required=True, help="Path to .xlsx file")
    parser.add_argument("--sheet", default="B2C GB", help="Sheet name to parse")
    parser.add_argument(
        "--json-out",
        default="data/regression/b2c_gb_cases.json",
        help="Path to output JSON",
    )
    parser.add_argument(
        "--csv-out",
        default="data/regression/b2c_gb_cases.csv",
        help="Path to output CSV",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Do not write CSV output",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print aggregated summary to stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    xlsx = Path(args.xlsx).expanduser().resolve()
    if not xlsx.exists():
        raise FileNotFoundError(f"Input file does not exist: {xlsx}")

    with ZipFile(xlsx) as zipf:
        sheets = workbook_sheet_targets(zipf)
        if args.sheet not in sheets:
            available = ", ".join(sorted(sheets))
            raise ValueError(f"Sheet '{args.sheet}' not found. Available: {available}")

        shared_strings = parse_shared_strings(zipf)
        rows = parse_sheet_rows(zipf, sheets[args.sheet], shared_strings)

    header_row_num = find_header_row(rows)
    columns = resolve_columns(rows[header_row_num])
    cases = extract_cases(rows, columns, header_row_num)

    if not cases:
        raise RuntimeError("No numeric case rows found in selected sheet.")

    json_out = Path(args.json_out)
    write_json(json_out, xlsx, args.sheet, header_row_num, cases)

    if not args.no_csv:
        write_csv(Path(args.csv_out), cases)

    if args.summary:
        print_summary(cases)

    print(f"JSON: {json_out}")
    if not args.no_csv:
        print(f"CSV: {args.csv_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
