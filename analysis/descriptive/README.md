# analysis/descriptive — 376 篇 × 12 子语料四指标描述统计（RAY-651，v2）

王雅琴老师 2026-11-11 确认语体方案后的第一步：**只做描述统计，不做显著性检验**。
v2 按 issue 评论把主口径改为 **alpha-token**，v1 的空白 token 口径降为敏感性分析。
口径写死在脚本里，没有调参入口；所有表格由脚本生成，人工解读单独放在 `observations.md`，
运行时原样嵌入报告并明确标注。

## 一条命令跑完

```bash
python3 analysis/descriptive/descriptive_stats.py
```

只用 Python 标准库（3.9+）。默认从 `<repo>/data` 读数据，写到
`analysis/descriptive/out-20261111/`；可用 `--data-root` / `--out-dir` 改路径。
耗时约 18 秒（4,510 篇 AI + 376 篇人类 × 2 套口径）。

## 输入（只读，不改原始数据）

| 路径 | 用途 |
|---|---|
| `data/brown2021/manifest.csv` | 500 篇人类文本索引（doc_id / filename / category） |
| `data/brown2021/<category>__<filename>` | 人类文本（AntConc 导出，标点独立成词） |
| `data/brown2021/ai_file_mapping.csv` | n ↔ BE21 文档号 |
| `data/aibrown/AI_Brown_plain_texts_cleaned.zip` | 31 个子语料，本分析取 12 个 |

## 锁定口径（v2）

| 项 | 定义 |
|---|---|
| 主分析 token | **alpha token**：剔除不含字母/数字的 token，再取窗口 |
| 敏感性 token | **空白 token**：`str.split()`，标点原样保留（v1 口径） |
| 对齐（两套相同） | 人类第 501–1500 个 token（跳过 500 词 prompt）；AI 第 1–1000 个 |
| MATTR | 窗口 100，窗口内小写，对全部窗口取平均；不足 100 词记 NA |
| MTLD | 阈值 0.72（严格小于），因子最短 10 词，正反双向平均；**不足 100 词记 NA** |
| 句长均值 | 在窗口对应的原文片段上切句（保护缩写/小数/省略号/首字母，`(?<=[.!?])\s+`，句末引号后再切）；句长 = 该句 alpha token 数 |
| 句长 CV | 句长总体标准差 / 均值（≥2 句才计算） |
| 退化文本 | 主分析下 MATTR > 0.90 或 MTLD > 1000；另出剔除后的汇总 |

与仓库旧管线的差别，写报告引用时要注意：

- 旧 `analysis/metrics.py` / `build_per_text_table.py` 用 spaCy 的字母 token 计词，
  且句长是含标点的 token 数；v2 主分析用 alpha token、句长只数词的 token，两者不可直接对比。
- MTLD 与 `lexical_diversity.lex_div.mtld` 语义一致（严格小于、最短 10 词），只在计算前小写；
  `run_manifest.json` 的 `checks.lexical_diversity` 记录逐值比对（MATTR/MTLD 完全一致）。
- v1（空白 token 主口径）见 git 提交 `75c93d5`；v2 的敏感性表复现 v1 的词汇指标。

## 产物（`out-20261111/`）

| 文件 | 内容 |
|---|---|
| `per_text_metrics.csv` | 逐篇：doc_id、n、BE21、语体、组别、温度、对齐、token 口径、四指标、词数、原文 token 数、句数、退化标记（9,772 行） |
| `summary_by_genre.csv` | 对齐 × 组别 × 语体（含 ALL）× 指标：N/均值/SD/中位数/Q1/Q3/IQR |
| `summary_excl_degenerate.csv` | 同上，剔除退化文本后 |
| `human_vs_model_diff.csv` | 人类 vs 每个模型的均值/中位数差值（含按语体） |
| `degenerate_texts.csv` | 被剔除的退化篇目与判定原因 |
| `genre_sample_table.csv` | 语体 × 人类篇数 × 12 组 AI 篇数 |
| `sample_index.csv` | 376 组 doc_id ↔ n ↔ BE21 对照清单（可复查） |
| `qa_tokenization.csv` | 两种口径下的词数、原文 token 数与标点占比 |
| `data_issues.csv` | 数据问题清单 D1–D8 |
| `run_manifest.json` | 配置、输入 sha256、缺失篇目、词数分布、退化计数、回归校验 |
| `report.md` | 中文报告（第 1–6 节脚本产出，第 7 节人工解读） |

## 核对方式

```bash
# 逐篇行数 = 376×2 + 12×376×2 = 9772（+ 表头 9773）
wc -l analysis/descriptive/out-20261111/per_text_metrics.csv

# 人类 376；gemini 两组各 375；其余 376
python3 - <<'PY'
import csv, collections
rows = list(csv.DictReader(open("analysis/descriptive/out-20261111/per_text_metrics.csv")))
print(collections.Counter(r["group"] for r in rows if r["alignment"] == "main"))
PY
```

## 已知数据问题（详见 `report.md` 第 6 节）

1. gemini-20-pro-exp 两个温度组各缺 n=76（BE21-C04，C 类），N=375。
2. gpt-4o 温度 0 有 228/376 篇不足 1,000 个 alpha 词，llama 温度 100 有 124/376 篇；窗口更短。
3. claude-35-sonnet 两组各有 3 篇不足 100 词，MATTR 与 MTLD 同时记 NA（N=373）。
4. 人类标点独立成词（13.9%），AI 仅 0.3%——这是 v2 改用 alpha 主口径的原因。
5. 退化文本 99 篇（llama 温度 100 95 篇、gpt-45 温度 100 4 篇），剔除后 llama 温度 100 的 N=281。
