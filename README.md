# Cloudstrucc Pages Studio for Dataverse

Cloudstrucc Pages Studio is a solution-oriented starter repository for installing a governed website administration experience into Microsoft Dataverse and then provisioning a Power Pages-backed Svelte/SPA website from the installed admin console.

## What is included

- An **admin HTML web resource** used as the website provisioning console.
- Three **theme-specific Studio web resources**: Start Bootstrap Landing Page, Landwind, and GC Design System.
- A Dataverse schema for websites, pages, components, themes, assets, data sources, identity providers, permissions, localization, deployments, and audit events.
- Unpacked **schema-only** and **full** solution source folders.
- Prebuilt ZIP packages produced from those folders.
- PAC CLI build, import, export, and deployment scripts for both PowerShell and Bash/macOS.
- A post-install provisioning approach for creating the Power Pages site and seeding Studio metadata.
- Agent instructions and focused project skills for Codex or Claude Code.

## Important implementation boundary

A Dataverse solution can install tables, columns, web resources, security artifacts, flows, and application components. A Power Pages website still needs a **provisioning operation** in the target tenant because the website host, site binding, language records, and environment-specific IDs do not exist until deployment.

The repository uses a two-stage pattern:

1. Import the managed or unmanaged solution.
2. Open the Cloudstrucc admin console and run **Create website**, which provisions or binds the Power Pages site and seeds the Cloudstrucc records.

The packed ZIPs are starter packages and must be validated in a development tenant before production use. Run Solution Checker and complete an actual Dataverse import before releasing a managed package.

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
│   ├── Build-Solutions.ps1
│   ├── Import-Solution.ps1
│   ├── Deploy.ps1
│   ├── Export-ValidatedSolution.ps1
│   ├── build-solutions.sh
│   ├── import-solution.sh
│   ├── deploy.sh
│   └── export-validated-solution.sh
├── config/
├── docs/
├── tests/
└── skills/
```

## Prerequisites

- A Power Platform environment with Dataverse.
- Permission to import solutions and create Power Pages sites.
- Power Platform CLI (`pac`) installed and available in `PATH`.
- Power Pages enabled in the tenant.
- Node.js 20+ if replacing the standalone web resources with compiled Svelte bundles.
- One of:
  - macOS/Linux terminal with Bash 3.2+.
  - PowerShell 7+.

On macOS, confirm the tools are available:

```bash
bash --version
pac --version
node --version
```

## macOS and Linux quick start

### 1. Make the scripts executable

Git normally preserves the executable bit. If needed:

```bash
chmod +x scripts/*.sh
```

### 2. Authenticate to Dataverse

```bash
pac auth create --url https://YOURORG.crm3.dynamics.com
pac auth list
pac auth select --index 1
```

### 3. Validate the repository

```bash
npm test
```

### 4. Pack all solutions

```bash
./scripts/build-solutions.sh
```

This creates:

```text
solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_unmanaged.zip
solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_managed.zip
solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip
solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip
```

### 5. Import an unmanaged development solution

```bash
./scripts/import-solution.sh \
  --environment-url https://YOURORG.crm3.dynamics.com \
  --solution-path ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip \
  --settings-file ./config/deployment-settings.dev.json
```

### 6. Import a managed test or production solution

```bash
./scripts/import-solution.sh \
  --environment-url https://YOURORG.crm3.dynamics.com \
  --solution-path ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip \
  --settings-file ./config/deployment-settings.prod.json
```

### 7. Build and deploy in one command

Managed deployment:

```bash
./scripts/deploy.sh \
  --environment-url https://YOURORG.crm3.dynamics.com \
  --package-type managed \
  --settings-file ./config/deployment-settings.prod.json
```

Unmanaged development deployment:

```bash
./scripts/deploy.sh \
  --environment-url https://YOURORG.crm3.dynamics.com \
  --package-type unmanaged \
  --settings-file ./config/deployment-settings.dev.json
```

### 8. Export validated packages from Dataverse

After importing and validating the solution in a development environment:

```bash
./scripts/export-validated-solution.sh \
  --environment-url https://YOURORG.crm3.dynamics.com \
  --solution-name CloudstruccPagesStudio \
  --output-dir ./dist
```

## PowerShell quick start

### Authenticate

```powershell
pac auth create --url https://YOURORG.crm3.dynamics.com
pac auth select --index 1
```

### Validate and pack

```powershell
npm test
./scripts/Build-Solutions.ps1
```

### Import

```powershell
./scripts/Import-Solution.ps1 `
  -EnvironmentUrl https://YOURORG.crm3.dynamics.com `
  -SolutionPath ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip `
  -SettingsFile ./config/deployment-settings.dev.json
```

### Deploy

```powershell
./scripts/Deploy.ps1 `
  -EnvironmentUrl https://YOURORG.crm3.dynamics.com `
  -PackageType managed `
  -SettingsFile ./config/deployment-settings.prod.json
```

## Script configuration

The Bash scripts use `pac` from `PATH`. Override the executable when necessary:

```bash
PAC_BIN=/custom/path/to/pac ./scripts/build-solutions.sh
```

All Bash scripts use strict mode:

```bash
set -euo pipefail
```

They stop on command failures, unset variables, invalid arguments, missing files, and missing tools.

## Post-install setup

1. Publish customizations.
2. Open the Cloudstrucc Pages Admin web resource from the solution or model-driven app.
3. Choose **Create website**.
4. Select the theme, language set, domain, identity configuration, and repository integration.
5. Provision or bind the Power Pages host.
6. Seed the site metadata.
7. Assign Cloudstrucc administration roles.
8. Open the Studio as an authorized administrator.

## Development workflow

1. Edit the admin or Studio source under `src/`.
2. Run `npm test`.
3. Copy or build assets into the full solution's `WebResources` directory.
4. Pack the unmanaged solution.
5. Import it into a development environment.
6. Run Solution Checker.
7. Test site creation, page editing, permissions, localization, and publishing.
8. Export the validated solution from Dataverse to refresh source-controlled solution files.
9. Generate the managed package only after validation succeeds.

## Solution strategy

- **Schema solution:** tables, columns, relationships, choices, and environment variables.
- **Full solution:** schema plus admin/Studio web resources and deployment metadata.
- Use unmanaged packages in development.
- Use managed packages in test and production.
- Do not hand-edit a managed package after Dataverse exports it.

## Troubleshooting

### `pac: command not found`

Install Power Platform CLI and ensure the executable is available in your shell's `PATH`. Restart the terminal after installation and verify:

```bash
command -v pac
pac --version
```

### Permission denied when running a Bash script

```bash
chmod +x scripts/*.sh
```

### Authentication profile points to the wrong environment

```bash
pac auth list
pac auth select --index 1
```

You can also pass `--environment-url` to the import, deploy, and export scripts so the intended target is explicit.

### Managed packing fails

Ensure the unpacked solution includes the Dataverse-managed metadata generated by an authoritative export. The `--useUnmanagedFileForMissingManaged` option helps during development but does not replace validation in a real Dataverse environment.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Dataverse schema](docs/SCHEMA.md)
- [Deployment and ALM](docs/DEPLOYMENT.md)
- [Power Pages provisioning](docs/POWER_PAGES_PROVISIONING.md)
- [Security model](docs/SECURITY.md)
- [Testing](docs/TESTING.md)

## Release gate

Before publishing a production package:

1. Run repository tests.
2. Pack with PAC CLI.
3. Run Solution Checker.
4. Import into a disposable development/test environment.
5. Exercise the admin console and site-provisioning workflow.
6. Verify tables, web resources, security roles, flows, and environment variables.
7. Export authoritative managed and unmanaged packages from Dataverse.
8. Commit only reviewed source and validated packages.
