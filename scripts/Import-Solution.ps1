param([Parameter(Mandatory=$true)][string]$EnvironmentUrl,[Parameter(Mandatory=$true)][string]$SolutionPath,[string]$SettingsFile)
$ErrorActionPreference="Stop"
$args=@("solution","import","--environment",$EnvironmentUrl,"--path",(Resolve-Path $SolutionPath),"--publish-changes","--async")
if($SettingsFile){$args += @("--settings-file",(Resolve-Path $SettingsFile))}
& pac @args
