#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "cloudstrucc-pages.schema.json"

def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)

data = json.loads(SCHEMA.read_text(encoding="utf-8"))
if data["publisher"]["prefix"] != "cs":
    fail("Publisher prefix must be cs")

seen_tables: set[str] = set()
for table in data.get("tables", []):
    logical = table.get("logicalName", "")
    if not logical.startswith("cs_"):
        fail(f"Table logical name must start with cs_: {logical}")
    if logical in seen_tables:
        fail(f"Duplicate table: {logical}")
    seen_tables.add(logical)
    primary = table.get("primaryName") or {}
    if primary.get("schemaName") != "cs_Name":
        fail(f"{logical}: primary name schema must be cs_Name")
    columns: set[str] = set()
    for col in table.get("columns", []):
        schema_name = col.get("schemaName", "")
        if not schema_name.startswith("cs_"):
            fail(f"{logical}: invalid column schema name {schema_name}")
        logical_col = schema_name.lower()
        if logical_col in columns:
            fail(f"{logical}: duplicate column {logical_col}")
        columns.add(logical_col)
        if col.get("type") not in {"string", "memo", "integer", "boolean", "datetime"}:
            fail(f"{logical}.{logical_col}: unsupported type {col.get('type')}")

for resource in data.get("webResources", []):
    path = ROOT / resource["path"]
    if not path.is_file():
        fail(f"Missing web resource file: {path}")

print(f"Schema valid: {len(seen_tables)} tables and {len(data.get('webResources', []))} web resources")
