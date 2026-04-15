# Detection_Agent_Pro

Detection_Agent_Pro 是一套面向论文与实验闭环的本地研究流程控制器，当前版本主要服务于“金属表面缺陷检测论文”的个人研究工作流。

它适合把下面这条链路串起来：

`研究主线整理 -> 模型改进实现 -> 实验验证 -> 数据分析 -> 论文草稿 -> Typst 导出`

当前默认研究方向：

- 金属表面缺陷检测
- 改进 YOLOv8
- NEU DET、GC10 DET 与自建 `port_defect`
- 公开数据集预训练 + 自建数据迁移微调
- 消融实验、跨数据集验证与部署评估
- Gemini 生成论文草稿，Codex 做 Typst 修订与导出

---

## 1. 工作流总览

系统按固定状态机运行：

1. `Phase 0` 环境检查
2. `Phase 1` 模型实现 / 训练 / 验证
3. `Phase 2` 数据分析 / 图表 / 对比实验
4. `Phase 3` 论文草稿生成与模板导出

你会在关键节点看到人工审查入口，避免实验有问题时直接进入论文写作。

---

## 2. 从零开始准备环境

### 2.1 基础要求

建议至少准备好下面这些工具：

- Python 3.10 及以上
- `pip`
- `git`
- `codex` CLI
- `typst`

如果你要跑 YOLOv8 实验，推荐同时准备：

- `torch`
- `torchvision`
- `ultralytics`
- `opencv-python`
- `numpy`
- `pandas`
- `matplotlib`
- `seaborn`

如果你要做导出或部署评估，还可以准备：

- `onnx`
- `onnxruntime`
- `thop`

### 2.2 克隆项目

```powershell
git clone https://github.com/kamalovecz/fluid-agent-pro.git
cd fluid-agent-pro
```

如果你已经有本地项目目录，直接进入项目根目录即可。

### 2.3 安装本项目

CLI 版本：

```powershell
pip install -e .
```

如果你要用 GUI：

```powershell
pip install -e ".[gui]"
```

### 2.4 安装研究实验依赖

本控制器本身尽量保持轻量，但你的论文实验环境通常还需要下面这些包：

```powershell
pip install torch torchvision ultralytics opencv-python numpy pandas matplotlib seaborn pyyaml
```

如需部署相关指标：

```powershell
pip install onnx onnxruntime thop
```

---

## 3. 设置 Gemini API

本项目在论文草稿生成阶段会调用 Gemini。控制器当前会读取下面两个环境变量中的任意一个：

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`

推荐统一使用 `GEMINI_API_KEY`。

### 3.1 获取 API Key

你可以在 Google AI Studio 创建 Gemini API Key：

- Google AI Studio: [https://aistudio.google.com/](https://aistudio.google.com/)
- Gemini API quickstart: [https://ai.google.dev/gemini-api/docs/quickstart](https://ai.google.dev/gemini-api/docs/quickstart)

### 3.2 在 Windows PowerShell 中设置

仅当前终端会话有效：

```powershell
$env:GEMINI_API_KEY="你的_Gemini_API_Key"
```

写入用户环境变量，后续终端也可用：

```powershell
setx GEMINI_API_KEY "你的_Gemini_API_Key"
```

设置完成后，重新打开一个新的 PowerShell，再检查是否生效：

```powershell
echo $env:GEMINI_API_KEY
```

如果你更习惯沿用 `GOOGLE_API_KEY`，也可以：

```powershell
setx GOOGLE_API_KEY "你的_Gemini_API_Key"
```

### 3.3 安全建议

- 不要把 API Key 写死在代码里
- 不要把 API Key 提交到 Git 仓库
- 建议只放在系统环境变量里

---

## 4. 准备工作区内容

推荐工作区结构：

```text
workspace/
├─ fluid_agent_pro.py
├─ research_plan.md
├─ metadata.json
├─ references.bib
├─ src/
├─ configs/
├─ weights/
├─ analysis/
├─ logs/
├─ plots/
└─ paper-template/
```

### 4.1 必要文件

- `research_plan.md`
- `fluid_agent_pro.py`
- `paper-template/clear-iclr/`

### 4.2 推荐文件

- `metadata.json`
- `references.bib`
- `src/`
- `configs/`
- `weights/`

### 4.3 `metadata.json` 示例

可以先放一份最小可运行版本：

```json
{
  "title": "Real-Time Metal Surface Defect Detection with Improved YOLOv8",
  "authors": ["Your Name"],
  "affiliations": ["Your School or Lab"],
  "keywords": [
    "metal surface defect detection",
    "YOLOv8",
    "transfer learning",
    "industrial deployment"
  ],
  "reference_doi": ""
}
```

---

## 5. 运行项目

### 5.1 CLI 启动

在项目根目录运行：

```powershell
fluid-agent-pro --workspace D:\Code\paper_pass_skill\fluid-agent-pro
```

如果你当前就在工作区目录，也可以：

```powershell
fluid-agent-pro --workspace .
```

### 5.2 GUI 启动

```powershell
fluid-agent-pro-gui
```

### 5.3 常用交互

- `Y`：通过并进入下一阶段
- `N`：打回并附加修改意见
- `P1` 或 `B`：从 Phase 2 回退到 Phase 1
- `P2`：从论文阶段回退到分析阶段
- `C`：咨询 Codex
- `Q`：退出流程

### 5.4 清理工作区

清理中间产物但保留 `src/`：

```powershell
fluid-agent-pro --clear --workspace .
```

连 `src/` 一起清理：

```powershell
fluid-agent-pro --clear-hard --workspace .
```

如果还要删除 `build/`、`dist/`、`*.egg-info`：

```powershell
fluid-agent-pro --clear --purge-install --workspace .
```

---

## 6. 本项目里的 MCP 组件

为了增强论文协作流程，我已经把下面 3 个 MCP 仓库下载到了项目内的 `mcp-servers/` 目录：

- `mcp-servers/zotero-mcp`
- `mcp-servers/stata-mcp`
- `mcp-servers/office-word-mcp-server`

注意：

- 这些 MCP 是“外部协作工具”，不是 `fluid_agent_pro.py` 自动启动的一部分
- 它们通常接入 Claude Desktop、Cursor、VS Code、ChatGPT Developer Mode 或支持 MCP 的客户端
- 其中 `stata-mcp` 主要是编辑器扩展，不是单独的本地 stdio 脚本项目

为了方便 Windows 本地接入，我还额外生成了：

- `mcp-client-configs/windows/claude_desktop_config.example.json`
- `mcp-client-configs/windows/cursor_mcp.example.json`
- `mcp-client-configs/windows/README.md`
- `scripts/start_zotero_mcp_stdio.ps1`
- `scripts/start_word_mcp_stdio.ps1`

---

## 7. Zotero MCP：文献检索与参考文献协作

仓库：

- [54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp)

适合做什么：

- 搜索 Zotero 文献库
- 读取元数据、标签、注释、PDF 内容
- 辅助摘要写作、文献综述、引文整理
- 语义检索论文

### 7.1 推荐安装方式

虽然仓库已经下载到 `mcp-servers/zotero-mcp`，但最简单的安装方式通常还是直接安装官方包：

```powershell
pip install zotero-mcp-server
```

如果你要语义检索，并希望复用本项目的 Gemini Key：

```powershell
pip install "zotero-mcp-server[semantic]"
```

当前这台机器上我已经把 **core 版** 安装到了：

- `mcp-servers/zotero-mcp/.venv/`

也就是说，基础文献检索、条目读取和本地 MCP 运行已经具备条件；但如果你后续想启用 `semantic` 语义检索，还需要额外安装 `semantic` 扩展依赖。

### 7.2 首次配置

```powershell
zotero-mcp setup
```

如果你使用本地 Zotero 库，常见方式是本地模式：

- 启动 Zotero Desktop
- 确保启用了本地 API
- MCP 侧使用 `ZOTERO_LOCAL=true`

### 7.3 与 Gemini API 联动

如果你安装了 `semantic` 扩展，`zotero-mcp` 支持使用 Gemini embeddings。此时可以直接复用你已经设置好的：

- `GEMINI_API_KEY`

常见相关环境变量包括：

- `ZOTERO_LOCAL=true`
- `GEMINI_API_KEY=...`
- `ZOTERO_EMBEDDING_MODEL=gemini`

### 7.4 常用命令

```powershell
zotero-mcp setup
zotero-mcp update-db
zotero-mcp db-status
zotero-mcp serve --transport stdio
```

如果你需要给 Web 端 MCP 客户端使用，也可以按上游文档启动 `sse`：

```powershell
zotero-mcp serve --transport sse --host localhost --port 8000
```

---

## 8. Office Word MCP：Word 文档协作

仓库：

- [GongRzhe/Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server)

适合做什么：

- 创建和修改 `.docx`
- 插入标题、段落、表格、图片、脚注
- 批量格式化论文或报告
- 将 Word 文档导出为 PDF

### 8.1 本地安装

进入已下载的仓库：

```powershell
cd mcp-servers\office-word-mcp-server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

也可以直接运行它自带的初始化脚本：

```powershell
python setup_mcp.py
```

当前这台机器上我已经把它安装到了：

- `mcp-servers/office-word-mcp-server/.venv/`

### 8.2 Claude Desktop 配置示例

上游 README 给出的典型配置思路是：

```json
{
  "mcpServers": {
    "word-document-server": {
      "command": "python",
      "args": [
        "D:/Code/paper_pass_skill/fluid-agent-pro/mcp-servers/office-word-mcp-server/word_mcp_server.py"
      ]
    }
  }
}
```

Windows 下 Claude Desktop 配置文件通常在：

```text
%APPDATA%\Claude\claude_desktop_config.json
```

### 8.3 适合你的论文流程的用法

这个 MCP 很适合做：

- 把实验结论整理成 Word 报告
- 先产出 `.docx` 初稿，再人工修订
- 为导师或合作者输出 Word 版本的阶段性材料

---

## 9. Stata MCP：统计分析协作

仓库：

- [hanlulong/stata-mcp](https://github.com/hanlulong/stata-mcp)

注意它的定位：

- 这是 **VS Code / Cursor / Antigravity 扩展**
- 不是像 Zotero MCP 或 Word MCP 那样直接 `pip install` 就能跑的普通 stdio 脚本
- 需要你本机已经安装 **Stata 17+**

### 9.1 适合什么场景

如果你的论文流程里需要：

- Stata 做统计检验
- `.do` 文件生成图表
- AI 直接驱动 Stata 跑分析

那么它很有用。

### 9.2 最常见安装方式

在 VS Code 中安装扩展：

```powershell
code --install-extension DeepEcon.stata-mcp
```

或在 Cursor 中安装 `.vsix` 包。更完整步骤请看上游 README。

### 9.3 与 Codex 联动

上游文档明确给出了 Codex 接入方式。因为 Stata MCP 是一个 SSE 服务，所以需要通过 `mcp-proxy` 桥接。

先安装：

```powershell
pip install mcp-proxy
```

然后把下面内容加入 Codex 配置文件：

- Windows: `%USERPROFILE%\.codex\config.toml`

```toml
[mcp_servers.stata-mcp]
command = "mcp-proxy"
args = ["http://localhost:4000/mcp"]
```

前提是：

- Stata MCP 扩展已经在 VS Code / Cursor 中安装
- IDE 已经打开
- 扩展已经自动启动了 `http://localhost:4000/mcp`

---

## 10. 推荐的论文协作组合

如果你的目标是把“论文选题 -> 文献 -> 实验 -> 图表 -> 论文初稿”尽量串起来，我建议这样组合：

### 10.1 最小可运行组合

- `FluidAgent Pro`
- `Gemini API`
- `Codex CLI`
- `Typst`

### 10.2 文献增强组合

- `FluidAgent Pro`
- `Gemini API`
- `Zotero MCP`

这样你可以把文献搜索、条目读取、注释提取和论文摘要写作连起来。

### 10.3 导师协作输出组合

- `FluidAgent Pro`
- `Office Word MCP`

这样你可以在 Typst / Markdown 之外，再给出 `.docx` 版本材料。

### 10.4 统计分析组合

- `FluidAgent Pro`
- `Stata MCP`

适用于你确实要把 Stata 纳入实验或附加统计环节。

---

## 11. 最常见问题

### 11.1 运行时提示缺少 Gemini API Key

先检查：

```powershell
echo $env:GEMINI_API_KEY
echo $env:GOOGLE_API_KEY
```

至少要有一个不为空。

### 11.2 `fluid-agent-pro` 命令找不到

重新执行：

```powershell
pip install -e .
```

如果仍然不行，直接用：

```powershell
python fluid_agent_pro.py --workspace .
```

### 11.3 `typst` 找不到

说明 Typst 没装好或不在 `PATH`。Phase 0 会直接检查这一点。

### 11.4 Zotero MCP 无法读取本地库

先确认：

- Zotero 已启动
- 本地 API 已启用
- 使用的是本地模式，或正确设置了 Zotero Web API 参数

### 11.5 Stata MCP 不工作

先确认：

- Stata 17+ 已安装
- VS Code / Cursor 扩展已安装
- 状态栏中 Stata MCP 服务已经启动
- `http://localhost:4000/mcp` 可用

---

## 12. 你现在可以怎么开始

如果你只想先把主项目跑起来，按下面顺序最稳：

1. 安装本项目：`pip install -e .`
2. 设置 `GEMINI_API_KEY`
3. 准备 `research_plan.md` 和 `metadata.json`
4. 启动：

```powershell
fluid-agent-pro --workspace .
```

如果你想增强论文协作，再按需添加：

- 文献协作：Zotero MCP
- Word 文档协作：Office Word MCP
- 统计分析协作：Stata MCP

---

## 13. 参考链接

- Gemini API quickstart: [https://ai.google.dev/gemini-api/docs/quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
- Google AI Studio: [https://aistudio.google.com/](https://aistudio.google.com/)
- Zotero MCP: [https://github.com/54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp)
- Stata MCP: [https://github.com/hanlulong/stata-mcp](https://github.com/hanlulong/stata-mcp)
- Office Word MCP Server: [https://github.com/GongRzhe/Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server)

---

## 14. Springer LaTeX Template Integration

The project now supports a Springer `svjour3` LaTeX template as an alternative to the original Typst export flow.

If your workspace contains the journal package:

```text
D:\Code\paper_pass_skill\fluid-agent-pro\468198_LaTeX_DL_468198_01072021\LaTeX_DL_468198_240419
```

the template export stage will automatically prefer that template and generate:

- `paper_final.tex`
- `template_export_manifest.json`
- `paper.pdf` if a local TeX toolchain is available

### 14.1 Recommended workflow

1. Keep writing and revising the scientific content in `paper.typ` through the normal FluidAgent Pro workflow.
2. When the workflow reaches `STATE_PAPER_TEMPLATE_EXPORT`, the controller will:
   - detect the Springer template
   - convert the repaired draft into `paper_final.tex`
   - keep the manuscript structure aligned with `svjour3`
   - try to compile `paper.pdf` when `latexmk` or `pdflatex` is installed
3. Continue polishing `paper_final.tex` as your journal-ready draft.

### 14.2 Metadata fields worth adding

For better LaTeX front matter, extend `metadata.json` like this:

```json
{
  "title": "Real-Time Metal Surface Defect Detection with Improved YOLOv8",
  "subtitle": "Cross-Dataset Modeling and Deployment-Oriented Evaluation",
  "authors": ["Your Name"],
  "affiliations": ["Your School or Lab"],
  "address": "City, Country",
  "email": "your_email@example.com",
  "keywords": [
    "metal surface defect detection",
    "YOLOv8",
    "NEU DET",
    "GC10 DET",
    "transfer learning"
  ],
  "venue": "Journal of Real-Time Image Processing"
}
```

### 14.3 If you want PDF output locally

Install one of the following:

- MiKTeX: [https://miktex.org/download](https://miktex.org/download)
- TeX Live: [https://www.tug.org/texlive/](https://www.tug.org/texlive/)

After installation, make sure `latexmk` or `pdflatex` is available in `PATH`.

You can check with:

```powershell
Get-Command latexmk,pdflatex,bibtex
```

If TeX tools are missing, the project will still generate `paper_final.tex`; only the PDF compilation step will be skipped.

### 14.4 Practical note

This integration is best used for:

- generating the first journal-formatted draft
- aligning title, abstract, sections, authors, affiliations, and bibliography with the official template
- continuing later manual refinement in LaTeX or with Word/Zotero-assisted writing

It is not meant to replace your experimental code. Your model code, datasets, and analysis scripts should remain in the project workspace as before.
