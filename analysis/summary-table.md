# 四指标初步汇总（Human × 四模型）

数据源：`analysis/per-text-table.csv`（149 篇 = 5 组 × 30 prompts − Kimi 缺 1 篇）。只做描述统计，未跑检验、未做分类器。

> 标准差一律为**样本标准差（ddof = 1）**；方差比 = var(组) / var(Human)，同样按 ddof = 1 计算。Human 行按定义方差比 = 1.00。

## 速览：均值 ± 标准差

| 组 | N | MATTR | 句长 CV | 平均段长 |
|---|---|---|---|---|
| Human | 30 | 0.678 ± 0.057 | 0.674 ± 0.132 | 61.5 ± 104.3 |
| Claude | 30 | 0.777 ± 0.030 | 0.766 ± 0.124 | 37.4 ± 11.7 |
| GPT | 30 | 0.763 ± 0.030 | 0.673 ± 0.087 | 10.1 ± 9.3 |
| DeepSeek | 30 | 0.729 ± 0.027 | 0.674 ± 0.090 | 45.4 ± 22.6 |
| Kimi | 29 | 0.757 ± 0.029 | 0.739 ± 0.141 | 45.3 ± 17.5 |

## 分指标明细（含 RQ2 方差比）

### MATTR

| 组 | N | 均值 | 标准差 | AI/Human 方差比 | 均值差 vs Human |
|---|---|---|---|---|---|
| Human | 30 | 0.678 | 0.057 | 1.00（参照） | — |
| Claude | 30 | 0.777 | 0.030 | 0.29 | +14.7% |
| GPT | 30 | 0.763 | 0.030 | 0.28 | +12.5% |
| DeepSeek | 30 | 0.729 | 0.027 | 0.22 | +7.5% |
| Kimi | 29 | 0.757 | 0.029 | 0.26 | +11.6% |

- **均值 4/4 组高于 Human（+7.5% ~ +14.7%）**；变异 4/4 组小于 Human（方差比 0.22–0.29，ddof=1）。四项里唯一可以下明确结论的一项：AI 文本词汇多样性更高，且组内更齐。

图：`analysis/figures/mattr-distribution.png`（300 dpi，矢量版同名 `.pdf`）

### 句长 CV

| 组 | N | 均值 | 标准差 | AI/Human 方差比 | 均值差 vs Human |
|---|---|---|---|---|---|
| Human | 30 | 0.674 | 0.132 | 1.00（参照） | — |
| Claude | 30 | 0.766 | 0.124 | 0.88 | +13.6% |
| GPT | 30 | 0.673 | 0.087 | 0.43 | -0.2% |
| DeepSeek | 30 | 0.674 | 0.090 | 0.47 | +0.0% |
| Kimi | 29 | 0.739 | 0.141 | 1.14 | +9.6% |

- **均值方向不一致（Claude、Kimi 高于 Human；GPT、DeepSeek 与 Human 基本持平（-0.2% / +0.0%）；跨组范围 -0.2% ~ +13.6%）**；变异 3/4 组小于 Human（方差比 0.43–1.14）。这一项不支持「AI 句子更规整」的直觉：两组高于人类、两组与人类持平；只作描述，不下结论。

图：`analysis/figures/sentence-length-cv-distribution.png`（300 dpi，矢量版同名 `.pdf`）

### 平均段长

| 组 | N | 均值 | 标准差 | AI/Human 方差比 | 均值差 vs Human |
|---|---|---|---|---|---|
| Human | 30 | 61.5 | 104.3 | 1.00（参照） | — |
| Claude | 30 | 37.4 | 11.7 | 0.01 | -39.2% |
| GPT | 30 | 10.1 | 9.3 | 0.01 | -83.6% |
| DeepSeek | 30 | 45.4 | 22.6 | 0.05 | -26.2% |
| Kimi | 29 | 45.3 | 17.5 | 0.03 | -26.3% |

- **均值 4/4 组低于 Human（-83.6% ~ -26.2%）**；变异 4/4 组小于 Human（方差比 0.01–0.05，ddof=1）。只作描述：人类文本里个别篇目整篇只有 1 段（最长 541 词），Human 的 SD 主要由此撑大，方差比低至 0.01 不能读成「AI 段落更整齐」；结论须先过段落切分核查。

图：`analysis/figures/paragraph-length-distribution.png`（300 dpi，矢量版同名 `.pdf`）

## 图注

- **MATTR**（`mattr-distribution.png`）：MATTR (moving-average TTR, window = 100)。一篇文章一个点（横向抖动避免重叠），箱体为四分位距、中线为中位数、须为 1.5×IQR；灰色带为 Human 的 25–75 分位区间。Human n = 30；Claude n = 30；GPT n = 30；DeepSeek n = 30；Kimi n = 29。
- **句长 CV**（`sentence-length-cv-distribution.png`）：Sentence-length CV (within text: SD / mean)。一篇文章一个点（横向抖动避免重叠），箱体为四分位距、中线为中位数、须为 1.5×IQR；灰色带为 Human 的 25–75 分位区间。Human n = 30；Claude n = 30；GPT n = 30；DeepSeek n = 30；Kimi n = 29。
- **平均段长**（`paragraph-length-distribution.png`）：Mean paragraph length (words per paragraph, log scale)。一篇文章一个点（横向抖动避免重叠），箱体为四分位距、中线为中位数、须为 1.5×IQR；灰色带为 Human 的 25–75 分位区间。Human n = 30；Claude n = 30；GPT n = 30；DeepSeek n = 30；Kimi n = 29。

## 备注

- 组名口径：GPT = GPT-5.6-Luna，Claude = Claude-Sonnet-5-High，DeepSeek = DeepSeek-V4-Flash，Kimi = Kimi-K3（与任务①一致，不含 gpt35 等其它条件）。
- Kimi 为 29 篇：prompt 26 在语料中无 Kimi 文本（`analysis/per-text-table-missing.csv`），故 N 与任务①的表一致。
- MATTR 窗口固定 100（`metric-specification.md` 未规定窗口，沿用 `analysis/mattr_group_ttest.py` 与报告 §3.4 的口径）。
- 段长对比前请先看段落切分核查结果（RAY-591 / `docs/2026-10-23-语料核查.md`）。
