from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts" / "bootstrap-dataverse.py")
bootstrap = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(bootstrap)


class BootstrapPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schema" / "cloudstrucc-pages.schema.json").read_text())

    def test_every_table_create_payload_contains_primary_name_and_all_columns(self):
        for table in self.schema["tables"]:
            payload = bootstrap.entity_payload(table)
            attrs = payload["Attributes"]
            self.assertEqual(len(attrs), 1 + len(table["columns"]))
            primary = attrs[0]
            self.assertTrue(primary["IsPrimaryName"])
            self.assertEqual(primary["@odata.type"], "Microsoft.Dynamics.CRM.StringAttributeMetadata")
            self.assertEqual(primary["SchemaName"], "cs_Name")
            self.assertEqual(primary["FormatName"]["Value"], "Text")
            self.assertEqual(
                {attribute["SchemaName"] for attribute in attrs[1:]},
                {column["schemaName"] for column in table["columns"]},
            )

    def test_all_column_types_build(self):
        for table in self.schema["tables"]:
            for column in table["columns"]:
                payload = bootstrap.column_payload(column)
                self.assertEqual(payload["SchemaName"], column["schemaName"])
                self.assertIn("@odata.type", payload)

    def test_unique_table_names(self):
        names = [table["logicalName"] for table in self.schema["tables"]]
        self.assertEqual(len(names), len(set(names)))

    def test_created_table_uses_returned_metadata_id_for_follow_up(self):
        table = self.schema["tables"][0]

        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "GET" and path == "EntityDefinitions":
                    return 200, {}, {"value": []}
                if method == "GET" and path == "EntityDefinitions(11111111-1111-1111-1111-111111111111)":
                    return 200, {}, {
                        "MetadataId": "11111111-1111-1111-1111-111111111111",
                        "LogicalName": table["logicalName"],
                        "PrimaryNameAttribute": "cs_name",
                        "SchemaName": table["schemaName"],
                    }
                if method == "POST" and path == "EntityDefinitions":
                    return 204, {
                        "OData-EntityId": (
                            "https://example.crm.dynamics.com/api/data/v9.2/"
                            "EntityDefinitions(11111111-1111-1111-1111-111111111111)"
                        )
                    }, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                return None

        client = FakeClient()
        bootstrap.ensure_table(client, table, "SchemaSolution", "FullSolution", 0)
        post = next(call for call in client.calls if call[0] == "POST" and call[1] == "EntityDefinitions")
        self.assertEqual(len(post[2]["Attributes"]), 1 + len(table["columns"]))
        self.assertIn(
            ("GET", "EntityDefinitions(11111111-1111-1111-1111-111111111111)", None),
            client.calls,
        )
        self.assertFalse(any("/Attributes" in call[1] for call in client.calls))

    def test_existing_partial_table_adds_only_missing_columns_by_metadata_id(self):
        table = self.schema["tables"][0]
        existing_columns = {"cs_siteurl"}

        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                if method == "POST" and path.endswith("/Attributes"):
                    return 204, {"OData-EntityId": "attribute"}, None
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                logical = params["$filter"].split("'")[1]
                if path == "EntityDefinitions":
                    return {
                        "MetadataId": "22222222-2222-2222-2222-222222222222",
                        "LogicalName": table["logicalName"],
                        "PrimaryNameAttribute": "cs_name",
                        "SchemaName": table["schemaName"],
                    }
                if logical in existing_columns:
                    return {"MetadataId": "33333333-3333-3333-3333-333333333333", "LogicalName": logical}
                return None

        client = FakeClient()
        bootstrap.ensure_table(client, table, "SchemaSolution", "FullSolution", 0)
        attribute_posts = [
            call for call in client.calls if call[0] == "POST" and call[1].endswith("/Attributes")
        ]
        self.assertEqual(len(attribute_posts), len(table["columns"]) - 1)
        self.assertTrue(
            all(
                call[1] == "EntityDefinitions(22222222-2222-2222-2222-222222222222)/Attributes"
                for call in attribute_posts
            )
        )


if __name__ == "__main__":
    unittest.main()
