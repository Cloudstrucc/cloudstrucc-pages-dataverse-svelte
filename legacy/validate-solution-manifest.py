#!/usr/bin/env python3
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TABLES = {
    "cs_website", "cs_page", "cs_componentdefinition", "cs_componentinstance",
    "cs_theme", "cs_asset", "cs_datasource", "cs_identityprovider",
    "cs_permission", "cs_localization", "cs_deployment", "cs_auditlog"
}

def validate(solution_kind: str) -> list[str]:
    errors = []
    base = ROOT / "solution" / solution_kind / "unpacked" / "Other"
    solution_xml = base / "Solution.xml"
    customizations_xml = base / "Customizations.xml"
    if not solution_xml.exists() or not customizations_xml.exists():
        return [f"{solution_kind}: missing Solution.xml or Customizations.xml"]

    sroot = ET.parse(solution_xml).getroot()
    roots = sroot.findall("./SolutionManifest/RootComponents/RootComponent")
    table_roots = {r.get("schemaName") for r in roots if r.get("type") == "1"}
    missing = sorted(REQUIRED_TABLES - table_roots)
    if missing:
        errors.append(f"{solution_kind}: missing table root components: {', '.join(missing)}")

    croot = ET.parse(customizations_xml).getroot()
    declared = {
        (node.findtext("Name") or "").strip()
        for node in croot.findall("./Entities/Entity")
    }
    undeclared = sorted(REQUIRED_TABLES - declared)
    if undeclared:
        errors.append(f"{solution_kind}: missing table definitions: {', '.join(undeclared)}")

    if solution_kind == "full":
        webresource_ids = {
            (node.findtext("WebResourceId") or "").strip().lower()
            for node in croot.findall("./WebResources/WebResource")
        }
        root_ids = {
            (r.get("id") or "").strip().lower()
            for r in roots if r.get("type") == "61"
        }
        missing_wr = sorted(webresource_ids - root_ids)
        if missing_wr:
            errors.append(f"full: {len(missing_wr)} web resources are not root components")
    return errors

all_errors = validate("schema") + validate("full")
if all_errors:
    print("Solution manifest validation failed:", file=sys.stderr)
    for error in all_errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)
print("Solution manifests are valid: required tables and web resources are declared as root components.")
