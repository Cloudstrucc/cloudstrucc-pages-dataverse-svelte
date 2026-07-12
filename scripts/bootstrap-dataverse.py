#!/usr/bin/env python3
"""Create the Cloudstrucc Dataverse schema and Studio web resources via Web API.

This replaces the invalid hand-authored solution XML approach. Dataverse creates the
metadata, including the primary-name column, and the companion export script then
produces authoritative managed/unmanaged solution ZIPs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT_DIR / "schema" / "cloudstrucc-pages.schema.json"
API_VERSION = "v9.2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap Cloudstrucc Pages Studio in Dataverse.")
    parser.add_argument("--environment-url", required=True, help="Dataverse URL, for example https://org.crm3.dynamics.com")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Path to schema JSON")
    parser.add_argument("--token", default=os.environ.get("DATAVERSE_ACCESS_TOKEN"), help="Bearer token; otherwise Azure CLI is used")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned actions without calling Dataverse")
    parser.add_argument("--skip-webresources", action="store_true", help="Create only publisher, solutions, and tables")
    parser.add_argument("--wait-seconds", type=float, default=2.0, help="Pause between metadata operations")
    return parser.parse_args()


def clean_env_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value.startswith("https://"):
        raise ValueError("--environment-url must start with https://")
    return value


def az_token(resource: str) -> str:
    cmd = [
        "az", "account", "get-access-token",
        "--resource", resource,
        "--query", "accessToken",
        "--output", "tsv",
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Azure CLI was not found. Install it, run 'az login', or set DATAVERSE_ACCESS_TOKEN."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Unable to obtain a Dataverse token with Azure CLI: {detail}") from exc
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned an empty access token.")
    return token


def label(text: str, lang: int = 1033) -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": lang,
            }
        ],
    }


def required_level(value: str = "None") -> dict[str, Any]:
    return {
        "Value": value,
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


def logical_from_schema(schema_name: str) -> str:
    return schema_name.lower()


class DataverseClient:
    def __init__(self, environment_url: str, token: str, dry_run: bool = False) -> None:
        self.environment_url = clean_env_url(environment_url)
        self.api_root = f"{self.environment_url}/api/data/{API_VERSION}"
        self.token = token
        self.dry_run = dry_run

    def _url(self, path: str, params: dict[str, str] | None = None) -> str:
        url = f"{self.api_root}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params, safe="'(),$=")
        return url

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        solution: str | None = None,
        allow_status: tuple[int, ...] = (),
    ) -> tuple[int, dict[str, str], Any]:
        url = self._url(path, params)
        if self.dry_run:
            print(f"DRY RUN {method} {url}")
            if method == "GET":
                if path.startswith("EntityDefinitions("):
                    if "/Attributes" in path:
                        return 200, {}, {"value": []}
                    if "LogicalName=" in path:
                        return 404, {}, None
                    return 200, {}, {
                        "MetadataId": "00000000-0000-0000-0000-000000000003",
                        "LogicalName": "cs_dryrun",
                        "PrimaryNameAttribute": "cs_name",
                        "SchemaName": "cs_DryRun",
                    }
                return 200, {}, {"value": []}
            return 204, {}, None

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        if solution:
            headers["MSCRM.SolutionUniqueName"] = solution
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
                parsed = json.loads(raw.decode("utf-8")) if raw else None
                return response.status, dict(response.headers.items()), parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if exc.code in allow_status:
                return exc.code, dict(exc.headers.items()), raw
            detail = raw
            try:
                parsed = json.loads(raw)
                detail = parsed.get("error", {}).get("message", raw)
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"Dataverse {method} {url} failed ({exc.code}): {detail}") from exc

    def first(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        _, _, data = self.request("GET", path, params=params)
        values = (data or {}).get("value", [])
        return values[0] if values else None


def primary_attribute_payload(table: dict[str, Any]) -> dict[str, Any]:
    primary = table["primaryName"]
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "AttributeType": "String",
        "AttributeTypeName": {"Value": "StringType"},
        "SchemaName": primary["schemaName"],
        "DisplayName": label(primary["displayName"]),
        "Description": label(f"Primary display name for {table['displayName']} records."),
        "RequiredLevel": required_level("None"),
        "MaxLength": int(primary.get("maxLength", 200)),
        "FormatName": {"Value": "Text"},
        "IsPrimaryName": True,
    }


def column_payload(column: dict[str, Any]) -> dict[str, Any]:
    common = {
        "SchemaName": column["schemaName"],
        "DisplayName": label(column["displayName"]),
        "Description": label(column.get("description", column["displayName"])),
        "RequiredLevel": required_level(column.get("requiredLevel", "None")),
    }
    col_type = column["type"].lower()
    if col_type == "string":
        return {
            **common,
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "AttributeType": "String",
            "AttributeTypeName": {"Value": "StringType"},
            "FormatName": {"Value": column.get("format", "Text")},
            "MaxLength": int(column.get("maxLength", 200)),
        }
    if col_type == "memo":
        return {
            **common,
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "AttributeType": "Memo",
            "AttributeTypeName": {"Value": "MemoType"},
            "Format": "TextArea",
            "ImeMode": "Disabled",
            "MaxLength": int(column.get("maxLength", 1048576)),
            "IsLocalizable": False,
        }
    if col_type == "integer":
        return {
            **common,
            "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
            "AttributeType": "Integer",
            "AttributeTypeName": {"Value": "IntegerType"},
            "Format": "None",
            "SourceTypeMask": 0,
            "MinValue": int(column.get("minValue", -2147483648)),
            "MaxValue": int(column.get("maxValue", 2147483647)),
        }
    if col_type == "boolean":
        return {
            **common,
            "@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
            "AttributeType": "Boolean",
            "AttributeTypeName": {"Value": "BooleanType"},
            "DefaultValue": bool(column.get("defaultValue", False)),
            "OptionSet": {
                "TrueOption": {"Value": 1, "Label": label("Yes")},
                "FalseOption": {"Value": 0, "Label": label("No")},
                "OptionSetType": "Boolean",
            },
        }
    if col_type == "datetime":
        return {
            **common,
            "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
            "AttributeType": "DateTime",
            "AttributeTypeName": {"Value": "DateTimeType"},
            "Format": column.get("format", "DateAndTime"),
        }
    raise ValueError(f"Unsupported column type: {column['type']} ({column['schemaName']})")


def entity_payload(table: dict[str, Any]) -> dict[str, Any]:
    """Build a complete table-create payload.

    Dataverse supports creating the primary-name attribute and all additional
    columns in the same EntityDefinitions POST. Doing this avoids a metadata
    propagation race where the table exists but its LogicalName alternate key
    is not queryable yet.
    """
    attributes = [primary_attribute_payload(table)]
    attributes.extend(column_payload(column) for column in table.get("columns", []))
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": table["schemaName"],
        "DisplayName": label(table["displayName"]),
        "DisplayCollectionName": label(table["displayCollectionName"]),
        "Description": label(table.get("description", table["displayName"])),
        "OwnershipType": "OrganizationOwned",
        "IsActivity": False,
        "HasActivities": False,
        "HasNotes": False,
        "Attributes": attributes,
    }


def extract_guid(entity_uri: str | None) -> str | None:
    if not entity_uri:
        return None
    match = re.search(r"\(([0-9a-fA-F-]{36})\)", entity_uri)
    return match.group(1) if match else None


def ensure_publisher(client: DataverseClient, publisher: dict[str, Any]) -> str:
    record = client.first(
        "publishers",
        {"$select": "publisherid,uniquename", "$filter": f"uniquename eq '{publisher['uniqueName']}'"},
    )
    if record:
        print(f"Publisher exists: {publisher['uniqueName']}")
        return record["publisherid"]
    payload = {
        "uniquename": publisher["uniqueName"],
        "friendlyname": publisher["friendlyName"],
        "customizationprefix": publisher["prefix"],
        "customizationoptionvalueprefix": int(publisher["optionValuePrefix"]),
        "supportingwebsiteurl": publisher.get("website"),
    }
    _, headers, _ = client.request("POST", "publishers", payload=payload)
    publisher_id = extract_guid(headers.get("OData-EntityId") or headers.get("odata-entityid"))
    if client.dry_run:
        return "00000000-0000-0000-0000-000000000001"
    if not publisher_id:
        record = client.first(
            "publishers",
            {"$select": "publisherid", "$filter": f"uniquename eq '{publisher['uniqueName']}'"},
        )
        publisher_id = record["publisherid"] if record else None
    if not publisher_id:
        raise RuntimeError("Publisher was created but its ID could not be resolved.")
    print(f"Created publisher: {publisher['uniqueName']}")
    return publisher_id


def ensure_solution(client: DataverseClient, solution: dict[str, Any], publisher_id: str) -> str:
    record = client.first(
        "solutions",
        {"$select": "solutionid,uniquename,version", "$filter": f"uniquename eq '{solution['uniqueName']}'"},
    )
    if record:
        print(f"Solution exists: {solution['uniqueName']} ({record.get('version')})")
        if record.get("version") != solution["version"]:
            client.request("PATCH", f"solutions({record['solutionid']})", payload={"version": solution["version"]})
        return record["solutionid"]
    payload = {
        "uniquename": solution["uniqueName"],
        "friendlyname": solution["friendlyName"],
        "version": solution["version"],
        "publisherid@odata.bind": f"/publishers({publisher_id})",
    }
    _, headers, _ = client.request("POST", "solutions", payload=payload)
    solution_id = extract_guid(headers.get("OData-EntityId") or headers.get("odata-entityid"))
    if client.dry_run:
        return "00000000-0000-0000-0000-000000000002"
    if not solution_id:
        record = client.first(
            "solutions",
            {"$select": "solutionid", "$filter": f"uniquename eq '{solution['uniqueName']}'"},
        )
        solution_id = record["solutionid"] if record else None
    if not solution_id:
        raise RuntimeError(f"Solution {solution['uniqueName']} was created but its ID could not be resolved.")
    print(f"Created solution: {solution['uniqueName']}")
    return solution_id


def entity_metadata_by_id(client: DataverseClient, metadata_id: str) -> dict[str, Any] | None:
    status, _, data = client.request(
        "GET",
        f"EntityDefinitions({metadata_id})",
        params={"$select": "MetadataId,LogicalName,PrimaryNameAttribute,SchemaName"},
        allow_status=(404,),
    )
    return None if status == 404 else data


def entity_metadata(
    client: DataverseClient, logical_name: str, schema_name: str | None = None
) -> dict[str, Any] | None:
    """Resolve table metadata through the EntityDefinitions collection.

    Some Dataverse environments return 404 for the LogicalName alternate-key
    route while the same table is already visible in the metadata collection.
    Using a filtered collection query avoids that route entirely and gives us
    the MetadataId needed for all subsequent attribute operations.
    """
    record = client.first(
        "EntityDefinitions",
        {
            "$select": "MetadataId,LogicalName,PrimaryNameAttribute,SchemaName",
            "$filter": f"LogicalName eq '{logical_name}'",
        },
    )
    if record is not None or not schema_name:
        return record
    return client.first(
        "EntityDefinitions",
        {
            "$select": "MetadataId,LogicalName,PrimaryNameAttribute,SchemaName",
            "$filter": f"SchemaName eq '{schema_name}'",
        },
    )


def wait_for_entity_metadata(
    client: DataverseClient,
    *,
    logical_name: str,
    metadata_id: str | None = None,
    attempts: int = 60,
    delay_seconds: float = 2.0,
) -> dict[str, Any]:
    """Poll Dataverse metadata until a newly created table is queryable."""
    last: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        if metadata_id:
            last = entity_metadata_by_id(client, metadata_id)
        if last is None:
            last = entity_metadata(client, logical_name)
        if last is not None:
            return last
        if client.dry_run:
            break
        print(f"  Waiting for metadata propagation ({attempt}/{attempts}): {logical_name}")
        time.sleep(max(delay_seconds, 0.1))
    raise RuntimeError(
        f"Table {logical_name} was created, but its metadata was not available after "
        f"{attempts} attempts. Re-run the bootstrap; it is idempotent."
    )


def attribute_exists(
    client: DataverseClient,
    table_logical: str,
    attribute_logical: str,
    metadata_id: str | None = None,
) -> bool:
    table_ref = f"EntityDefinitions({metadata_id})" if metadata_id else f"EntityDefinitions(LogicalName='{table_logical}')"
    record = client.first(
        f"{table_ref}/Attributes",
        {"$select": "MetadataId,LogicalName", "$filter": f"LogicalName eq '{attribute_logical}'"},
    )
    return record is not None


def add_solution_component(
    client: DataverseClient,
    solution_unique: str,
    component_id: str,
    component_type: int,
    *,
    attempts: int = 30,
    delay_seconds: float = 2.0,
) -> None:
    payload = {
        "ComponentId": component_id,
        "ComponentType": component_type,
        "SolutionUniqueName": solution_unique,
        "AddRequiredComponents": False,
        "DoNotIncludeSubcomponents": False,
    }
    for attempt in range(1, attempts + 1):
        status, _, body = client.request(
            "POST", "AddSolutionComponent", payload=payload, allow_status=(400, 404)
        )
        if status not in (400, 404):
            return
        text = str(body).lower()
        if "already" in text or "exists" in text or "duplicate" in text:
            return
        transient = any(
            marker in text
            for marker in ("does not exist", "not found", "cannot find", "metadata")
        )
        if transient and attempt < attempts and not client.dry_run:
            print(
                f"  Waiting to add component to {solution_unique} "
                f"({attempt}/{attempts})"
            )
            time.sleep(max(delay_seconds, 0.1))
            continue
        raise RuntimeError(
            f"Unable to add component {component_id} to {solution_unique}: {body}"
        )


def ensure_table(
    client: DataverseClient,
    table: dict[str, Any],
    schema_solution: str,
    full_solution: str,
    wait_seconds: float,
) -> None:
    logical_name = table["logicalName"]
    metadata = entity_metadata(client, logical_name, table["schemaName"])
    created_now = metadata is None

    if metadata:
        if not metadata.get("PrimaryNameAttribute") and metadata.get("MetadataId"):
            metadata = wait_for_entity_metadata(
                client,
                logical_name=logical_name,
                metadata_id=metadata["MetadataId"],
                delay_seconds=max(wait_seconds, 1.0),
            )
        primary = metadata.get("PrimaryNameAttribute")
        expected_primary = logical_from_schema(table["primaryName"]["schemaName"])
        if primary != expected_primary:
            raise RuntimeError(
                f"Existing table {logical_name} has primary name '{primary}', expected "
                f"'{expected_primary}'. Delete or rename the conflicting table."
            )
        print(f"Table exists: {logical_name}")
    else:
        status, headers, body = client.request(
            "POST",
            "EntityDefinitions",
            payload=entity_payload(table),
            solution=schema_solution,
            allow_status=(400, 409),
        )
        metadata_id = extract_guid(
            headers.get("OData-EntityId") or headers.get("odata-entityid")
        )
        if client.dry_run:
            metadata_id = metadata_id or "00000000-0000-0000-0000-000000000003"

        if status in (400, 409):
            text = str(body).lower()
            duplicate = any(
                marker in text
                for marker in (
                    "already exists",
                    "duplicate",
                    "with name",
                    "same name",
                )
            )
            if not duplicate:
                raise RuntimeError(
                    f"Unable to create table {logical_name}: {body}"
                )
            print(
                f"Table creation reported an existing table; resolving metadata: "
                f"{logical_name}"
            )
        else:
            print(
                f"Created table with primary name and {len(table.get('columns', []))} columns: "
                f"{logical_name}"
            )

        metadata = wait_for_entity_metadata(
            client,
            logical_name=logical_name,
            metadata_id=metadata_id,
            delay_seconds=max(wait_seconds, 1.0),
        )
        created_now = status not in (400, 409)

    metadata_id = metadata.get("MetadataId")
    if not metadata_id:
        metadata = wait_for_entity_metadata(
            client,
            logical_name=logical_name,
            delay_seconds=max(wait_seconds, 1.0),
        )
        metadata_id = metadata.get("MetadataId")
    if not metadata_id:
        raise RuntimeError(f"Unable to resolve MetadataId for {logical_name}.")

    # Existing tables may be remnants of an interrupted earlier bootstrap. Add
    # only missing columns. New tables already received every column in the
    # initial EntityDefinitions POST.
    if not created_now:
        for column in table.get("columns", []):
            logical_column = logical_from_schema(column["schemaName"])
            if attribute_exists(client, logical_name, logical_column, metadata_id):
                print(f"  Column exists: {logical_column}")
                continue
            client.request(
                "POST",
                f"EntityDefinitions({metadata_id})/Attributes",
                payload=column_payload(column),
                solution=schema_solution,
            )
            print(f"  Created column: {logical_column}")
            if not client.dry_run:
                time.sleep(max(wait_seconds, 0))

    add_solution_component(
        client,
        full_solution,
        metadata_id,
        1,
        delay_seconds=max(wait_seconds, 1.0),
    )


def ensure_webresource(
    client: DataverseClient,
    resource: dict[str, Any],
    full_solution: str,
) -> str:
    source_path = ROOT_DIR / resource["path"]
    if not source_path.is_file():
        raise FileNotFoundError(f"Web resource source file not found: {source_path}")
    content = base64.b64encode(source_path.read_bytes()).decode("ascii")
    record = client.first(
        "webresourceset",
        {"$select": "webresourceid,name", "$filter": f"name eq '{resource['name']}'"},
    )
    payload = {
        "name": resource["name"],
        "displayname": resource["displayName"],
        "description": "Cloudstrucc Pages Studio web resource",
        "webresourcetype": int(resource["type"]),
        "content": content,
        "languagecode": 1033,
    }
    if record:
        resource_id = record["webresourceid"]
        client.request("PATCH", f"webresourceset({resource_id})", payload=payload)
        print(f"Updated web resource: {resource['name']}")
    else:
        _, headers, _ = client.request("POST", "webresourceset", payload=payload, solution=full_solution)
        resource_id = extract_guid(headers.get("OData-EntityId") or headers.get("odata-entityid"))
        if client.dry_run:
            resource_id = "00000000-0000-0000-0000-000000000004"
        if not resource_id:
            record = client.first(
                "webresourceset",
                {"$select": "webresourceid", "$filter": f"name eq '{resource['name']}'"},
            )
            resource_id = record["webresourceid"] if record else None
        if not resource_id:
            raise RuntimeError(f"Unable to resolve web resource ID: {resource['name']}")
        print(f"Created web resource: {resource['name']}")
    add_solution_component(client, full_solution, resource_id, 61)
    return resource_id


def main() -> int:
    args = parse_args()
    schema_path = Path(args.schema).resolve()
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    environment_url = clean_env_url(args.environment_url)
    token = args.token or ("dry-run-token" if args.dry_run else az_token(environment_url))
    client = DataverseClient(environment_url, token, args.dry_run)

    print(f"Target environment: {environment_url}")
    print(f"Schema file: {schema_path}")
    if args.dry_run:
        print("DRY RUN: no Dataverse changes will be made.")

    publisher_id = ensure_publisher(client, schema["publisher"])
    schema_solution = schema["solutions"]["schema"]
    full_solution = schema["solutions"]["full"]
    ensure_solution(client, schema_solution, publisher_id)
    full_solution_id = ensure_solution(client, full_solution, publisher_id)

    # Flush metadata from any earlier interrupted run before resolving tables by
    # logical name. This makes the bootstrap safely resumable after a partial
    # create, such as cs_website having been created before a propagation error.
    client.request("POST", "PublishAllXml", payload={})
    print("Published any pending customizations from earlier runs.")

    for table in schema["tables"]:
        ensure_table(
            client,
            table,
            schema_solution["uniqueName"],
            full_solution["uniqueName"],
            args.wait_seconds,
        )

    admin_resource_id = None
    if not args.skip_webresources:
        for resource in schema.get("webResources", []):
            resource_id = ensure_webresource(client, resource, full_solution["uniqueName"])
            if resource["name"].endswith("/admin.html"):
                admin_resource_id = resource_id
        if admin_resource_id:
            client.request(
                "PATCH",
                f"solutions({full_solution_id})",
                payload={"configurationpageid@odata.bind": f"/webresourceset({admin_resource_id})"},
            )
            print("Configured the admin web resource as the solution configuration page.")

    client.request("POST", "PublishAllXml", payload={})
    print("Published all customizations.")
    print()
    print("Bootstrap complete.")
    print("Next: run scripts/export-solutions.sh to generate authoritative solution ZIP files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
