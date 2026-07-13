# Architecture

Codex Forge is an installable Codex plugin with three layers:

1. `hooks/hooks.json` attaches the automatic lifecycle to Codex sessions and turns.
2. `skills/codex-forge/SKILL.md` supplies semantic workflow rules to the agent.
3. `skills/codex-forge/scripts/forge.py` owns deterministic repository writes, task classification, verification, and plan archival.

Dependency direction is one-way: Hooks call the standard-library manager; the Skill may route Codex to the manager for recovery; the manager never calls Codex internals. For planned work, the hook stores task context without creating a file; after analyzing intent, the model supplies a semantic title to the manager's `start-plan` command, which creates the final ExecPlan atomically. Target repositories remain the source of durable knowledge, while transient per-session state lives in `PLUGIN_DATA`.

Core concepts are task assessment, artifact routing, active-to-completed ExecPlan lifecycle, managed documentation blocks, deterministic generated knowledge, and verification-gated completion.

<!-- codex-forge:managed:start -->
## Automatically observed repository facts

- Detected stack: Python
- Top-level directories: `.codex-plugin/`, `.sentrux/`, `docs/`, `hooks/`, `skills/`, `tests/`
- Generated repository and verification knowledge lives under `docs/generated/`.
<!-- codex-forge:managed:end -->
