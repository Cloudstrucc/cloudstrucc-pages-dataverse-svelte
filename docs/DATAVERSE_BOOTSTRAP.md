# Dataverse bootstrap and authoritative solution export

## Why this workflow exists

Dataverse solution table metadata is not safe to synthesize by editing `Customizations.xml`. The supported metadata API creates a table by posting an `EntityMetadata` representation to `EntityDefinitions`. The payload must include a string attribute with `IsPrimaryName: true`.

The bootstrap associates created metadata with `CloudstruccPagesSchema` by sending the `MSCRM.SolutionUniqueName` header. It adds each table to `CloudstruccPagesStudio`, creates the web resources, publishes the customizations, and then PAC CLI exports the real solution packages.

## Official documentation

- https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/create-update-entity-definitions-using-web-api
- https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/create-update-column-definitions-using-web-api
- https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/solution
- https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/webresource
- https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/solution
- https://learn.microsoft.com/en-us/power-apps/developer/data-platform/reference/entities/publisher

## Lifecycle

```text
schema JSON
  -> Dataverse metadata Web API
  -> Dataverse publisher and unmanaged solutions
  -> Dataverse-generated export ZIP
  -> import into test/prod
```

## Security

- Prefer a dedicated build environment.
- Use an interactive Azure CLI login or a short-lived token.
- Never place access tokens in repository files.
- Use a service principal and least-privilege application user for CI/CD.
