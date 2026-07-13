# Testing

## Local structural tests

```bash
npm test
```

Runs `scripts/validate-schema.py`, compiles `scripts/bootstrap-dataverse.py`, and does a full dry run against a placeholder environment URL (`--skip-webresources`). Checks include schema validity, publisher prefix, table/column shape, and Dataverse Web API payload construction (`python3 -m unittest discover -s tests`, run separately — see below).

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Runs the payload-shape unit tests in `tests/test_bootstrap_payloads.py`, including the SiteMap/AppModule payloads that provision the "Cloudstrucc Pages Admin" model-driven app (`ensure_sitemap`, `ensure_appmodule`, `add_app_components`, `publish_app_module`).

## UI test suite (Playwright)

The UI suite is intentionally kept separate from `npm test` because it downloads and drives a real Chromium browser — it is not a prerequisite for the lightweight structural checks above.

```bash
npm run test:ui:install   # one-time: downloads the Chromium binary
npm run test:ui           # runs every spec against both stages below
npm run test:ui:wireframes    # only the wireframes/ POC pages
npm run test:ui:webresources  # only the shipped src/**/*.html web resources
```

Specs live in `tests/ui/` and load pages directly via `file://` URLs — no dev server is required.

- `tests/ui/pages.js` — the single source of truth mapping a logical page name to its `wireframe` and `webresource` file paths.
- `tests/ui/admin-console.spec.js` — sidebar navigation, header sync, and the Create-website modal (fields, theme picker, close/cancel) for the admin console.
- `tests/ui/studio-shell.spec.js` — the shared Studio shell (rail panels, EN/FR toggle, device preview, zoom, panel collapse/restore, Publish modal, Preview overlay), parameterized across all three themes (Bootstrap, GC Design System, Landwind/Tailwind).

Both `wireframes` and `webresources` Playwright **projects** run the exact same spec files; only the resolved file path differs (see `playwright.config.js`). A regression in either stage fails its own project without touching the other.

### Wireframe-first workflow for UI changes

1. Make the UI change in the file under `wireframes/` first (see the table in `tests/ui/pages.js`).
2. Run `npm run test:ui:wireframes` and update/extend the relevant spec until it reflects and validates the intended change.
3. Get the change approved (visual review of the wireframe + passing wireframe tests).
4. Port the same change to the corresponding file under `src/` (admin web resource or studio web resource).
5. Run `npm run test:ui:webresources` (or `npm run test:ui` for both stages) to confirm the shipped artifact matches the approved wireframe.
6. Commit the wireframe, the web resource, and any spec updates together.

Do not port a UI change to `src/` before its wireframe counterpart has passing tests and approval — that ordering is the whole point of the workflow.

## Environment tests

1. Import schema solution into a disposable environment.
2. Confirm all custom tables and columns exist.
3. Import full unmanaged solution.
4. Open the "Cloudstrucc Pages Admin" model-driven app (not just the raw web resource URL) and confirm the Admin Console subarea loads `admin.html` in the SiteMap.
5. Create a test website for each theme.
6. Confirm English/French setup.
7. Open Studio and add/edit/reorder components.
8. Test panel collapse/restore and canvas fit.
9. Publish and verify the Power Pages site.
10. Run Solution Checker and accessibility scans.

Steps 7 and 8 are also covered by the automated `studio-shell.spec.js` UI suite above; the manual pass here should focus on anything the automated suite cannot exercise from a static `file://` context (live Dataverse data, actual publish/import behavior, cross-browser checks).

Never mark a release production-ready until these environment tests pass.
