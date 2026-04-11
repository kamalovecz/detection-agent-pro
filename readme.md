# FluidAgent Pro

FluidAgent Pro 是一套面向论文与实验闭环的本地研究流程控制器，当前版本主要服务于“改进 YOLOv8 做金属表面缺陷检测论文”的个人研究工作流。

## 研究主线

这套项目当前默认适配下面这类课题：

- 金属表面缺陷检测
- 改进 YOLOv8
- NEU DET、GC10 DET 与自建 `port_defect`
- 公开数据集预训练 + 自建数据迁移微调
- 消融实验、跨数据集验证与部署评估
- Gemini 生成论文草稿，Codex 做 Typst 修订与导出

## 工作流

系统按固定状态机运行：

1. `Phase 0` 环境检查
2. `Phase 1` 模型实现 / 训练 / 验证
3. `Phase 2` 数据分析 / 图表 / 对比实验
4. `Phase 3` 论文草稿生成与模板导出

每个阶段都可以插入人工审核，确保不会在实验有问题时直接进入论文写作。

## 推荐工作区结构

```text
workspace/
├─ fluid_agent_pro.py
├─ research_plan.md
├─ metadata.json
├─ references.bib
├─ src/
├─ configs/
├─ weights/
├─ analysis/
├─ logs/
├─ plots/
└─ paper-template/
```

## 快速开始

```bash
pip install -e .
fluid-agent-pro --workspace /path/to/workspace
```

如果需要 GUI：

```bash
pip install -e ".[gui]"
fluid-agent-pro-gui
```

## 关键输入

- `research_plan.md`：驱动整套流程的阶段说明
- `metadata.json`：论文标题、作者、关键词等元数据
- `src/`：你的 YOLOv8 与实验代码
- `analysis/`、`plots/`：实验统计与论文图表

## 当前建议的论文主线

推荐围绕以下方向组织论文：

**面向真实工业场景的金属表面缺陷实时检测方法研究：基于改进 YOLOv8 的跨数据集建模与部署优化**

## 说明

当前模板导出仍保留 `clear-iclr` 这一 Typst 模板目录名，以兼容现有控制器逻辑；但整体提示词、研究计划和项目说明已经改为以工业缺陷检测研究为中心。
