---
status: implemented
last_verified: 2026-07-13
---

# Automatic Harness Lifecycle

## Lifecycle

`SessionStart` bootstraps routing and deterministic knowledge. `UserPromptSubmit` classifies the task and stores its context without creating an ExecPlan. For standard or large work, the model first analyzes the concrete intent and generates a semantic title, then invokes `start-plan` to create the final plan. `PostToolUse` refreshes generated knowledge and records mechanical progress. `Stop` runs the detected repository verification and archives a passing plan.

An explicit `$codex-forge-init` invocation runs the same bootstrap and freshness check immediately. It is a user-controlled entrypoint, not a second initialization implementation.

## Invariants

- Human text outside `codex-forge:managed` blocks is preserved.
- `docs/generated/` is derived only from repository state.
- Lightweight tasks never create an ExecPlan.
- Standard and large tasks cannot finish until the model has supplied a semantic title and created the ExecPlan.
- Failed verification leaves the plan active and continues the agent turn.
- Reported hard blockers leave the plan active.
- A repeated Stop hook does not create an infinite continuation loop.

## Recovery

All writes use an adjacent temporary file followed by atomic replacement. Bootstrap and refresh operations are idempotent; rerunning them repairs missing managed artifacts without duplicating managed blocks.
