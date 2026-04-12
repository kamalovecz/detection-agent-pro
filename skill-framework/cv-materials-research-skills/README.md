# CV Materials Research Skills

这是一套面向“计算机视觉 + 材料缺陷检测”的科研全流程专家 Skills，组织为 `1 个主控 Skill + 11 个子专家 Skill`。整体设计同时吸收了两个来源的优点：

- `awesome-ai-research-writing`：蒸馏出可复用的 `Role / Task / Constraints / Execution Protocol / Output` 提示骨架，以及高频科研写作入口。
- `nuwa-skill`：借鉴“主控路由 + references 下沉 + 阶段化协议 + 风险边界”的结构化 Skill 组织方式。

## 1. 套件目标

这套 Skills 不是通用科研顾问，而是固定约束在以下领域：

- 计算机视觉
- 材料缺陷检测

默认适配的典型任务包括：

- 选题、创新点与论文定位
- 基于 PDF 的文献综述与 Related Work
- 方法创新与实验设计
- 结果分析、图表叙事与论文写作
- 审稿意见、改稿策略、投稿策略
- 基金申请、汇报答辩、演示组织
- 将科研需求翻译成可直接交给 Codex 的实现任务

## 2. 目录结构

```text
cv-materials-research-skills/
├─ README.md
├─ references/
│  ├─ bilingual-switch.md
│  ├─ codex-handoff-guide.md
│  ├─ domain-constraints.md
│  ├─ evidence-and-citation-policy.md
│  ├─ prompt-skeletons.md
│  ├─ task-routing.md
│  └─ unified-output-template.md
├─ research-orchestrator/
│  └─ SKILL.md
├─ topic-advisor/
│  └─ SKILL.md
├─ literature-reviewer/
│  └─ SKILL.md
├─ method-innovator/
│  └─ SKILL.md
├─ experiment-designer/
│  └─ SKILL.md
├─ result-analyst/
│  └─ SKILL.md
├─ academic-writer/
│  └─ SKILL.md
├─ code-to-codex-planner/
│  └─ SKILL.md
├─ review-commentator/
│  └─ SKILL.md
├─ submission-strategist/
│  └─ SKILL.md
├─ grant-writer/
│  └─ SKILL.md
└─ presentation-coach/
   └─ SKILL.md
```

## 3. Skill 列表

| Skill | 角色定位 | 主要任务 |
|---|---|---|
| `research-orchestrator` | 主控调度 | 识别任务类型、路由子专家、统一输出模板、组织后续 handoff |
| `topic-advisor` | 选题顾问 | 收敛问题定义、创新点边界、题目定位、贡献框架 |
| `literature-reviewer` | 文献综述专家 | 基于 PDF/论文列表做综述、聚类、对比、空白点梳理 |
| `method-innovator` | 方法创新专家 | 提出保守可验证的创新方向、机制假设与优先级 |
| `experiment-designer` | 实验设计专家 | 基线、消融、数据集、指标、复现与公平性设计 |
| `result-analyst` | 结果分析专家 | 读表格/曲线/日志，判断结论是否成立并指出异常 |
| `academic-writer` | 学术写作专家 | 段落写作、句子功能分析、引用插槽、Related Work 组织 |
| `code-to-codex-planner` | 实现规划专家 | 把科研需求翻译成可交给 Codex 的最小实现任务 |
| `review-commentator` | 审稿评论专家 | 站在 reviewer 视角指出硬伤、可修复问题和改稿策略 |
| `submission-strategist` | 投稿策略专家 | 会议/期刊匹配、rebuttal、checklist、时间线安排 |
| `grant-writer` | 基金写作专家 | 项目摘要、意义、目标、里程碑、风险与可行性 |
| `presentation-coach` | 汇报答辩专家 | 口头报告、答辩、poster、slides、Q&A 准备 |

## 4. 统一输出约束

所有 Skill 都会强制使用统一输出模板：

1. 任务理解
2. 当前问题诊断
3. 建议方案
4. 风险点
5. 下一步行动
6. 可交给 Codex 的实现任务

模板细则见 `references/unified-output-template.md`。

## 5. 双语切换

默认语言是中文；如果用户显式切换，则切换到英文。

- 中文命令：`/lang zh`、`切换中文`、`中文模式`
- 英文命令：`/lang en`、`switch english`、`english mode`

详细规则见 `references/bilingual-switch.md`。

## 6. 三个高频任务入口

### 入口 1

`基于这些 PDF 帮我完成文献综述`

推荐路由：

`research-orchestrator -> literature-reviewer -> academic-writer`

适合输出：

- 文献主题聚类
- 代表性工作对比
- 研究空白与冲突点
- 可直接写入论文的 Related Work 结构

### 入口 2

`根据我的论文初稿给我提供审稿意见和建议`

推荐路由：

`research-orchestrator -> review-commentator -> submission-strategist`

适合输出：

- reviewer 式 Summary / Strengths / Weaknesses
- 真正致命问题 vs 可修问题
- rebuttal 与改稿优先级

### 入口 3

`根据我的论文初稿提供其中句子的特定含义和属性和适合插入哪些参考文献`

推荐路由：

`research-orchestrator -> academic-writer -> literature-reviewer`

适合输出：

- 句子语义与修辞功能标注
- claim 类型识别
- 适合插入的参考文献类型与检索关键词
- 哪些句子应该引用论文、哪些句子应该指向作者自己的图表/结果

## 7. 安装方式

### 7.1 安装到 Codex 本地 Skills 目录

建议复制“本目录下的全部内容”，不要只复制单个 Skill 文件夹，因为所有 Skill 都依赖同级 `references/`。

```powershell
$src = "D:\Code\paper_pass_skill\fluid-agent-pro\skill-framework\cv-materials-research-skills"
$dst = "$env:USERPROFILE\.codex\skills"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
```

### 7.2 安装到项目本地 `.claude/skills`

如果你在 Cursor / Claude Code 风格环境中使用项目级 Skills，可以这样复制：

```powershell
$src = "D:\Code\paper_pass_skill\fluid-agent-pro\skill-framework\cv-materials-research-skills"
$dst = "D:\YourProject\.claude\skills"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
```

### 7.3 使用提醒

- 请保持 12 个 Skill 文件夹与 `references/` 同级。
- 如果你只单独拷贝某一个 Skill，该 Skill 内部引用的共享规则会丢失。
- 当前版本优先保证 `SKILL.md` 可读性与可维护性，没有额外生成 `agents/openai.yaml`。

## 8. 设计蒸馏说明

### 从 `awesome-ai-research-writing` 蒸馏出的内容

- 任务入口驱动：围绕文献综述、实验分析、Reviewer 视角、句子级写作与引用等高频任务设计触发词。
- 提示骨架复用：统一采用 `角色定位 -> 任务 -> 约束 -> 执行协议 -> 输出格式` 的骨架。
- 证据优先：对 PDF、实验数据、论文初稿等用户给定材料优先处理，避免空泛写作。
- 可操作输出：强调不是泛泛建议，而是可直接改稿、补实验、补引用的动作项。

### 从 `nuwa-skill` 蒸馏出的内容

- 主控 Skill 负责路由与阶段化协调，而不是让所有子 Skill 彼此重复。
- 共享约束沉到 `references/`，避免 12 个 `SKILL.md` 重复膨胀。
- 每个 Skill 都写清楚“何时使用、如何执行、何时承认边界、下一步交给谁”。
- 输出里显式保留风险与边界，而不是只给乐观建议。

## 9. 完整操作流程

### Phase 1：确定入口

先把你的材料交给 `research-orchestrator`，材料可以是：

- PDF 文献包
- 论文初稿
- 表格、曲线、日志、实验结果
- 选题描述、研究想法
- 目标会议/期刊
- 代码仓库路径与待实现需求

### Phase 2：主控路由

`research-orchestrator` 会先识别当前最适合的主技能，再决定是否需要辅技能。例如：

- 选题不清楚：先去 `topic-advisor`
- 已有 PDF：先去 `literature-reviewer`
- 已有初稿：先去 `review-commentator`
- 已有实验结果：先去 `result-analyst`
- 已明确要落地代码：转 `code-to-codex-planner`

### Phase 3：子专家输出

子专家不会给“散乱建议”，而是统一输出：

- 当前阶段真正的问题在哪里
- 哪些建议可立即执行
- 哪些风险会影响论文可信度或投稿结果
- 哪些事项可以立即交给 Codex 实现

### Phase 4：Codex 落地

当输出中出现“可交给 Codex 的实现任务”后，可以直接把该部分交给 Codex 做代码实现、脚本补齐、实验配置修改、图表生成或论文排版改动。

推荐顺序：

1. `method-innovator` 或 `experiment-designer` 先明确研究动作
2. `code-to-codex-planner` 把动作转成最小实现任务
3. Codex 执行代码修改或分析脚本
4. `result-analyst` 再判断结果是否支撑论文主张

### Phase 5：论文与投稿闭环

当实验阶段稳定后，进入：

1. `academic-writer`：写段落、Related Work、摘要、图表说明
2. `review-commentator`：从 reviewer 视角发现硬伤
3. `submission-strategist`：决定投哪里、怎么补、怎么 rebuttal
4. `presentation-coach`：准备报告、答辩、海报

如果是项目申请或纵向经费，再引入：

`grant-writer`

## 10. 推荐使用姿势

### 场景 A：从 PDF 综述开始

```text
Use research-orchestrator with these PDFs to build a literature review for material defect detection.
```

### 场景 B：从论文初稿修改开始

```text
根据我的论文初稿给我提供审稿意见和建议，目标会议是 WACV。
```

### 场景 C：从实现需求开始

```text
根据这个实验方案，把需要改的模型模块、训练脚本和验证脚本整理成可交给 Codex 的实现任务。
```

### 场景 D：从句子级写作与引用开始

```text
根据我的论文初稿，分析这几句话的含义、属性以及适合插入哪些参考文献。
```

## 11. 后续扩展建议

如果你后面希望把这套 Skills 继续产品化，可以再加三类内容：

- `agents/openai.yaml`：补充 UI 展示元信息
- `examples/`：给每个 Skill 增加 1-2 个真实触发样例
- `scripts/`：把经常重复的 PDF 解析、文献表生成、实验结果汇总做成脚本

当前版本先保持最小但完整：`SKILL.md + references + README`。
