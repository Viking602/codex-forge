# Codex Forge

Codex Forge is a Codex plugin that keeps a repository's engineering knowledge current while Codex works. It classifies each task, creates an execution plan when the scope warrants one, refreshes deterministic repository maps, runs the repository's verification command, and archives completed plans.

The plugin is implemented with Python's standard library and writes its durable output into the repository it is managing.

## What it manages

| Lifecycle event | Action |
| --- | --- |
| `SessionStart` | Creates or repairs the repository's Harness entrypoints and generated maps. |
| `UserPromptSubmit` | Classifies the task and stores its context. For standard and large work, the model analyzes intent and supplies the title before the active ExecPlan is created. |
| `PostToolUse` | Refreshes generated knowledge and records mechanical progress after repository writes. |
| `Stop` | Runs one detected repository-native verification command and archives a passing ExecPlan. |

Codex Forge maintains these repository paths:

- `AGENTS.md` for short routing instructions
- `ARCHITECTURE.md` for durable boundaries and architecture facts
- `docs/design-docs/` for design decisions
- `docs/product-specs/` for implemented product behavior
- `docs/exec-plans/` for active and completed execution plans
- `docs/generated/` for deterministic repository and verification maps

Human-authored text outside `codex-forge:managed` blocks is preserved. Files under `docs/generated/` are derived output and should not be edited by hand.

## Requirements

- Codex with plugin support
- Python 3.10 or newer available as `python3`
- Git for repository-root detection

## Install for local use

Clone the plugin:

```bash
git clone https://github.com/Viking602/codex-forge.git
cd codex-forge
```

Use the built-in `plugin-creator` skill in Codex to add the checked-out folder to your personal marketplace without changing the plugin:

```text
$plugin-creator Add this existing plugin to my personal marketplace without modifying it: /absolute/path/to/codex-forge
```

Restart Codex, install **Codex Forge** from the local plugin directory, review and trust its lifecycle hooks, then start a new task. Codex loads installed plugin components in new tasks.

For the underlying marketplace format and other installation scopes, see the [official Codex plugin documentation](https://learn.chatgpt.com/docs/build-plugins#install-a-local-plugin-manually).

## Use

Once installed and enabled, normal repository work uses the automatic lifecycle. No planning or documentation command is required.

To initialize or repair the current repository immediately, invoke:

```text
$codex-forge-init
```

The initialization skill runs the same deterministic bootstrap and freshness checks used by the hooks.

## Task classes

- **Lightweight:** bounded, low-risk work; no ExecPlan is created.
- **Standard:** multi-step implementation work; one active ExecPlan is maintained.
- **Large:** work involving durable boundaries such as architecture, migrations, databases, authentication, security, or public APIs; one active ExecPlan is maintained and durable knowledge is reconciled.

For standard and large tasks, Codex Forge does not derive a filename from the prompt. The model first identifies the concrete intent and generates a semantic title, then the lifecycle manager creates the final dated plan file.

If a lightweight task expands across multiple files, Codex Forge promotes it to standard work.

## Development

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Run the lifecycle manager directly for plugin development or recovery:

```bash
python3 skills/codex-forge/scripts/forge.py bootstrap --repo /path/to/repository
python3 skills/codex-forge/scripts/forge.py check --repo /path/to/repository
python3 skills/codex-forge/scripts/forge.py assess --prompt "implement a feature"
```

The manager has no third-party runtime dependencies.

## Repository layout

```text
.codex-plugin/plugin.json       Plugin manifest
hooks/hooks.json                Codex lifecycle hook definitions
skills/codex-forge/             Automatic workflow rules and manager
skills/codex-forge-init/        Explicit initialization entrypoint
docs/                           Architecture, design, product, and plan records
tests/                          Standard-library unit tests
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the dependency boundaries and [docs/product-specs/automatic-harness-management.md](docs/product-specs/automatic-harness-management.md) for implemented behavior.
