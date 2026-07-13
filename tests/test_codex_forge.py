import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "skills" / "codex-forge" / "scripts" / "forge.py"
SPEC = importlib.util.spec_from_file_location("codex_forge", MODULE_PATH)
forge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = forge
SPEC.loader.exec_module(forge)


class CodexForgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        self.state = Path(self.temp.name) / "state"
        self.env = patch.dict(os.environ, {"CODEX_FORGE_STATE_DIR": str(self.state)}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def hook(self, event, **values):
        payload = {"hook_event_name": event, "cwd": str(self.root), "session_id": "test", **values}
        output = io.StringIO()
        with redirect_stdout(output):
            forge.handle_hook(payload)
        return json.loads(output.getvalue())

    def start_plan(self, title="交付验证流程"):
        output = io.StringIO()
        with redirect_stdout(output):
            result = forge.main(
                ["start-plan", "--repo", str(self.root), "--session-id", "test", "--title", title]
            )
        self.assertEqual(0, result)
        return next((self.root / "docs/exec-plans/active").glob("*.md"))

    def test_classifies_tasks_without_unneeded_plans(self):
        self.assertEqual("lightweight", forge.assess("修正文档错别字").level)
        self.assertEqual("standard", forge.assess("实现一个普通功能并补测试").level)
        self.assertEqual("standard", forge.assess("增加一个初始化的指令").level)
        self.assertEqual("large", forge.assess("迁移数据库并修改公共 API").level)

    def test_bootstrap_command_initializes_current_repository(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = forge.main(["bootstrap", "--repo", str(self.root)])
        self.assertEqual(0, result)
        self.assertIn("Bootstrapped", output.getvalue())
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertTrue((self.root / "ARCHITECTURE.md").exists())
        self.assertTrue((self.root / "docs/generated/repository-map.md").exists())

    def test_bootstrap_is_deterministic_and_preserves_human_text(self):
        (self.root / "AGENTS.md").write_text("# Team Rules\n\nKeep this.\n", encoding="utf-8")
        forge.bootstrap(self.root)
        first = (self.root / "docs/generated/repository-map.md").read_text(encoding="utf-8")
        forge.refresh(self.root)
        second = (self.root / "docs/generated/repository-map.md").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertIn("Keep this.", (self.root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertTrue((self.root / "docs/design-docs/index.md").exists())
        self.assertTrue((self.root / "docs/product-specs/index.md").exists())

    def test_standard_task_creates_and_archives_exec_plan(self):
        result = self.hook("UserPromptSubmit", prompt="实现一个普通功能并补测试")
        active = list((self.root / "docs/exec-plans/active").glob("*.md"))
        self.assertEqual([], active)
        self.assertIn("analyze the concrete task intent", result["hookSpecificOutput"]["additionalContext"])
        self.assertIn("start-plan", result["hookSpecificOutput"]["additionalContext"])
        with self.assertRaises(ValueError):
            forge.start_plan(self.root, "test", "<MODEL_GENERATED_TITLE>")
        self.assertEqual([], list((self.root / "docs/exec-plans/active").glob("*.md")))
        plan = self.start_plan()
        self.assertEqual("交付验证流程.md", plan.name[11:])
        self.assertIn("# 交付验证流程", plan.read_text(encoding="utf-8"))
        result = self.hook("Stop", stop_hook_active=False, last_assistant_message="已完成")
        self.assertIn("Archived", result["systemMessage"])
        self.assertEqual([], list((self.root / "docs/exec-plans/active").glob("*.md")))
        completed = list((self.root / "docs/exec-plans/completed").glob("*.md"))
        self.assertEqual(1, len(completed))
        self.assertEqual("交付验证流程.md", completed[0].name[11:])
        self.assertIn("status: completed", completed[0].read_text(encoding="utf-8"))

    def test_stop_requires_intent_analysis_and_plan_creation(self):
        self.hook("UserPromptSubmit", prompt="实现一个普通功能并补测试")
        result = self.hook("Stop", stop_hook_active=False, last_assistant_message="已完成")
        self.assertEqual("block", result["decision"])
        self.assertIn("analyze the concrete task intent", result["reason"])
        self.assertEqual([], list((self.root / "docs/exec-plans/active").glob("*.md")))

    def test_lightweight_task_never_creates_plan(self):
        self.hook("UserPromptSubmit", prompt="修正文档错别字")
        self.assertEqual([], list((self.root / "docs/exec-plans/active").glob("*.md")))
        result = self.hook("Stop", stop_hook_active=False, last_assistant_message="完成")
        self.assertIn("no ExecPlan", result["systemMessage"])

    def test_multi_file_edit_escalates_lightweight_task(self):
        self.hook("UserPromptSubmit", prompt="小修正")
        patch_text = "*** Add File: one.txt\n*** Add File: two.txt\n"
        result = self.hook("PostToolUse", tool_name="apply_patch", tool_input={"command": patch_text})
        plans = list((self.root / "docs/exec-plans/active").glob("*.md"))
        self.assertEqual([], plans)
        self.assertIn("start-plan", result["systemMessage"])
        self.assertIn("task_class: standard", self.start_plan().read_text(encoding="utf-8"))

    def test_failed_verification_keeps_plan_active(self):
        (self.root / "tests").mkdir()
        (self.root / "tests/test_failure.py").write_text(
            "import unittest\nclass Failure(unittest.TestCase):\n def test_no(self): self.fail('expected')\n",
            encoding="utf-8",
        )
        self.hook("UserPromptSubmit", prompt="实现一个普通功能并补测试")
        self.start_plan()
        result = self.hook("Stop", stop_hook_active=False, last_assistant_message="已完成")
        self.assertEqual("block", result["decision"])
        self.assertEqual(1, len(list((self.root / "docs/exec-plans/active").glob("*.md"))))
        self.assertEqual([], list((self.root / "docs/exec-plans/completed").glob("*.md")))

    def test_detects_stale_links(self):
        forge.bootstrap(self.root)
        (self.root / "BROKEN.md").write_text("[missing](./not-there.md)\n", encoding="utf-8")
        forge.refresh(self.root)
        self.assertTrue(any("broken link" in issue for issue in forge.check_stale(self.root)))


if __name__ == "__main__":
    unittest.main()
