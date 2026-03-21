# FluidAgent Pro 项目依赖

这份文档列出完整流程需要的环境、工具和运行时凭据。核心控制器本身尽量保持标准库实现，但完整科研流水线会依赖外部工具链。

## 1. 基础运行环境

- Python 3.10 或更高版本
- Linux 或 WSL 环境
- 你的 CFD 工程源码、编译器和测试数据

## 2. 必需命令行工具

- `codex` CLI
  - 用于代码实现、验证辅助、论文修复和模板化导出
  - 需要在 `PATH` 中可直接执行
- `typst`
  - 用于论文源文件编译成 PDF
  - Phase 0 会先检查 `typst --version`

## 3. Python 依赖

- 核心控制器：当前以标准库为主，不依赖第三方 Python 包即可启动 CLI
- `PySide6>=6.7`
  - 仅 GUI 模式需要
  - 安装命令：`pip install -e '.[gui]'`
- `pandas`
  - 数据分析阶段常用
  - Phase 0 会按研究方案检查是否可用
- `matplotlib`
  - 绘图阶段常用
  - Phase 0 会按研究方案检查是否可用
- `PyInstaller>=6.0`
  - 仅打包成安装包时需要
  - 安装命令：`pip install -e '.[packager]'`

## 4. Gemini API 依赖

Gemini 主要用于论文草稿生成阶段，也就是 `STATE_PAPER_WRITING`。

需要准备：

- `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`
  - 至少设置一个
  - 程序会优先读取 `GEMINI_API_KEY`
- 可选的 `FLUID_AGENT_GEMINI_MODEL`
  - 用于覆盖默认模型名
  - 默认值是 `gemini-2.5-pro`
- 可访问 Gemini API 的网络环境

Gemini 在流程中的职责是：

- 根据 `research_plan.md`、`metadata.json` 和分析结果生成论文草稿
- 不直接负责代码实现
- 不负责 Typst 语法修复
- 不负责最终模板化导出

后续两步分别由 Codex 接管：

- `STATE_PAPER_FIX`：修 Typst 语法、引用和结构
- `STATE_PAPER_TEMPLATE_EXPORT`：按 `paper-template/clear-iclr/` 重排并导出 PDF

## 5. 工作区必备文件

- `fluid_agent_pro.py`
- `research_plan.md`
- `paper-template/clear-iclr/`

建议再准备：

- `metadata.json`
- `references.bib`
- 你的求解器源码和结果数据

