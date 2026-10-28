# analysis/ 数据表说明

本目录的 `per-text-table.csv` 是「每篇文本一行」的分析底表（王雅琴老师 2026-10-19 建议第 1 项），
也是词数分布图与后续四指标汇总的共同输入。

## 文件

| 文件 | 内容 |
|---|---|
| `per-text-table.csv` | 150 行：Human 30 + Claude 30 + GPT 30 + DeepSeek 30 + Kimi 30（2026-10-28 重生成；此前 Kimi 缺 prompt 26，为 149 行） |
| `per-text-table-missing.csv` | 缺失清单：哪篇、缺什么 |
| `per-text-table.md` | 前 20 行预览、各组 n、缺失清单、核对记录 |
| `build_per_text_table.py` | 生成脚本 |
| `figures/` | 组会图（词数分布图 + 图注 README） |

## 字段与口径

| 列 | 含义 | 来源 / 计算 |
|---|---|---|
| `prompt_id` | prompt 编号（0–29） | `data/processed/sample_v1.json` |
| `model` | `Human` / `Claude` / `GPT` / `DeepSeek` / `Kimi` | 分别对应语料字段 `human_story`、`Claude-Sonnet-5-High_story`、`GPT-5.6-Luna_story`、`DeepSeek-V4-Flash_story`、`Kimi-K3_story` |
| `group` | `国内` / `国外` / `Human` | DeepSeek、Kimi = 国内；Claude、GPT = 国外；只作样本标注，本表不比较中外差异 |
| `word_count` | 字母词数 | 由原文重算：spaCy `en_core_web_sm`，先转小写，词 = `token.is_alpha`；与 `results_v1.json` 的 `n_words` 逐篇相同（149/149） |
| `MATTR` | 移动平均类符形符比，**窗口 100** | 由原文重算：`lexical_diversity.lex_div.tokenize` + 完整窗口平均 |
| `mtld` | MTLD（Jarvis & McCarthy），全文尺度词汇多样性 | `lexical_diversity.lex_div.mtld`，**因子阈值默认 0.72**、正反向平均；token 与 `word_count` 同一套（spaCy 字母词、先转小写），与 MATTR 的 token 口径**不同**，只比方向不比水平 |
| `mean_sentence_length` | 平均句长（字母词/句） | spaCy 分句 + 每句字母词数；与 `results_v1.json: sentence_length` 逐篇相同 |
| `sentence_length_CV` | 句长变异系数（`pstdev / mean`） | 与 `mean_sentence_length` 使用同一组句长；与 `results_v1.json` 的 `sqrt(sentence_length_var)/sentence_length` 等价 |
| `mean_paragraph_length` | 平均段落长度（字母词/段） | 空行切段，单段时回退 `<newline>`；与 `results_v1.json: paragraph_length` 逐篇相同 |
| `n_sentences` / `n_paragraphs` | 句数 / 段数（便于核对） | 同一次分句/切段结果 |
| `missing_fields` | 该行缺哪些指标（正常行为空） | 生成脚本填写 |

**MATTR 窗口 = 100**。`docs/metric-specification.md` 是 2026-08-05 锁定的八指标清单，
原文没有 MATTR 条目、也没有写窗口；此处沿用 `analysis/mattr_group_ttest.py` 与
proposal v13/v14 §3.2/§4.2 的固定窗口 100（老师 2026-09-21 指定），
不做跨窗口比较。窗口不随文本长度调整，所有文本同一参数。README 已同步注明。

**MTLD 口径（2026-10-28 增补，RAY-598）**：`mtld` 用 `word_count` 那一套字母词 token，
阈值取 `lexical_diversity` 默认 0.72，正反向各算一次取平均，不做调参。与 `MATTR` 相比，
`mtld` 剔除了数字与带标点的词（`MATTR` 的 `lex_div.tokenize` 会把它们留下），所以两者
绝对水平不可直接比较；`per-text-table.md` 的「核对」另给了两种 token 口径的 MTLD 对照。

**word_count 的两个旧口径**：`metrics_filtered_alpha.json` 的 `word_count_alpha` 是
大小写敏感的分词结果，与 `results_v1.json` 的 `n_words` 在 25 篇上差 1–17 词；本表统一采用
`results_v1` 的小写口径（与 `mean_sentence_length`、`mean_paragraph_length` 同一条管线）。
`sentence_length_CV` 也因此与 `analysis/metrics_extended_results.json` 的同名列最多差
0.011（旧文件在统计句长时未先转小写，`Mrs.` 等缩写会被切成不同 token）；本表让 CV 与
`mean_sentence_length` 共用同一组句长，以本表为准。

**为什么不用 `len(text.split())`**：Human 原文来自 HuggingFace 数据集，标点前后带空格
（如 `child , you`）；空白分词会把标点当成词，系统性高估 Human 长度（prompt 0：split = 339，
字母词 = 261）。四组 AI 是生成长文本，标点不带空格，两种口径差异只有 ±1–2%。为让五组可比，
统一采用字母词口径。

## 行数与缺失

- 150 行 = 30 prompts × 5 组，五组各 30 篇；按 `prompt_id` 排序，同一 prompt 的五组相邻，便于逐题对照。
- **Kimi `prompt_id=26` 已于 2026-10-24 补齐**（此前 `sample_v1.json` 中无该篇，表只有 149 行、
  Kimi n = 29；当时的备份在 `analysis/backups/`）。现在缺失清单 `per-text-table-missing.csv` 为空。
- 150 篇的规定字段全部有值，无空值、无 NaN（含新增的 `mtld`）；另附 `n_sentences` / `n_paragraphs` 两列供核对。

## 复现与校验

```bash
cd /home/hunde/length-confound-archive
python3.12 analysis/build_per_text_table.py   # 底表
python3.12 analysis/summary_table.py          # 汇总表 + 分布图
```

脚本会用 `results_v1.json` 做全量交叉核对：`word_count`、`mean_sentence_length`、
`mean_paragraph_length` 的最大绝对差应均为 0；`per-text-table.md` 里还记录 5 篇
`word_count` 的独立正则抽检、MATTR 与 MTLD 的组均值对照。MATTR 组均值 Human 0.6780、
Claude 0.7773、GPT 0.7628、DeepSeek 0.7290、Kimi 0.7574（proposal v13/v14 表 2b 记 Kimi 0.7568，
那是 Kimi 29 篇时的值；补齐 prompt 26 后为 30 篇，差 0.0006 属样本范围差异）。

## 只做描述

本表只做逐篇汇总，不做推断统计；分组差异的检验与图见 `figures/` 及其 README。
