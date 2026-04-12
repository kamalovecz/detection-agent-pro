# Candidate References for `paper_pass0412.pdf`

> 目标：基于 [citation_needed.md](/D:/Code/paper_pass_skill/fluid-agent-pro/origin_paper/citation_needed.md) 整理一版“可优先使用的候选参考文献清单”。  
> 原则：只把“已核实”的条目标记为可直接入 Bib；对暂未完全核实的条目单独列为“待核后再用”。

## 1. 使用建议

- 先补“方法名、数据集名、工具链名、经典检测论文”的硬引用，再补综述与场景文献。
- `YOLOv8` 当前更稳妥的引用方式是使用 `Ultralytics YOLO` 的 Zenodo/GitHub 记录，而不是引用不明确的非官方二手论文。
- `NEU-DET` 更接近“公开数据库 / 数据集网站”引用，而不是正式会议论文。
- 对 `Style Adaptation Module`、`SCRL-EMD` 这类你文中提到但当前元数据不完整的条目，先不要直接塞进正文，等 DOI/作者/期刊页核实后再入 `references.bib`。

## 2. 已核实，可直接使用

### 2.1 框架、数据集、综述

| BibKey | 条目 | 建议用途 | 状态 |
|---|---|---|---|
| `jocher2024ultralytics` | Jocher et al., *Ultralytics YOLO*, Zenodo, 2024 | 作为 `YOLOv8` 基线实现来源 | 已核实 |
| `song2013neudet` | Song and Yan, *NEU Surface Defect Database*, 2013 | 作为 `NEU-DET` 数据集来源 | 已核实 |
| `lv2020gc10det` | Lv et al., *Deep Metallic Surface Defect Detection: The New Benchmark and Detection Network*, Sensors, 2020 | 作为 `GC10-DET` 数据集来源 | 已核实 |
| `fang2020metalreview` | Fang et al., *Research Progress of Automated Visual Surface Defect Detection for Industrial Metal Planar Materials*, Sensors, 2020 | 作为早期工业金属表面缺陷综述 | 已核实 |
| `ameri2024slr` | Ameri et al., *A Systematic Review of Deep Learning Approaches for Surface Defect Detection in Industrial Applications*, EAAI, 2024 | 用于第 2.1 节综述收束 | 已核实 |

### 2.2 轻量化与实时检测

| BibKey | 条目 | 建议用途 | 状态 |
|---|---|---|---|
| `sandler2018mobilenetv2` | Sandler et al., *MobileNetV2*, CVPR 2018 | 支撑移动端轻量化设计范式 | 已核实 |
| `ma2018shufflenetv2` | Ma et al., *ShuffleNet V2*, ECCV 2018 | 支撑“真实速度不只由 FLOPs 决定” | 已核实 |
| `ding2021repvgg` | Ding et al., *RepVGG*, CVPR 2021 | 支撑结构重参数化与规整推理图 | 已核实 |
| `lyu2022rtmdet` | Lyu et al., *RTMDet*, arXiv 2022 | 作为实时检测器与训练策略对比 | 已核实 |
| `chen2023fasternet` | Chen et al., *Run, Don't Walk: Chasing Higher FLOPS for Faster Neural Networks*, CVPR 2023 | 支撑“DWConv / memory access / latency”论证 | 已核实 |

### 2.3 检测损失与样本分配

| BibKey | 条目 | 建议用途 | 状态 |
|---|---|---|---|
| `lin2020focal` | Lin et al., *Focal Loss for Dense Object Detection*, TPAMI, 2020 | 2.3 节困难样本经典基线 | 已核实 |
| `li2020gfl` | Li et al., *Generalized Focal Loss*, NeurIPS 2020 | 支撑质量估计与分布式框回归 | 已核实 |
| `zhang2020atss` | Zhang et al., *ATSS*, CVPR 2020 | 支撑自适应样本选择 | 已核实 |
| `zhang2021varifocalnet` | Zhang et al., *VarifocalNet*, CVPR 2021 | 支撑 IoU-aware dense detector 相关论述 | 已核实 |
| `feng2021tood` | Feng et al., *TOOD*, ICCV 2021 | 支撑 task-aligned head / task-aligned loss | 已核实 |
| `li2021gflv2` | Li et al., *Generalized Focal Loss V2*, CVPR 2021 | 支撑 DGQP 与高质量定位估计 | 已核实 |
| `wang2022curriculum` | Wang et al., *A Survey on Curriculum Learning*, TPAMI, 2022 | 支撑 RuleLoss 的 curriculum learning 动机 | 已核实 |
| `liu2022rfla` | Liu et al., *RFLA: Gaussian Receptive Field based Label Assignment for Tiny Object Detection*, arXiv 2022 | 可用于 tiny object label assignment 论证 | 已核实 |

### 2.4 域适应、小样本与工业应用

| BibKey | 条目 | 建议用途 | 状态 |
|---|---|---|---|
| `li2023dayolov5` | Li et al., *A Domain Adaptation YOLOv5 Model for Industrial Defect Inspection*, Measurement, 2023 | 支撑 DAYOLOv5 与跨厂域迁移 | 已核实 |
| `chen2024aiotfewshot` | Chen et al., *AIoT-enabled defect detection with minimal data*, Internet of Things, 2024 | 支撑 few-shot / AIoT 方向 | 已核实 |
| `chen2025uclgvd` | Chen et al., *A novel method for surface defect inspection: Unsupervised continual learning for gradually varying domains*, EAAI, 2025 | 支撑“轻量化 + 域适应联合考虑” | 已核实 |

### 2.5 官方工具链与硬件文档

| BibKey | 条目 | 建议用途 | 状态 |
|---|---|---|---|
| `rockchip2026rknn` | Rockchip, *RKNN Toolkit2* GitHub repository | 作为 RKNN 工具链官方来源 | 已核实 |
| `rockchip2026opsupport` | Rockchip, *RKNN Toolkit2 OP Support* document | 支撑算子支持 / unsupported operator 论述 | 已核实 |
| `orangepi2026orangepi5` | Orange Pi, *Orange Pi 5 Wiki* | 支撑 RK3588S / Orange Pi 5 硬件规格 | 已核实 |

## 3. 待核后再用

这些条目与你文中的论述高度相关，但目前我没有拿到足够稳定的一手元数据，先只给“候选占位”，不要直接作为正式 Bib 条目使用。

| 临时 BibKey | 当前掌握信息 | 建议用途 | 当前状态 |
|---|---|---|---|
| `li2024styleadaptation_todo` | *Style Adaptation Module: Enhancing Detector Robustness to Inter-Manufacturer Variability in Surface Defect Detection*, Computers in Industry, 2024 左右；作者含 Li Xinghui 团队成员 | 支撑“跨制造商风格差异”段落 | 待核 DOI / 卷期 / 页码 |
| `hu2023scrlemd_todo` | 你文中写作 `SCRL-EMD`；当前更接近的已见条目是 *Steel surface defect detection based on self-supervised contrastive representation learning with matching metric* | 支撑自监督预训练 / 数据稀缺场景 | 待核最终应引用哪篇 |
| `portcraneuav2023_todo` | 港机 / 集装箱起重机 UAV 巡检与结构健康监测论文 | 支撑“港机场景风险与人工巡检局限” | 待核具体论文与来源 |

## 4. 建议优先插入顺序

### 第一批，必须先补

1. `jocher2024ultralytics`
2. `song2013neudet`
3. `lv2020gc10det`
4. `sandler2018mobilenetv2`
5. `ma2018shufflenetv2`
6. `ding2021repvgg`
7. `lin2020focal`
8. `li2020gfl`
9. `zhang2020atss`
10. `zhang2021varifocalnet`
11. `feng2021tood`
12. `li2021gflv2`

### 第二批，用于把 Related Work 写完整

1. `fang2020metalreview`
2. `ameri2024slr`
3. `lyu2022rtmdet`
4. `chen2023fasternet`
5. `li2023dayolov5`
6. `chen2025uclgvd`
7. `chen2024aiotfewshot`
8. `wang2022curriculum`

### 第三批，用于部署与硬件感知

1. `rockchip2026rknn`
2. `rockchip2026opsupport`
3. `orangepi2026orangepi5`

## 5. 插入建议

- 摘要 / 引言：优先插 `YOLOv8`、`NEU-DET`、`GC10-DET`、`MobileNetV2`、`ShuffleNet V2`、`RepVGG`。
- 相关工作 2.1：优先插 `fang2020metalreview`、`ameri2024slr`、`lv2020gc10det`、`li2023dayolov5`、`chen2024aiotfewshot`、`chen2025uclgvd`。
- 相关工作 2.2：优先插 `sandler2018mobilenetv2`、`ma2018shufflenetv2`、`ding2021repvgg`、`lyu2022rtmdet`、`chen2023fasternet`。
- 相关工作 2.3：优先插 `lin2020focal`、`li2020gfl`、`zhang2020atss`、`zhang2021varifocalnet`、`feng2021tood`、`li2021gflv2`、`wang2022curriculum`。
