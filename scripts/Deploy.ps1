param([Parameter(Mandatory=$true)][string]$EnvironmentUrl,[ValidateSet("managed","unmanaged")][string]$PackageType="managed",[string]$SettingsFile="./config/deployment-settings.prod.json")
$root=Split-Path -Parent $PSScriptRoot
& "$PSScriptRoot/Build-Solutions.ps1"
$path="$root/solution/full/packed/CloudstruccPagesStudio_1_0_0_0_$PackageType.zip"
& "$PSScriptRoot/Import-Solution.ps1" -EnvironmentUrl $EnvironmentUrl -SolutionPath $path -SettingsFile $SettingsFile
