# Troubleshooting

## 404 immediately after `Created table: cs_website`

This was a metadata-propagation race in v1.0.4. Dataverse created the table, but the script immediately queried the `LogicalName` alternate key before it was available.

Use v1.0.5 and rerun the same first-install command. The process is resumable and does not require deleting `cs_website`:

```bash
./scripts/first-install.sh \
  --environment-url "https://goc-theme-dev.crm3.dynamics.com" \
  --managed
```

The corrected bootstrap publishes pending metadata, resolves the partial table through the metadata collection, adds missing columns by table `MetadataId`, and continues. It never calls `EntityDefinitions(LogicalName='...')/Attributes`.

## `PrimaryName attribute not found for Entity: cs_website`

Do not use the old hand-authored solution ZIPs. Run the metadata bootstrap and import only the solution packages exported from Dataverse under `solution/exported/`.

## `solution file not found`

The export files are created only after the bootstrap completes successfully. If bootstrap stops, there is no solution ZIP to import yet.

Also replace placeholder URLs such as `https://TARGET.crm3.dynamics.com` with a real Dataverse environment URL.

## Azure CLI cannot obtain a token

```bash
az login
az account show
az account get-access-token \
  --resource "https://YOUR-DEV.crm3.dynamics.com" \
  --query accessToken \
  --output tsv
```

You may also set `DATAVERSE_ACCESS_TOKEN` before running the bootstrap.

## A conflicting `cs_website` table already exists

The bootstrap refuses to reuse a table when its primary-name column is not `cs_name`. Use a clean development environment or remove only the conflicting development table after confirming that it does not contain needed data.

## PAC export fails after successful bootstrap

```bash
pac auth list
pac auth who
./scripts/export-solutions.sh \
  --environment-url "https://YOUR-DEV.crm3.dynamics.com" \
  --managed
```

## `EntityDefinitions(LogicalName='cs_page')/Attributes` returns 404

This means you are still running the v1.0.4 bootstrap. Version 1.0.5 does not use the alternate-key route for attribute work. It resolves the table from the `EntityDefinitions` collection, captures `MetadataId`, and uses:

```text
EntityDefinitions(<metadata-guid>)/Attributes
```

Replace the repository with v1.0.5 and rerun `first-install.sh`. Existing tables are repaired in place. Exported solution ZIPs are created only after bootstrap finishes, so do not run `import-solution.sh` against `solution/exported/...` until `first-install.sh` succeeds.
