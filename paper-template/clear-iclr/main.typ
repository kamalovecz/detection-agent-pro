#import "@preview/clear-iclr:0.7.0": iclr2025
#import "/logo.typ": LaTeX, LaTeXe

#let authors = (
  (
    names: ([Author Name]),
    affilation: [School or Laboratory of Intelligent Manufacturing],
    address: [City, Country],
    email: "author@example.com",
  ),
)

#show: iclr2025.with(
  title: [Real-Time Metal Surface Defect Detection with Improved YOLOv8],
  authors: authors,
  keywords: (
    #text("metal surface defect detection"),
    #text("YOLOv8"),
    #text("transfer learning"),
    #text("industrial deployment"),
  ),
  abstract: [
    This template shell is retained for FluidAgent Pro compatibility. Replace
    the metadata and manuscript body with the generated research content for
    NEU DET, GC10 DET, and port_defect based experiments.
  ],
  bibliography: bibliography("main.bib"),
  appendix: [],
  accepted: false,
)

= Abstract

This placeholder file is only a template scaffold. The controller will rewrite
`paper_final.typ` using your generated manuscript content.

= Introduction

Describe the industrial motivation, defect categories, and the limitations of
baseline YOLOv8 under complex texture interference, low contrast, and
real-time constraints.

= Methods

Summarize the improved YOLOv8 design, including shallow detail enhancement,
high-resolution small-defect representation, multi-scale fusion optimization,
and transfer-learning strategy.

= Results

Report quantitative comparisons on NEU DET, GC10 DET, and port_defect, plus
ablation and deployment-oriented metrics such as Params, FLOPs, FPS, latency,
and model size when available.

= Discussion

Discuss generalization across datasets, tiny-defect behavior, failure cases,
and the tradeoff between detection accuracy and deployment efficiency.

= Conclusion

Summarize the engineering and academic value of the proposed method for
real-world metal surface inspection.
