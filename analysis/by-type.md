# 任务类型趋势：按类聚合与逐 prompt 散点（RAY-602 第二步）

数据：`analysis/per-text-table.csv`（150 篇 = 30 prompts × 5 组）＋ `analysis/prompt-types.csv`（第一步四类，已由作者确认）。
脚本：`analysis/prompt_type_trends.py`；重跑会同时覆盖本文件、`by-type.csv` 与四张图。

## 口径

- **配对差值** = 同一 `prompt_id` 的 AI 值 − Human 值；先逐题作差，再在类型内取均值。正数表示该类 AI 高于 Human，负数表示低于。
- 四指标：`MATTR`（窗口 100）、`mtld`、`mean_sentence_length`（字母词/句）、`mean_paragraph_length`（字母词/段），全部直接取自 `per-text-table.csv`，未重算、未改口径。
- 每格 n = 该类型下的配对数（四模型均完整 30 对，故 n 即该类 prompt 数）。某格 n < 5 时在 CSV 的 `flag` 列标 `n<5`，此处不解读。
- **只报描述统计**：不做显著性检验、不建模、不作因果推断；n 只有 5–10，差值均值仅描述这份语料。

## 每类条数

| 类型 | n |
|---|---:|
| 奇幻/超自然 | 10 |
| 科幻/推想 | 6 |
| 现实/社会 | 5 |
| 极简提示/形式约束 | 9 |
| **合计** | **30** |

## MATTR (window 100)：AI − Human 配对差值均值

| 类型 (n) | Human 均值 | Claude 差值 | GPT 差值 | DeepSeek 差值 | Kimi 差值 |
|---:|---:|---:|---:|---:|---:|
| 奇幻/超自然 (10) | 0.684 | +0.091 | +0.072 | +0.043 | +0.074 |
| 科幻/推想 (6) | 0.701 | +0.071 | +0.068 | +0.033 | +0.062 |
| 现实/社会 (5) | 0.686 | +0.108 | +0.097 | +0.063 | +0.078 |
| 极简提示/形式约束 (9) | 0.651 | +0.122 | +0.103 | +0.065 | +0.098 |

## MTLD：AI − Human 配对差值均值

| 类型 (n) | Human 均值 | Claude 差值 | GPT 差值 | DeepSeek 差值 | Kimi 差值 |
|---:|---:|---:|---:|---:|---:|
| 奇幻/超自然 (10) | 64.3 | +52.1 | +29.8 | +23.2 | +41.3 |
| 科幻/推想 (6) | 82.8 | +54.4 | +37.4 | +16.1 | +38.9 |
| 现实/社会 (5) | 70.9 | +75.1 | +52.1 | +22.3 | +44.5 |
| 极简提示/形式约束 (9) | 62.8 | +61.2 | +40.1 | +12.9 | +36.6 |

## Mean sentence length (words/sentence)：AI − Human 配对差值均值

| 类型 (n) | Human 均值 | Claude 差值 | GPT 差值 | DeepSeek 差值 | Kimi 差值 |
|---:|---:|---:|---:|---:|---:|
| 奇幻/超自然 (10) | 9.88 | +3.14 | -2.94 | -1.36 | +1.81 |
| 科幻/推想 (6) | 9.92 | +4.33 | -2.80 | -0.39 | +1.96 |
| 现实/社会 (5) | 9.85 | +4.07 | -0.67 | +0.24 | +3.60 |
| 极简提示/形式约束 (9) | 11.41 | +4.69 | -3.40 | -1.14 | +3.37 |

## Mean paragraph length (words/paragraph)：AI − Human 配对差值均值

| 类型 (n) | Human 均值 | Claude 差值 | GPT 差值 | DeepSeek 差值 | Kimi 差值 |
|---:|---:|---:|---:|---:|---:|
| 奇幻/超自然 (10) | 42.4 | -6.6 | -35.1 | -7.2 | -4.1 |
| 科幻/推想 (6) | 75.5 | -36.0 | -67.5 | -29.1 | -31.9 |
| 现实/社会 (5) | 25.2 | +11.1 | -5.9 | +21.6 | +26.4 |
| 极简提示/形式约束 (9) | 93.6 | -55.2 | -84.1 | -38.4 | -41.6 |

## 逐 prompt 散点图

横轴 Human、纵轴 AI，每个点是一个 prompt，四模型四色＋四种点形；虚线为 y = x，点在线上方表示该题 AI 值高于 Human，下方表示低于。

- `analysis/figures/pair-mattr.png` — MATTR (window 100)，30 prompts × 4 models，300 dpi。
- `analysis/figures/pair-mtld.png` — MTLD，30 prompts × 4 models，300 dpi。
- `analysis/figures/pair-mean-sentence-length.png` — Mean sentence length (words/sentence)，30 prompts × 4 models，300 dpi。
- `analysis/figures/pair-mean-paragraph-length.png` — Mean paragraph length (words/paragraph)，30 prompts × 4 models，300 dpi，log–log 轴。

## 限制

- 每类只有 5–10 个 prompt，格内 n 很小；差值均值对个别极端文本敏感（尤其段长），只作趋势描述，不构成总体估计。
- 类型是按 prompt 写法人工判定的四类，不是随机分组；分类口径见 `prompt-types.csv` 的 `reason` 列。
- 图与表都不回答「AI 是否受任务类型影响更大」，只呈现这份语料上的配对差值。
