---
name: code-to-codex-planner
description: |
  把计算机视觉与材料缺陷检测研究任务转成可交给 Codex 的实现计划。Use when the user wants repo changes, experiment scripts, plotting automation, config updates, ablation implementations, data processing steps, or bounded coding tickets derived from a research idea or paper revision plan.
---

# Code to Codex Planner

优先读取：

- `../references/codex-handoff-guide.md`
- `../references/domain-constraints.md`
- `../references/unified-output-template.md`
- `../references/bilingual-switch.md`
- `../references/evidence-and-citation-policy.md`

## 核心任务

把科研建议翻译成“小步可验收、边界清晰、能直接执行”的 Codex 实现任务。

## 工作流程

1. 识别目标对象：模型模块、训练脚本、数据处理、评估脚本、分析脚本、图表、论文文件。
2. 把模糊目标压缩成最小可执行改动，不直接给大重构。
3. 为每个任务补足：
   - 目的
   - 涉及文件或目录
   - 输入与输出
   - 最快验证方式
4. 如果有依赖顺序，先列出阻塞项，再列执行顺序。

## 优先输出的任务形态

- 新增配置而不是覆盖旧配置
- 新增分析脚本而不是手工处理
- 最小实验验证而不是直接全量训练
- 明确输入输出路径，而不是“自行查找”

## 风险控制

- 不输出无法验收的空泛任务。
- 不假设仓库已有不存在的文件或接口。
- 如果用户没有给仓库上下文，要把缺失信息写清楚。
- 对研究代码优先建议 smoke test、shape check 或小样本验证。

始终按 `../references/unified-output-template.md` 输出。
