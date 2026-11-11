# analysis/descriptive — 376 篇 × 12 子语料四指标描述统计（RAY-651）

王雅琴老师 2026-11-11 确认语体方案后的第一步：**只做描述统计，不做显著性检验**。
口径由 issue 锁定，脚本不提供任何「自动调参」入口；所有表格由脚本生成，人工解读单独放在
`observations.md`，运行时原样嵌入报告并明确标注。

## 一条命令跑完

```bash
python3 analysis/descriptive/descriptive_stats.py
```

只用 Python 标准库（3.9+）。默认从 `<repo>/data` 读数据，写到
`analysis/descriptive/out-20261111/`；可用 `--data-root` / `--out-dir` 改路径，
`--no-appendix` 跳过标点诊断附录。

耗时约 20 秒（4,510 篇 AI + 376 篇人类 × 2 套对齐）。

## 输入（只读，不改原始数据）

| 路径 | 用途 |
|---|---|
| `data/brown2021/manifest.csv` | 500 篇人类文本索引（doc_id / filename / category） |
| `data/brown2021/<category>__<filename>` | 人类文本（AntConc 导出，标点独立成词） |
| `data/brown2021/ai_file_mapping.csv` | n ↔ BE21 文档号 |
| `data/aibrown/AI_Brown_plain_texts_cleaned.zip` | 31 个子语料，本分析取 12 个 |

## 锁定口径

| 项 | 定义 |
|---|---|
| 词 | `str.split()` 的空白 token，标点原样保留（包括独立成词的标点） |
| 主分析对齐 | 人类第 501–1500 词（跳过 500 词 prompt）；AI 第 1–1000 词 |
| 敏感性对齐 | 人类第 1–1000 词；AI 第 1–1000 词（按定义与主分析相同） |
| MATTR | 窗口 100，窗口内小写，对全部窗口取平均；不足 100 词记 NA |
| MTLD | 阈值 0.72（严格小于），因子最短 10 词，正向 + 反向平均，末段按 (1−TTR)/(1−0.72) 折算 |
| 句长均值 | 先保护缩写/小数/省略号/单字母缩写，再按 `(?<=[.!?])\s+` 切句；句长 = 该句空白 token 数 |
| 句长 CV | 句长总体标准差 / 均值（≥2 句才计算） |

与仓库旧管线的差别，写报告引用时要注意：

- 旧 `analysis/metrics.py` / `build_per_text_table.py` 用 spaCy 的**字母 token** 计词；
  本分析按 issue 要求改用**空白 token**，两者词数不可直接对比。
- MTLD 与 `lexical_diversity.lex_div.mtld` 语义一致（同样严格小于、同样最短 10 词），
  只在计算前把 token 小写；`run_manifest.json` 的 `checks.lexical_diversity` 记录了一次
  逐值比对（A01 第 501–1500 词，MATTR/MTLD 均完全一致）。
- 切句用正则而非 spaCy，因此句数、句长与旧表不同，属预期差异。

## 产物（`out-20261111/`）

| 文件 | 内容 |
|---|---|
| `per_text_metrics.csv` | 逐篇：doc_id、n、BE21、语体、组别、温度、对齐、四指标、词数、句数（9,772 行） |
| `summary_by_genre.csv` | 对齐 × 组别 × 语体（含 ALL）× 指标：N/均值/SD/中位数/Q1/Q3/IQR |
| `human_vs_model_diff.csv` | 人类 vs 每个模型的均值与中位数差值（含按语体） |
| `genre_sample_table.csv` | 语体 × 人类篇数 × 12 组 AI 篇数 |
| `sample_index.csv` | 376 组 doc_id ↔ n ↔ BE21 对照清单（可复查） |
| `qa_tokenization.csv` | 标点 token 诊断（人类 vs AI 的实词量差异） |
| `data_issues.csv` | 数据问题清单 D1–D7 |
| `appendix_alpha_tokens.csv` | 剥离标点-only token 后重算的诊断（**非协议口径**，只看 D4 影响） |
| `run_manifest.json` | 配置、输入 sha256、缺失篇目、AI 词数分布、回归校验 |
| `report.md` | 中文报告（第 1–6 节脚本产出，第 7 节人工解读） |

## 核对方式

```bash
# 逐篇行数 = 376×2 + 12×376×2 = 9772
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
2. gpt-4o 温度 0 有 224/376 篇不足 1,000 词，llama 温度 100 有 122/376 篇；窗口更短。
3. claude-35-sonnet 两组各有 3 篇不足 100 词，MATTR 记 NA（该指标 N=373）。
4. 人类标点独立成词，主分析窗口 13.9% 为标点-only token，AI 仅 0.3%。
5. MTLD 在 gpt-45 温度 100、llama 温度 100 出现成片高值；llama 温度 100 含词语堆叠的退化文本。
