# 每篇文本一行（per-text table）

生成脚本：`analysis/build_per_text_table.py`（2026-10-23）。
数据源：`data/processed/sample_v1.json`、`metrics_filtered_alpha.json`、`metrics_results.json`、
`analysis/metrics_extended_results.json`。只含 Human 与四个模型，不含 gpt35 等其它条件。

## 口径

- `word_count`：spaCy `en_core_web_sm` 的字母词（`token.is_alpha`）计数，五组同一口径；
  与 `metrics_extended_results.json` 的 `n_words` 逐篇全等（149/149）。
- `MATTR`：移动平均类符形符比，窗口固定 **100**（`lexical_diversity.lex_div.tokenize`；
  仅对完整窗口取平均）。`metric-specification.md` 未规定 MATTR 窗口；此处沿用
  `analysis/mattr_group_ttest.py` 与报告 §3.4 的固定窗口 100。
- `mean_sentence_length`：句内字母词数的均值（`metrics_results.json: sentence_length`）。
- `sentence_length_CV`：句长 `pstdev / mean`（`metrics_extended_results.json`）。
- `mean_paragraph_length`：段内字母词数的均值（`metrics_results.json: paragraph_length`）。

## 各组样本数

| group | model | n |
|---|---|---|
| Human | Human | 30 |
| 国外 | Claude-Sonnet-5-High | 30 |
| 国外 | GPT-5.6-Luna | 30 |
| 国内 | DeepSeek-V4-Flash | 30 |
| 国内 | Kimi-K3 | 29 |
| **合计** | | **149** |

## 前 20 行预览

| prompt_id | model | group | word_count | MATTR | mean_sentence_length | sentence_length_CV | mean_paragraph_length | n_sentences | n_paragraphs |
|---|---|---|---|---|---|---|---|---|---|
| 0 | Human | Human | 261 | 0.727341 | 6.525000 | 1.012531 | 130.000000 | 40 | 2 |
| 0 | Claude-Sonnet-5-High | 国外 | 637 | 0.773911 | 11.796296 | 0.807751 | 31.850000 | 54 | 20 |
| 0 | GPT-5.6-Luna | 国外 | 777 | 0.776881 | 6.876106 | 0.731680 | 7.063636 | 113 | 110 |
| 0 | DeepSeek-V4-Flash | 国内 | 525 | 0.749910 | 7.000000 | 0.758086 | 26.250000 | 75 | 20 |
| 0 | Kimi-K3 | 国内 | 624 | 0.768278 | 11.142857 | 0.802947 | 52.000000 | 56 | 12 |
| 1 | Human | Human | 757 | 0.680919 | 10.093333 | 0.641709 | 20.382353 | 75 | 34 |
| 1 | Claude-Sonnet-5-High | 国外 | 612 | 0.778059 | 15.692308 | 0.481475 | 40.800000 | 39 | 15 |
| 1 | GPT-5.6-Luna | 国外 | 757 | 0.759149 | 8.053191 | 0.608427 | 10.093333 | 94 | 75 |
| 1 | DeepSeek-V4-Flash | 国内 | 807 | 0.736961 | 10.480519 | 0.654334 | 38.428571 | 77 | 21 |
| 1 | Kimi-K3 | 国内 | 641 | 0.753060 | 17.324324 | 0.785172 | 49.307692 | 37 | 13 |
| 2 | Human | Human | 723 | 0.700218 | 10.041667 | 0.761939 | 40.647059 | 72 | 17 |
| 2 | Claude-Sonnet-5-High | 国外 | 655 | 0.727577 | 17.236842 | 0.609550 | 72.777778 | 38 | 9 |
| 2 | GPT-5.6-Luna | 国外 | 731 | 0.725055 | 7.860215 | 0.631196 | 9.024691 | 93 | 81 |
| 2 | DeepSeek-V4-Flash | 国内 | 682 | 0.689000 | 9.884058 | 0.677384 | 62.000000 | 69 | 11 |
| 2 | Kimi-K3 | 国内 | 801 | 0.715807 | 11.125000 | 0.818496 | 36.409091 | 72 | 22 |
| 3 | Human | Human | 356 | 0.681955 | 10.171429 | 0.607638 | 22.571429 | 35 | 14 |
| 3 | Claude-Sonnet-5-High | 国外 | 682 | 0.724803 | 17.487179 | 0.934619 | 42.625000 | 39 | 16 |
| 3 | GPT-5.6-Luna | 国外 | 801 | 0.736382 | 7.348624 | 0.567657 | 8.900000 | 109 | 90 |
| 3 | DeepSeek-V4-Flash | 国内 | 670 | 0.736117 | 9.852941 | 0.594675 | 41.875000 | 68 | 16 |
| 3 | Kimi-K3 | 国内 | 635 | 0.765151 | 16.282051 | 0.681641 | 52.916667 | 39 | 12 |

## 缺失清单

| prompt_id | model | group | 缺失字段 | 说明 |
|---|---|---|---|---|
| 26 | Kimi-K3 | 国内 | text,word_count,MATTR,mean_sentence_length,sentence_length_CV,mean_paragraph_length | 语料中无该篇文本（sample_v1.json 无该字段或为空） |

Kimi-K3 缺 `prompt_id=26`（整篇无文本），因此 Kimi 组 n=29；该篇不进入任何按篇统计。
缺失清单同时以 CSV 形式保存在 `analysis/per-text-table-missing.csv`。

## 校验记录

- 行数 149 = 30 prompts × 5 组 − Kimi 缺 1 篇；各组 n 与上表一致。
- `word_count` 与独立汇总的 `metrics_extended_results.json: n_words` 逐篇相同（149/149）。
- Human 组 MATTR(100) 均值 = 0.6779849667，与
  `analysis/mattr_group_ttest_results.json` 的 `human_mean` = 0.6779849286 一致（差 < 1e-6，来自 CSV 保留 6 位小数的舍入）。
- 抽 5 篇（seed=42）核对 `word_count`：p5/DeepSeek-V4-Flash=676, p1/Claude-Sonnet-5-High=612, p14/Human=367, p12/GPT-5.6-Luna=803, p11/GPT-5.6-Luna=730。

## 备注

- Human 原文来自 HuggingFace 数据集，标点前后带空格；若用 `len(text.split())` 会把标点
  误计为词（如 prompt 0：split=339 vs 字母词=261）。本表统一用字母词口径，避免把
  语料的排版差异当成文本长度差异。
