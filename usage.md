# FluidAgent Pro 快速使用

## 1. 准备工作区

工作区里至少要有：

- `fluid_agent_pro.py`
- `research_plan.md`
- `paper-template/clear-iclr/`

建议再准备：

- `metadata.json`
- 你的 CFD 工程源码和测试数据

## 2. 安装

命令行版：

```bash
pip install -e .
```

带 GUI 版：

```bash
pip install -e '.[gui]'
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

## 4. 常用交互

在审查点通常会看到这些输入：

- `Y`：通过并进入下一阶段
- `N`：打回并附加反馈
- `P1` 或 `B`：从 Phase 2 回退到 Phase 1
- `P2`：从论文阶段回退到分析阶段
- `C`：咨询 Codex
- `Q`：退出流程

## 5. 清理工作区

- `fluid-agent-pro --clear`：清理中间产物，保留 `src/`
- `fluid-agent-pro --clear-hard`：连 `src/` 一起清理
- `--purge-install`：同时删除 `build/`、`dist/` 和 `*.egg-info`

## 6. 环境要求

- Python 3.10+
- `codex` CLI
- `typst`
- `pandas`
- `matplotlib`
- `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`

