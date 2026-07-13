#!/usr/bin/env python3
"""Zero-dependency lifecycle manager for a repository Harness knowledge base."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from knowledge import atomic_write, bootstrap, check_stale, refresh, verification_commands


RISK_TERMS = re.compile(
    r"架构|新模块|大规模|迁移|数据库|schema|认证|授权|安全|兼容性|公共\s*api|public\s+api|"
    r"architecture|new\s+module|migration|database|auth|security|breaking\s+change",
    re.I,
)
STANDARD_TERMS = re.compile(
    r"新增|增加|功能|重构|多文件|分阶段|实现|feature|refactor|multi[- ]file|implement|end[- ]to[- ]end",
    re.I,
)
BLOCKED_TERMS = re.compile(r"\bblocked\b|阻塞|缺少凭据|需要用户|无法继续", re.I)


@dataclass(frozen=True)
class Assessment:
    level: str
    reasons: tuple[str, ...]


def git_root(cwd: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def repository_root(cwd: str | Path) -> Path | None:
    current = Path(cwd).expanduser().resolve()
    root = git_root(current)
    if root:
        return root
    markers = (".git", ".codex-plugin", "pyproject.toml", "package.json", "go.mod", "Cargo.toml", "AGENTS.md")
    return current if any((current / marker).exists() for marker in markers) else None


def assess(prompt: str) -> Assessment:
    reasons: list[str] = []
    if RISK_TERMS.search(prompt):
        reasons.append("high-risk or durable system boundary")
    mentioned_paths = set(re.findall(r"(?:[\w.-]+/)+[\w.-]+", prompt))
    if len(mentioned_paths) > 1:
        reasons.append("multiple explicit file paths")
    if len(prompt) > 1200:
        reasons.append("large task description")
    if reasons:
        return Assessment("large", tuple(reasons))
    if STANDARD_TERMS.search(prompt) or len(mentioned_paths) == 1 or len(prompt) > 350:
        return Assessment("standard", ("multi-step feature or implementation work",))
    return Assessment("lightweight", ("bounded low-risk change",))


def normalize_plan_title(value: str) -> tuple[str, str]:
    title = " ".join(value.strip("# -*\t").split())
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", title.lower()).strip("-")
    if not title or title == "<MODEL_GENERATED_TITLE>" or not slug or len(title) > 80:
        raise ValueError("plan title must be a model-generated semantic title of 1-80 filename-safe characters")
    return title, slug


def plan_template(prompt: str, assessment: Assessment, title: str) -> str:
    summary = " ".join(prompt.split())[:500]
    reasons = "; ".join(assessment.reasons)
    return f"""---
status: active
task_class: {assessment.level}
created: {date.today().isoformat()}
---

# {title}

## Purpose / Big Picture

Deliver the requested task while keeping repository knowledge and verification synchronized.

## Progress

- [ ] Implementation complete
- [ ] Verification passed
- [ ] Durable knowledge reconciled

<!-- codex-forge:auto-progress:start -->
Automatic lifecycle tracking initialized.
<!-- codex-forge:auto-progress:end -->

## Surprises & Discoveries

- None yet.

## Decision Log

- Codex Forge classified this as `{assessment.level}` because: {reasons}.

## Outcomes & Retrospective

- Pending.

## Context and Orientation

Task: {summary}

## Plan of Work

1. Inspect the routed repository knowledge and affected implementation.
2. Make the smallest complete change.
3. Verify behavior and reconcile durable knowledge.

## Concrete Steps

- Follow repository-native implementation and verification paths.

## Validation and Acceptance

- Pending automatic verification.

## Idempotence and Recovery

- Re-run repository-native checks; keep this plan active while blocked or failing.

## Artifacts and Notes

- Generated documents are refreshed by Codex Forge.

## Interfaces and Dependencies

- No new dependency is assumed by the plan.
"""


def ensure_plan(root: Path, prompt: str, assessment: Assessment, title: str) -> Path:
    title, slug = normalize_plan_title(title)
    active = root / "docs" / "exec-plans" / "active"
    active.mkdir(parents=True, exist_ok=True)
    path = active / f"{date.today().isoformat()}-{slug}.md"
    if path.exists():
        raise ValueError(f"an active plan named {path.name} already exists; generate a more specific title")
    atomic_write(path, plan_template(prompt, assessment, title))
    return path


def plan_creation_instruction(root: Path, session_id: str) -> str:
    command = shlex.join(
        [sys.executable, str(Path(__file__).resolve()), "start-plan", "--repo", str(root), "--session-id", session_id, "--title", "<MODEL_GENERATED_TITLE>"]
    )
    return (
        "Before creating any ExecPlan, analyze the concrete task intent and generate a concise semantic plan title. "
        f"Then replace <MODEL_GENERATED_TITLE> and run `{command}`. Do not copy or truncate the current prompt."
    )


def start_plan(root: Path, session_id: str, title: str) -> Path:
    state = load_state(session_id)
    existing = Path(state["plan"]) if state.get("plan") else None
    if existing and existing.exists():
        return existing
    if state.get("root") != str(root) or state.get("level") not in {"standard", "large"}:
        raise ValueError("no pending standard or large task exists for this repository and session")
    assessment = Assessment(state["level"], tuple(state.get("reasons", [])))
    plan = ensure_plan(root, state.get("prompt", ""), assessment, title)
    state["plan"] = str(plan)
    save_state(session_id, state)
    refresh(root)
    return plan


def replace_section_line(path: Path, marker: str, line: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"<!-- codex-forge:{re.escape(marker)}:start -->.*?<!-- codex-forge:{re.escape(marker)}:end -->",
        re.S,
    )
    block = f"<!-- codex-forge:{marker}:start -->\n{line}\n<!-- codex-forge:{marker}:end -->"
    atomic_write(path, pattern.sub(block, text, count=1) if pattern.search(text) else text + "\n" + block)


def record_progress(plan: Path | None, message: str) -> None:
    if plan:
        replace_section_line(plan, "auto-progress", message)


def run_verification(root: Path, timeout: int = 120) -> tuple[bool, str]:
    commands = verification_commands(root)
    if not commands:
        return True, "No deterministic verification command was detected; structural checks passed."
    command = commands[0]
    try:
        result = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return False, f"`{command}` timed out after {timeout}s."
    output = (result.stdout + "\n" + result.stderr).strip()
    tail = "\n".join(output.splitlines()[-12:])
    return result.returncode == 0, f"`{command}` exited {result.returncode}.\n\n```text\n{tail}\n```"


def finish_plan(root: Path, plan: Path | None, verification: str) -> Path | None:
    if not plan or not plan.exists():
        return None
    text = plan.read_text(encoding="utf-8")
    text = text.replace("status: active", "status: completed", 1)
    text = text.replace("- [ ] Implementation complete", "- [x] Implementation complete")
    text = text.replace("- [ ] Verification passed", "- [x] Verification passed")
    text = text.replace("- [ ] Durable knowledge reconciled", "- [x] Durable knowledge reconciled")
    text = re.sub(r"## Outcomes & Retrospective\n\n.*?(?=\n## )", "## Outcomes & Retrospective\n\n- Completed and archived after automatic verification.\n", text, count=1, flags=re.S)
    text = re.sub(r"## Validation and Acceptance\n\n.*?(?=\n## )", f"## Validation and Acceptance\n\n{verification}\n", text, count=1, flags=re.S)
    completed = root / "docs" / "exec-plans" / "completed" / plan.name
    atomic_write(completed, text)
    plan.unlink()
    return completed


def state_dir() -> Path:
    path = Path(os.environ.get("CODEX_FORGE_STATE_DIR") or os.environ.get("PLUGIN_DATA") or Path.home() / ".codex-forge")
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^0-9A-Za-z_.-]", "_", session_id or "default")
    return state_dir() / f"{safe}.json"


def save_state(session_id: str, payload: dict[str, Any]) -> None:
    atomic_write(state_path(session_id), json.dumps(payload, ensure_ascii=False, indent=2))


def load_state(session_id: str) -> dict[str, Any]:
    path = state_path(session_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def hook_output(context: str, event: str, **extra: Any) -> None:
    payload: dict[str, Any] = {"continue": True, **extra}
    if context:
        if event in {"SessionStart", "UserPromptSubmit", "SubagentStart"}:
            payload["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": context}
        else:
            payload["systemMessage"] = context
    print(json.dumps(payload, ensure_ascii=False))


def on_session_start(root: Path, session_id: str, data: dict[str, Any]) -> int:
    bootstrap(root)
    issues = check_stale(root)
    context = "Read AGENTS.md and ARCHITECTURE.md before repository work. Codex Forge owns docs/generated/."
    if issues:
        context += " Stale knowledge detected: " + "; ".join(issues)
    hook_output(context, "SessionStart")
    return 0


def on_user_prompt(root: Path, session_id: str, data: dict[str, Any]) -> int:
    bootstrap(root)
    prompt = str(data.get("prompt", ""))
    assessment = assess(prompt)
    save_state(
        session_id,
        {
            "root": str(root),
            "level": assessment.level,
            "reasons": list(assessment.reasons),
            "prompt": prompt,
            "plan": "",
            "touched": [],
        },
    )
    context = f"Codex Forge classified this task as {assessment.level}: {'; '.join(assessment.reasons)}. "
    context += plan_creation_instruction(root, session_id) if assessment.level != "lightweight" else "Do not create an ExecPlan or Product Spec for this task."
    context += " Reconcile durable knowledge before the final response; never hand-edit docs/generated/."
    hook_output(context, "UserPromptSubmit")
    return 0


def on_post_tool(root: Path, session_id: str, data: dict[str, Any]) -> int:
    state = load_state(session_id)
    plan = Path(state["plan"]) if state.get("plan") and Path(state["plan"]).exists() else None
    command = str((data.get("tool_input") or {}).get("command", ""))
    touched = set(state.get("touched", []))
    touched.update(re.findall(r"\*\*\* (?:Add|Update|Delete) File: ([^\n]+)", command))
    state["touched"] = sorted(touched)
    if state.get("level") == "lightweight" and len(touched) > 1:
        assessment = Assessment("standard", ("task expanded beyond one file",))
        state.update(level="standard", reasons=list(assessment.reasons))
    record_progress(plan, f"Automatic activity: `{data.get('tool_name', 'tool')}` completed; {len(touched)} changed file(s) observed.")
    save_state(session_id, state)
    refresh(root)
    hook_output(plan_creation_instruction(root, session_id) if state.get("level") != "lightweight" and not plan else "", "PostToolUse")
    return 0


def on_stop(root: Path, session_id: str, data: dict[str, Any]) -> int:
    if data.get("stop_hook_active"):
        hook_output("", "Stop")
        return 0
    state = load_state(session_id)
    plan = Path(state["plan"]) if state.get("plan") and Path(state["plan"]).exists() else None
    if BLOCKED_TERMS.search(str(data.get("last_assistant_message", ""))):
        record_progress(plan, "Paused at a reported hard blocker; plan remains active.")
        refresh(root)
        hook_output("The active plan remains unarchived because the turn reported a blocker.", "Stop")
        return 0
    if state.get("level") in {"standard", "large"} and not plan:
        refresh(root)
        print(json.dumps({"decision": "block", "reason": plan_creation_instruction(root, session_id)}, ensure_ascii=False))
        return 0
    refresh(root)
    passed, evidence = run_verification(root)
    if not passed:
        record_progress(plan, "Automatic verification failed; repair is required before archival.")
        print(json.dumps({"decision": "block", "reason": f"Codex Forge verification failed. Fix the failure and rerun verification.\n\n{evidence}"}, ensure_ascii=False))
        return 0
    archived = finish_plan(root, plan, evidence)
    refresh(root)
    issues = check_stale(root)
    message = f"Verification passed. Archived {archived.relative_to(root)}." if archived else "Verification passed; no ExecPlan was required."
    if issues:
        message += " Remaining stale knowledge: " + "; ".join(issues)
    hook_output(message, "Stop")
    return 0


HOOK_HANDLERS = {
    "SessionStart": on_session_start,
    "UserPromptSubmit": on_user_prompt,
    "PostToolUse": on_post_tool,
    "Stop": on_stop,
}


def handle_hook(data: dict[str, Any]) -> int:
    event = str(data.get("hook_event_name", ""))
    root = repository_root(data.get("cwd") or Path.cwd())
    if root is None:
        hook_output("Codex Forge found no repository marker; no Harness files were written.", event or "SessionStart")
        return 0
    handler = HOOK_HANDLERS.get(event)
    if handler:
        return handler(root, str(data.get("session_id", "default")), data)
    hook_output("", event or "SessionStart")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("bootstrap", "refresh", "assess", "check", "complete", "start-plan", "hook"))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--title", default="")
    args = parser.parse_args(argv)
    if args.command == "hook":
        try:
            return handle_hook(json.load(sys.stdin))
        except (json.JSONDecodeError, TypeError) as error:
            print(json.dumps({"continue": True, "systemMessage": f"Codex Forge ignored invalid hook input: {error}"}))
            return 0
    root = Path(args.repo).expanduser().resolve()
    if args.command == "bootstrap":
        changed = bootstrap(root)
        print(f"Bootstrapped {root}; {len(changed)} file(s) changed.")
    elif args.command == "refresh":
        changed = refresh(root)
        print(f"Refreshed {root}; {len(changed)} file(s) changed.")
    elif args.command == "assess":
        print(json.dumps(asdict(assess(args.prompt)), ensure_ascii=False))
    elif args.command == "start-plan":
        try:
            plan = start_plan(root, args.session_id, args.title)
        except ValueError as error:
            parser.error(str(error))
        print(f"Created {plan.relative_to(root)}.")
    elif args.command == "check":
        issues = check_stale(root)
        if issues:
            print("\n".join(issues))
            return 1
        print("Harness knowledge is current.")
    elif args.command == "complete":
        refresh(root)
        passed, evidence = run_verification(root)
        print(evidence)
        return 0 if passed else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
