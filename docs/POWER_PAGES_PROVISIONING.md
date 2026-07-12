# Power Pages provisioning

## Why provisioning is post-install

A solution is portable metadata. A Power Pages site requires environment-specific host and website records. The installed admin console gathers the target-specific values and invokes a Power Automate flow or custom API.

## Provisioning contract

Input:

```json
{
  "websiteName": "Citizen Services",
  "theme": "gcdesign",
  "languages": ["en-CA", "fr-CA"],
  "defaultLanguage": "en-CA",
  "authenticationMode": "entra",
  "domain": "services.example.ca",
  "repositoryProvider": "azure-devops"
}
```

Output:

```json
{
  "status": "Succeeded",
  "websiteRecordId": "GUID",
  "powerPagesWebsiteId": "GUID",
  "siteUrl": "https://...powerappsportals.com",
  "studioUrl": "https://.../studio"
}
```

## Recommended implementation

- Admin web resource creates a draft `cs_website` record.
- Web resource calls a custom API or Power Automate flow.
- Flow provisions or binds the Power Pages site using supported tenant operations.
- Flow seeds languages, theme, initial pages, identity records, permissions, and Studio assets.
- Flow records success/failure in `cs_deployment` and `cs_auditlog`.

Do not expose a raw unauthenticated HTTP-trigger URL in the browser. Use Dataverse/custom API or a Power Pages-authorized cloud-flow invocation.
