# 引言折叠前后对比（只含变化部分）

2026-10-17 · length-confound-archive

## 一、一句话结论

- 新两段是**新增**，没有和既有段落做文字融合；插在「Most existing work…（Juola）」段之后、「The present study addresses this gap…」段之前，也就是引言第 3 段与第 4 段之间。

- 原 §2 的十段没有一段原文搬入，全部内容改写压缩进这两段。

- 引言其余段落原样保留；全文只有一处词改：`8 structural metrics` 改成 `eight locked structural metrics`（中文同处：`8 个结构指标` 改成 `八个锁定结构指标`）。


## 二、原 §2 十段的去向

| 原 §2 段落 | 现在在哪 |
|---|---|
| Fan, Lewis & Dauphin (2018) 数据集 | 新 P1 第 2 句（并入） |
| Huang et al. (2024) GPT-WritingPrompts 与人物刻画 | 新 P1 第 2 句（含「500 词故事」说明） |
| Chakrabarty et al. (2024a) 风格个性 | 新 P1 第 3 句 |
| Chakrabarty et al. (2024b) 写作者介入 | 新 P1 第 3 句 |
| Lucy & Bamman (2021) 体裁偏差 | 新 P1 第 3 句 |
| O'Sullivan (2025) Burrows' Delta | 新 P1 第 1 句 |
| McCarthy & Jarvis (2010) MTLD | 新 P2 第 1 句 |
| 「Collectively…」总结句（连词与词汇支持最强） | 新 P2 末句 |
| 「The study builds on…」引入句 | 删除（新段自带引入） |
| GPT-3.5 字数 531 ± 40 的归因说明 | 新 P1 第 2 句 |

## 三、插入位置前后（英文）

【前】

> …principled framework for identifying structural patterns that persist across topics and genres.
>
> The present study addresses this gap by comparing 8 structural metrics across 9 contemporary AI models…


【后】

> …principled framework for identifying structural patterns that persist across topics and genres.
>
> **（新增 P1）** This study sits at the intersection of two strands of prior work. First, recent applications of stylometry reach high accuracy in distinguishing human from AI creative writing (O'Sullivan, 2025). Corpus work on prompt-matched stories, in particular the GPT-WritingPrompts collection, documents systematic human-versus-GPT-3.5 differences in character portrayal (Huang et al., 2024); our human baseline and prompt set come from the parent WritingPrompts corpus (Fan et al., 2018), and the shorter stories in the GPT-3.5 condition (531 ± 40 words) reflect that collection's 500-word instruction rather than a model property. Second, studies of LLM creativity find that AI prose is fluent but comparatively lacking in idiosyncratic style (Chakrabarty et al., 2024a) and that writers edit model output to inject personal voice (Chakrabarty et al., 2024b), while genre conventions further shape model output (Lucy & Bamman, 2021); together these findings suggest that AI text may be more uniform than human text, the prediction that our variance-based tests target directly.
>
> **（新增 P2）** A second strand concerns measurement. Vocabulary-richness indices differ in how they treat text length: raw type-token ratio is length-sensitive, which motivated length-controlled alternatives such as MTLD (McCarthy & Jarvis, 2010) and MATTR with a moving window (Covington & McFall, 2010; the window is fixed at 100 tokens in this study). Because length covaries with stylistic variables more broadly, comparisons that ignore it risk reporting the statistics of length rather than of style. Within our hypothesis set, conjunction frequency and vocabulary diversity have the strongest prior support, whereas the evidence on sentence- and paragraph-length variance is more mixed; the report therefore tests four directional hypotheses plus one classification benchmark (H5) across nine contemporary models.
>
> The present study addresses this gap by comparing eight locked structural metrics across 9 contemporary AI models…


## 四、新增两段全文（中文）

**（新增 P1）** 本研究处在两条既有研究脉络的交汇处。其一，计量文体学近年的应用在区分人类与 AI 创作文本上能达到较高准确率（O'Sullivan, 2025）。在题目匹配的故事语料上，GPT-WritingPrompts 数据集记录了人类与 GPT-3.5 在人物刻画维度上的系统性差异（Huang et al., 2024）；本文的人类基线与题目集来自其母语料 WritingPrompts（Fan et al., 2018），而 GPT-3.5 条件的故事偏短（531 ± 40 词）源于该数据集采集时的「500 词故事」指令，并非模型特性。其二，关于 LLM 创造力的研究表明，AI 文本流畅但相对缺乏个人化的风格特征（Chakrabarty et al., 2024a），写作者常需编辑模型输出以注入个人风格（Chakrabarty et al., 2024b），而体裁惯例也会塑造模型输出（Lucy & Bamman, 2021）；这些结果共同提示 AI 文本可能比人类文本更同质，这正是本文以方差为核心的检验所针对的预测。

**（新增 P2）** 第二条脉络关乎测量。词汇丰富度指标对文本长度的处理各不相同：原始类符形符比对长度敏感，因而催生了控制长度的替代方案，如 MTLD（McCarthy & Jarvis, 2010）与采用移动窗口的 MATTR（Covington & McFall, 2010；本文将窗口固定为 100 个词元）。由于长度与文体变量普遍共变，忽略长度的比较有把「长度的统计」当成「风格的统计」的风险。在本文的假设集中，连词频率与词汇多样性获得的既有支持最强，句长与段长方差的证据则较为混杂；报告据此在九个当代模型上检验四条方向性假设与一项分类基准（H5）。


## 五、其余改动（不属于文本内容）

- 章号前移：3→2、4→3、5→4、6→5（含子节），交叉引用约 30 处同步。
- 参考文献 12 条全部仍被正文引用。
- 图 1 至图 15、表格编号未变。
