# 路由与高频入口

## 主控路由原则

- 一次任务只设一个主技能。
- 如有需要，可补一个到两个辅技能。
- 如果任务同时包含科研判断与代码落地，先做科研判断，再转 `code-to-codex-planner`。

## 高频入口映射

| 用户意图 | 主技能 | 辅技能 | 典型产出 |
|---|---|---|---|
| 基于这些 PDF 帮我完成文献综述 | `literature-reviewer` | `academic-writer` | 综述框架、对比矩阵、研究空白、Related Work 草稿 |
| 根据我的论文初稿给我提供审稿意见和建议 | `review-commentator` | `submission-strategist` | reviewer 式批评、改稿优先级、投稿风险 |
| 根据我的论文初稿提供其中句子的特定含义和属性和适合插入哪些参考文献 | `academic-writer` | `literature-reviewer` | 句子属性、引用插槽、检索关键词、改写建议 |

## 全流程路由图

1. 选题模糊 -> `topic-advisor`
2. 需要补文献证据 -> `literature-reviewer`
3. 需要提出创新点 -> `method-innovator`
4. 需要做实验方案 -> `experiment-designer`
5. 需要把方案变成实现任务 -> `code-to-codex-planner`
6. 实验跑完需要判断结论 -> `result-analyst`
7. 需要写论文段落 / Related Work -> `academic-writer`
8. 需要 reviewer 视角批评 -> `review-commentator`
9. 需要决定投哪里 / 如何 rebuttal -> `submission-strategist`
10. 需要基金申请文本 -> `grant-writer`
11. 需要汇报、答辩或海报 -> `presentation-coach`

## 何时使用主控 `research-orchestrator`

优先在以下场景使用主控：

- 用户只给了一个模糊需求，尚不清楚该用哪一个子专家
- 用户一次性给了 PDF、初稿、结果表和投稿目标，需要统一协调
- 用户希望获得“先做什么、后做什么”的全流程计划
- 用户明确提出“帮我组织整套研究工作流”
