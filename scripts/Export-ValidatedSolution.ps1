param([Parameter(Mandatory=$true)][string]$EnvironmentUrl,[string]$SolutionName="CloudstruccPagesStudio")
$root=Split-Path -Parent $PSScriptRoot
pac solution export --environment $EnvironmentUrl --name $SolutionName --path "$root/dist/${SolutionName}_unmanaged.zip" --overwrite
pac solution export --environment $EnvironmentUrl --name $SolutionName --path "$root/dist/${SolutionName}_managed.zip" --managed --overwrite
