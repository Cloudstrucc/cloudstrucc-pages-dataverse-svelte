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

    def test_ensure_webresource_recreates_when_existing_type_mismatches(self):
        # Regression test: webresourcetype is immutable in Dataverse after a web
        # resource is created (PATCHing a new value is silently ignored rather
        # than erroring). A web resource created once with the wrong type -- as
        # happened for the admin app icon (created as RESX/12 instead of the
        # required Vector SVG/11) -- can therefore never be repaired by PATCH
        # alone and must be deleted and recreated with the correct type.
        resource = next(r for r in self.schema["webResources"] if r["name"].endswith("admin-icon.svg"))
        self.assertEqual(resource["type"], 11, "schema regressed to the wrong webresourcetype")

        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "GET" and path == (
                    "RetrieveDependenciesForDelete(ObjectId=99999999-9999-9999-9999-999999999999,"
                    "ComponentType=61)"
                ):
                    # Simulate the real-world case: a SiteMap that referenced
                    # this icon via $webresource: blocks deleting it.
                    return 200, {}, {
                        "value": [
                            {"dependentcomponenttype": 62, "dependentcomponentobjectid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
                        ]
                    }
                if method == "DELETE" and path == "sitemaps(aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)":
                    return 204, {}, None
                if method == "DELETE" and path == "webresourceset(99999999-9999-9999-9999-999999999999)":
                    return 204, {}, None
                if method == "POST" and path == "webresourceset":
                    return 204, {
                        "OData-EntityId": (
                            "https://example.crm.dynamics.com/api/data/v9.2/"
                            "webresourceset(88888888-8888-8888-8888-888888888888)"
                        )
                    }, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                # Simulate a record created earlier with the wrong (RESX)
                # webresourcetype instead of the schema's declared type.
                return {
                    "webresourceid": "99999999-9999-9999-9999-999999999999",
                    "name": resource["name"],
                    "webresourcetype": 12,
                }

        client = FakeClient()
        resource_id = bootstrap.ensure_webresource(client, resource, "FullSolution")

        self.assertEqual(resource_id, "88888888-8888-8888-8888-888888888888")
        self.assertIn(
            ("DELETE", "sitemaps(aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)", None),
            client.calls,
            "must remove the dependent SiteMap before it can delete the mistyped web resource",
        )
        self.assertIn(("DELETE", "webresourceset(99999999-9999-9999-9999-999999999999)", None), client.calls)
        dependent_delete_index = client.calls.index(
            ("DELETE", "sitemaps(aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)", None)
        )
        delete_index = client.calls.index(
            ("DELETE", "webresourceset(99999999-9999-9999-9999-999999999999)", None)
        )
        create_index = next(i for i, call in enumerate(client.calls) if call[0] == "POST" and call[1] == "webresourceset")
        self.assertLess(dependent_delete_index, delete_index, "must clear dependents before deleting the resource")
        self.assertLess(delete_index, create_index, "must delete the mistyped record before recreating it")
        self.assertFalse(
            any(call[0] == "PATCH" for call in client.calls),
            "must not PATCH a record whose type needs to change; PATCH silently ignores webresourcetype",
        )

    def test_clear_blocking_dependents_raises_on_unrecognized_dependent_type(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "GET" and path.startswith("RetrieveDependenciesForDelete"):
                    return 200, {}, {
                        "value": [{"dependentcomponenttype": 2, "dependentcomponentobjectid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}]
                    }
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                raise AssertionError("first() should not be called")

        client = FakeClient()
        with self.assertRaises(RuntimeError):
            bootstrap.clear_blocking_dependents(client, 61, "99999999-9999-9999-9999-999999999999")

    def test_ensure_webresource_patches_when_type_matches(self):
        resource = next(r for r in self.schema["webResources"] if r["name"].endswith("admin-icon.svg"))

        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "PATCH" and path == "webresourceset(77777777-7777-7777-7777-777777777777)":
                    return 204, {}, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                return {
                    "webresourceid": "77777777-7777-7777-7777-777777777777",
                    "name": resource["name"],
                    "webresourcetype": resource["type"],
                }

        client = FakeClient()
        resource_id = bootstrap.ensure_webresource(client, resource, "FullSolution")

        self.assertEqual(resource_id, "77777777-7777-7777-7777-777777777777")
        self.assertFalse(any(call[0] == "DELETE" for call in client.calls))
        self.assertTrue(any(call[0] == "PATCH" for call in client.calls))


class BootstrapAdminAppTests(unittest.TestCase):
    """Payload tests for the admin model-driven app: SiteMap + AppModule wiring."""

    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schema" / "cloudstrucc-pages.schema.json").read_text())
        cls.site_map = cls.schema["siteMap"]
        cls.app_module = cls.schema["appModule"]

    def test_schema_declares_sitemap_and_appmodule(self):
        self.assertIn("adminWebResourceName", self.site_map)
        self.assertIn("iconWebResourceName", self.site_map)
        self.assertIn("xmlTemplate", self.site_map)
        self.assertIn("uniqueName", self.app_module)
        self.assertIn("iconWebResourceName", self.app_module)

    def test_webresource_directive_format(self):
        self.assertEqual(
            bootstrap.webresource_directive("cs_/cloudstrucc/pages/admin.html"),
            "$webresource:cs_/cloudstrucc/pages/admin.html",
        )

    def test_ensure_sitemap_create_substitutes_directives_and_adds_component(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "POST" and path == "sitemaps":
                    return 204, {
                        "OData-EntityId": (
                            "https://example.crm.dynamics.com/api/data/v9.2/"
                            "sitemaps(44444444-4444-4444-4444-444444444444)"
                        )
                    }, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                return None

        client = FakeClient()
        sitemap_id = bootstrap.ensure_sitemap(
            client,
            self.site_map,
            self.site_map["adminWebResourceName"],
            self.site_map["iconWebResourceName"],
            "FullSolution",
        )
        self.assertEqual(sitemap_id, "44444444-4444-4444-4444-444444444444")
        post = next(call for call in client.calls if call[0] == "POST" and call[1] == "sitemaps")
        xml = post[2]["sitemapxml"]
        self.assertIn("$webresource:cs_/cloudstrucc/pages/admin.html", xml)
        self.assertIn("$webresource:cs_/cloudstrucc/pages/admin-icon.svg", xml)
        self.assertNotIn("{adminUrl}", xml)
        self.assertNotIn("{iconUrl}", xml)
        self.assertEqual(post[2]["sitemapnameunique"], self.site_map["uniqueName"])
        component_call = next(
            call for call in client.calls if call[0] == "POST" and call[1] == "AddSolutionComponent"
        )
        self.assertEqual(component_call[2]["ComponentId"], "44444444-4444-4444-4444-444444444444")
        self.assertEqual(component_call[2]["ComponentType"], 62)

    def test_ensure_sitemap_update_existing_patches_without_changing_unique_name(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "PATCH" and path.startswith("sitemaps("):
                    return 204, {}, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                return {"sitemapid": "55555555-5555-5555-5555-555555555555", "sitemapnameunique": self.parent_unique}

        client = FakeClient()
        client.parent_unique = self.site_map["uniqueName"]
        sitemap_id = bootstrap.ensure_sitemap(
            client,
            self.site_map,
            self.site_map["adminWebResourceName"],
            self.site_map["iconWebResourceName"],
            "FullSolution",
        )
        self.assertEqual(sitemap_id, "55555555-5555-5555-5555-555555555555")
        patch = next(call for call in client.calls if call[0] == "PATCH")
        self.assertNotIn("sitemapnameunique", patch[2])

    def test_ensure_appmodule_create_sets_webresourceid_and_adds_component(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "POST" and path == "appmodules":
                    return 204, {
                        "OData-EntityId": (
                            "https://example.crm.dynamics.com/api/data/v9.2/"
                            "appmodules(66666666-6666-6666-6666-666666666666)"
                        )
                    }, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                return None

        client = FakeClient()
        appmodule_id = bootstrap.ensure_appmodule(
            client, self.app_module, "77777777-7777-7777-7777-777777777777", "FullSolution"
        )
        self.assertEqual(appmodule_id, "66666666-6666-6666-6666-666666666666")
        post = next(call for call in client.calls if call[0] == "POST" and call[1] == "appmodules")
        self.assertEqual(post[2]["webresourceid"], "77777777-7777-7777-7777-777777777777")
        self.assertEqual(post[2]["uniquename"], self.app_module["uniqueName"])
        component_call = next(
            call for call in client.calls if call[0] == "POST" and call[1] == "AddSolutionComponent"
        )
        self.assertEqual(component_call[2]["ComponentType"], 80)

    def test_clear_orphaned_appmodule_reservations_removes_dead_objectid_only(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "GET" and path == "solutioncomponents":
                    return 200, {}, {
                        "value": [
                            {
                                "solutioncomponentid": "aaaaaaaa-0000-0000-0000-000000000001",
                                "objectid": "11111111-1111-1111-1111-111111111111",
                                "_solutionid_value": "22222222-2222-2222-2222-222222222222",
                            },
                            {
                                "solutioncomponentid": "aaaaaaaa-0000-0000-0000-000000000002",
                                "objectid": "99999999-9999-9999-9999-999999999999",
                                "_solutionid_value": "33333333-3333-3333-3333-333333333333",
                            },
                        ]
                    }
                if method == "GET" and path == "appmodules(11111111-1111-1111-1111-111111111111)":
                    return 200, {}, {"appmoduleid": "11111111-1111-1111-1111-111111111111"}
                if method == "GET" and path == "appmodules(99999999-9999-9999-9999-999999999999)":
                    return 404, {}, None
                if method == "GET" and path == "solutions(33333333-3333-3333-3333-333333333333)":
                    return 200, {}, {"uniquename": "CloudstruccPagesStudio"}
                if method == "POST" and path == "RemoveSolutionComponent":
                    return 204, {}, None
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                raise AssertionError("first() should not be called")

        client = FakeClient()
        cleared, default_blocked = bootstrap.clear_orphaned_appmodule_reservations(client)
        self.assertEqual(cleared, 1)
        self.assertEqual(default_blocked, [])
        remove_call = next(call for call in client.calls if call[0] == "POST" and call[1] == "RemoveSolutionComponent")
        self.assertEqual(
            remove_call[2],
            {
                "SolutionComponent": {"solutioncomponentid": "99999999-9999-9999-9999-999999999999"},
                "ComponentType": 80,
                "SolutionUniqueName": "CloudstruccPagesStudio",
            },
        )
        # The live appmodule's reservation must never be touched.
        self.assertFalse(
            any(
                call[0] == "GET" and call[1] == "solutions(22222222-2222-2222-2222-222222222222)"
                for call in client.calls
            )
        )

    def test_ensure_appmodule_recreates_after_clearing_orphaned_duplicate(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
                self.appmodule_create_attempts = 0

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "POST" and path == "appmodules":
                    self.appmodule_create_attempts += 1
                    if self.appmodule_create_attempts == 1:
                        return 400, {}, '{"error":{"code":"0x80050135","message":"-2147155681"}}'
                    return 204, {
                        "OData-EntityId": (
                            "https://example.crm.dynamics.com/api/data/v9.2/"
                            "appmodules(66666666-6666-6666-6666-666666666666)"
                        )
                    }, None
                if method == "GET" and path == "solutioncomponents":
                    return 200, {}, {
                        "value": [
                            {
                                "solutioncomponentid": "aaaaaaaa-0000-0000-0000-000000000002",
                                "objectid": "99999999-9999-9999-9999-999999999999",
                                "_solutionid_value": "33333333-3333-3333-3333-333333333333",
                            },
                        ]
                    }
                if method == "GET" and path == "appmodules(99999999-9999-9999-9999-999999999999)":
                    return 404, {}, None
                if method == "GET" and path == "solutions(33333333-3333-3333-3333-333333333333)":
                    return 200, {}, {"uniquename": "CloudstruccPagesStudio"}
                if method == "POST" and path == "RemoveSolutionComponent":
                    return 204, {}, None
                if method == "POST" and path == "AddSolutionComponent":
                    return 200, {}, {}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                self.calls.append(("FIRST", path, None))
                return None

        client = FakeClient()
        appmodule_id = bootstrap.ensure_appmodule(
            client, self.app_module, "77777777-7777-7777-7777-777777777777", "FullSolution"
        )
        self.assertEqual(appmodule_id, "66666666-6666-6666-6666-666666666666")
        self.assertEqual(client.appmodule_create_attempts, 2)
        remove_call = next(call for call in client.calls if call[0] == "POST" and call[1] == "RemoveSolutionComponent")
        self.assertEqual(
            remove_call[2]["SolutionComponent"],
            {"solutioncomponentid": "99999999-9999-9999-9999-999999999999"},
        )

    def test_ensure_appmodule_raises_actionable_error_when_only_default_solution_blocks(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "POST" and path == "appmodules":
                    return 400, {}, '{"error":{"code":"0x80050135","message":"-2147155681"}}'
                if method == "GET" and path == "solutioncomponents":
                    return 200, {}, {
                        "value": [
                            {
                                "solutioncomponentid": "aaaaaaaa-0000-0000-0000-000000000002",
                                "objectid": "99999999-9999-9999-9999-999999999999",
                                "_solutionid_value": "44444444-4444-4444-4444-444444444444",
                            },
                        ]
                    }
                if method == "GET" and path == "appmodules(99999999-9999-9999-9999-999999999999)":
                    return 404, {}, None
                if method == "GET" and path == "solutions(44444444-4444-4444-4444-444444444444)":
                    return 200, {}, {"uniquename": "Default"}
                if method == "POST" and path == "RemoveSolutionComponent":
                    # Real Dataverse behavior, confirmed live against
                    # goc-theme-dev: components cannot be removed from the
                    # Default Solution via this action.
                    return 400, {}, (
                        '{"error":{"code":"0x8004f000","message":"A Solution '
                        'Component cannot be removed from the Default Solution."}}'
                    )
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                return None

        client = FakeClient()
        with self.assertRaises(RuntimeError) as ctx:
            bootstrap.ensure_appmodule(
                client, self.app_module, "77777777-7777-7777-7777-777777777777", "FullSolution"
            )
        message = str(ctx.exception)
        self.assertIn("Default Solution", message)
        self.assertIn("99999999-9999-9999-9999-999999999999", message)

    def test_ensure_appmodule_create_failure_without_orphan_raises(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                if method == "POST" and path == "appmodules":
                    return 400, {}, '{"error":{"message":"some other failure"}}'
                if method == "GET" and path == "solutioncomponents":
                    return 200, {}, {"value": []}
                raise AssertionError(f"Unexpected request: {method} {path}")

            def first(self, path: str, params: dict[str, str]):
                return None

        client = FakeClient()
        with self.assertRaises(RuntimeError):
            bootstrap.ensure_appmodule(
                client, self.app_module, "77777777-7777-7777-7777-777777777777", "FullSolution"
            )

    def test_add_app_components_builds_typed_component_references(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                return 204, {}, None

            def first(self, path: str, params: dict[str, str]):
                raise AssertionError("first() should not be called")

        client = FakeClient()
        bootstrap.add_app_components(
            client,
            "66666666-6666-6666-6666-666666666666",
            [
                ("sitemap", "44444444-4444-4444-4444-444444444444"),
                ("webresource", "88888888-8888-8888-8888-888888888888"),
            ],
        )
        method, path, payload = client.calls[0]
        self.assertEqual(method, "POST")
        # AddAppComponents is an unbound Web API action -- it is invoked as a
        # plain POST to the action name with AppId supplied in the payload,
        # NOT bound to an appmodules(id)/Microsoft.Dynamics.CRM.AddAppComponents
        # segment (that shape 404s: "Resource not found for the segment").
        self.assertEqual(path, "AddAppComponents")
        self.assertEqual(payload["AppId"], "66666666-6666-6666-6666-666666666666")
        self.assertEqual(
            payload["Components"],
            [
                {"@odata.type": "Microsoft.Dynamics.CRM.sitemap", "sitemapid": "44444444-4444-4444-4444-444444444444"},
                {"@odata.type": "Microsoft.Dynamics.CRM.webresource", "webresourceid": "88888888-8888-8888-8888-888888888888"},
            ],
        )

    def test_publish_app_module_builds_parameter_xml_with_app_id(self):
        class FakeClient:
            dry_run = False

            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

            def request(self, method: str, path: str, **kwargs: Any):
                self.calls.append((method, path, kwargs.get("payload")))
                return 204, {}, None

            def first(self, path: str, params: dict[str, str]):
                raise AssertionError("first() should not be called")

        client = FakeClient()
        bootstrap.publish_app_module(client, "66666666-6666-6666-6666-666666666666")
        method, path, payload = client.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(path, "PublishXml")
        self.assertIn("<appmodule>66666666-6666-6666-6666-666666666666</appmodule>", payload["ParameterXml"])


if __name__ == "__main__":
    unittest.main()
