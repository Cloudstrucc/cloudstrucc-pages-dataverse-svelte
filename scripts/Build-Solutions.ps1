param([string]$Pac = "pac")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
& $Pac solution pack --zipfile "$root/solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_unmanaged.zip" --folder "$root/solution/schema/unpacked" --packagetype Unmanaged --allowWrite --clobber
& $Pac solution pack --zipfile "$root/solution/schema/packed/CloudstruccPagesSchema_1_0_0_0_managed.zip" --folder "$root/solution/schema/unpacked" --packagetype Managed --useUnmanagedFileForMissingManaged --allowWrite --clobber
& $Pac solution pack --zipfile "$root/solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip" --folder "$root/solution/full/unpacked" --packagetype Unmanaged --allowWrite --clobber
& $Pac solution pack --zipfile "$root/solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip" --folder "$root/solution/full/unpacked" --packagetype Managed --useUnmanagedFileForMissingManaged --allowWrite --clobber
