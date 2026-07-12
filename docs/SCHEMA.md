# Dataverse schema

| Table | Purpose |
|---|---|
| `cs_website` | Website root, host binding, theme, default language, status |
| `cs_page` | Route, title, template, language, parent page, publication state |
| `cs_componentdefinition` | Reusable Svelte/component type and configuration schema |
| `cs_componentinstance` | Component placement and page-specific configuration |
| `cs_theme` | Theme adapter, tokens, CSS classes, asset defaults |
| `cs_asset` | Images, icons, favicons, CSS, JavaScript, and files |
| `cs_datasource` | Dataverse, OData, FetchXML, REST, or static data definitions |
| `cs_identityprovider` | OIDC/Entra/Google/Apple/X/passkey/anonymous configuration |
| `cs_permission` | Parent/child table, row, relationship, and column permissions |
| `cs_localization` | Locale-specific labels and content values |
| `cs_deployment` | Publish and repository deployment history |
| `cs_auditlog` | Administrative, Studio, AI, and publish events |

## Ownership

Configuration tables use organization ownership unless records need business-unit partitioning. Audit records should be append-only for normal users. File/image content should use Dataverse file columns or external storage for large assets.

## Relationships

- Website 1:N Pages
- Website 1:N Themes, data sources, identity providers, permissions, localization, deployments
- Page 1:N Component instances
- Component definition 1:N Component instances
- Permission 1:N child permissions
- Page 1:N localized page records or localization entries
