---
name: codex-forge-init
description: Explicitly initialize or repair Codex Forge Harness documentation in the current repository. Use only when the user asks to initialize, bootstrap, set up, or regenerate the repository's initial Agent-first documentation and knowledge routes.
---

# Initialize Codex Forge

Resolve this skill's directory from the loaded `SKILL.md` path, then run:

```bash
python3 <skill-directory>/../codex-forge/scripts/forge.py bootstrap --repo "$PWD"
python3 <skill-directory>/../codex-forge/scripts/forge.py check --repo "$PWD"
```

Replace `<skill-directory>` with the absolute directory containing this file. Run both commands from the current project directory.

Report the initialized paths and validation result. Preserve existing human-authored content outside `codex-forge:managed` blocks. Do not create a Product Spec or ExecPlan solely for initialization.
