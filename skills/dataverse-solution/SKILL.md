---
name: dataverse-solution
description: build and validate cloudstrucc dataverse solution source and packages. use for table schema, solution xml, pac cli build/import/export, deployment settings, or managed/unmanaged alm changes.
---

# Workflow
1. Read `README.md`, `docs/SCHEMA.md`, and `docs/DEPLOYMENT.md`.
2. Modify unpacked solution source, never only a ZIP.
3. Update web-resource copies when source changes.
4. Run `npm test`.
5. Pack with PAC CLI when available.
6. Run Solution Checker in an authenticated development environment.
7. Report what was locally tested versus environment-tested.

# Guardrails
- Do not import, publish, delete, or upgrade without explicit approval.
- Do not store environment IDs or secrets in source.
- Do not call a fallback ZIP a tenant-validated managed solution.
