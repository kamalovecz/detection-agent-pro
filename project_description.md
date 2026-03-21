# FluidAgent Pro 项目简介

FluidAgent Pro 是一个面向 CFD 科研流程的本地自动化控制器，用来把“研究方案 -> 代码实现 -> 结果验证 -> 数据分析 -> 论文生成”串成可恢复、可回退的工作流。

## 它能做什么

- 解析 `research_plan.md`，把研究方案切成多个阶段。
- 调用 Codex 完成代码实现、验证修复、数据分析和论文模板化整理。
- 调用 Gemini 生成论文草稿。
- 在关键节点暂停，等待人工审查后再继续。
- 支持从 Phase 2 回退到 Phase 1，或者从论文阶段回退到分析阶段。

## 适用场景

- 你已经有一篇论文算法，希望把它接入自己的 CFD 求解器。
- 你需要自动运行验证、画图、生成论文草稿和最终 PDF。
- 你希望整个流程能在命令行或桌面 GUI 中持续运行，并可中途恢复。

## 核心输入

- `fluid_agent_pro.py`
- `research_plan.md`
- `paper-template/clear-iclr/`
- 可选的 `metadata.json`

## 主要特点

- CLI 和 GUI 共用同一套控制器。
- 支持 Phase 0 环境检查，先确认工具可用再启动任务。
- 支持 `clear` / `clear-hard` 清理工作区。
- 支持 `Y / N / P1 / P2 / C / Q` 这类审查交互。
- 适合在 Linux 或 WSL 环境下运行。

