# Sentence to BibKey Mapping for `paper_pass0412.pdf`

> 目标：把当前已核实的 `VERIFIED` 条目，按论文正文中的具体句子或近原句回填成“句子 -> 推荐 BibKey”清单。  
> 范围：优先覆盖摘要、引言、Related Work、数据集描述和部署平台描述。  
> 原则：只回填已核实条目；涉及未核实论文的句子先不强行补 citation。

## 0. 合并前先统一键名

根目录 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib) 已经存在少量重合条目，因此后续如果要合并，不建议直接把 [bib_input_template.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/origin_paper/bib_input_template.bib) 全量复制进去。

| 候选文件中的键名 | 建议最终统一键名 | 原因 |
|---|---|---|
| `fang2020metalreview` | `fang2020review` | 根目录 `references.bib` 已存在同一篇综述，建议沿用已有键名 |
| `lin2020focal` | `lin2017focal` | 根目录 `references.bib` 已存在 Focal Loss 条目，建议沿用已有键名 |

除上述两项外，其余 `VERIFIED` 键名可按候选文件保持不变。

## 1. 摘要与引言

| 位置 | 句子或近原句 | 推荐 BibKey | 建议写法 | 说明 |
|---|---|---|---|---|
| 第 1 页 摘要 | “该方法以 YOLOv8n 为基线，从结构设计与训练优化两个层面进行协同改进。” | `jocher2024ultralytics` | `以 YOLOv8n 为基线\cite{jocher2024ultralytics}` | 这里属于“基线框架来源”引用 |
| 第 1 页 摘要 | “实验在 NEU-DET 和 GC10-DET 公开数据集上开展。” | `song2013neudet`, `lv2020gc10det` | `实验在 NEU-DET 和 GC10-DET 公开数据集上开展\cite{song2013neudet,lv2020gc10det}` | 两个数据集都应有来源 |
| 第 1 页 摘要 | “并进一步在 RK3588S 平台完成 RKNN 导出与边缘端推理验证。” | `rockchip2026rknn` | `...完成 RKNN 导出与边缘端推理验证\cite{rockchip2026rknn}` | 这里主要支撑工具链来源，不必在摘要里同时塞硬件 wiki |
| 第 2-3 页 引言 | “围绕边缘部署需求，轻量化神经网络设计已经成为目标检测研究的重要方向。MobileNetV2...ShuffleNet V2...RepVGG...RTMDet...” | `sandler2018mobilenetv2`, `ma2018shufflenetv2`, `ding2021repvgg`, `lyu2022rtmdet` | `MobileNetV2... \cite{sandler2018mobilenetv2}，ShuffleNet V2... \cite{ma2018shufflenetv2}，RepVGG... \cite{ding2021repvgg}，RTMDet... \cite{lyu2022rtmdet}` | 这类“点名方法”建议各自紧跟原始论文 |
| 第 3 页 引言 | “现有困难样本优化方法如 Focal Loss、GFL 与 ATSS...” | `lin2017focal`, `li2020gfl`, `zhang2020atss` | `Focal Loss、GFL 与 ATSS\cite{lin2017focal,li2020gfl,zhang2020atss}` | 根目录已存在 `lin2017focal`，后续统一沿用它 |
| 第 3 页 引言 | “YOLOv8 在本文中采用 Ultralytics 官方实现作为基础检测框架。” | `jocher2024ultralytics` | `YOLOv8 在本文中采用 Ultralytics 官方实现\cite{jocher2024ultralytics}` | 这是最明确、最应补的一处 |

## 2. Related Work 2.1 金属表面缺陷检测

| 位置 | 句子或近原句 | 推荐 BibKey | 建议写法 | 说明 |
|---|---|---|---|---|
| 第 4 页 2.1 首段 | “早期研究主要依赖边缘算子、纹理描述符、阈值分割以及 SVM 等浅层分类器...” | `fang2020review` | `...依赖边缘算子、纹理描述符、阈值分割以及 SVM 等浅层分类器\cite{fang2020review}` | 这类历史综述句最适合由 survey 支撑 |
| 第 4 页 2.1 首段 | “Lv 等构建的 GC10-DET 数据集则推动了复杂金属缺陷检测从‘小规模、低复杂度’实验走向更具挑战性的标准化评测。” | `lv2020gc10det` | `Lv 等构建的 GC10-DET 数据集... \cite{lv2020gc10det}` | 该句是标准的数据集论文引用点 |
| 第 4 页 2.1 第二段 | “现有研究大多围绕 NEU-DET、GC10-DET 等公开数据集展开...” | `song2013neudet`, `lv2020gc10det` | `NEU-DET、GC10-DET 等公开数据集\cite{song2013neudet,lv2020gc10det}` | 这里只需要给数据集来源，不必额外堆引用 |
| 第 4 页 2.1 第三段 | “现有综述指出，深度学习目标检测已经成为工业表面缺陷定位的主流技术路线...” | `fang2020review`, `liu2024slr` | `现有综述指出... \cite{fang2020review,liu2024slr}` | 建议把原文中“2023 年综述和 2024 年综述”改写为更稳妥的“现有综述指出” |
| 第 5 页 2.1 第五段 | “DAYOLOv5 将域适应引入工业缺陷检测...” | `li2023dayolov5` | `DAYOLOv5 将域适应引入工业缺陷检测\cite{li2023dayolov5}` | 这是域适应主线的重要近邻工作 |
| 第 5 页 2.1 第五段 | “AIoT few-shot 研究也表明，面向极少样本条件的元学习策略可以有效缓解过拟合。” | `chen2024aiotfewshot` | `AIoT few-shot 研究表明... \cite{chen2024aiotfewshot}` | 可支撑 few-shot / minimal-data 论述 |
| 第 5 页 2.1 第五段 | “UCL-GVD 这类工作已经开始把轻量化和域适应放在同一个问题框架中讨论...” | `chen2025uclgvd` | `UCL-GVD... \cite{chen2025uclgvd}` | 这句和你的 T1/T2 迁移实验定位最接近 |

## 3. Related Work 2.2 轻量化目标检测与硬件感知设计

| 位置 | 句子或近原句 | 推荐 BibKey | 建议写法 | 说明 |
|---|---|---|---|---|
| 第 5 页 2.2 首段 | “MobileNetV2 通过倒残差和线性瓶颈建立了移动端视觉网络的重要设计范式...” | `sandler2018mobilenetv2` | `MobileNetV2... \cite{sandler2018mobilenetv2}` | 原始论文引用点非常明确 |
| 第 5 页 2.2 首段 | “RTMDet 的系统性研究进一步说明...” | `lyu2022rtmdet` | `RTMDet 的系统性研究进一步说明... \cite{lyu2022rtmdet}` | 可支撑实时检测器的系统设计论述 |
| 第 5 页 2.2 第二段 | “ShuffleNet V2 明确指出...；RepVGG 则进一步证明...” | `ma2018shufflenetv2`, `ding2021repvgg` | `ShuffleNet V2... \cite{ma2018shufflenetv2}；RepVGG... \cite{ding2021repvgg}` | 这句最好拆成两个半句分别挂引用 |
| 第 6 页 2.2 第四段 | “2023 年的 FasterNet 更进一步点明了很多‘理论轻量化’模块的部署盲区...” | `chen2023fasternet` | `2023 年的 FasterNet... \cite{chen2023fasternet}` | 很适合支撑你对 DWConv / memory access 的批判 |
| 第 6 页 2.2 第四段 | “以 Rockchip 官方 RKNN 工具链为例，当前公开的 OP 支持表仍将 GridSample 和 GroupNormalization 标为 unsupported...” | `rockchip2026opsupport`, `rockchip2026rknn` | `...OP 支持表... \cite{rockchip2026opsupport,rockchip2026rknn}` | 一个引官方支持表，一个引工具链仓库 |

## 4. Related Work 2.3 困难样本挖掘与损失函数优化

| 位置 | 句子或近原句 | 推荐 BibKey | 建议写法 | 说明 |
|---|---|---|---|---|
| 第 6 页 2.3 首段 | “Focal Loss 通过降低易分类样本对总损失的主导作用...；GFL...；ATSS...” | `lin2017focal`, `li2020gfl`, `zhang2020atss` | `Focal Loss... \cite{lin2017focal}；GFL... \cite{li2020gfl}；ATSS... \cite{zhang2020atss}` | 建议不要三篇只放在句末一把抓，最好逐个方法名对应 |
| 第 7 页 2.3 第二段 | “VarifocalNet...；TOOD...；GFLV2...；RFLA...” | `zhang2021varifocalnet`, `feng2021tood`, `li2021gflv2`, `liu2022rfla` | `VarifocalNet... \cite{zhang2021varifocalnet}；TOOD... \cite{feng2021tood}；GFLV2... \cite{li2021gflv2}；RFLA... \cite{liu2022rfla}` | 同样建议逐个方法贴原始论文 |
| 第 12-13 页 RuleLoss 动机 | “借鉴课程学习（Curriculum Learning）的循序渐进思想...” | `wang2022curriculum` | `借鉴课程学习（Curriculum Learning）的循序渐进思想\cite{wang2022curriculum}` | 这是 RuleLoss 动机最稳的一处外部支撑 |

## 5. 数据集与部署平台

| 位置 | 句子或近原句 | 推荐 BibKey | 建议写法 | 说明 |
|---|---|---|---|---|
| 第 16-17 页 4.1 数据集 | “本文选取两个公开金属表面缺陷数据集 NEU-DET 和 GC10-DET...” | `song2013neudet`, `lv2020gc10det` | `NEU-DET 和 GC10-DET\cite{song2013neudet,lv2020gc10det}` | 这是实验节里必须补的一组硬引用 |
| 第 16 页 4.1 数据集 | “NEU-DET 数据集由东北大学发布...” | `song2013neudet` | `NEU-DET 数据集由东北大学发布\cite{song2013neudet}` | 建议在首次详细介绍处补 |
| 第 17 页 4.1 数据集 | “GC10-DET 数据集来源于真实工业钢板生产场景...” | `lv2020gc10det` | `GC10-DET 数据集来源于真实工业钢板生产场景\cite{lv2020gc10det}` | 与上条对应 |
| 第 17 页 4.2 平台设置 | “在本研究的边缘部署实验中，采用 Orange Pi 5 作为主要推理设备。该平台搭载瑞芯微 RK3588S...” | `orangepi2026orangepi5` | `采用 Orange Pi 5 作为主要推理设备\cite{orangepi2026orangepi5}` | 主要支撑板卡规格与 SoC 信息 |
| 第 17 页 4.2 平台设置 | “模型训练在 Ultralytics YOLO 检测框架下完成...” | `jocher2024ultralytics` | `模型训练在 Ultralytics YOLO 检测框架下完成\cite{jocher2024ultralytics}` | 与摘要/引言中的框架来源保持一致 |

## 6. 当前不建议用 VERIFIED 强行回填的句子

下列句子与正文关系很强，但当前仍缺少稳定的一手元数据，建议先保留占位或先改写，暂不并入最终 `references.bib`：

- 第 4-5 页关于“2023 年钢制集装箱起重机 UAV 结构健康监测研究”的句子。
- 第 5 页关于 “Style Adaptation” 的句子。
- 第 5 页关于 “SCRL-EMD” 的句子。

对应原因见 [citation_needed.md](/D:/Code/paper_pass_skill/fluid-agent-pro/origin_paper/citation_needed.md) 和 [candidate_references.md](/D:/Code/paper_pass_skill/fluid-agent-pro/origin_paper/candidate_references.md) 中的 `TODO` 区域。

## 7. 是否现在合并进最终 `references.bib`

当前判断：**建议先不直接全量合并**，但可以准备“规范化合并”。

原因：

- 根目录 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib) 已存在 5 个重合条目：`jocher2024ultralytics`、`song2013neudet`、`lv2020gc10det`、`fang2020review`、`lin2017focal`。
- 候选模板中的 `fang2020metalreview` 与 `lin2020focal` 若直接复制，会与现有条目形成“同文不同键”的冲突。
- 你正文里仍有少量句子依赖 `TODO` 文献，如果现在全量并表，后续还会再做一次清理。

更稳妥的顺序：

1. 先按照本文件把正文 citation 插槽补齐。
2. 再把 `VERIFIED` 条目按“统一键名”规则并入最终 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib)。
3. 最后补 `TODO` 文献，完成一次统一去重。
