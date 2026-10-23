# analysis/ 数据表说明

本目录的 `per-text-table.csv` 是「每篇文本一行」的分析底表（王雅琴老师 2026-10-19 建议第 1 项），
也是词数分布图与后续四指标汇总的共同输入。

## 文件

| 文件 | 内容 |
|---|---|
| `per-text-table.csv` | 149 行：Human 30 + Claude 30 + GPT-5.6-Luna 30 + DeepSeek-V4-Flash 30 + Kimi-K3 29 |
| `per-text-table-missing.csv` | 缺失清单：哪篇、缺什么 |
| `per-text-table.md` | 前 20 行预览、各组 n、缺失清单、校验记录 |
| `build_per_text_table.py` | 生成脚本 |
| `figures/` | 组会图（词数分布图 + 图注 README） |

## 字段与口径

| 列 | 含义 | 来源 / 计算 |
|---|---|---|
| `prompt_id` | prompt 编号（0–29） | `data/processed/sample_v1.json` |
| `model` | 模型全名或 `Human` | 同上（语料 condition） |
| `group` | `国内` / `国外` / `Human` | DeepSeek、Kimi = 国内；Claude、GPT = 国外 |
| `word_count` | 字母词数 | `metrics_filtered_alpha.json: word_count_alpha`；spaCy `en_core_web_sm`，词 = `token.is_alpha` |
| `MATTR` | 移动平均类符形符比，**窗口 100** | 由原文重算：`lexical_diversity.lex_div.tokenize` + 完整窗口平均 |
| `mean_sentence_length` | 平均句长（字母词/句） | `metrics_results.json: sentence_length` |
| `sentence_length_CV` | 句长变异系数（`pstdev / mean`） | `analysis/metrics_extended_results.json: sentence_length_cv` |
| `mean_paragraph_length` | 平均段落长度（字母词/段） | `metrics_results.json: paragraph_length` |
| `n_sentences` / `n_paragraphs` | 句数 / 段数（便于核对） | `metrics_results.json: _n_sentences / _n_paragraphs` |

**MATTR 窗口 = 100**。`docs/metric-specification.md` 未规定 MATTR 窗口；此处沿用
`analysis/mattr_group_ttest.py` 与报告 §3.4 的固定窗口 100（老师 2026-09-21 指定），
不做跨窗口比较。窗口不随文本长度调整，所有文本同一参数。

**为什么不用 `len(text.split())`**：Human 原文来自 HuggingFace 数据集，标点前后带空格
（如 `child , you`）；空白分词会把标点当成词，系统性高估 Human 长度（prompt 0：split = 339，
字母词 = 261）。四组 AI 是生成长文本，标点不带空格，两种口径差异只有 ±1–2%。为让五组可比，
统一采用字母词口径。

## 行数与缺失

- 149 行 = 30 prompts × 5 组 − Kimi 缺 1 篇；按 `prompt_id` 排序，同一 prompt 的五组相邻，便于逐题对照。
- **Kimi-K3 缺 `prompt_id=26`**（`sample_v1.json` 中无该篇文本）。该篇不进入任何按篇统计，
  在 `per-text-table-missing.csv` 中单列；Kimi 组 n = 29。
- 其余 149 篇的规定 8 个字段均完整，无空值（另附 `n_sentences` / `n_paragraphs` 两列供核对）。

## 复现与校验

```bash
cd /home/hunde/length-confound-archive
/usr/bin/python3 analysis/build_per_text_table.py
```

脚本内置断言：行数 = 149、各组 n 符合预期、`word_count` 与独立汇总的
`metrics_extended_results.json: n_words` 逐篇相同、Human 组 MATTR(100) 均值与
`mattr_group_ttest_results.json` 的 `human_mean`（0.6779849286）一致。任一项不符会直接报错。

## 只做描述

本表只做逐篇汇总，不做推断统计；分组差异的检验与图见 `figures/` 及其 README。
