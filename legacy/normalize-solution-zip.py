#!/usr/bin/env python3
"""Normalize and validate a Dataverse solution ZIP for import.

Ensures solution.xml, customizations.xml, and [Content_Types].xml are at the
ZIP root. Supports repairing legacy/fallback archives that placed the first two
files under Other/.
"""
from __future__ import annotations
import argparse
import tempfile
import zipfile
from pathlib import Path

REQUIRED = {"solution.xml", "customizations.xml", "[Content_Types].xml"}

def normalize(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Solution ZIP not found: {path}")
    with zipfile.ZipFile(path, "r") as src:
        names = src.namelist()
        lower = {n.lower(): n for n in names}
        mappings: dict[str, str] = {}
        for target in REQUIRED:
            key = target.lower()
            if key in lower:
                mappings[target] = lower[key]
                continue
            legacy = f"other/{target}".lower()
            if legacy in lower:
                mappings[target] = lower[legacy]
                continue
            # Legacy files may retain title case.
            candidates = [n for n in names if n.lower().endswith('/' + key)]
            if len(candidates) == 1:
                mappings[target] = candidates[0]
                continue
            raise SystemExit(f"{path.name}: required file missing: {target}")

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False, dir=path.parent) as tf:
            temp_path = Path(tf.name)
        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as out:
                written = set()
                # Write required package files first with canonical root names.
                for target in ("solution.xml", "customizations.xml", "[Content_Types].xml"):
                    out.writestr(target, src.read(mappings[target]))
                    written.add(mappings[target])
                # Preserve all remaining payload except duplicate/legacy package files.
                for info in src.infolist():
                    name = info.filename
                    if name in written:
                        continue
                    lname = name.lower()
                    if lname in {"other/solution.xml", "other/customizations.xml"}:
                        continue
                    if lname in {"solution.xml", "customizations.xml", "[content_types].xml"}:
                        continue
                    if name.endswith('/'):
                        continue
                    out.writestr(name, src.read(name))
            temp_path.replace(path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    validate(path)

def validate(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as z:
        roots = {n for n in z.namelist() if '/' not in n.rstrip('/')}
        missing = REQUIRED - roots
        if missing:
            raise SystemExit(f"{path.name}: invalid root; missing {sorted(missing)}")
        for prohibited in ("Other/Solution.xml", "Other/Customizations.xml"):
            if prohibited in z.namelist():
                raise SystemExit(f"{path.name}: legacy duplicate remains: {prohibited}")
        bad_case = [n for n in roots if n.lower() in {"solution.xml","customizations.xml"} and n not in {"solution.xml","customizations.xml"}]
        if bad_case:
            raise SystemExit(f"{path.name}: package filenames must be lowercase: {bad_case}")
    print(f"Validated importable ZIP root: {path}")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args=parser.parse_args()
    if args.validate_only:
        validate(args.zip_path)
    else:
        normalize(args.zip_path)
