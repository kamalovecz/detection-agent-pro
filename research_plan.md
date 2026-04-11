# Research Plan: research_plan.md

## Phase 0: Environment Setup

**Toolchain Detection:**

- 在执行任何训练、验证、分析和论文导出之前，先检查 `python --version`、`pip --version` 与 `typst --version` 是否可用。
- 检查深度学习核心依赖是否可导入，包括 `torch`、`torchvision`、`ultralytics`、`opencv-python`、`numpy`、`pandas`、`matplotlib` 与 `seaborn`。
- 如需 GPU 训练或部署，请记录 `torch.cuda.is_available()`、CUDA 版本、GPU 型号及显存信息；若存在 `nvidia-smi`，将其输出写入 `logs/phase0_environment_check.json`。
- 如需导出或部署模型，请额外检查 `onnx`、`onnxruntime`，以及用户指定平台所需的工具链。
- 若任何关键工具或依赖缺失，必须停止后续阶段，并在终端与 `logs/phase0_environment_check.json` 中明确列出缺失项。

## Phase 1: Implementation & Verification

**Objective:**  
围绕“面向真实工业场景的金属表面缺陷实时检测”这一目标，对 YOLOv8 进行面向小缺陷、复杂纹理背景和部署约束的改进，并完成在 NEU DET、GC10 DET 与自建 `port_defect` 数据集上的训练、验证与迁移微调准备。

**Model Implementation Guide:**

- 将 `src/` 视为模型与实验脚本的主目录，优先保留已有 YOLOv8 项目结构，只做增量修改，不要重写整个工程。
- 若项目中尚未完成改进模块，请优先围绕以下三个方向选择最小可实现方案：
  1. 浅层边缘 / 结构增强，用于增强裂纹、划痕、斑块等缺陷的初始感知。
  2. 高分辨率小目标敏感分支增强，用于改善微小缺陷的表征能力。
  3. Neck 或特征融合优化，在尽量不显著增加复杂度的前提下提升多尺度表达。
- 明确区分三类训练设置：
  1. `NEU DET` 单独训练或基线验证。
  2. `GC10 DET` 单独训练或基线验证。
  3. 公开数据集预训练后迁移到 `port_defect` 的微调实验。
- 训练与验证阶段至少产出以下内容：
  - `weights/best.pt`
  - `logs/train.log`
  - `logs/val.log`
  - `analysis/metrics_summary.csv`
  - `analysis/experiment_manifest.json`
- 若已有导出脚本，请补充 ONNX 或部署前模型导出记录，并将关键信息写入 `logs/export.log`。

**Verification Criteria:**

- 确认训练脚本、验证脚本、推理脚本可以正常运行，并保留命令、配置与权重来源。
- 至少报告 `Precision`、`Recall`、`mAP@0.5` 与 `mAP@0.5:0.95`。
- 如环境允许，进一步报告 `Params`、`FLOPs`、模型大小、单张推理延迟与 `FPS`。
- 若进行迁移学习，必须明确记录预训练权重来源、冻结 / 解冻策略、微调数据划分和训练轮次。
- 如出现训练失败、指标异常波动或数据路径错误，必须先修复本阶段问题，不得带病进入后续分析阶段。

**Expected Logs:**

- `logs/train.log` 中应包含数据集名称、配置文件、模型配置、输入尺寸、batch size、epoch、学习率与权重初始化方式。
- `logs/val.log` 中应包含每个数据集上的 Precision、Recall、mAP@0.5、mAP@0.5:0.95 以及可用时的 FPS / latency。
- `analysis/experiment_manifest.json` 中应记录实验编号、模型改动说明、训练顺序、迁移设置和导出产物路径。

## Phase 2: Data Analysis & Comparison

**Analysis Script Requirements:**

- 使用 Python 读取训练日志、验证日志和实验记录，统一汇总 NEU DET、GC10 DET 与 `port_defect` 的结果。
- 生成基线 YOLOv8 与改进模型的对比表，至少涵盖 `Precision`、`Recall`、`mAP@0.5`、`mAP@0.5:0.95`。
- 生成消融实验表，分别统计浅层增强模块、高分辨率增强模块、融合优化模块等改动的独立贡献与联合贡献。
- 生成跨数据集迁移实验对比，重点分析“公开数据集预训练 -> port_defect 微调”的效果变化。
- 若已有部署测试结果，汇总 `Params`、`FLOPs`、模型大小、延迟与 FPS，并形成精度-复杂度对照表。
- 将整理后的核心表格写入：
  - `analysis/main_results.csv`
  - `analysis/ablation_results.csv`
  - `analysis/transfer_results.csv`
  - `analysis/deployment_results.csv`

**Plotting Instructions:**

- 绘制主结果图，展示基线模型与改进模型在三个数据集上的检测性能差异。
- 绘制消融实验图，突出每个改进模块对核心指标的影响。
- 绘制迁移学习对比图，强调公开数据集预训练对 `port_defect` 的增益。
- 绘制部署对比图，展示精度、参数量、FLOPs 与 FPS 或延迟之间的平衡关系。
- 如存在典型误检 / 漏检案例，输出示例图到 `plots/failure_cases/` 并在分析脚本中生成简要说明。
- 最终至少输出以下图表文件：
  - `plots/main_results.png`
  - `plots/ablation_results.png`
  - `plots/transfer_results.png`
  - `plots/deployment_results.png`

**Expected Metrics:**

- 重点分析改进方法在小缺陷、低对比度缺陷和高纹理背景缺陷上的检测收益。
- 重点分析不同数据集之间的泛化差异，以及 `port_defect` 上的真实场景适配能力。
- 重点分析精度与复杂度、实时性之间的平衡，而不是单纯追求单一指标最高值。

## Phase 3: Paper Framework

**Results Structure:**

- 论文标题建议围绕“改进 YOLOv8 + 金属表面缺陷检测 + 跨数据集验证 + 工业部署评估”展开。
- 摘要应交代四类核心问题：复杂纹理干扰、小缺陷检测难、跨数据集域差异、实时部署约束。
- 引言末尾贡献建议按以下顺序组织：
  1. 提出面向工业场景的改进 YOLOv8 缺陷检测框架。
  2. 引入轻量化细节增强与小目标敏感特征建模策略。
  3. 构建 NEU DET、GC10 DET 与 `port_defect` 的跨数据集实验与部署验证闭环。
- 方法部分应包含：
  - 基线 YOLOv8 结构概述
  - 改进模块设计
  - 迁移学习设置
  - 损失与训练策略
- 实验部分应包含：
  - 数据集介绍
  - 实验设置
  - 主结果比较
  - 消融实验
  - 迁移学习与部署评估
- 论文草稿生成阶段需要优先引用：
  - `analysis/main_results.csv`
  - `analysis/ablation_results.csv`
  - `analysis/transfer_results.csv`
  - `analysis/deployment_results.csv`
  - `plots/main_results.png`
  - `plots/ablation_results.png`
  - `plots/transfer_results.png`
  - `plots/deployment_results.png`

**Discussion Focus:**

- 讨论浅层边缘增强为何有助于提升裂纹、划痕、斑块等缺陷的检测稳定性。
- 讨论高分辨率分支增强为何能够改善小尺度与弱纹理缺陷的特征表达。
- 讨论公开数据集预训练对自建 `port_defect` 微调的作用及其局限。
- 讨论精度、复杂度与部署时延之间的折中，并说明模型真实工业落地的可行性。
