# Cloudstrucc Pages Studio for Dataverse

Cloudstrucc Pages Studio is a solution-oriented starter repository for installing a governed website administration experience into Microsoft Dataverse and then provisioning a Power Pages-backed Svelte/SPA website from the installed admin console.

## What is included

- An **admin HTML web resource** used as the website provisioning console.
- Three **theme-specific Studio web resources**: Start Bootstrap Landing Page, Landwind, and GC Design System.
- A Dataverse schema for websites, pages, components, themes, assets, data sources, identity providers, permissions, localization, deployments, and audit events.
- Unpacked **schema-only** and **full** solution source folders.
- Prebuilt ZIP packages produced from those folders.
- PAC CLI build, import, export, and deployment scripts.
- A post-install provisioning approach for creating the Power Pages site and seeding Studio metadata.
- Agent instructions and focused project skills for Codex or Claude Code.

## Important implementation boundary

A Dataverse solution can install tables, columns, web resources, security artifacts, flows, and application components. A Power Pages website still needs a **provisioning operation** in the target tenant because the website host, site binding, language records, and environment-specific IDs do not exist until deployment. This repository therefore uses a two-stage pattern:

1. Import the managed or unmanaged solution.
2. Open the Cloudstrucc admin console and run **Create website**, which provisions or binds the Power Pages site and seeds the Cloudstrucc records.

The provided packed ZIPs are generated starter packages and are structurally validated in this repository. They have **not been imported into your tenant**, because this environment has no Dataverse connection or PAC CLI authentication. Before production use, run `pac solution check` and perform an import into a development environment.

## Repository structure

```text
cloudstrucc-pages-dataverse/
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── package.json
├── src/
│   ├── admin-webresource/
│   ├── studio-webresources/
│   └── shared/
├── solution/
│   ├── schema/
│   │   ├── unpacked/
│   │   └── packed/
│   └── full/
│       ├── unpacked/
│       └── packed/
├── scripts/
├── config/
├── docs/
├── tests/
└── skills/
```

## Prerequisites

- A Power Platform environment with Dataverse.
- Permission to import solutions and create Power Pages sites.
- Power Platform CLI (`pac`) installed.
- Power Pages enabled in the tenant.
- Node.js 20+ only if you later replace the standalone web resources with compiled Svelte bundles.
- PowerShell 7+ for the deployment scripts.

## Quick start

### 1. Authenticate

```powershell
pac auth create --url https://YOURORG.crm3.dynamics.com
pac auth select --index 1
```

### 2. Validate the repository

```bash
npm test
```

### 3. Pack using PAC CLI

```powershell
./scripts/Build-Solutions.ps1
```

This creates:

```text
solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_unmanaged.zip
solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_managed.zip
solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip
solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip
```

### 4. Import

Development:

```powershell
./scripts/Import-Solution.ps1   -EnvironmentUrl https://YOURORG.crm3.dynamics.com   -SolutionPath ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip
```

Production:

```powershell
./scripts/Import-Solution.ps1   -EnvironmentUrl https://YOURORG.crm3.dynamics.com   -SolutionPath ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip   -SettingsFile ./config/deployment-settings.prod.json
```

### 5. Post-install

1. Publish customizations.
2. Open the Cloudstrucc Pages Admin web resource from the solution or model-driven app shell.
3. Choose **Create website**.
4. Select the theme, language set, domain, identity configuration, and repository integration.
5. Provision the Power Pages host.
6. Seed the site metadata.
7. Open the Studio as an authorized administrator.

## Development workflow

1. Edit the admin or Studio source under `src/`.
2. Run `npm test`.
3. Copy or build assets into the full solution's `WebResources` directory.
4. Pack the unmanaged solution.
5. Import into a development environment.
6. Run Solution Checker.
7. Test site creation, page editing, permissions, localization, and publish flows.
8. Export the validated solution from Dataverse to refresh the source-controlled unpacked solution.
9. Only then produce the managed package.

## Solution strategy

- **Schema solution:** tables, columns, relationships, choices, and environment variables.
- **Full solution:** schema plus admin/Studio web resources and deployment metadata.
- Use unmanaged packages in development.
- Use managed packages in test and production.
- Never hand-edit a managed package after export.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Dataverse schema](docs/SCHEMA.md)
- [Deployment and ALM](docs/DEPLOYMENT.md)
- [Power Pages provisioning](docs/POWER_PAGES_PROVISIONING.md)
- [Security model](docs/SECURITY.md)
- [Testing](docs/TESTING.md)

## Microsoft guidance used

The project follows the PAC CLI solution pack/import workflow, Dataverse solution ALM, model-driven app web-resource patterns, and Power Pages solution/CLI concepts. Always verify commands against the current Microsoft Learn documentation before production deployment.
