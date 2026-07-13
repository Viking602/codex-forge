---
name: codex-forge
description: Automatically build and maintain a repository-first Harness knowledge base during Codex engineering work. Use for any repository task that may change code, tests, configuration, architecture, product behavior, or durable engineering knowledge; classify the task, manage ExecPlan lifecycle when warranted, reconcile long-term knowledge, refresh generated maps and indexes, verify the result, and archive completed plans without asking the user to invoke planning or documentation commands.
---

# Codex Forge

Treat the repository as the knowledge base. Hooks bootstrap and inspect the Harness automatically; use their injected task class and paths as the current routing contract.

## Execute the task

1. Read `AGENTS.md`, `ARCHITECTURE.md`, and only the routed documents relevant to the task.
2. Accept the automatic task class unless concrete scope proves it wrong:
   - `lightweight`: execute directly; do not create a plan or spec.
   - `standard`: analyze the concrete intent, generate a concise semantic plan title, run the hook-injected `start-plan` command, then use the resulting active ExecPlan.
   - `large`: create the active ExecPlan through the same intent-first flow and update durable architecture, design, or product knowledge only when behavior truly changes.
3. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current at meaningful milestones. Hooks record mechanical activity; replace that with semantic facts when useful.
4. Search existing knowledge before writing. Merge or correct an existing topic before creating another file, then refresh its index.
5. Never hand-edit `docs/generated/`. The lifecycle hook deterministically rebuilds it from repository state.
6. Run the repository verification routed by `docs/generated/verification-map.md`. Fix failures before declaring completion.
7. Before the final response, extract only durable facts into `ARCHITECTURE.md`, `docs/design-docs/`, or `docs/product-specs/`. Leave one-off execution detail in the ExecPlan.
8. Finish the ExecPlan outcomes. The Stop hook performs final verification and moves passing active plans into `completed/`.

## Boundaries

- Keep `AGENTS.md` routing-only.
- Do not create Product Specs or Design Docs for speculative behavior.
- Put ordinary future ideas nowhere; record only concrete deferred risk in the tech-debt tracker when that tracker exists.
- Preserve human-authored text outside `codex-forge:managed` blocks.
- If a real credential, destructive-action, identity, or instruction-conflict blocker remains, record it in the active plan and report it; do not fake completion.

The deterministic manager is at `scripts/forge.py`. Run it directly only for plugin development or recovery; normal users rely on hooks.

Use `$codex-forge-init` when the user explicitly wants to initialize the current repository's Harness documentation immediately.
