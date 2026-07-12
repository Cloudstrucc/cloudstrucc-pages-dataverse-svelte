---
name: power-pages-provisioning
description: design or implement cloudstrucc power pages website provisioning from the dataverse admin console. use for create-site flows, languages, themes, domains, identity providers, initial pages, permissions, and site-binding operations.
---

# Workflow
1. Read `docs/POWER_PAGES_PROVISIONING.md` and `docs/SECURITY.md`.
2. Keep solution import separate from environment-specific site provisioning.
3. Create a draft website record before orchestration.
4. Invoke a governed flow or custom API, not a public secret-bearing endpoint.
5. Make operations idempotent and record deployment/audit status.
6. Seed theme, languages, pages, identity, and permissions transactionally where possible.
7. Test rollback and retry behavior.
