# §3.4 词长改写 diff（保留改写方案）
2026-10-17

改动：标题去掉「附加发现／候选 H6」；正文删掉「怎么发现的」叙述（分类器特征重要性检视）；披露句改为一行干净表述；表 5 图注尾句同步。

---

## EN

--- proposal_v14.md.bak-wordlen-pre	2026-10-17 15:37:43.737675787 +0800
+++ proposal_v14.md	2026-10-17 15:37:43.755357079 +0800
@@ -237,9 +237,9 @@
 
 MTLD (using the lexical_diversity reference implementation; see §2.4) ranks as the dominant feature (0.340 importance), followed by sentence length (0.127) and TTR (0.112). Conjunction frequency ranks 6th (0.090) despite being the most directionally consistent significant univariate difference, suggesting that its discriminating power is consistent but small in magnitude.
 
-### 3.4 Additional Finding: Word Length (Candidate H6)
+### 3.4 Word Length: A Difference Not Explained by Length
 
-Word length (chars/word) emerged as a candidate metric when inspecting feature importance from the overall classifier (where it ranked 7th of 8 features) and the GPT-3.5 per-condition classifier (where it was the top feature with importance 0.278). Group comparisons for word length are significant in 3 of 9 conditions (GPT-3.5, GPT-5.6-Luna, Gemini-3.6-Flash; all AI > human; Table 2a), and the AI groups' word-length variance is smaller than the human group's in 8/9 conditions. Notably, word length is the metric whose differences are *not* eliminated by length control: after residualizing on word count, significant differences increase to 5 of 9 conditions (GPT-3.5, MiMo-V2.5-Pro, GPT-5.6-Luna, Claude-Sonnet-5-High, Gemini-3.6-Flash; AI > human), and an ANCOVA robustness check retains 3 of 9 (GPT-3.5, MiniMax-M3, Gemini-3.6-Flash). If anything, text length masks the word-length difference: AI texts are longer, and longer texts use shorter words (r = −0.17 between word length and word count), which dilutes the raw contrast.
+Word length (characters per word) is not among the pre-specified hypotheses; it is reported here as an exploratory finding because it is the one dimension on which group differences are not eliminated by length control. Group comparisons are significant in 3 of 9 conditions (GPT-3.5, GPT-5.6-Luna, Gemini-3.6-Flash; all AI > human; Table 2a), and the AI groups' word-length variance is smaller than the human group's in 8/9 conditions. Notably, word length is the metric whose differences are *not* eliminated by length control: after residualizing on word count, significant differences increase to 5 of 9 conditions (GPT-3.5, MiMo-V2.5-Pro, GPT-5.6-Luna, Claude-Sonnet-5-High, Gemini-3.6-Flash; AI > human), and an ANCOVA robustness check retains 3 of 9 (GPT-3.5, MiniMax-M3, Gemini-3.6-Flash). If anything, text length masks the word-length difference: AI texts are longer, and longer texts use shorter words (r = −0.17 between word length and word count), which dilutes the raw contrast.
 
 | Condition | n | ΔM | Raw p | Raw d | Residualized p | Residualized d |
 |---|---|---|---|---|---|---|
@@ -253,7 +253,7 @@
 | Gemini-3.6-Flash | 30 | +0.32 | <0.0001 | +1.18 | <0.0001 | +1.47 |
 | Kimi-K3 | 29 | +0.01 | 0.8457 | +0.05 | 0.1970 | +0.34 |
 
-*Table 5. Word length: group comparisons (independent-samples Welch t-tests, two-tailed, uncorrected) and length-controlled results (pooled residualization on word count). ΔM = M(AI) − M(Human). 3/9 conditions show raw significant differences; 5/9 survive length control. Three descriptive patterns: GPT-3.5 is an outlier (+15.0% vs human); Gemini-3.6-Flash, despite being recent, also uses longer words (+7.5%); the modern open-source models (DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark, Kimi-K3) show no significant raw differences. This finding is post-hoc and is reported as an 'Additional Finding' rather than as a pre-registered hypothesis (H6 candidate); it requires independent confirmation at N=90.*
+*Table 5. Word length: group comparisons (independent-samples Welch t-tests, two-tailed, uncorrected) and length-controlled results (pooled residualization on word count). ΔM = M(AI) − M(Human). 3/9 conditions show raw significant differences; 5/9 survive length control. Three descriptive patterns: GPT-3.5 is an outlier (+15.0% vs human); Gemini-3.6-Flash, despite being recent, also uses longer words (+7.5%); the modern open-source models (DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark, Kimi-K3) show no significant raw differences. The pattern is exploratory rather than pre-registered and requires independent confirmation before it is treated as a stable result.*
 
 ### 3.5 Supplementary Indicators
 


---

## ZH

--- proposal_v14_zh.md.bak-wordlen-pre	2026-10-17 15:37:43.738760410 +0800
+++ proposal_v14_zh.md	2026-10-17 15:37:43.756224385 +0800
@@ -236,9 +236,9 @@
 
 文本词汇多样性指标（MTLD）（采用 lexical_diversity 参考实现；见 §2.4）位居主导特征（重要性 0.340），其后是句长（0.127）与类符形符比（TTR）（0.112）。连词频率尽管是方向最一致的单变量显著差异，却仅排第 6（0.090），这表明其区分能力虽稳定，但幅度很小。
 
-### 3.4 附加发现：词长（候选 H6）
+### 3.4 词长：一项未被长度解释的差异
 
-在检视总体分类器（词长在 8 个特征中排第 7）与 GPT-3.5 各条件分类器（词长为首要特征，重要性 0.278）的特征重要性时，词长（字符/词）浮现为一项候选指标。词长的组间比较在 9 个条件中有 3 个显著（GPT-3.5、GPT-5.6-Luna、Gemini-3.6-Flash；均为 AI > 人类；见表 2a），且 AI 组的词长方差在 8/9 个条件中小于人类组。值得注意的是，词长是唯一一个差异未被长度控制消除的指标：对词数做残差化后，显著条件增加到 5/9（GPT-3.5、MiMo-V2.5-Pro、GPT-5.6-Luna、Claude-Sonnet-5-High、Gemini-3.6-Flash；AI > 人类），ANCOVA 稳健性检查保留 3/9（GPT-3.5、MiniMax-M3、Gemini-3.6-Flash）。如果要说有什么影响，文本长度反而掩盖了词长差异：AI 文本更长，而更长的文本用词更短（词长与词数的 r = −0.17），稀释了原始对比。
+词长（字符/词）不在预先设定的假设之列，此处作为探索性发现报告，因为它是唯一一个组间差异未被长度控制消除的维度。组间比较在 9 个条件中有 3 个显著（GPT-3.5、GPT-5.6-Luna、Gemini-3.6-Flash；均为 AI > 人类；见表 2a），且 AI 组的词长方差在 8/9 个条件中小于人类组。值得注意的是，词长是唯一一个差异未被长度控制消除的指标：对词数做残差化后，显著条件增加到 5/9（GPT-3.5、MiMo-V2.5-Pro、GPT-5.6-Luna、Claude-Sonnet-5-High、Gemini-3.6-Flash；AI > 人类），ANCOVA 稳健性检查保留 3/9（GPT-3.5、MiniMax-M3、Gemini-3.6-Flash）。如果要说有什么影响，文本长度反而掩盖了词长差异：AI 文本更长，而更长的文本用词更短（词长与词数的 r = −0.17），稀释了原始对比。
 
 | 条件 | n | ΔM | 原始 p | 原始 d | 残差化 p | 残差化 d |
 |---|---|---|---|---|---|---|
@@ -252,7 +252,7 @@
 | Gemini-3.6-Flash | 30 | +0.32 | <0.0001 | +1.18 | <0.0001 | +1.47 |
 | Kimi-K3 | 29 | +0.01 | 0.8457 | +0.05 | 0.1970 | +0.34 |
 
-*表 5. 词长：组间比较（独立样本 Welch t 检验，双尾、不校正）与长度控制结果（对词数做合并残差化）。ΔM = M(AI) − M(人类)。3/9 个条件原始显著；5/9 在长度控制后保留。三种描述性模式：GPT-3.5 是离群者（比人类 +15.0%）；Gemini-3.6-Flash 尽管是近期模型，用词也更长（+7.5%）；现代开源模型（DeepSeek-V4-Flash、MiniMax-M3、Muse-Spark、Kimi-K3）没有显著的原始差异。该发现属事后分析，作为探索性发现报告，而非预注册假设；需在 N=90 下独立确认。*
+*表 5. 词长：组间比较（独立样本 Welch t 检验，双尾、不校正）与长度控制结果（对词数做合并残差化）。ΔM = M(AI) − M(人类)。3/9 个条件原始显著；5/9 在长度控制后保留。三种描述性模式：GPT-3.5 是离群者（比人类 +15.0%）；Gemini-3.6-Flash 尽管是近期模型，用词也更长（+7.5%）；现代开源模型（DeepSeek-V4-Flash、MiniMax-M3、Muse-Spark、Kimi-K3）没有显著的原始差异。该模式属探索性发现、非预注册假设，需在 N=90 的独立复现中确认后再作为稳定结论。*
 
 ### 3.5 增补指标
 

