---
status: implemented
last_verified: 2026-07-11
---

# Automatic Harness Management

## User outcome

When Codex works in a repository with Codex Forge enabled, the repository gains and maintains enough durable knowledge to route future work without requiring the user to create plans or documentation manually.

## Behavior

- Missing Harness entrypoints are created automatically in recognized repositories.
- Users can explicitly invoke `$codex-forge-init` to initialize or repair the current repository immediately.
- Tasks are classified as lightweight, standard, or large from risk, scope, and prompt signals.
- Standard and large tasks receive one dated Active ExecPlan; lightweight tasks receive none.
- Repository and verification maps plus design and product indexes are refreshed deterministically.
- The Stop lifecycle runs one repository-native verification command when detected.
- Passing plans move to `docs/exec-plans/completed/`; failures or blockers remain active.
- Existing human-authored routing and architecture text is preserved.
- The explicit initialization skill cannot trigger implicitly during ordinary tasks.

## Boundaries

Phase 1 does not generate dependency graphs, API surfaces, database schemas, quality scores, knowledge graphs, cross-repository state, or cloud services.
