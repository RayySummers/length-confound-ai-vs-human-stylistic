# 每篇文本一行：per-text table

**生成日期**：2026-10-28 重生成（MTLD 列增补，RAY-598；初版 2026-10-24）  
**脚本**：`analysis/build_per_text_table.py`  
**数据**：`data/processed/sample_v1.json`（30 prompts）  
**主表**：`analysis/per-text-table.csv`（150 行）  
**缺失清单**：`analysis/per-text-table-missing.csv`

## 范围

只保留导师指定的四模型 + Human：

| 组 | 模型 | 语料字段 | N |
|---|---|---|---|
| Human | Human | `human_story` | 30 |
| 国外 | Claude | `Claude-Sonnet-5-High_story` | 30 |
| 国外 | GPT | `GPT-5.6-Luna_story` | 30 |
| 国内 | DeepSeek | `DeepSeek-V4-Flash_story` | 30 |
| 国内 | Kimi | `Kimi-K3_story` | 30 |
| **合计** | | | **150** |

未纳入：GPT-3.5、Gemini-3.6-Flash、MiniMax-M3、MiMo-V2.5-Pro、Muse-Spark-1.2-Contributor。  
按组汇总：Human 30、国内 60、国外 60。

## 指标定义与参数

| 字段 | 定义 | 实现 |
|---|---|---|
| `word_count` | 字母词（alphabetic token）数 | spaCy `en_core_web_sm`，先转小写；标点、数字、Markdown 符号不计 |
| `MATTR` | 移动平均类符形符比 | `lexical_diversity.lex_div`；**窗口固定 100**，所有文本同一窗口，不调参 |
| `mtld` | MTLD（Jarvis & McCarthy），衡量词汇多样性在全文尺度上「用掉多少个形符才把 TTR 降到阈值以下」 | `lexical_diversity.lex_div.mtld`，**默认因子阈值 0.72**（未调参），正反向各算一次取平均；token 与 `word_count` 同一套（spaCy 字母词、先转小写） |
| `mean_sentence_length` | 平均句长（词/句） | spaCy 分句 + 每句字母词数 |
| `sentence_length_CV` | 句长变异系数 = 总体 SD / 均值 | 与 `mean_sentence_length` 使用同一组句长（`pstdev`，ddof=0） |
| `mean_paragraph_length` | 平均段长（词/段） | 空行切段；若只有一段则回退到语料的 `<newline>` 切分（与 `analysis/metrics.py` 一致） |

**MATTR 窗口说明**：`docs/metric-specification.md` 是 2026-08-05 锁定的八指标清单，**原文没有 MATTR 条目，也没有写窗口大小**。本表采用全项目既定的 **100**：2026-09-21 组会决定「MATTR 窗口统一取 100」，proposal v13/v14 §3.2 与 §4.2 也明确写「fixed window 100」。README 已同步注明。窗口不是在本任务里选的，也未做跨窗口比较。

**MTLD 口径说明**：`mtld` 的输入是 `word_count` 用的那一套字母词 token（spaCy `is_alpha`，文本先转小写），
阈值取 `lex_div.mtld` 的默认 0.72，正反向平均。这与 `MATTR` 的 tokenisation（`lex_div.tokenize`：只删标点后按空白切分，
数字和带连字符的词也算 token）**不同**，因此两者可以看方向是否一致，**不能直接比较绝对水平**；
下方「核对」给出两种 token 口径的 MTLD 对照。

## 各组样本数（供 RQ1 使用）

| 模型 | N |
|---|---|
| Human | 30 |
| Claude | 30 |
| GPT | 30 |
| DeepSeek | 30 |
| Kimi | 30 |
| 合计 | 150 |

| 组 | N |
|---|---|
| Human | 30 |
| 国内 | 60 |
| 国外 | 60 |

**行数说明**：30 prompts × 5 组 = 150 个单元，语料 150 篇齐全（Kimi prompt 26 已于 2026-10-24 补齐），主表 150 行。

## 前 20 行预览

| prompt_id | model | group | word_count | MATTR | mtld | mean_sentence_length | sentence_length_CV | mean_paragraph_length |
|---|---|---|---|---|---|---|---|---|
| 0 | Human | Human | 261 | 0.7273 | 99.56 | 6.5250 | 1.0125 | 130.0000 |
| 0 | Claude | 国外 | 637 | 0.7739 | 109.30 | 11.7963 | 0.8078 | 31.8500 |
| 0 | GPT | 国外 | 777 | 0.7769 | 98.61 | 6.8761 | 0.7317 | 7.0636 |
| 0 | DeepSeek | 国内 | 525 | 0.7499 | 90.08 | 7.0000 | 0.7581 | 26.2500 |
| 0 | Kimi | 国内 | 624 | 0.7683 | 125.48 | 11.1429 | 0.8029 | 52.0000 |
| 1 | Human | Human | 757 | 0.6809 | 68.75 | 10.0933 | 0.6417 | 20.3824 |
| 1 | Claude | 国外 | 612 | 0.7781 | 131.66 | 15.6923 | 0.4815 | 40.8000 |
| 1 | GPT | 国外 | 757 | 0.7591 | 109.74 | 8.0532 | 0.6084 | 10.0933 |
| 1 | DeepSeek | 国内 | 807 | 0.7370 | 93.01 | 10.4805 | 0.6543 | 38.4286 |
| 1 | Kimi | 国内 | 641 | 0.7531 | 89.79 | 17.3243 | 0.7852 | 49.3077 |
| 2 | Human | Human | 723 | 0.7002 | 71.23 | 10.0417 | 0.7619 | 40.6471 |
| 2 | Claude | 国外 | 655 | 0.7276 | 81.07 | 17.2368 | 0.6096 | 72.7778 |
| 2 | GPT | 国外 | 731 | 0.7251 | 71.09 | 7.8602 | 0.6312 | 9.0247 |
| 2 | DeepSeek | 国内 | 682 | 0.6890 | 72.77 | 9.8841 | 0.6774 | 62.0000 |
| 2 | Kimi | 国内 | 801 | 0.7158 | 85.85 | 11.1250 | 0.8185 | 36.4091 |
| 3 | Human | Human | 356 | 0.6820 | 49.95 | 10.1714 | 0.6076 | 22.5714 |
| 3 | Claude | 国外 | 682 | 0.7248 | 89.04 | 17.4872 | 0.9346 | 42.6250 |
| 3 | GPT | 国外 | 801 | 0.7364 | 91.78 | 7.3486 | 0.5677 | 8.9000 |
| 3 | DeepSeek | 国内 | 670 | 0.7361 | 108.67 | 9.8529 | 0.5947 | 41.8750 |
| 3 | Kimi | 国内 | 635 | 0.7652 | 118.20 | 16.2821 | 0.6816 | 52.9167 |

> 完整 CSV 另含 `n_sentences`、`n_paragraphs`、`missing_fields` 三列，便于审计切分与缺值。MTLD 在预览里保留 2 位小数，CSV 存 6 位。

## 缺失清单

无。

## 核对

- **行数**：150 行 = 语料中保留范围内的实际篇数；30×5 网格已满（Kimi prompt 26 补齐后），无空缺。
- **word_count 全量对照**：与 `data/processed/results_v1.json` 的 per-sample 记录逐行对照（149/150 行）：`word_count`、`mean_sentence_length`、`mean_paragraph_length` 的最大绝对差分别为 0.000000、0.000000、0.000000。
- **word_count 抽 5 篇独立复核**：用正则 `[A-Za-z]+(?:['’][A-Za-z]+)?` 从原文另行计数。

| prompt_id | model | word_count（本表） | 独立正则计数 | 差值 | 差值 % |
|---|---|---|---|---|---|
| 0 | Human | 261 | 268 | +7 | +2.68% |
| 3 | Claude | 682 | 682 | +0 | +0.00% |
| 7 | GPT | 769 | 769 | +0 | +0.00% |
| 12 | DeepSeek | 316 | 316 | +0 | +0.00% |
| 29 | Kimi | 746 | 748 | +2 | +0.27% |

  Human prompt 0 的 +7 来自语料原始分词：原文把 `it's` 写成 `it 's`，正则会把孤立的 `s` 也算作一个词，spaCy 只算 `it`。这是分词口径差异，不是漏词；其余 4 篇完全一致或差 0.3% 以内。

- **MATTR 对照**（窗口 100，与 proposal v13/v14 表 2b 的已发表组均值/标准差对照）：

| 组 | N | MATTR M | MATTR SD | 报告值 M | 报告值 SD | ΔM | ΔSD |
|---|---|---|---|---|---|---|---|
| Human | 30 | 0.6780 | 0.0569 | 0.6780 | 0.0570 | 0.0000 | -0.0001 |
| Claude | 30 | 0.7773 | 0.0305 | 0.7773 | 0.0305 | 0.0000 | 0.0000 |
| GPT | 30 | 0.7628 | 0.0299 | 0.7628 | 0.0299 | 0.0000 | 0.0000 |
| DeepSeek | 30 | 0.7290 | 0.0268 | 0.7290 | 0.0268 | 0.0000 | 0.0000 |
| Kimi | 30 | 0.7574 | 0.0289 | 0.7568 | 0.0291 | 0.0006 | -0.0002 |

  报告值取自 proposal v13/v14 表 2b（3–4 位小数）。Kimi 的 ΔM 超出 4 位小数的舍入误差：已发表值是在语料补齐前算的（Kimi 29 篇，缺 prompt 26），本表为 30 篇，属样本范围差异而非重算偏差；其余各组 Δ 为舍入差，本表重算值与报告值一致。

- **MTLD 各组描述统计**（阈值 0.72，token = `word_count` 口径；样本标准差 ddof = 1）：

| 组 | N | MTLD M | MTLD SD | 最小 | 最大 |
|---|---|---|---|---|---|
| Human | 30 | 68.66 | 25.13 | 21.6 | 135.9 |
| Claude | 30 | 127.79 | 38.62 | 81.1 | 262.6 |
| GPT | 30 | 106.79 | 26.72 | 65.2 | 168.9 |
| DeepSeek | 30 | 87.18 | 21.15 | 49.2 | 139.1 |
| Kimi | 30 | 108.61 | 23.70 | 63.8 | 175.9 |

- **MTLD token 口径对照**（同一批文本、同一阈值，只换 tokenisation）：

| 组 | N | word_count 口径 M | lex_div 口径 M | Δ（后−前） |
|---|---|---|---|---|
| Human | 30 | 68.66 | 72.39 | 3.73 |
| Claude | 30 | 127.79 | 159.26 | 31.48 |
| GPT | 30 | 106.79 | 132.97 | 26.19 |
| DeepSeek | 30 | 87.18 | 101.32 | 14.15 |
| Kimi | 30 | 108.61 | 131.28 | 22.67 |

  逐篇最大差 89.04、平均 19.92（n=150）；组均值排序 word_count 口径为 Claude > Kimi > GPT > DeepSeek > Human，lex_div 口径为 Claude > GPT > Kimi > DeepSeek > Human。两种口径的绝对水平不同（`lex_div` 口径把数字、连字符词也算作 token），
  所以 MTLD 只和同一口径的数字比；方向是否与 MATTR 一致在 `analysis/summary-table.md` 里读。

- **CV 口径说明**：`sentence_length_CV` 与 `analysis/metrics_extended_results.json` 的同名列最大差 0.010965（平均 0.000379，n=149）。原因是旧文件在统计句长时未先转小写，`Mrs.` 等缩写会被切成不同 token；本表让 CV 与 `mean_sentence_length` 共用同一组句长，故以本表为准。

## 注意

- 本表只做描述，没有跑任何推断性统计（无 t 检验、无方差检验、无分类器）。
- `group` 只作样本标注（国内/国外/Human）；本表不比较中外差异，也不做模型间检验。
- 段落切分沿用既有 `analysis/metrics.py` 的口径，本任务没有重做切分核查；GPT 文本里的 Markdown 小标题/属性行可能被切成很多短段，`mean_paragraph_length` 应结合任务⑤的切分核查阅读。
- `MATTR` 的 tokenisation 与 `word_count` 不完全相同（前者由 `lex_div` 去标点后按空白切分，后者只数 spaCy 字母词），两者不应混用为同一个「词数」；`mtld` 用的是 `word_count` 那一套，所以 `mtld` 与 `MATTR` 的 token 口径也不相同。
- `mtld` 是描述统计量：本表没有为它跑任何检验，也不据此下「AI 词汇更多样」的推断结论（另单处理）。
