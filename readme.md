## 简明文档

如果你只想快速了解项目，可以先看：

- [项目简介](project_description.md)
- [快速使用](usage.md)

如果你想了解完整的设计背景、状态机和模块划分，可以继续阅读下面的 SDD。

### 📝 FluidAgent Pro: 软件架构设计方案 (SDD)

#### **0. 项目背景与业务上下文 (Project Background & Domain Context)**

* **业务场景** ：本系统是一个专门针对计算流体力学 (CFD) 领域的自动化科研流水线。核心业务是将前沿文献中的新算法（例如各类扩展的多相流模型、复杂的颗粒曳力方程）自动化植入现有的求解器软件中，并与原生模型进行横向对比分析。
* **用户画像** ：主要使用者为致力于密集气固两相流 (dense gas-solid two-phase flows) 研究的博士级研究员。
* **核心技术栈环境** ：
* **底层物理计算** ：高度依赖现代 C++ 编写的底层仿真求解器代码。
* **数据分析与绘图** ：高度依赖 Python 生态（如 pandas 等）。
* **自动化调度** ：依赖 Linux/WSL 环境下的命令行与 Bash 脚本执行环境。
* **痛点与设计妥协** ：CFD 仿真具有“高耗时”、“易发散”、“物理约束强”的特点。因此，系统**绝对不能**像普通软件那样毫无顾忌地一路狂奔执行到底。在关键的“C++ 算法植入编译后”与“海量数据特征提取后”，必须设置坚如磐石的  **Human-in-the-Loop (人工干预断点)** 。系统必须具备极强的异常捕获能力，并在终端清晰地将仿真守恒日志或残差报错抛给人类审查。

#### 1. 核心架构模式：有限状态机 (Finite State Machine, FSM)

整个系统将作为一个以 CLI 为主干的状态机运行。程序运行时会读取本地的 `.agent_state.json` 文件来确定当前处于哪个阶段。

**状态定义 (States):**

* `STATE_INIT`: 检查工作目录环境（解析 `research_plan.md` 和 `metadata.json`）。
* `STATE_CODING_VERIFY`: 调度 Codex 进行 C++ 代码集成与初步物理量守恒验证。
* `STATE_WAIT_VERIFY_REVIEW`: 挂起进程，等待人类在命令行审查验证日志。
* `STATE_DATA_ANALYSIS`: 调度 Codex 编写 Python 脚本进行参数化扫描和生成图表。
* `STATE_WAIT_ANALYSIS_REVIEW`: 挂起进程，等待人类审查图表和数据统计特征；如果发现求解器实现本身有误，可以在这里回退到 Phase 1 重新修改代码。
* `STATE_PAPER_WRITING`: 调度 Gemini API 根据通过的数据和 `metadata.json` 生成 Typst 论文。
* `STATE_PAPER_FIX`: 由 Codex 对论文草稿做 Typst 语法、引用与结构修复。
* `STATE_WAIT_PAPER_REVIEW`: 挂起进程，等待人类审查论文修复结果。
* `STATE_PAPER_TEMPLATE_EXPORT`: 由 Codex 基于 `paper-template/clear-iclr/` 模板重排 Typst，并输出最终 PDF。
* `STATE_WAIT_PAPER_TEMPLATE_REVIEW`: 挂起进程，等待人类审查模板化导出结果。
* `STATE_DONE`: 流程结束。

#### 2. 目录结构与数据流约定

系统强依赖于标准化的工作空间约定。

```text
workspace/
├── research_plan.md       # (输入) Gemini Web端生成的标准化研究方案
├── metadata.json          # (输入) 论文元数据 (Title, Authors, Reference DOI)
├── .agent_state.json      # (系统) 状态机持久化文件，记录当前执行到哪一步
├── src/                   # (输出) Codex 生成的 C++ 代码和编译脚本
├── analysis/              # (输出) Codex 生成的 Python 画图脚本和 CSV 数据
├── logs/                  # (输出) Codex 运行的验证日志 (如 verify.log)
├── plots/                 # (输出) 最终的对比折线图/云图
└── paper.typ              # (输出) 最终生成的 Typst 论文源文件
```

#### 3. 核心模块设计 (Python 类结构)

**Module 1: `PlanParser` (方案解析器)**

* **职责**: 解析 `research_plan.md`。这个 Markdown 必须有严格的 Heading（如 `## Phase 1: Verification`，`## Phase 2: Analysis`）。
* **行为**: 提取出不同阶段的自然语言描述，将其作为独立的 Prompt 喂给后期的 Codex。

**Module 2: `AgentContext` (状态管理器)**

* **职责**: 维护 `.agent_state.json`。
* **行为**: 包含 `load_state()`, `save_state()`, `transition_to(next_state)`。如果用户意外关闭了终端，重新运行脚本时可以从上一个 `WAIT_REVIEW` 状态恢复。

**Module 3: `CodexDelegator` (执行器封装)**

* **职责**: 与本地 Codex CLI 交互。
* **行为**:
  * 接收 `PlanParser` 切片出来的子任务。
  * 动态生成临时文件 `current_task.txt` 交给 Codex。
  * 监控 Codex 的执行，等待其输出结束语后自动退出 Codex 进程（类似于我们之前的稳定版逻辑）。

**Module 4: `HumanReviewCLI` (人工审查网关)**

* **职责**: 在状态机达到 `WAIT` 状态时阻塞程序。
* **行为**:
  * 在终端打印提示：“[Action Required] 请检查 `logs/verify.log`。输入 'Y' 批准并进入下一步，输入 'N' 并附带修改意见打回给 Codex，输入 'B' 可在论文阶段回退到 Phase 2，输入 'C' 可咨询 Codex：”
  * 如果用户输入意见（如“发现动量不守恒”），则状态机**回滚**到上一个活动状态，并将意见拼接到 Codex 的 Prompt 中重新执行。
  * 当用户在 Phase 3 选择 `B` 时，工作流会回退到 Phase 2，清除论文阶段的生成产物，并重新以分析阶段为目标继续迭代。

**Module 5: `GeminiWriter` (论文引擎)**

* **职责**: 组装所有终态数据，调用 Gemini API。
* **行为**: 读取 `research_plan.md` 中的理论框架，结合 `metadata.json` 的引文信息，以及 `analysis/` 下的数据摘要，利用 prompt 模板一次性生成 `.typ` 格式文本。

#### 4. 控制流与异常处理 (Control Flow & Fail-Safes)

* **重试机制**: 在 `GeminiWriter` 中必须保留针对 `503/429` 状态码的 Exponential Backoff（指数退避）重试逻辑。
* **增量修改 (Incremental Updates)**: 当人类在 `WAIT` 节点打回重做时，Codex 应当基于当前目录下的已有代码进行修改，而不是从零开始重写（利用 Codex/Aider 自带的 Git commit 分析或文件读取能力）。

---

### 🚀 给 Codex 的开发指令

当你准备好让 Codex 帮你写这套框架时，你只需要将上面的设计文档连同下面这句话发给它：

> "请作为高级 Python 架构师，根据上述 SDD 编写 `fluid_agent_pro.py`。要求使用面向对象编程 (OOP)，实现完整的状态机逻辑和人工交互 CLI。你可以使用 `json`, `os`, `subprocess` 等标准库。请先给出核心框架和类的骨架代码。"

### 💡 下一步建议

为了让这个自动化流程不崩溃，整个系统的“命脉”在于第一步网页端生成的 **`research_plan.md` 的格式必须极其规范**（程序才能通过正则表达式或特定标题把它切开）。

**你需要我为你设计一份配套的 `research_plan.md` 模板标准吗？** 以后你在网页端和 Gemini 讨论完算法后，直接让它按这个模板把方案总结出来，就能无缝对接到本地代码了。

---

### 📦 当前封装形态

当前这套系统已经可以作为一个可安装的本地 CLI 软件运行：

```bash
pip install -e .
fluid-agent-pro --workspace /path/to/project
```

如果要清理工作区里生成的中间文件和缓存，但保留 `pip install -e` 产生的 editable-install 元数据：

```bash
fluid-agent-pro --clear --workspace /path/to/project
```

如果连 `src/` 也要一起清理：

```bash
fluid-agent-pro --clear-hard --workspace /path/to/project
```

如果需要连 `pip install -e` 产生的中间文件也一起删掉，再额外加上：

```bash
fluid-agent-pro --clear --purge-install --workspace /path/to/project
```

如果需要“重置后重新开始”，先执行一次 `--clear` 或 `--clear-hard`，必要时再加 `--purge-install`，然后正常启动工作流即可。

如果要使用桌面 GUI：

```bash
pip install -e .[gui]
fluid-agent-pro-gui
```

GUI 里也提供了 `Clear Workspace` 按钮，以及 `Include src/` / `Purge editable-install files` 选项用于切换清理范围，Phase 2 审查提供 `Back P1` 按钮用于回退到 Phase 1（CLI 里同时接受 `P1` 和 `B`），Phase 3 审查提供 `Back P2` 按钮用于回退到 Phase 2。

**最小项目输入**
- `fluid_agent_pro.py`
- `research_plan.md`
- 外部 `paper-template/clear-iclr/` 模板目录

**建议的运行前准备**
- `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`
- `codex` CLI
- `typst`
- 你的真实 CFD 工程代码、数据和 `metadata.json`

后续如果要正式产品化，再把配置中心、跨平台安装器和外部模板路径管理继续补强即可；目前先保持 CLI/GUI 共用控制器的稳定性最重要。
