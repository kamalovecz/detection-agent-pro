# FluidAgent Pro 快速使用

## 1. 准备工作区

推荐工作区至少包含：

- `fluid_agent_pro.py`
- `research_plan.md`
- `metadata.json`
- `paper-template/clear-iclr/`

建议额外准备：

- `src/`：你的 YOLOv8 工程与改进模块
- `configs/`：数据集与模型配置
- `weights/`：预训练与微调权重
- `analysis/`：统计脚本与结果表
- `plots/`：论文图表
- `references.bib`

## 2. 安装

CLI：

```bash
pip install -e .
```

GUI：

```bash
pip install -e ".[gui]"
```

## 3. 启动

CLI：

```bash
fluid-agent-pro --workspace /path/to/workspace
```

GUI：

```bash
fluid-agent-pro-gui
```

## 4. 推荐工作流

1. 在 `research_plan.md` 中写清 Phase 0 到 Phase 3 的目标。
2. 将你的检测代码、配置、日志输出目录准备好。
3. 先跑 Phase 0 环境检查。
4. 让 Codex 帮你整理或修改训练、验证、导出与分析脚本。
5. 在人工审查通过后进入论文草稿生成与模板导出。

## 5. 常用交互

- `Y`：通过并进入下一阶段
- `N`：打回并附加修改意见
- `P1` 或 `B`：从 Phase 2 回退到 Phase 1
- `P2`：从论文阶段回退到分析阶段
- `C`：咨询 Codex
- `Q`：退出流程

## 6. 清理工作区

- `fluid-agent-pro --clear`：清理中间产物，保留 `src/`
- `fluid-agent-pro --clear-hard`：连 `src/` 一起清理
- `--purge-install`：同时删除 `build/`、`dist/` 与 `*.egg-info`

## 7. 运行前建议确认

- `GEMINI_API_KEY` 或 `GOOGLE_API_KEY` 已设置
- `codex` CLI 可直接调用
- `typst` 可正常运行
- 你的 Python 深度学习环境能导入 `torch`、`ultralytics`、`opencv-python`、`pandas`、`matplotlib`
