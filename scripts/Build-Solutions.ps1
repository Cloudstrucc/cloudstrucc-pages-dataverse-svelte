$ErrorActionPreference = 'Stop'
Write-Error @'
The hand-authored XML packing workflow has been retired because Dataverse rejected
its table metadata. Run the macOS/Linux bootstrap/export workflow from Bash, or
implement the equivalent Dataverse Web API bootstrap for PowerShell before exporting
solutions from a build environment.

Recommended:
  ./scripts/first-install.sh --environment-url https://YOUR-DEV.crm3.dynamics.com
'@
