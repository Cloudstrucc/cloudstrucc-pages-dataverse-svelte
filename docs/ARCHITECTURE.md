# Architecture

## Logical architecture

```mermaid
flowchart LR
  Admin[Model-driven app / admin web resource] --> DV[(Dataverse)]
  Admin --> Provision[Provisioning flow or custom API]
  Provision --> PP[Power Pages website]
  PP --> Studio[Cloudstrucc Studio SPA]
  Studio --> API[Dataverse Web API abstraction]
  API --> DV
  Studio --> Repo[GitHub / Azure DevOps / GitLab]
  Studio --> AI[Power Automate AI dispatch]
```

## Layers

1. **Dataverse metadata layer**: custom Cloudstrucc tables represent websites, pages, component definitions, component instances, themes, data sources, permissions, localization, and deployments.
2. **Admin layer**: an HTML web resource embedded in a model-driven app. It provisions sites and manages environment-level configuration.
3. **Studio layer**: a Svelte/TypeScript SPA compiled to static web resources and hosted from the Power Pages site.
4. **Runtime layer**: the generated site consumes Dataverse through the Power Pages Web API and a governed query abstraction.
5. **Automation layer**: Power Automate handles AI prompts, approvals, site-provisioning orchestration, and audit logging.
6. **ALM layer**: PAC CLI, solutions, deployment settings, source control, and environment-specific values.

## Provisioning sequence

```mermaid
sequenceDiagram
  participant A as Administrator
  participant W as Admin web resource
  participant D as Dataverse
  participant P as Provisioning flow/API
  participant S as Power Pages

  A->>W: Create website
  W->>D: Create cs_website draft
  W->>P: Submit provisioning request
  P->>S: Create or bind website host
  P->>D: Seed theme, languages, pages, components
  P->>D: Store site ID and URL
  P-->>W: Provisioning completed
  W-->>A: Open Studio
```
