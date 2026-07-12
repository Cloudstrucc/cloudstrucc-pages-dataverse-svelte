param(
    [Parameter(Mandatory=$true)][string]$EnvironmentUrl,
    [Parameter(Mandatory=$true)][string]$SolutionPath,
    [string]$SettingsFile = ''
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $SolutionPath)) { throw "Solution package not found: $SolutionPath" }
$args = @('solution','import','--environment',$EnvironmentUrl,'--path',(Resolve-Path $SolutionPath),'--publish-changes','--async')
if ($SettingsFile) {
    if (-not (Test-Path $SettingsFile)) { throw "Settings file not found: $SettingsFile" }
    $args += @('--settings-file',(Resolve-Path $SettingsFile))
}
& pac @args
if ($LASTEXITCODE -ne 0) { throw "PAC solution import failed with exit code $LASTEXITCODE" }
