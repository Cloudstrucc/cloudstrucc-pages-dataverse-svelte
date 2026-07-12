# Security

- Admin console access is limited to Cloudstrucc Pages Administrator and System Administrator roles.
- Studio access requires an authenticated administrator/maker identity.
- Secrets are stored in connection references, environment variables, or Azure Key Vault-backed connections; never in web resources.
- Every AI-generated change follows propose, preview, approve, apply, audit.
- Data-source definitions use allowlisted tables and columns.
- FetchXML/OData is parsed and validated before execution.
- JavaScript and CSS changes require sanitization, CSP review, and optional approval.
- Publishing validates permissions, localization completeness, WCAG, and current-record hashes.
