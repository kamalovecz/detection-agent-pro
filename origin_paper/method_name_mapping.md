# Method and Module Name Mapping

> 目标：建立一套唯一、层级清楚的命名体系，避免标题、方法、消融与部署版本混在一起。

## 推荐命名层级

- 论文主方法名：建议确定一个唯一总名；如果暂时不重新起名，可暂用 `B3-Lite-INNOV` 作为最终部署版本主名。
- 消融版本名：`B0 / B1 / B2-Lite / B3-Lite / B3-Lite-INNOV`
- 模块名：`SADH`、`A-GFPN`、`Rep-HFE`、`RuleLoss`
- 数据集名：`NEU-DET`、`GC10-DET`、`PORT_defect`

## 当前写法 -> 建议统一写法

| 类别 | 当前写法 | 建议统一写法 | 说明 |
|---|---|---|---|
| 论文题目 / 总方法名 | `XXX-Net` | `最终正式方法名（待定）` | `XXX-Net` 明显是占位符，必须替换；如果暂不重新命名，可先用 `B3-Lite-INNOV` 顶上 |
| 框架版本 | `B3-Lite` | `B3-Lite` | 作为正式消融版本名保留 |
| 框架版本 | `B3-LITE` | `B3-Lite` | 统一大小写和连字符 |
| 最终部署版 | `B3-LITE-INNOV` | `B3-Lite-INNOV` | 统一大小写；作为最终部署版本 |
| FPN / Neck 模块 | `A-FPN` | `A-GFPN` 或 `A-FPN` 二选一 | 目前摘要和正文不一致；如果不是两个不同模块，全文只能保留一个 |
| 高频增强模块 | `Rephub` | `Rep-HFE` | `Rephub` 看起来像旧名或笔误，建议统一到正式缩写 |
| 高频增强模块 | `RepHFE` | `Rep-HFE` | 首次出现时给全称，后文用 `Rep-HFE` |
| 高频增强模块 | `Rep-HFE` | `Rep-HFE` | 建议保留 |
| 检测头 | `SADH` | `SADH` | 保留，并在首次出现处给全称 |
| 损失函数 | `Rule-weighted Loss` | `RuleLoss (Rule-weighted Loss)` | 首次出现可写全称 + 缩写 |
| 损失函数 | `Dynamic Rule-weighted Loss` | `RuleLoss` | 若不是单独的新变体，后文统一简称 |
| 损失函数 | `RuleLoss` | `RuleLoss` | 作为后文唯一简称 |
| 数据集 | `PORT_defect` | `PORT_defect` | 正文统一正式写法 |
| 数据集简称 | `PORT` | `PORT` | 仅在表格或对比列标题中作为简称 |
| 数据集 | `GC10-NET` | `GC10-DET` | 明显误写 |
| 小节标题 | `不同 detect 对比` | `不同检测器对比` | 中文论文中不建议中英混杂标题 |

## 推荐首次定义方式

### 方法总名

- 正式方法首次出现：`本文提出 B3-Lite-INNOV，一种面向 RK3588S 边缘部署的轻量化港机表面缺陷检测框架。`
- 如果后续要改一个更适合作为题目的名字，应同时同步：标题、摘要、引言贡献段、方法节首段、实验表标题。

### 模块首次定义

- `SADH`：写出全称 + 缩写
- `A-GFPN`：写出全称 + 缩写
- `Rep-HFE`：写出全称 + 缩写
- `RuleLoss`：`RuleLoss (Rule-weighted Loss)`

## 命名统一执行顺序

1. 先定论文主方法名。
2. 再定模块正式名。
3. 再统一所有表格、图 caption 和实验编号。
4. 最后统一摘要、引言、方法、实验正文中的所有写法。
