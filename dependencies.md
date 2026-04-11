# FluidAgent Pro 项目依赖

这份文档列出当前这套“金属表面缺陷检测论文工作流”推荐的环境与工具。

## 1. 基础运行环境

- Python 3.10+
- Windows、Linux 或 WSL
- 可选 GPU 环境，用于 YOLOv8 训练、验证与部署测试

## 2. 必需命令行工具

- `codex` CLI
  - 用于实现、分析、论文修订与模板导出阶段
- `typst`
  - 用于将论文源文件编译为 PDF

## 3. 推荐 Python 依赖

- `torch`
- `torchvision`
- `ultralytics`
- `opencv-python`
- `numpy`
- `pandas`
- `matplotlib`
- `seaborn`
- `pyyaml`

可选依赖：

- `onnx`
- `onnxruntime`
- `thop`
- `PySide6>=6.7`：GUI 模式
- `PyInstaller>=6.0`：打包

## 4. Gemini API 依赖

Gemini 主要用于论文草稿生成阶段，也就是 `STATE_PAPER_WRITING`。

需要准备：

- `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`
- 可选环境变量 `FLUID_AGENT_GEMINI_MODEL`
- 可访问 Gemini API 的网络环境

Gemini 在本项目中的职责：

- 根据 `research_plan.md`、`metadata.json` 和分析结果生成论文草稿
- 不直接负责训练代码实现
- 不直接负责 Typst 语法修复
- 不直接负责最终模板导出

后两步由 Codex 接管：

- `STATE_PAPER_FIX`：修复 `paper.typ`
- `STATE_PAPER_TEMPLATE_EXPORT`：生成 `paper_final.typ` 并导出 `paper.pdf`

## 5. 推荐工作区内容

- `fluid_agent_pro.py`
- `research_plan.md`
- `metadata.json`
- `references.bib`
- `paper-template/clear-iclr/`
- `src/`
- `configs/`
- `weights/`
- `analysis/`
- `plots/`
