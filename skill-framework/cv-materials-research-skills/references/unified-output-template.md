# 统一输出模板

所有 Skill 的最终回答都应使用同一套标题结构。不要漏掉任何一节。

## 中文模板

### 任务理解

- 用户现在到底要解决什么问题
- 输入材料有哪些
- 当前是否属于闭集模式或开集模式

### 当前问题诊断

- 当前最关键的证据缺口、逻辑缺口或实现缺口
- 哪些判断是已验证，哪些只是推断

### 建议方案

- 给出 2 到 5 条最重要、最可执行的方案
- 优先保守、可验证、低风险

### 风险点

- 可能导致论文结论失真、实验不公平、引用不准确、投稿不匹配的因素

### 下一步行动

- 按优先级列出 2 到 5 个直接动作
- 尽量区分“先补材料”与“先动手实现”

### 可交给 Codex 的实现任务

- 输出 3 到 7 个尽量可执行的任务
- 明确任务对象、产物与最快验证方式
- 如果当前阶段不适合编码，就明确写：
  - `当前无需编码实现，优先补证据 / 补实验 / 补文献`

## English Template

### Task Understanding

- What the user actually needs solved
- What artifacts are available
- Whether this is closed-world or open-world analysis

### Current Diagnosis

- The most important evidence, logic, or implementation gaps
- What is verified versus inferred

### Recommended Plan

- Provide 2 to 5 concrete and conservative recommendations

### Risks

- Anything that can weaken validity, fairness, citation quality, or venue fit

### Next Actions

- List 2 to 5 immediate actions in priority order

### Codex Implementation Tasks

- Provide 3 to 7 bounded tasks whenever coding or automation is helpful
- If coding is premature, explicitly say so

## 通用细则

- 如果信息不足，不要跳过该节，直接写明“待补信息”。
- 输出要以研究决策为中心，不要写成空泛的励志建议。
- 如果任务与引用、稿件或实验直接相关，必须显式写出证据边界。
