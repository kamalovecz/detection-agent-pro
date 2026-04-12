# Standardized Experiment Table Skeleton

> 固定字段：`Model / Dataset / Recall / mAP50 / mAP50-95 / Params / FLOPs / Size / Latency / FPS / Deployability`  
> 规则：没有数据时统一写 `TBD`，不要留空，也不要只写“较高/较低/极速”。

## 1. 主表 schema

| Model | Dataset | Recall | mAP50 | mAP50-95 | Params | FLOPs | Size | Latency | FPS | Deployability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 2. Table A: NEU-DET progressive ablation

| Model | Dataset | Recall | mAP50 | mAP50-95 | Params | FLOPs | Size | Latency | FPS | Deployability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B0 (YOLOv8n Baseline) | NEU-DET | 0.678 | 0.722 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| B1 (+SADH) | NEU-DET | 0.688 | 0.696 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| B2-Lite (+A-GFPN + Rep-HFE) | NEU-DET | 0.642 | 0.715 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| B3-Lite (+RuleLoss) | NEU-DET | 0.686 | 0.720 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 3. Table B: GC10-DET generalization / capacity boundary

| Model | Dataset | Recall | mAP50 | mAP50-95 | Params | FLOPs | Size | Latency | FPS | Deployability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B0 (YOLOv8n Baseline) | GC10-DET | TBD | 0.621 | 0.333 | TBD | TBD | TBD | TBD | TBD | TBD |
| B1 (+SADH) | GC10-DET | TBD | 0.555 | 0.284 | TBD | TBD | TBD | TBD | TBD | TBD |
| B2-Lite (full lightweight structure) | GC10-DET | TBD | 0.591 | 0.282 | TBD | TBD | TBD | TBD | TBD | TBD |

## 4. Table C: PORT_defect transfer + deployment collaboration

| Model | Dataset | Recall | mAP50 | mAP50-95 | Params | FLOPs | Size | Latency | FPS | Deployability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| T0 (B3-Lite, no pretrain) | PORT_defect | 0.575 | 0.609 | 0.328 | TBD | TBD | TBD | TBD | TBD | Hardware unsupported |
| T1 (YOLOv8n + COCO pretrain + RuleLoss) | PORT_defect | 0.597 | 0.635 | 0.341 | TBD | TBD | TBD | TBD | TBD | High memory / latency |
| T2 (B3-Lite + NEU-DET pretrain + RuleLoss) | PORT_defect | 0.601 | 0.639 | 0.358 | TBD | TBD | TBD | TBD | TBD | CPU fallback |
| T3 (B3-Lite-INNOV + NEU-DET pretrain + RuleLoss) | PORT_defect | 0.632 | 0.652 | 0.369 | TBD | TBD | TBD | TBD | TBD | Pure NPU deployable |

## 5. Table D: Cross-method comparison

| Model | Dataset | Recall | mAP50 | mAP50-95 | Params | FLOPs | Size | Latency | FPS | Deployability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Faster R-CNN | NEU-DET | TBD | 0.687 | TBD | ~41.5 | TBD | TBD | TBD | TBD | Not edge-friendly |
| Faster R-CNN | GC10-DET | TBD | 0.477 | TBD | ~41.5 | TBD | TBD | TBD | TBD | Not edge-friendly |
| Faster R-CNN | PORT_defect | TBD | 0.397 | TBD | ~41.5 | TBD | TBD | TBD | TBD | Not edge-friendly |
| ATSS | NEU-DET | TBD | 0.671 | TBD | ~32.1 | TBD | TBD | TBD | TBD | TBD |
| ATSS | GC10-DET | TBD | 0.626 | TBD | ~32.1 | TBD | TBD | TBD | TBD | TBD |
| ATSS | PORT_defect | TBD | 0.495 | TBD | ~32.1 | TBD | TBD | TBD | TBD | TBD |
| GFL | NEU-DET | TBD | 0.685 | TBD | ~32.0 | TBD | TBD | TBD | TBD | TBD |
| GFL | GC10-DET | TBD | 0.628 | TBD | ~32.0 | TBD | TBD | TBD | TBD | TBD |
| GFL | PORT_defect | TBD | 0.501 | TBD | ~32.0 | TBD | TBD | TBD | TBD | TBD |
| YOLOX-s | NEU-DET | TBD | 0.754 | TBD | ~9.0 | TBD | TBD | TBD | TBD | TBD |
| YOLOX-s | GC10-DET | TBD | 0.611 | TBD | ~9.0 | TBD | TBD | TBD | TBD | TBD |
| YOLOX-s | PORT_defect | TBD | 0.541 | TBD | ~9.0 | TBD | TBD | TBD | TBD | TBD |
| RTMDet-tiny | NEU-DET | TBD | 0.700 | TBD | ~4.9 | TBD | TBD | TBD | TBD | TBD |
| RTMDet-tiny | GC10-DET | TBD | 0.650 | TBD | ~4.9 | TBD | TBD | TBD | TBD | TBD |
| RTMDet-tiny | PORT_defect | TBD | 0.598 | TBD | ~4.9 | TBD | TBD | TBD | TBD | TBD |
| B3-Lite-INNOV (Ours) | NEU-DET | 0.686 | 0.720 | TBD | ~2.1 or TBD | TBD | TBD | TBD | TBD | TBD |
| B3-Lite-INNOV (Ours) | GC10-DET | TBD | 0.591 | 0.282 | ~2.1 or TBD | TBD | TBD | TBD | TBD | TBD |
| B3-Lite-INNOV (Ours) | PORT_defect | 0.632 | 0.652 | 0.369 | ~2.1 or TBD | TBD | TBD | TBD | TBD | Pure NPU deployable |

## 6. 必须补齐的板端指标

- `Latency`：单张图像端到端平均推理时间，单位建议 `ms`
- `FPS`：同一平台同一输入尺寸下的稳定值
- `Deployability`：统一写成以下离散标签之一
  - `Pure NPU`
  - `NPU + CPU fallback`
  - `CPU only`
  - `Unsupported`
- `Size`：建议写 `PT / ONNX / RKNN` 中实际用于部署的那个文件大小

## 7. 表格使用建议

- 摘要与引言结尾贡献段，只引用主表中的最终定量结果。
- 消融表必须至少说明 `RuleLoss` 是否零额外推理开销。
- 部署表必须和 RK3588S 实测绑定，不能只写趋势判断。
