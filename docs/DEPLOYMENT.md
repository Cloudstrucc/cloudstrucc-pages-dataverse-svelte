# Deployment and ALM

## Build

Use PAC CLI as the authoritative packer:

```powershell
pac solution pack --zipfile ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_unmanaged.zip --folder ./solution/full/unpacked --packagetype Unmanaged
pac solution pack --zipfile ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip --folder ./solution/full/unpacked --packagetype Managed --useUnmanagedFileForMissingManaged
```

## Import

```powershell
pac solution import --path ./solution/full/packed/CloudstruccPagesStudio_1_0_0_0_managed.zip --environment $EnvironmentUrl --settings-file ./config/deployment-settings.prod.json --publish-changes --async
```

## Recommended pipeline

1. Lint and test source.
2. Build Svelte applications.
3. Copy built files into solution web resources.
4. Pack unmanaged.
5. Import into integration environment.
6. Run automated smoke tests.
7. Run Solution Checker.
8. Export the environment-validated unmanaged and managed solutions.
9. Publish managed artifact.
10. Import with deployment settings.

## Rollback

- Use solution upgrades for managed releases.
- Keep the previous managed version available.
- Store page/component revisions in Dataverse before publishing.
- Use a holding solution for staged upgrades where appropriate.
