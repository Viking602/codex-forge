---
status: completed
task_class: large
created: 2026-07-11
---

# Codex Forge 实施计划

## Purpose / Big Picture

Deliver the requested task while keeping repository knowledge and verification synchronized.

## Progress

- [x] Implementation complete
- [x] Verification passed
- [x] Durable knowledge reconciled

<!-- codex-forge:auto-progress:start -->
Implemented the Phase 1 lifecycle, added durable architecture/design/product knowledge, and reached 7 passing regression tests.
<!-- codex-forge:auto-progress:end -->

## Surprises & Discoveries

- The current official Codex lifecycle supports plugin-bundled `SessionStart`, `UserPromptSubmit`, `PostToolUse`, and `Stop` command hooks.
- Plugin hooks require one-time user trust review; after trust, the lifecycle is automatic.
- The bundled plugin validator currently requires PyYAML in its execution environment even though the plugin itself has no runtime dependency.

## Decision Log

- Codex Forge classified this as `large` because: high-risk or durable system boundary; multiple explicit file paths; large task description.
- Phase 1 uses one Python standard-library manager instead of an MCP server or persistent service.
- Generated knowledge is content-hashed and excludes `docs/generated/` to avoid self-referential churn.
- Product and design knowledge remain model-maintained; only facts that can be derived deterministically are script-generated.
- Deterministic knowledge generation was split from lifecycle orchestration to keep both source files below the Sentrux God File threshold without introducing a cycle.

## Outcomes & Retrospective

- Completed and archived after automatic verification.
- Final governance pass reduced the highest function complexity from Radon D (22) to B (10); Sentrux reports no complex-function regression.

## Context and Orientation

Task: # Codex Forge 实施计划 > 面向 Codex 的自动 Harness 知识库插件 ## 1. 项目目标 Codex Forge 用于自动构建和维护一套面向 Codex 的 Harness 知识库。 插件不要求用户手动创建 Plan、Spec、Design 或其他工程文档，而是根据当前任务的复杂度、风险、影响范围和长期价值，自动决定是否创建、更新、归档或合并相关 Artifact。 最终目标是让 Codex 随着仓库演进持续积累知识，减少每次任务重新理解代码库的成本。 ## 2. 核心原则 ### 2.1 Repository is the Knowledge Base 长期有效的工程知识必须保存在仓库中。 Prompt 只描述当前任务，不承载长期架构、规范、产品行为和验证知识。 ### 2.2 Harness First 插件维护的核心不是 Prompt，而是完整 Harness，包括： - 仓库知识 - 架构边界 - 产品规格 - 执行计划 - 设计文档 - 自动生成知识 - 外部参考资料 - 验证规则 - 技术债务 - 文档新鲜度 ### 2.3 Automatic 

## Plan of Work

1. Inspect the routed repository knowledge and affected implementation.
2. Make the smallest complete change.
3. Verify behavior and reconcile durable knowledge.

## Concrete Steps

- Follow repository-native implementation and verification paths.

## Validation and Acceptance

`python3 -m unittest discover -s tests` exited 0.

```text
.......
----------------------------------------------------------------------
Ran 7 tests in 0.252s

OK
```

## Idempotence and Recovery

- Re-run repository-native checks; keep this plan active while blocked or failing.

## Artifacts and Notes

- Generated documents are refreshed by Codex Forge.

## Interfaces and Dependencies

- No new dependency is assumed by the plan.
