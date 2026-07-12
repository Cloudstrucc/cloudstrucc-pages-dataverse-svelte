# CLAUDE.md

## Mission
Build Cloudstrucc Pages Studio as an installable Dataverse solution and a Power Pages-backed Svelte website authoring product.

## Start every task
1. Read `README.md`.
2. Read the relevant file in `docs/`.
3. Inspect the current git diff.
4. Identify whether the change affects schema, solution XML, web resources, provisioning, or all four.
5. Make the smallest coherent change.

## Required guardrails
- Never push, merge, tag, publish, or import into an environment unless explicitly requested.
- Never commit secrets, tenant URLs, connection IDs, client secrets, API keys, or exported authentication profiles.
- Run `npm test` before proposing a commit.
- For solution work, run `pac solution check` when an authenticated development environment is available.
- Treat generated solution ZIPs as build outputs; source of truth is the unpacked solution plus `src/`.
- Do not directly edit production-managed solution artifacts.
- Preserve publisher prefix `cs` unless the owner explicitly changes it.
- Use environment variables and connection references for environment-specific values.
- Require human confirmation before applying AI-generated page, CSS, JavaScript, security, or permission changes.

## Context and token discipline
- Keep a short task ledger in `.agent/task.md` and update it after each meaningful milestone.
- Re-read only the files needed for the current step.
- Summarize large files instead of repeatedly loading them.
- After completing a subtask, write a concise state summary, clear stale assumptions, and continue from the summary.
- Start a fresh agent context after roughly 12-15 substantial exchanges, after a major architecture decision, or whenever context contains obsolete generated output.
- Do not paste full generated solution XML into chat unless requested; reference file paths and summarize changes.

## Definition of done
- Source updated.
- Documentation updated when behavior or schema changes.
- Validation passes.
- No secrets or environment IDs added.
- Deployment implications documented.
- The user is told what was and was not tested.

## Claude Code operating notes
- Use a plan for changes spanning more than three files.
- Prefer targeted reads and grep over loading entire generated XML files.
- Ask before running any command that authenticates, imports, publishes, deletes, or upgrades a Dataverse solution.
- Use subagents only for isolated analysis; keep one authoritative implementation path.
