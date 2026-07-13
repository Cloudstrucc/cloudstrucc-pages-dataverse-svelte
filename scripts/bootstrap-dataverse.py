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


# Maps solution component type codes (as used with AddSolutionComponent /
# RetrieveDependenciesForDelete) back to the Web API entity set that owns
# records of that type, for the small set of component types this bootstrap
# itself creates and may need to delete out of a dependency's way.
COMPONENT_TYPE_ENTITY_SET = {
    61: "webresourceset",
    62: "sitemaps",
    80: "appmodules",
}


def clear_blocking_dependents(client: DataverseClient, component_type: int, object_id: str) -> None:
    """Delete records that would block deleting the given solution component.

    A SiteMap that references a web resource via a $webresource: directive
    creates a hard delete-blocking dependency on that web resource. When a web
    resource must be deleted and recreated (see the webresourcetype-mismatch
    handling in ensure_webresource), any such dependent record has to be
    removed first. The dependent records this recreates (SiteMap, AppModule)
    are themselves idempotently recreated later in the same bootstrap run, so
    deleting them here is safe and not a data loss.
    """
    if client.dry_run:
        return
    _, _, body = client.request(
        "GET",
        f"RetrieveDependenciesForDelete(ObjectId={object_id},ComponentType={component_type})",
    )
    for dependency in (body or {}).get("value", []):
        dep_type = dependency.get("dependentcomponenttype")
        dep_id = dependency.get("dependentcomponentobjectid")
        entity_set = COMPONENT_TYPE_ENTITY_SET.get(dep_type)
        if not dep_id:
            continue
        if not entity_set:
            raise RuntimeError(
                f"Cannot delete component {object_id}: it is blocked by an unrecognized "
                f"dependent component (type {dep_type}, id {dep_id}). Remove that "
                "dependency manually in the maker portal and rerun the bootstrap."
            )
        client.request("DELETE", f"{entity_set}({dep_id})", allow_status=(404,))
        print(f"  Removed dependent {entity_set}({dep_id}) to allow recreation.")


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
        {"$select": "webresourceid,name,webresourcetype", "$filter": f"name eq '{resource['name']}'"},
    )
    payload = {
        "name": resource["name"],
        "displayname": resource["displayName"],
        "description": "Cloudstrucc Pages Studio web resource",
        "webresourcetype": int(resource["type"]),
        "content": content,
        "languagecode": 1033,
    }
    # webresourcetype is immutable after creation: Dataverse silently ignores
    # a changed value on PATCH instead of erroring, so a record created with
    # the wrong type (e.g. an earlier bootstrap bug) can never be repaired by
    # PATCH. Detect the mismatch and recreate the record instead.
    if record and not client.dry_run and record.get("webresourcetype") != int(resource["type"]):
        stale_id = record["webresourceid"]
        clear_blocking_dependents(client, 61, stale_id)
        client.request("DELETE", f"webresourceset({stale_id})")
        print(
            f"Deleted web resource with wrong webresourcetype "
            f"({record.get('webresourcetype')} != {resource['type']}): {resource['name']}"
        )
        record = None
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


def webresource_directive(resource_name: str) -> str:
    """Build the $webresource: directive Dataverse expects inside SiteMap XML.

    Using a raw URL instead of this directive creates an app that renders but
    carries no tracked solution dependency on the web resource, which breaks
    export/import and silently orphans the SubArea if the resource is renamed.
    """
    return f"$webresource:{resource_name}"


def ensure_sitemap(
    client: DataverseClient,
    sitemap: dict[str, Any],
    admin_resource_name: str,
    icon_resource_name: str,
    full_solution: str,
) -> str:
    xml = sitemap["xmlTemplate"].replace(
        "{adminUrl}", webresource_directive(admin_resource_name)
    ).replace(
        "{iconUrl}", webresource_directive(icon_resource_name)
    )
    record = client.first(
        "sitemaps",
        {"$select": "sitemapid,sitemapnameunique", "$filter": f"sitemapnameunique eq '{sitemap['uniqueName']}'"},
    )
    payload = {
        "sitemapname": sitemap["name"],
        "sitemapxml": xml,
    }
    if record:
        sitemap_id = record["sitemapid"]
        client.request("PATCH", f"sitemaps({sitemap_id})", payload=payload)
        print(f"Updated sitemap: {sitemap['uniqueName']}")
    else:
        payload["sitemapnameunique"] = sitemap["uniqueName"]
        _, headers, _ = client.request("POST", "sitemaps", payload=payload, solution=full_solution)
        sitemap_id = extract_guid(headers.get("OData-EntityId") or headers.get("odata-entityid"))
        if client.dry_run:
            sitemap_id = sitemap_id or "00000000-0000-0000-0000-000000000005"
        if not sitemap_id:
            record = client.first(
                "sitemaps",
                {"$select": "sitemapid", "$filter": f"sitemapnameunique eq '{sitemap['uniqueName']}'"},
            )
            sitemap_id = record["sitemapid"] if record else None
        if not sitemap_id:
            raise RuntimeError(f"Unable to resolve sitemap ID: {sitemap['uniqueName']}")
        print(f"Created sitemap: {sitemap['uniqueName']}")
    add_solution_component(client, full_solution, sitemap_id, 62)
    return sitemap_id


def clear_orphaned_appmodule_reservations(client: DataverseClient) -> tuple[int, list[str]]:
    """Remove solutioncomponent rows for app modules that no longer exist.

    Dataverse appears to enforce the appmodules.uniquename uniqueness
    constraint against the solutioncomponent index rather than solely
    against the appmodules table itself. If a previous bootstrap run created
    an app module and it was rolled back/deleted server-side before
    AddAppComponents finished wiring it up (for example, an earlier bug in
    this script that called AddAppComponents with the wrong URL shape and
    raised before the app module was ever fully attached), the
    componenttype=80 solutioncomponent rows that reference its now
    -nonexistent objectid can remain behind. Those rows keep the uniquename
    permanently reserved, so a later create attempt fails with
    DuplicateAppModuleUniqueName (Dataverse error -2147155681) even though a
    lookup by uniquename finds no matching appmodules record. Confirmed live
    against goc-theme-dev: GET appmodules(<dead objectid>) returns 404
    "Does Not Exist" while POST appmodules with the same uniquename still
    fails as a duplicate.

    This scans every componenttype=80 solution component, checks whether its
    objectid still resolves to a real appmodules record, and removes (via
    RemoveSolutionComponent) any that do not. It is safe to run broadly: a
    solutioncomponent row can only be "orphaned" here if its target record is
    already gone, so clearing it cannot affect any app module that still
    exists. Returns (number of orphans cleared, objectids blocked because
    they live only in the Default Solution -- see note below).

    Note: Dataverse rejects RemoveSolutionComponent for the Default Solution
    ("A Solution Component cannot be removed from the Default Solution") --
    confirmed live against goc-theme-dev. Default-solution memberships are
    meant to be maintained automatically by the platform as a side effect of
    a component's real add/delete lifecycle; there is no supported Web API
    call that removes one directly. If the only remaining orphaned
    reservation for a given uniquename lives in the Default solution, this
    function cannot clear it and ensure_appmodule will raise a specific,
    actionable error rather than the opaque duplicate-name message.
    """
    if client.dry_run:
        return 0, []
    _, _, data = client.request(
        "GET",
        "solutioncomponents",
        params={
            "$select": "solutioncomponentid,objectid,_solutionid_value",
            "$filter": "componenttype eq 80",
        },
    )
    rows = (data or {}).get("value", [])
    exists_cache: dict[str, bool] = {}
    solution_name_cache: dict[str, str | None] = {}
    cleared = 0
    default_blocked: list[str] = []
    for row in rows:
        object_id = row.get("objectid")
        solution_id = row.get("_solutionid_value")
        component_id = row.get("solutioncomponentid")
        if not object_id or not solution_id or not component_id:
            continue
        if object_id not in exists_cache:
            status, _, _ = client.request(
                "GET",
                f"appmodules({object_id})",
                params={"$select": "appmoduleid"},
                allow_status=(404,),
            )
            exists_cache[object_id] = status != 404
        if exists_cache[object_id]:
            continue  # appmodule still exists; this reservation is legitimate.
        if solution_id not in solution_name_cache:
            _, _, sol = client.request(
                "GET",
                f"solutions({solution_id})",
                params={"$select": "uniquename"},
                allow_status=(404,),
            )
            solution_name_cache[solution_id] = (sol or {}).get("uniquename")
        solution_unique = solution_name_cache[solution_id]
        if not solution_unique:
            continue
        # Unlike AddSolutionComponent (whose ComponentId parameter is a plain
        # Edm.Guid), RemoveSolutionComponent's "SolutionComponent" parameter
        # is typed as the solutioncomponent entity itself. Two shapes were
        # tried and rejected live before landing on this one:
        #   - a flat "ComponentId" property -> "not a valid parameter"
        #   - "SolutionComponent@odata.bind" -> "parameter payloads do not
        #     support OData property annotations" (unbound action parameters
        #     can't use @odata.bind at all)
        # The shape Dataverse actually accepts is a nested object under
        # "SolutionComponent" whose "solutioncomponentid" property holds the
        # *objectid of the underlying component* (i.e. the same value that
        # would be ComponentId for AddSolutionComponent), not the
        # solutioncomponent row's own primary key. Confirmed live against
        # goc-theme-dev: POSTing {"SolutionComponent":
        # {"solutioncomponentid": "<dead appmodule objectid>"}, "ComponentType":
        # 80, "SolutionUniqueName": "CloudstruccPagesStudio"} returned 200 and
        # removed the correct orphaned row.
        remove_payload = {
            "SolutionComponent": {"solutioncomponentid": object_id},
            "ComponentType": 80,
            "SolutionUniqueName": solution_unique,
        }
        status, _, body = client.request(
            "POST",
            "RemoveSolutionComponent",
            payload=remove_payload,
            allow_status=(400, 404),
        )
        if status in (200, 204):
            print(
                f"  Removed orphaned app module solution component {component_id} "
                f"(dead objectid {object_id}, solution {solution_unique})."
            )
            cleared += 1
        else:
            print(f"  WARNING: could not remove orphaned solution component {component_id}: {body}")
            if "cannot be removed from the default solution" in str(body).lower():
                default_blocked.append(object_id)
    return cleared, default_blocked


def ensure_appmodule(
    client: DataverseClient,
    app_module: dict[str, Any],
    icon_resource_id: str,
    full_solution: str,
) -> str:
    record = client.first(
        "appmodules",
        {"$select": "appmoduleid,uniquename", "$filter": f"uniquename eq '{app_module['uniqueName']}'"},
    )
    payload = {
        "name": app_module["name"],
        "description": app_module.get("description", ""),
        "webresourceid": icon_resource_id,
    }
    if record:
        appmodule_id = record["appmoduleid"]
        client.request("PATCH", f"appmodules({appmodule_id})", payload=payload)
        print(f"Updated app module: {app_module['uniqueName']}")
    else:
        payload["uniquename"] = app_module["uniqueName"]
        status, headers, body = client.request(
            "POST", "appmodules", payload=payload, solution=full_solution, allow_status=(400,)
        )
        if status == 400:
            # See clear_orphaned_appmodule_reservations for why a create can
            # fail as a duplicate even though no appmodules record exists.
            # Clear any orphaned reservations and retry exactly once.
            cleared, default_blocked = clear_orphaned_appmodule_reservations(client)
            if not cleared:
                if default_blocked:
                    raise RuntimeError(
                        f"Unable to create app module {app_module['uniqueName']}: Dataverse "
                        f"still has a stale Default Solution reservation for the deleted app "
                        f"module {default_blocked[0]} and refuses to let this script remove it "
                        "(\"A Solution Component cannot be removed from the Default Solution\"). "
                        "This uniquename cannot be reused until that reservation is cleared, "
                        "which is outside this script's reach via the Web API. Options: (1) wait "
                        "and rerun later in case the platform's own consistency job clears it, "
                        "(2) ask Microsoft support to purge the stale solutioncomponent row for "
                        f"objectid {default_blocked[0]}, or (3) change appModule.uniqueName in "
                        "the schema to a new value and rerun."
                    )
                raise RuntimeError(
                    f"Unable to create app module {app_module['uniqueName']}: {body}"
                )
            status, headers, body = client.request(
                "POST", "appmodules", payload=payload, solution=full_solution
            )
        appmodule_id = extract_guid(headers.get("OData-EntityId") or headers.get("odata-entityid"))
        if client.dry_run:
            appmodule_id = appmodule_id or "00000000-0000-0000-0000-000000000006"
        if not appmodule_id:
            record = client.first(
                "appmodules",
                {"$select": "appmoduleid", "$filter": f"uniquename eq '{app_module['uniqueName']}'"},
            )
            appmodule_id = record["appmoduleid"] if record else None
        if not appmodule_id:
            raise RuntimeError(f"Unable to resolve app module ID: {app_module['uniqueName']}")
        print(f"Created app module: {app_module['uniqueName']}")
    add_solution_component(client, full_solution, appmodule_id, 80)
    return appmodule_id


def add_app_components(
    client: DataverseClient,
    appmodule_id: str,
    components: list[tuple[str, str]],
) -> None:
    """Attach components (sitemap, table, view, form, ...) to an app module.

    components: list of (entity_logical_name, record_id) tuples, for example
    [("sitemap", sitemap_id)].

    AddAppComponents is an UNBOUND Web API action (it takes AppId as an
    explicit parameter rather than being bound to an appmodules(id) segment).
    POSTing to appmodules(id)/Microsoft.Dynamics.CRM.AddAppComponents returns
    a 404 "Resource not found for the segment" because that bound-action URL
    shape does not exist for this action; the correct call is a plain POST to
    the AddAppComponents action with AppId included in the body. Confirmed
    against https://learn.microsoft.com/power-apps/developer/data-platform/webapi/reference/addappcomponents

    IMPORTANT: web resources are NOT a valid standalone AddAppComponents
    component type. Confirmed live against goc-theme-dev: passing
    ("webresource", <id>) here fails with 0x80050112 "An app can't reference
    the component type 'webresource'." The admin web resource is instead
    wired into the app indirectly through the SiteMap XML's $webresource:
    directive (see webresource_directive() in ensure_sitemap()), which is
    Microsoft's documented mechanism for exposing a web resource inside a
    model-driven app's navigation. Do not add "webresource" tuples to the
    components list passed to this function.
    """
    payload = {
        "AppId": appmodule_id,
        "Components": [
            {"@odata.type": f"Microsoft.Dynamics.CRM.{entity}", f"{entity}id": record_id}
            for entity, record_id in components
        ],
    }
    status, _, body = client.request(
        "POST",
        "AddAppComponents",
        payload=payload,
        allow_status=(400,),
    )
    if status == 400:
        text = str(body).lower()
        if "already" in text or "exists" in text or "duplicate" in text:
            print("  App components already attached.")
            return
        raise RuntimeError(f"Unable to add app components to {appmodule_id}: {body}")
    print("  Attached sitemap to app module.")


def validate_app_module(client: DataverseClient, appmodule_id: str) -> None:
    _, _, body = client.request("GET", f"ValidateApp(AppModuleId={appmodule_id})")
    missing = (body or {}).get("MissingComponents") or []
    if missing:
        print(f"  WARNING: ValidateApp reported missing components: {missing}")
    else:
        print("  ValidateApp reported no missing components.")


def publish_app_module(client: DataverseClient, appmodule_id: str) -> None:
    xml = f"<importexportxml><appmodules><appmodule>{appmodule_id}</appmodule></appmodules></importexportxml>"
    client.request("POST", "PublishXml", payload={"ParameterXml": xml})
    print("  Published app module.")


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
    icon_resource_id = None
    if not args.skip_webresources:
        site_map = schema.get("siteMap") or {}
        app_module = schema.get("appModule") or {}
        admin_resource_name = site_map.get("adminWebResourceName")
        icon_resource_name = site_map.get("iconWebResourceName") or app_module.get("iconWebResourceName")
        for resource in schema.get("webResources", []):
            resource_id = ensure_webresource(client, resource, full_solution["uniqueName"])
            if admin_resource_name and resource["name"] == admin_resource_name:
                admin_resource_id = resource_id
            if icon_resource_name and resource["name"] == icon_resource_name:
                icon_resource_id = resource_id
        if admin_resource_id:
            client.request(
                "PATCH",
                f"solutions({full_solution_id})",
                payload={"configurationpageid@odata.bind": f"/webresourceset({admin_resource_id})"},
            )
            print("Configured the admin web resource as the solution configuration page.")

        if site_map and app_module:
            if not admin_resource_id or not icon_resource_id:
                raise RuntimeError(
                    "Cannot provision the admin app: admin or icon web resource was not created."
                )
            sitemap_id = ensure_sitemap(
                client,
                site_map,
                admin_resource_name,
                icon_resource_name,
                full_solution["uniqueName"],
            )
            appmodule_id = ensure_appmodule(client, app_module, icon_resource_id, full_solution["uniqueName"])
            add_app_components(
                client,
                appmodule_id,
                [("sitemap", sitemap_id)],
            )
            validate_app_module(client, appmodule_id)
            publish_app_module(client, appmodule_id)
            print(f"Provisioned model-driven app: {app_module['name']}")

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
