

# Research Plan: research_plan.md

## Phase 0: Environment Setup

**Toolchain Detection:**

* 在执行任何处理和编译之前，脚本必须首先检测工作流所需的工具链环境。
* 验证 Python 环境以及 `pandas` 和 `matplotlib` 库的可用性。
* 必须通过在系统终端执行 `typst --version` 命令来检测排版工具 Typst 的环境。
* 如果未检测到上述任何关键工具（尤其是 Typst），程序必须直接停止运行，并向终端输出明确的错误提示告知用户环境缺失。

## Phase 1: Implementation & Verification

**Objective:** 采用有限体积法 (FVM) 和 SIMPLE 算法求解二维不可压缩顶盖驱动方腔流，并在 **$Re = 1000$** 条件下验证求解器精度。

**C++ Implementation Guide:**

* **构建一个覆盖坐标范围 **$x \in [0, 1]$** 和 **$y \in [0, 1]$** 的 **$129 \times 129$** 均匀笛卡尔网格 **^^^^^^^^^^^^^^^^^^。
* 实现 SIMPLE 压力-速度耦合算法的主循环，包括动量预测和压力校正步骤。
* **针对对流项，应用带有延迟校正 (deferred correction) 的一阶迎风差分格式，以在维持对角占优与稳定性的同时恢复二阶精度 **^^。
* **设定标准边界条件：顶部驱动壁面速度设为 **$u=1, v=0$^^；左侧、右侧、底部固定壁面设定为无滑移条件 **$u=0, v=0$**。
  **Verification Criteria:**
* 确保连续性方程的质量残差在每个外部迭代步内下降至设定的收敛标准（如 **$10^{-4}$** 容差）。
* 验证算法在整个 **$129 \times 129$** 网格范围内的全局质量与动量守恒。
  **Expected Logs:** `verify.log` 中需要输出每次外部 SIMPLE 迭代的步数、动量残差以及质量连续性残差。

## Phase 2: Data Analysis & Comparison

**Analysis Script Requirements:**

* 编写 Python 脚本处理 C++ 求解器输出的流场结果 CSV 文件。
* **读取并解析存放在 **`<span class="citation-171">ref.data</span>` 目录下的基准文本文件 `<span class="citation-171">ghiau.u.txt</span>` (Table I) ^^^^^^^^与 `<span class="citation-170">ghiav.v.txt</span>` (Table II) ^^^^^^^^。
* 必须准确提取文本文件中 **$Re = 1000$** 条件下对应的数据列进行精确的横向对比。
  **Plotting Instructions:**
* **绘制纵向中心线速度对比图：Y 轴为无量纲坐标 **$y$**，X 轴为速度 **$u$**。提取的 **`<span class="citation-169">ref.data/ghiau.u.txt</span>` 基准文献数据必须绘制为离散散点 (Scatter points)，而新 FVM 求解器的模拟数据必须绘制为平滑曲线 (Smooth line) ^^。图例对比项为 "New Model (Curve)" vs. "Ghia 1982 (Scatter)"，保存文件名为 `u_comparison_plot.png`。
* **绘制横向中心线速度对比图：Y 轴为速度 **$v$**，X 轴为无量纲坐标 **$x$**。同样，**`<span class="citation-168">ref.data/ghiav.v.txt</span>` 文献数据绘制为离散散点，模拟数据绘制为平滑曲线 ^^。图例对比项为 "New Model (Curve)" vs. "Ghia 1982 (Scatter)"，保存文件名为 `v_comparison_plot.png`。
  **Expected Metrics:** 重点关注涡心附近的峰值速度以及近壁面的速度梯度，确认代表模拟结果的平滑曲线是否能够精准穿过代表基准数据的散点 ^^。

## Phase 3: Paper Framework

**Results Structure:**

* 简述 FVM SIMPLE 求解器在 **$129 \times 129$** 网格下的迭代收敛历程与最终配置。
* 引用 `u_comparison_plot.png` 和 `v_comparison_plot.png` 两张图表，系统展示新求解器在 **$Re = 1000$** 时与 Ghia (1982) 表格数据的吻合度。
  **Discussion Focus:**
* 重点分析 SIMPLE 算法在当前网格分辨率下对不可压缩流场压力-速度耦合的处理精度。
* **探讨一阶迎风格式及其延迟校正对极值点数据的影响，以及可能存在的数值假扩散现象 **^^。
