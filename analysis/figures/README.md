# 组会材料② · 五组文本的词数分布图

2026-10-23 · 数据：`analysis/per-text-table.csv`（149 篇 = 5 组 × 30 prompts − Kimi 缺 1 篇）

## 文件

| 文件 | 内容 |
|---|---|
| `wordcount-distribution.png` | 300 dpi 位图（2220 × 1500 px），用于 PPT / 即时预览 |
| `wordcount-distribution.pdf` | 同图矢量版（Arial 已嵌入），用于报告排版 |
| `wordcount-distribution-stats.json` | 图中全部数字（各组 n、min、Q1、中位数、Q3、max、IQR、逐篇取值、重叠计数），供核对与复用 |
| `../wordcount_distribution.py` | 生成脚本（读 `analysis/per-text-table.csv`） |
| `../fig_style.py` | 五组共用配色 / 字体 / 坐标轴样式，后续同批图请直接 import |

## 图注（可直接用于报告 / PPT）

> **图 1　五组文本的词数分布。** 箱线图为第 25、50、75 百分位，须线延伸至 1.5×IQR，每个散点为一篇文本；灰色横带标出 Human 的 25–75 分位区间（261–543 词）。各组中位数（Q1–Q3；IQR 宽度）：Human 365（261–543；282，n = 30）、Claude 664（637–685；48，n = 30）、GPT 779（739–819；79.5，n = 30）、DeepSeek 691（659–757；98，n = 30）、Kimi 675（628–732；104，n = 29，缺 prompt 26）。落在 Human 25–75 分位区间内（含端点）的 AI 文本为 Claude 0/30、GPT 0/30、DeepSeek 3/30（10.0%）、Kimi 2/29（6.9%），合计 5/119（4.2%）；反向落在各 AI 组 25–75 分位区间内的 Human 文本依次为 0/30、2/30、3/30、2/30。词数为 spaCy 的字母词（`is_alpha`）计数，五组同一口径。此处只描述分布，不解释成因；数值四舍五入到整词（GPT 中位数 778.5、Q3 818.5 等精确值见下表与 stats JSON）。

**重叠程度一句话**：Human 的 25–75 分位区间为 **261–543 词**，四组 AI 文本只有 **5/119 篇（4.2%）** 落在其中（Claude 0/30、GPT 0/30、DeepSeek 3/30、Kimi 2/29）；词数分布在五组间基本分离，重叠程度不足以支持按词数区间做逐篇匹配。

## 数字表

| 组（图上标签） | 语料 model | n | min | Q1 | 中位数 | Q3 | max | IQR | 落在 Human IQR 内 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Human | `human` | 30 | 110 | 261.00 | 365.0 | 542.75 | 1112 | 281.75 | — |
| Claude | `Claude-Sonnet-5-High` | 30 | 612 | 637.00 | 663.5 | 685.00 | 715 | 48.00 | **0/30（0.0%）** |
| GPT | `GPT-5.6-Luna` | 30 | 645 | 739.00 | 778.5 | 818.50 | 920 | 79.50 | **0/30（0.0%）** |
| DeepSeek | `DeepSeek-V4-Flash` | 30 | 316 | 659.25 | 691.0 | 757.25 | 950 | 98.00 | **3/30（10.0%）** |
| Kimi | `Kimi-K3` | 29 | 475 | 628.00 | 675.0 | 732.00 | 801 | 104.00 | **2/29（6.9%）** |

反向（Human 落在各 AI 组的 Q1–Q3 内）：Claude 0/30、GPT 2/30（6.7%）、DeepSeek 3/30（10.0%）、Kimi 2/30（6.7%）。

## 怎么读

- **位置**：Human 中位数 365 词；四个 AI 组 664–779 词，是 Human 的 1.82–2.13 倍。
- **离散度**：Human 的 IQR 宽 282 词，AI 组只有 48–104 词（约为 Human 的 1/6–1/3）；Human 的上尾（max 1112）高于所有 AI 组的中位数。
- **重叠**：Human 的 Q1–Q3 带（261–543）横跨各列，但带内的 AI 点极少（合计 5/119）；Claude 与 GPT 的最小值（612、645）已在 Human 的 Q3 之上。
- **可写的说法**：「在这份语料上，Human 文本的词数分布比四组 AI 文本更短、更分散，区间重叠很小。」
- **不要写的说法**：「因为模型更啰嗦 / AI 不会控制长度 / 长度差异说明风格差异」。图只呈现词数分布，不能支持成因或风格解释；长度与体裁、抽样、生成长度上限等因素在此未分离。

## 口径与关键决定

1. **`word_count` = 字母词（`is_alpha` token）**，由 spaCy `en_core_web_sm` 计数，五组同口径（详见 `analysis/README.md`）。不采用 `len(text.split())`：Human 原文来自 HuggingFace 数据集，标点前后带空格，空白分词会把标点误计为词（prompt 0：split = 339 vs 字母词 = 261），从而高估 Human 长度。
   - 敏感性：若改用空白分词，Human 中位数变为 458、IQR 329–627，AI 落在 Human IQR 内的篇数升为 13/119（10.9%）；重叠仍低、结论方向不变，但数字不同——所以全表与全图只用一种口径。
2. **「GPT」= `GPT-5.6-Luna`**（本组语料中的四模型之一，图上脚注已注明）。语料里另有一份 `gpt35`（GPT-3.5，HuggingFace 数据集自带的历史基线），不属于导师 10-19 圈定的四模型，未进入本表与本图。**若把「GPT」换成 gpt35，重叠会变成 20/30（66.7%），结论相反**（gpt35 中位数 537.5、IQR 493–558）。因此看图前必须先确认「GPT」指哪一个；本图固定为 GPT-5.6-Luna。
3. **Kimi n = 29**：`prompt_id=26` 无语料文本（`sample_v1.json` 中该字段缺失），图上已标 n = 29，未做插补。
4. **颜色**：Human 中性 `#333333`；AI 沿用既有蓝色基准 `#7f9dc0` 的同色系四阶（Claude `#2c5a86`、GPT `#4f7ba6`、DeepSeek `#7f9dc0`、Kimi `#a3b9cf`）。后续同批图直接 `from fig_style import GROUP_COLORS`，不要再另起配色。
5. **只描述、不作因果**：图注与上表均不含「因为……所以……」式解释。

## 复现

```bash
cd /home/hunde/length-confound-archive
/usr/bin/python3 analysis/wordcount_distribution.py
```

依赖：Python 3.12、numpy、matplotlib（本机 `/usr/bin/python3` 已具备）。脚本从
`analysis/per-text-table.csv` 读取逐篇词数，重算分位数与重叠计数后出图，并把同一批数字写入
`wordcount-distribution-stats.json`。改动数据表后重跑即可，无需手改图。

## 校验记录

- 五组齐全，n = 30/30/30/30/29；图中无其它模型。
- 所有数字由脚本从 CSV 现算：Human IQR `[261.00, 542.75]`，pooled AI 重叠 `5/119 = 4.20%`；与 `../per-text-table.md` 的逐篇数据一致。
- PNG：2220 × 1500 px @ 300 dpi；PDF：单页矢量，ArialMT / Arial-BoldMT 均已嵌入（`pdffonts` 检查）。
- 视觉检查：五组箱线、散点、Human IQR 带、各列 `0/30`–`2/29` 计数均正常显示；Kimi 浅色点仍可辨，计数文字用中性深色以保证对比度。

## 更新记录

- 2026-10-23：首版。基于 `analysis/per-text-table.csv`（新建），按任务要求出五组箱线 + 散点图；图注、重叠统计、口径说明同上。
