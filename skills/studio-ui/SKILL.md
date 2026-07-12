---
name: studio-ui
description: develop the cloudstrucc pages studio admin and theme-specific editor ui. use for svelte components, canvas behavior, drag/drop, source editing, localization, permissions, theme adapters, or web-resource builds.
---

# Workflow
1. Preserve the three theme adapters and shared interaction behavior.
2. Use TypeScript and lightweight Svelte components for production; standalone HTML remains a design prototype.
3. Ensure panel collapse/restore, fit, zoom, drag/drop, and keyboard navigation work.
4. Sanitize editable HTML and require preview/approval before apply.
5. Run accessibility and JavaScript syntax tests.
6. Update solution web resources after building.

# Context discipline
Load only the theme and component files needed. Summarize generated bundles rather than reading them repeatedly.
