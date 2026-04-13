# `references.bib` 接入初稿指南

> 目标：把 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib) 真正接到当前初稿写作流程里，而不是停留在“有一个 Bib 文件但正文没在用”。

## 1. 当前仓库里有两条写作路径

### 路径 A：LaTeX 初稿

- 当前文件：[paper_final.tex](/D:/Code/paper_pass_skill/fluid-agent-pro/paper_final.tex)
- 适用场景：你想沿用现在这份 Springer 风格的 LaTeX 初稿继续改稿
- 当前状态：我已经把它改成了 BibTeX 接法，文末使用：

```tex
\bibliographystyle{spmpsci}
\bibliography{references}
```

这表示 LaTeX 会自动读取同目录下的 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib)。

### 路径 B：Typst 权威模板

- 当前模板：[main.typ](/D:/Code/paper_pass_skill/fluid-agent-pro/paper-template/clear-iclr/main.typ)
- 当前模板自带引用方式：

```typst
bibliography("main.bib")
```

- 这条路径默认读取的是 [main.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/paper-template/clear-iclr/main.bib)，不是根目录 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib)。

如果你后面决定切换到 Typst，再单独做一次 Bib 同步更稳。

## 2. LaTeX 路线怎么把参考文献真正导入出来

### 第一步：在正文中插入 citation key

你不能只放一个 `references.bib` 文件；正文里必须真的写 `\cite{...}`，文末参考文献才会出现。

当前 [paper_final.tex](/D:/Code/paper_pass_skill/fluid-agent-pro/paper_final.tex) 已经补了几个示例：

```tex
\cite{fang2020review,zou2021review}
\cite{jocher2024ultralytics}
\cite{song2013neudet}
\cite{lv2020gc10det}
```

后续你可以继续按照 [sentence_to_bibkey_mapping.md](/D:/Code/paper_pass_skill/fluid-agent-pro/origin_paper/sentence_to_bibkey_mapping.md) 补更多引用。

### 第二步：文末使用 BibTeX 入口

当前 [paper_final.tex](/D:/Code/paper_pass_skill/fluid-agent-pro/paper_final.tex) 末尾已经是：

```tex
\bibliographystyle{spmpsci}
\bibliography{references}
```

这里的 `references` 不带 `.bib` 后缀。

### 第三步：按 BibTeX 顺序编译

如果你在 [paper_final.tex](/D:/Code/paper_pass_skill/fluid-agent-pro/paper_final.tex) 所在目录编译，标准顺序是：

```powershell
pdflatex paper_final.tex
bibtex paper_final
pdflatex paper_final.tex
pdflatex paper_final.tex
```

如果你用 `latexmk`，可以直接：

```powershell
latexmk -pdf paper_final.tex
```

## 3. 常见失败点

- 只写了 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib)，但正文没有任何 `\cite{...}`。
- 写成 `\bibliography{references.bib}`。在 BibTeX 里通常应写成 `\bibliography{references}`。
- 运行了 `pdflatex`，但没有再跑 `bibtex`。
- 改了 Bib 条目后只编译 1 次，导致引用和文末列表没有刷新。
- citation key 拼写和 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib) 里的键不一致。

## 4. 这次我已经帮你做好的部分

- 已把 [paper_final.tex](/D:/Code/paper_pass_skill/fluid-agent-pro/paper_final.tex) 从手写 `thebibliography` 占位切换到 `BibTeX`。
- 已补了几处最基本的 `\cite{...}`，确保参考文献列表不再是空壳。
- 已把 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib) 里两个明显不规范的旧条目做了保守校正：
  - `zou2021review`
  - `liu2024slr`

## 5. 下一步建议

1. 先沿用 LaTeX 路线，把 [sentence_to_bibkey_mapping.md](/D:/Code/paper_pass_skill/fluid-agent-pro/origin_paper/sentence_to_bibkey_mapping.md) 里的推荐引用逐句补到 [paper_final.tex](/D:/Code/paper_pass_skill/fluid-agent-pro/paper_final.tex)。
2. 等正文 citation 基本补齐后，再做第二轮 `references.bib` 元数据规范化，继续清理其余老条目。
3. 如果最后决定切到 Typst，再把根目录 [references.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/references.bib) 同步到 [main.bib](/D:/Code/paper_pass_skill/fluid-agent-pro/paper-template/clear-iclr/main.bib)。
