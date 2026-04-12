# Citation Needed for Related Work

> 范围：基于第4-7页的 Related Work 段落整理。  
> 目标：列出应优先补齐的引用位，而不是现在就虚构 Bib 条目。

## 0. 总体判断

- 当前 PDF 末尾只有 1 条参考文献，明显不足以支撑第 2 节的综述写作。
- 第 2 节中凡是出现具体方法名、数据集名、综述年份、官方工具链或明确研究结论的地方，都应补正式引用。

## 1. Section 2.1 金属表面缺陷检测

| 位置 | 当前论断 / 句群 | 需要的引用类型 | 建议检索关键词 | 优先级 |
|---|---|---|---|---|
| 2.1 首段 | 早期方法依赖边缘算子、纹理描述符、阈值分割和 SVM | 早期 defect detection 综述或代表工作 | `metal surface defect detection traditional feature SVM survey` | 高 |
| 2.1 首段 | `He 等` 的多层级特征融合钢表面缺陷检测 | 具体方法论文 | `steel surface defect detection multi-level feature fusion He` | 高 |
| 2.1 首段 | `Lv 等` 构建 GC10-DET 数据集 | 数据集原始论文 | `GC10-DET dataset paper Lv` | 高 |
| 2.1 第二段 | 从公开基准到港机场景存在明显域偏移 | 跨域 / industrial domain shift 文献 + 港机场景文献 | `industrial defect detection domain shift surface defect` | 中 |
| 2.1 第三段 | `2023 年关于实时表面缺陷检测的综述` | survey | `2023 real-time surface defect detection survey` | 高 |
| 2.1 第三段 | `2024 年面向目标检测的系统综述` | survey | `2024 object detection survey industrial defect detection` | 中 |
| 2.1 第四段 | 钢制集装箱起重机 UAV 结构健康监测研究 | 场景论文 / UAV inspection | `steel container crane UAV structural health monitoring 2023` | 高 |
| 2.1 第五段 | `DAYOLOv5` 域适应工业缺陷检测 | 方法论文 | `DAYOLOv5 domain adaptation industrial defect detection` | 高 |
| 2.1 第五段 | `Style Adaptation` 针对跨厂商风格差异 | 方法论文 | `style adaptation industrial defect detection 2024` | 中 |
| 2.1 第五段 | `SCRL-EMD` 自监督预训练迁移到 Faster R-CNN / RetinaNet | 方法论文 | `SCRL-EMD steel surface self-supervised defect detection` | 高 |
| 2.1 第五段 | `AIoT few-shot` 极少样本研究 | 方法论文 | `AIoT few-shot defect detection 2024` | 中 |
| 2.1 第五段 | `UCL-GVD` 轻量化与域适应结合 | 方法论文 | `UCL-GVD defect detection 2025` | 中 |

## 2. Section 2.2 轻量化目标检测与硬件感知设计

| 位置 | 当前论断 / 句群 | 需要的引用类型 | 建议检索关键词 | 优先级 |
|---|---|---|---|---|
| 2.2 首段 | MobileNetV2 轻量化设计范式 | 原始论文 | `MobileNetV2 paper` | 高 |
| 2.2 首段 | RTMDet 系统性研究 | 原始论文 | `RTMDet paper` | 高 |
| 2.2 第二段 | ShuffleNet V2 提出真实速度不只由 FLOPs 决定 | 原始论文 | `ShuffleNet V2 practical guidelines efficient CNN architecture` | 高 |
| 2.2 第二段 | RepVGG 证明推理图规整更利于硬件执行 | 原始论文 | `RepVGG paper` | 高 |
| 2.2 第三段 | YOLOX anchor-free / decoupled head / SimOTA | 原始论文 | `YOLOX paper` | 高 |
| 2.2 第三段 | `Fast and Accurate Model Scaling` 指出 FLOPs 不充分 | 原始论文 | `Fast and Accurate Model Scaling paper` | 中 |
| 2.2 第三段 | FasterNet 指出 DWConv / GConv 部署盲区 | 原始论文 | `FasterNet rethink CNN efficiency memory access` | 高 |
| 2.2 第三段 | 2024 边缘设备实测研究 | benchmark / measurement paper | `edge device object detection benchmark Jetson Coral 2024` | 中 |
| 2.2 第四段 | RKNN OP 支持表与 release notes | 官方文档 / toolchain docs | `RKNN Toolkit operator support docs GroupNormalization GridSample` | 高 |

## 3. Section 2.3 困难样本挖掘与损失函数优化

| 位置 | 当前论断 / 句群 | 需要的引用类型 | 建议检索关键词 | 优先级 |
|---|---|---|---|---|
| 2.3 首段 | Focal Loss | 原始论文 | `Focal Loss paper` | 高 |
| 2.3 首段 | GFL | 原始论文 | `Generalized Focal Loss paper` | 高 |
| 2.3 首段 | ATSS | 原始论文 | `ATSS paper` | 高 |
| 2.3 第二段 | VarifocalNet / Varifocal Loss | 原始论文 | `VarifocalNet paper` | 高 |
| 2.3 第二段 | TOOD | 原始论文 | `TOOD paper` | 高 |
| 2.3 第二段 | GFLV2 + DGQP | 原始论文 | `GFLV2 DGQP paper` | 中 |
| 2.3 第二段 | RFLA tiny object | 原始论文 | `RFLA tiny object detection paper` | 中 |
| 2.3 第三段 | ACCV 2024 YOLO small object with DGB and FRM | 原始论文 | `ACCV 2024 YOLO small object DGB FRM` | 中 |
| 3.4.4 | `curriculum learning` | 综述或原始课程学习论文 | `curriculum learning survey` | 高 |

## 4. 其它必须补的非 Related Work 引用

| 位置 | 当前论断 / 句群 | 需要的引用类型 | 建议检索关键词 | 优先级 |
|---|---|---|---|---|
| 摘要 / 引言 / 方法 | YOLOv8 作为基线框架 | 官方实现或论文/技术报告 | `Ultralytics YOLOv8 paper technical report` | 高 |
| 引言 / 数据集节 | NEU-DET | 数据集原始论文 | `NEU-DET dataset paper` | 高 |
| 引言 / 数据集节 | GC10-DET | 数据集原始论文 | `GC10-DET dataset paper` | 高 |
| 部署相关段落 | RK3588S / Orange Pi 5 / RKNN toolchain | 官方文档 | `RK3588S RKNN toolkit docs Orange Pi 5 specs` | 高 |

## 5. 建议补引用顺序

1. 先补所有“命名工作”的原始论文引用。
2. 再补两个 survey 和一个场景论文，收束第 2.1 节。
3. 再补 RKNN / RK3588S 官方文档，支撑硬件感知部署论证。
4. 最后统一把正文里的口头引用改成正式 citation key。
