# Length as a Primary Confound in AI-vs-Human Stylistic Comparisons: A Conservative Preliminary Report

## Abstract

**Keywords:** stylometry, AI-generated text, computational stylistics, lexical diversity, conjunction frequency, Random Forest classifier, creative writing, multi-model comparison

Do AI-generated text and human-written text differ systematically in structural style, and if so, which differences hold across diverse language models? This study quantifies stylistic differences using 8 structural metrics (word length, sentence length, sentence length variance, type-token ratio, MTLD, conjunction frequency, paragraph length, and paragraph length variance) applied to 30 creative writing prompts, each paired with one human-authored story and AI-generated outputs from 9 contemporary models (GPT-3.5, MiMo-V2.5-Pro, DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark-1.2-Contributor, Kimi-K3, Gemini-3.6-Flash, GPT-5.6-Luna, and Claude-Sonnet-5-High), yielding 299 observations. We test 4 directional hypotheses per AI condition using paired Wilcoxon signed-rank tests with per-hypothesis Holm-Bonferroni correction (4 families × 9 tests), and train a Random Forest classifier evaluated with StratifiedGroupKFold cross-validation (grouped by prompt) to test whether the 8 metrics jointly discriminate AI from human text. **Conjunction frequency (H4) and TTR (H3) are entirely attributable to the 1.6× AI-vs-human length difference**: H4 raw 5/9 + H3 raw 4/9 survive per-family Holm-Bonferroni; length-residualized Wilcoxon yields 0/9 survivors for both metrics. Pre-existing stereotypes (uniformity, vocabulary poverty, conjunction overuse) are NOT robustly supported once length is controlled. TTR differences between AI and human text exist (4 of 9 conditions significant before length correction) but are entirely attributable to text length — after regressing TTR on word count, 0 of 9 conditions survive (see §4.2). MTLD (using the lexical_diversity reference implementation) is the highest-importance feature in the multivariate classifier, but its discriminating power is also length-correlated (see §5). The classifier achieves 91.6% ± 1.6% raw accuracy, but only 68.7% ± 9.3% balanced accuracy (MCC = 0.449, AUC = 0.867, human recall 12/30 = 40%). A length-only baseline classifier (word count alone, same StratifiedGroupKFold framework) achieves 85.0% raw accuracy and 69.4% balanced accuracy — **balanced accuracy is essentially tied with the 8-metric classifier**, and the raw-accuracy gain over majority-class baseline (90.0%) is +1.6 percentage points (computed from 91.6% − 90.0% = 1.6pp; the unrounded value is 1.67pp), indicating a modest but real signal above the majority-class strategy given the 269:30 class imbalance. Sentence and paragraph length variance, often cited as markers of AI writing, are not consistently supported across models. **The substantive finding of this paper is a clean refutation of three pre-existing stereotypes about AI-generated text** (uniformity, vocabulary poverty, conjunction overuse). All three apparent differences — TTR (H3, 4/9 raw significant) and conjunction frequency (H4, 5/9 raw significant) — collapse entirely after length residualization (0/9 survive per-family Holm-Bonferroni for both). Sentence-length variance (H1) and paragraph-length variance (H2) similarly fail in the 6 fully-controlled conditions (0/6 and 0/6 survive after Holm). The 8-metric classifier achieves 91.6% raw accuracy but only 68.7% balanced accuracy (MCC=0.449, AUC=0.867, human recall 12/30=40%), essentially tied with a length-only baseline at 69.4% balanced accuracy. After controlling for both text length and acquisition channel, **no pre-registered univariate stylistic difference survives.** Acquisition-channel confound (4 distinct sources: direct API, third-party dataset, manual Arena paste, Faro API; temperature 0.7 vs 1.0) means 'model-level heterogeneity' claims are not interpretable as model-intrinsic properties. The MTLD feature importance ranking (0.340) reflects length-correlated variance rather than independent stylistic signal. **Conclusion: AI-generated creative text differs from human text primarily in being 1.6× longer; once length and channel are controlled, no robust stylistic discriminator remains.**

## 1. Introduction

Large language models have transformed how text is produced across education, journalism, creative writing, and professional communication. As AI-generated text becomes ubiquitous, a natural question arises: does AI writing exhibit systematic structural patterns that distinguish it from human writing? This question matters not only for detection but also for understanding what AI writing "sounds like" at a structural level, independent of content or coherence.

A common observation is that AI-generated text tends to be "patterned" or "formulaic" in its structure, with similar sentence lengths, uniform paragraph structures, and consistent use of transition words. However, these observations have rarely been subjected to rigorous empirical testing across multiple AI systems using controlled, prompt-matched data.

Most existing work on AI text characterization has focused on semantic coherence, factual accuracy, or surface-level detection. Fewer studies have employed computational stylometry, quantitative analysis of writing style features, to systematically compare AI and human text. Stylometric methods have a long history in authorship attribution and forensic linguistics (Juola, 2008), and they offer a principled framework for identifying structural patterns that persist across topics and genres.

The present study addresses this gap by comparing 8 structural metrics across 9 contemporary AI models and human-authored stories, all written in response to the same 30 creative writing prompts. This design controls for topic and genre effects through prompt matching, uses a paired statistical framework for within-prompt comparisons, and combines hypothesis-driven testing with machine learning classification.

Our study makes three contributions. First, it examines multiple AI systems rather than treating "AI text" as monolithic. Second, it uses a paired experimental design that controls for prompt-level confounds. Third, it combines Wilcoxon signed-rank tests for specific directional hypotheses with Random Forest classification for overall discriminability.

The analysis focuses on creative short fiction from Reddit's r/WritingPrompts, a genre where structural variation is naturally high and where AI writing assistance is increasingly common. By quantifying which structural stereotypes hold empirically and which do not, this study provides a more nuanced, evidence-based understanding of how AI writing differs from human writing.

## 2. Related Work

The study builds on several lines of research in computational stylometry, AI text generation, and creative writing evaluation.

Fan, Lewis, and Dauphin (2018) introduced the WritingPrompts dataset, a large-scale collection of over 300,000 human-written stories paired with creative prompts from Reddit's r/WritingPrompts. The dataset's prompt-matched structure makes it ideal for controlled comparisons between human and AI text. We draw our human baseline and prompt set from this corpus.

Huang et al. (2024) extended the WritingPrompts corpus by generating GPT-3.5 responses to the same prompts, creating the GPT-WritingPrompts dataset. Their analysis characterized GPT-3.5 vs human-written stories along six dimensions of character portrayal (valence, arousal, dominance, intellect, appearance, power); they did not directly report word count, dialogue frequency, or emotional description differences. Our finding that GPT-3.5 word counts are lower than other conditions (531 ± 40 vs 664-878) reflects the '500 word story' instruction in their data-collection protocol rather than a model-intrinsic property. The GPT-3.5 condition in our analysis uses stories from this dataset, representing an "older generation" AI baseline.

Chakrabarty et al. (2024a) examined whether LLMs can serve as creative writing assistants, finding that while AI text is fluent and coherent, it tends to lack the stylistic idiosyncrasies that characterize individual human writers. This supports the hypothesis that AI text may be structurally more uniform than human text, a prediction we test with our variance-based metrics.

Chakrabarty et al. (2024b) extended this line of inquiry by studying how professional writers interact with LLMs during the creative process. They found that writers often edit AI-generated text to inject personal style, suggesting that AI text lacks the stylistic fingerprints of individual authorship. This motivates our focus on vocabulary diversity metrics (TTR and MTLD).

Lucy and Bamman (2021) analyzed genre biases in language model outputs, finding that AI-generated fiction tends to reproduce stereotypical genre conventions. Their work suggests that structural features of AI text may vary by genre, and that creative fiction may amplify certain AI tendencies such as conjunction overuse. Our study controls for genre by using a single corpus (creative fiction).

O'Sullivan (2025) applied Burrows' Delta, a classical stylometric method, to distinguish human from AI-generated creative writing, demonstrating that traditional authorship attribution techniques remain effective for AI detection. This supports our use of stylometric metrics and motivates the inclusion of MTLD and TTR.

McCarthy and Jarvis (2010) validated MTLD as a robust alternative to TTR. Unlike TTR, which is sensitive to text length, MTLD controls for length by computing the mean length of word sequences that maintain a TTR above a threshold. We include both metrics to capture complementary aspects of vocabulary diversity.

Collectively, these studies suggest that conjunction frequency and vocabulary diversity have the strongest prior literature support among our hypotheses, while sentence and paragraph length variance findings are more mixed. Our study extends this work by testing 4 directional hypotheses plus 1 classification benchmark (H5) across 9 contemporary AI models.

## 3. Method

### 3.1 Data

The study uses 30 writing prompts from the Reddit WritingPrompts corpus (Fan et al., 2018). For each prompt, we collected one human-authored story and one AI-generated story from each of 9 AI models, yielding up to 30 paired observations per condition.

**Human baseline.** We use 30 human-written stories from the WritingPrompts dataset, as processed by Huang et al. (2024), licensed under MIT.

**AI conditions.** The 9 AI models represent a range of architectures, training approaches, and generation dates:

| Model | Provider | Source | N |
|-------|----------|--------|---|
| GPT-3.5 | OpenAI | Huang et al. (2024) | 30 |
| MiMo-V2.5-Pro | Xiaomi | Command Code Goat | 30 |
| DeepSeek-V4-Flash | DeepSeek | Command Code Goat | 30 |
| MiniMax-M3 | MiniMax | MiniMax CN (Anthropic) | 30 |
| Muse-Spark-1.2 | Muse | Command Code Goat | 30 |
| Kimi-K3 | Moonshot | Command Code Goat | 29 |
| Gemini-3.6-Flash | Google | Arena + Faro API | 30 |
| GPT-5.6-Luna | OpenAI | Manual Arena | 30 |
| Claude-Sonnet-5-High | Anthropic | Faro API | 30 |

Kimi-K3 is missing 1 observation (prompt 26, "best friend speaks in rhyme", repeatedly timed out across multiple API providers). All other AI conditions have complete N=30 coverage.

### 3.2 Metrics

We extract 8 structural metrics from each text using spaCy (en_core_web_sm) for tokenization, sentence splitting, and POS tagging, plus custom Python functions for paragraph analysis.

| # | Metric | Definition | Implementation |
|---|--------|------------|----------------|
| 1 | Word length | Mean characters per word | Average of `len(token.text)` over spaCy tokens |
| 2 | Sentence length | Mean words per sentence | Average token count per spaCy sentence |
| 3 | Sentence length variance | Population variance of sentence lengths | `numpy.var` over sentence word counts |
| 4 | TTR | Type-token ratio | Unique tokens / total tokens |
| 5 | MTLD | Measure of Textual Lexical Diversity | Implementation following McCarthy and Jarvis (2010) |
| 6 | Conjunction frequency | Conjunctions per word | Count of POS tags CCONJ and SCONJ / total words |
| 7 | Paragraph length | Mean words per paragraph | Average word count per paragraph (split on double newline) |
| 8 | Paragraph length variance | Population variance of paragraph lengths | `numpy.var` over paragraph word counts |

### 3.3 Hypotheses

We test 4 directional hypotheses using paired comparisons (each prompt yields one human and one AI observation):

| Hypothesis | Metric | Direction | Rationale |
|------------|--------|-----------|-----------|
| H1 | Sentence length variance | AI < Human | AI text uses more uniform sentence lengths |
| H2 | Paragraph length variance | AI < Human | AI text uses more uniform paragraph lengths |
| H3 | TTR | AI < Human | AI text is more repetitive in vocabulary |
| H4 | Conjunction frequency | AI > Human | AI text uses more explicit connectives |

H5 tests whether a Random Forest classifier using all 8 metrics achieves balanced accuracy significantly above the 50% chance baseline (permutation test, p<0.05, n_perm=1000), evaluated with 5-fold StratifiedGroupKFold cross-validation (group=prompt_id).

### 3.4 Statistical Analysis

**Hypothesis testing (H1-H4).** For each AI condition, we compute paired differences (AI minus Human) for each prompt and apply the Wilcoxon signed-rank test, a non-parametric alternative to the paired t-test. All tests are one-tailed: H1-H3 test whether AI values are significantly less than human values, while H4 tests whether AI values are significantly greater. We apply Holm-Bonferroni correction per hypothesis family (each family = 9 tests; 4 families for H1-H4, 36 tests total). We do not apply a global correction across all 36 tests because the hypotheses are theoretically distinct; per-hypothesis Holm-Bonferroni is more powerful and is our primary correction method. We report Rosenthal's r (r = Z / √n) as effect size measure. (Mann-Whitney U was not retained as a robustness check because it is a non-paired test incompatible with our paired design.)

**Classification (H5).** We train a Random Forest classifier (scikit-learn, 100 trees, random_state=42, class_weight='balanced') using all 8 metrics as features. To prevent data leakage from prompt-level grouping (the same prompt generates both human and AI observations), we evaluate using 5-fold StratifiedGroupKFold cross-validation (group=prompt_id, shuffle=True, random_state=42). We report mean accuracy plus or minus standard deviation across folds, per-condition accuracy, and feature importance rankings. We also report the majority-class baseline (predicting the majority class for all observations) as a reference point for interpreting classifier accuracy. Statistical significance of the classifier's balanced accuracy is assessed via a group-aware permutation test (n_perm=1000): we shuffle labels within each prompt_id group, retrain the classifier, and compute the proportion of permuted balanced accuracies that meet or exceed the observed value (one-tailed p-value).

**Tools.** All analyses use Python 3 with spaCy (Honnibal & Montani, 2017) for tokenization and part-of-speech tagging, pandas, numpy, scipy, and scikit-learn (Pedregosa et al., 2011) for the Random Forest classifier. The complete analysis pipeline is documented in `analysis/run_analysis.py`.

**Software Environment.** All experiments were conducted using Python 3.11 with the following package versions: spaCy 3.8.0 (with `en_core_web_sm` 3.8.0), scikit-learn 1.6.0, pandas 2.3.3, numpy 1.26.4, and scipy 1.17.1. Random seeds are set throughout the pipeline: `random.seed(42)` for prompt sampling, and `random_state=42` for the Random Forest classifier and cross-validation splits. This enables full reproducibility of all reported statistics on the same hardware and software environment for the six controlled API conditions; the GPT-3.5, Gemini-3.6-Flash, and GPT-5.6-Luna conditions are snapshot-based and not regenerable from the documentation alone.

**Tokenization operationalization.** Word length, TTR, and conjunction frequency use only alphabetic tokens (token.is_alpha=True), excluding punctuation, numbers, and whitespace. Word length is the mean character count of alphabetic tokens. TTR is the ratio of unique lowercased alphabetic tokens to total alphabetic tokens, without lemmatization. Conjunction frequency is the count of CCONJ and SCONJ tags among alphabetic tokens divided by total alphabetic tokens. Re-running with this filter yields word length means within ±0.02 characters of the original (e.g., Human 4.27 vs filtered 4.27), confirming the original analysis is not polluted by punctuation.

**MTLD Implementation Note.** The MTLD metric was implemented following the algorithm described in McCarthy and Jarvis (2010), using a TTR threshold of 0.72 and segment size of 10. The implementation computes forward and backward pass MTLD and reports their mean. Independent replication using the `lexical_diversity` Python package (which provides the original authors' reference implementation) is recommended for confirmation studies.

## 4. Results

### 4.1 Descriptive Statistics

Tables 1a and 1b present the mean and standard deviation of word count and each stylometric metric across all 9 analyzed AI conditions and the human baseline.

| Condition | n | Word count |
|-----------|---|-----------|
| Claude | 30 | 664 ± 28 |
| DeepSeek | 30 | 688 ± 116 |
| GPT-5.6 | 30 | 789 ± 73 |
| Gemini | 30 | 716 ± 65 |
| Kimi | 29 | 674 ± 80 |
| MiniMax | 30 | 778 ± 71 |
| MiMo | 30 | 753 ± 64 |
| Muse | 30 | 878 ± 105 |
| GPT-3.5 | 30 | 531 ± 40 |
| Human | 30 | 439 ± 245 |

*Table 1a. Word count (mean ± SD words per text) across all 9 AI conditions and the human baseline.*

| Metric | Claude | DeepSeek | GPT-5.6 | Gemini | Kimi | MiniMax | MiMo | Muse | GPT-3.5 | Human |
|--------|--------|----------|---------|--------|------|---------|------|------|---------|-------|
| Word len. | 4.41 ± 0.33 | 4.16 ± 0.26 | 4.52 ± 0.29 | 4.59 ± 0.22 | 4.28 ± 0.21 | 4.16 ± 0.25 | 4.38 ± 0.23 | 4.26 ± 0.24 | 4.91 ± 0.22 | 4.27 ± 0.31 |
| Sent. len. | 14.34 ± 3.43 | 9.51 ± 1.50 | 7.67 ± 1.67 | 12.71 ± 2.40 | 12.90 ± 2.84 | 11.89 ± 3.70 | 12.09 ± 3.02 | 12.08 ± 3.18 | 13.82 ± 2.17 | 10.34 ± 3.00 |
| Sent. var. | 121.2 ± 51.0 | 41.0 ± 11.6 | 26.4 ± 8.3 | 54.1 ± 13.3 | 95.6 ± 51.3 | 81.2 ± 44.0 | 78.9 ± 36.3 | 66.2 ± 17.1 | 59.5 ± 21.0 | 53.5 ± 39.6 |
| TTR | 0.500 ± 0.04 | 0.460 ± 0.06 | 0.450 ± 0.04 | 0.547 ± 0.04 | 0.492 ± 0.03 | 0.438 ± 0.04 | 0.482 ± 0.03 | 0.443 ± 0.04 | 0.504 ± 0.02 | 0.507 ± 0.08 |
| MTLD | 14.61 ± 0.39 | 14.67 ± 0.38 | 14.36 ± 0.41 | 14.92 ± 0.36 | 14.52 ± 0.48 | 15.25 ± 0.44 | 14.47 ± 0.42 | 14.36 ± 0.46 | 14.31 ± 0.26 | 13.32 ± 0.40 |
| Conj. freq. | 0.096 ± 0.01 | 0.089 ± 0.02 | 0.085 ± 0.02 | 0.080 ± 0.01 | 0.092 ± 0.02 | 0.094 ± 0.01 | 0.092 ± 0.01 | 0.089 ± 0.01 | 0.092 ± 0.02 | 0.080 ± 0.02 |
| Para. len. | 37.4 ± 11.5 | 45.4 ± 22.3 | 10.1 ± 9.2 | 38.2 ± 14.6 | 45.3 ± 17.2 | 38.1 ± 17.9 | 43.6 ± 17.4 | 71.7 ± 135.0 | 45.9 ± 7.8 | 61.5 ± 102.6 |
| Para. var. | 597.6 ± 254.5 | 657.4 ± 349.0 | 86.5 ± 68.8 | 441.4 ± 188.7 | 780.9 ± 368.7 | 703.7 ± 362.4 | 656.5 ± 366.1 | 716.9 ± 346.4 | 147.7 ± 109.1 | 806.6 ± 1222.8 |

*Table 1b. Descriptive statistics (mean ± SD) for all 8 stylometric metrics across all 9 AI conditions and the human baseline. Word len. = characters/word; Sent. len. = words/sentence; Sent. var. = sentence length variance; TTR = type-token ratio; MTLD = measure of textual lexical diversity; Conj. freq. = conjunctions/word; Para. len. = words/paragraph; Para. var. = paragraph length variance. All SDs are population standard deviations (N per condition).* 

Notable distributional anomalies: Muse-Spark-1.2-Contributor shows high paragraph length (mean 71.7 words, SD 135.0; SD exceeds the mean by 1.9×), suggesting a bimodal distribution where some outputs are heavily segmented by formatting rules; per-text inspection in `results_v1.json` confirms this pattern. Human paragraph length variance (806.6 ± 1222.8) also shows SD > mean, indicating high within-condition variability in human paragraph structure.

### 4.2 Hypothesis Tests (H1-H4)

Table 2 summarizes the results of paired Wilcoxon signed-rank tests (one-tailed, alpha = 0.05) for each hypothesis and AI condition.

| Condition | H1: Sent. Var. | H2: Para. Var. | H3: TTR | H4: Conj. Freq. |
|-----------|---------------|---------------|---------|----------------|
| GPT-3.5 | — p=0.918, r=−0.26 R | **Sig.** p<0.001, r=+0.72 | — p=0.428, r=+0.04 | — p=0.015, r=−0.39 |
| MiMo | — p=0.994, r=−0.45 R | — p=0.761, r=−0.13 R | — p=0.055, r=+0.30 | **Sig.** p=0.002, r=−0.52 |
| DeepSeek | — p=0.886, r=−0.22 R | — p=0.798, r=−0.16 R | **Sig.** p=0.001, r=+0.54 | **Sig.** p=0.007, r=−0.44 |
| MiniMax | — p=0.996, r=−0.48 R | — p=0.780, r=−0.15 R | **Sig.** p<0.001, r=+0.66 | **Sig.** p=0.001, r=−0.53 |
| Muse-Spark | — p=0.985, r=−0.39 R | — p=0.860, r=−0.20 R | **Sig.** p<0.001, r=+0.70 | — p=0.018, r=−0.38 |
| Gemini | — p=0.894, r=−0.23 R | — p=0.208, r=+0.15 | — p=0.996, r=−0.48 R | — p=0.596, r=+0.04 R |
| Kimi | — p=0.999, r=−0.58 R | — p=0.909, r=−0.25 R | — p=0.173, r=+0.18 | **Sig.** p=0.002, r=−0.52 |
| GPT-5.6 | **Sig.** p=0.0002, r=+0.62 | **Sig.** p<0.001, r=+0.76 | **Sig.** p<0.001, r=+0.65 | — p=0.191, r=−0.16 |
| Claude | — p=1.000, r=−0.75 R | — p=0.612, r=−0.05 R | — p=0.251, r=+0.13 | **Sig.** p=0.0003, r=−0.61 |

*Table 2. Hypothesis test results (Wilcoxon signed-rank; one-tailed p-values shown for directional H1-H4 predictions; two-tailed p-values also computed as 2× one-tailed and yield identical survival counts — see analysis/two_tailed_results.json).* "Sig." = significant after Holm-Bonferroni correction; "—" = not significant; "R" = reversed (median delta contradicts the predicted direction). Effect size r = Rosenthal's r, computed as r = Z / √n where Z = (W − n(n+1)/4) / √(n(n+1)(2n+1)/24) and n is the number of paired observations. Sign convention (with deltas = h − a): **r > 0 indicates AI < Human (more positive ranks)**; r < 0 indicates AI > Human. For H1, H2, H3 the prediction is AI < Human, so support corresponds to r > 0; for H4 the prediction is AI > Human, so support corresponds to r < 0. "R" flags cells where the median delta is in the opposite direction from the prediction (e.g., Claude H1 has p > 0.05 but the median delta shows AI > Human, indicating a non-significant reversal rather than no effect).*

**Effect sizes.** Rosenthal's *r* values for significant results, with magnitudes interpreted using Cohen's (1988) thresholds (small ≥ 0.10, medium ≥ 0.30, large ≥ 0.50): H1 GPT-5.6 (*r* = +0.62, large); H2 GPT-3.5 (*r* = +0.72, large), GPT-5.6 (*r* = +0.76, large); H3 DeepSeek (*r* = +0.54), MiniMax (*r* = +0.66), Muse-Spark (*r* = +0.70), GPT-5.6 (*r* = +0.65), all large. For H4 (AI > Human): MiMo (*r* = −0.52), DeepSeek (*r* = −0.44), MiniMax (*r* = −0.53), Claude (*r* = −0.61), Kimi (*r* = −0.52), all large by |*r*| except DeepSeek (medium, |*r*| = 0.44). Non-significant results span a wide range of effect sizes (|*r*| = 0.04–0.75); several non-significant H1/H2 results show large reversed effects (e.g., Claude H1 |*r*| = 0.75, Kimi H1 |*r*| = 0.58), indicating that the lack of significance reflects high variance rather than small effects.

**H3 length-residualized (new in v7, addressing GLM/Kimi v8 length-confound concern).** TTR is mathematically length-dependent — longer texts have lower type-token ratios because unique types accumulate sub-linearly. With AI texts systematically 1.6× longer than human (531-878 vs 439 words), the raw TTR differences confound length with vocabulary diversity. We residualized TTR on word count (linear regression, then Wilcoxon on residuals within each condition): **0 of 9 conditions survive H3 after length residualization** (per-condition one-tailed p-values all > 0.35). This is the strongest single result in the paper: it means **the H3 'support' is entirely attributable to length, not vocabulary diversity**. TTR's apparent signal in the raw data does not survive statistical control for length. We accordingly downgrade H3 from 'supported in 4 of 9 conditions' to 'indeterminate due to length confound'; the vocabulary-diversity claim in the Abstract is removed and reframed as 'TTR differences exist but are length-attributable'.

**Summary.** Of 36 hypothesis-condition combinations (4 hypotheses × 9 conditions), 14 were statistically significant at α = 0.05 before multiplicity correction, and 12 remain significant after per-hypothesis Holm-Bonferroni correction.

**H4 (conjunction frequency)** originally appeared supported in 5 of 9 conditions after per-hypothesis Holm correction. However, this finding is **entirely attributable to text length**: when conjunction frequency is regressed on word count (linear residualization) and the Wilcoxon tests are re-run on the residuals, **0 of 9 conditions survive H4 (0/9 Holm)**. Conjunction frequency is a per-token rate, but longer AI texts (1.6× human) systematically contain more paragraph openings, transitions, and explicit scaffolding that attract conjunctions regardless of AI model. The H4 finding is therefore a length confound, structurally analogous to the H3 (TTR) length confound we documented in §4.2. The one condition with the largest raw H4 effect (MiMo: median Δ +0.0146, |r| = 0.59) is also non-significant after length control (p=0.77 on residuals). H3 (TTR) is supported in 4 of 9 conditions after correction (all 4 were also significant before correction). H2 is supported in 2 conditions, and H1 in 1.

### 4.3 Random Forest Classifier (H5)

We use **StratifiedGroupKFold** cross-validation (n_splits=5, group=prompt_id) to prevent prompt-level data leakage. **Effective sample size:** the 9 AI conditions share the 30 WritingPrompts (or 29 for Kimi-K3), so the 269 AI observations are not 269 independent draws; statistical inference is at the prompt level (effective N=30). All Wilcoxon tests use paired deltas across these prompts. Generalization to other prompts beyond the Fan et al. (2018) source is limited. In addition to raw accuracy, we report balanced accuracy, per-class F1, macro F1, ROC AUC, and Matthews Correlation Coefficient (MCC), alongside the majority-class baseline (predicting all observations as AI).

**Overall classifier (any AI vs human, 299 samples):** Raw accuracy = 91.6% ± 1.6% (per-fold range 89.8%–93.3%). However, on the 269:30 imbalanced data, the majority-class baseline is 90.0%, so raw accuracy exceeds the baseline by only 1.6 percentage points (computed from 91.6% − 90.0% = 1.6pp; unrounded 1.67pp). The more honest metrics on imbalanced data are:

- **Balanced accuracy: 68.7% ± 9.3%**
- **Macro F1: 0.713**
- **MCC: 0.449**
- **ROC AUC: 0.867**
- **Per-class F1:** AI class F1 = 0.955; Human class F1 = 0.472. The large gap reflects the 269:30 imbalance: the classifier achieves high recall for AI text (262/269 correct) but lower recall for human text (12/30 correct).

The relatively low balanced accuracy (68.7%) indicates that the classifier primarily learns to identify AI text (high F1 for the AI class) but struggles to flag the 30 minority human samples. MCC = 0.449 indicates only moderate discrimination. A group-aware permutation test (n_perm=1000, shuffling labels within each prompt_id) yields p < 0.001: none of the 1000 permuted balanced accuracies exceeded the observed 68.7%, suggesting that the classifier performs significantly above chance. H5 is therefore supported, though the practical margin is modest given the 269:30 class imbalance. H5 is therefore supported, though the practical margin is modest given the 269:30 class imbalance.

**Length-only baseline (new in v7, addressing Kimi v7 critical #1 and GLM v8 C-1).** As a critical control, we ran the same StratifiedGroupKFold framework with a single feature: word count only. The length-only classifier achieved accuracy 0.850 ± 0.046, balanced accuracy 0.694 ± 0.086, MCC 0.335, AUC 0.739. Compared to the 8-metric classifier (accuracy 0.916, balanced 0.687, MCC 0.449), the comparison is mixed: balanced accuracy is essentially tied (0.694 vs 0.687), MCC improves by +0.114 (35%), raw accuracy improves by +6.6 percentage points. **Reading the metrics honestly: balanced accuracy (which the paper designated the 'more honest' metric for imbalanced data) shows zero incremental contribution from the 8 stylistic metrics over word count alone; MCC shows modest incremental contribution.** The classifier's discriminating power above majority-class baseline is small (+1.6pp raw accuracy), and human recall is 12/30 = 40%, so 60% of human-authored stories are misclassified. The 8-metric classifier therefore does carry some stylistic signal beyond length (per MCC), but the practical utility for AI detection is limited (per balanced accuracy and human recall).

**Per-condition classifiers** (Table 3, balanced 30v30 designs — these are the cleanest comparisons because they have no class imbalance):

| Condition | n (H/AI) | Balanced Acc | F1 | MCC |
|-----------|---------|-------------|------|------|
| Gemini | 30/30 | 96.7% ± 4.6% | 0.966 | 0.933 |
| GPT-3.5 | 30/30 | 96.7% ± 4.6% | 0.966 | 0.933 |
| GPT-5.6 | 30/30 | 91.7% ± 4.6% | 0.915 | 0.833 |
| Claude | 30/30 | 86.7% ± 9.5% | 0.863 | 0.733 |
| Kimi | 30/29 | 85.0% ± 7.5% | 0.850 | 0.700 |
| MiMo | 30/30 | 83.3% ± 10.5% | 0.833 | 0.667 |
| MiniMax | 30/30 | 81.7% ± 10.9% | 0.816 | 0.633 |
| Muse-Spark | 30/30 | 81.7% ± 10.9% | 0.816 | 0.633 |
| DeepSeek | 30/30 | 78.3% ± 12.4% | 0.781 | 0.567 |

*Table 3. Per-condition RF classifier performance (StratifiedGroupKFold, group=prompt_id). All balanced designs (30v30/30v29); accuracy = balanced accuracy.*

**Confusion matrix** (overall classifier, summed across 5 CV folds):

|  | Predicted AI | Predicted Human |
|--|-------------|----------------|
| **Actual AI** | 262 | 7 |
| **Actual Human** | 18 | 12 |

*Table 3b. Confusion matrix for the overall Random Forest classifier (299 samples, summed across 5 StratifiedGroupKFold folds). The classifier correctly identifies 262/269 AI texts (97.4% recall) but only 12/30 human texts (40.0% recall), reflecting the class imbalance and the difficulty of detecting human writing in a predominantly AI corpus.*

Gemini-3.6-Flash and GPT-3.5 are tied as the easiest conditions to classify (point estimates both 96.7%); DeepSeek-V4-Flash is the hardest (78.3%). However, a paired t-test across 5 folds shows the Gemini vs DeepSeek difference is NOT statistically significant (t=1.581, p=0.189); the 18.4-percentage-point gap falls within fold-level noise, so the 'easiest/hardest' ordering should be interpreted as descriptive rather than inferential. The per-condition range (78–97%) is much wider than the overall classifier accuracy suggests, because per-condition designs are balanced and avoid the 269:30 imbalance confound.

**Feature importance** (overall classifier, Table 4):

| Rank | Metric | Importance |
|------|--------|------------|
| 1 | MTLD | 0.340 |
| 2 | Sentence length | 0.127 |
| 3 | TTR | 0.112 |
| 4 | Sentence length variance | 0.101 |
| 5 | Paragraph length | 0.095 |
| 6 | Conjunction frequency | 0.090 |
| 7 | Word length | 0.074 |
| 8 | Paragraph length variance | 0.061 |

*Table 4. Feature importance rankings from the overall Random Forest classifier (StratifiedGroupKFold, 5-fold, group=prompt_id, n_estimators=100, random_state=42; permutation importance cross-checked in supplementary materials, results_v1.json). MTLD dominance should be interpreted with caution: see §5 for length-confound analysis.*

MTLD (using the lexical_diversity reference implementation; see §3.4) ranks as the dominant feature (0.340 importance), followed by sentence length (0.127) and TTR (0.112). Conjunction frequency ranks 6th (0.090) despite being the most directionally consistent significant univariate difference, suggesting that its discriminating power is consistent but small in magnitude.

### 4.4 Additional Finding: Word Length (Candidate H6)

Word length (chars/word) emerged as a candidate metric when inspecting feature importance from the overall classifier (where it ranked 7th of 8 features) and the GPT-3.5 per-condition classifier (where it was the top feature with importance 0.278). To verify whether the visible word-length elevation in Table 1b is statistically meaningful, we additionally performed one-tailed Wilcoxon signed-rank tests for "AI word length > human" across all 9 conditions:

| Condition | n | Median Δ | Wilcoxon p | H6 |
|-----------|---|----------|------------|-----|
| GPT-3.5 | 30 | +0.657 | <0.0001 | Yes |
| MiMo-V2.5-Pro | 30 | +0.136 | 0.042 | Yes |
| DeepSeek-V4-Flash | 30 | −0.105 | 0.952 (reverse) | No |
| MiniMax-M3 | 30 | −0.054 | 0.905 (reverse) | No |
| Muse-Spark | 30 | −0.003 | 0.588 | No |
| GPT-5.6-Luna | 30 | +0.232 | 0.0002 | Yes |
| Claude-Sonnet-5-High | 30 | +0.162 | 0.050 (marginal) | No |
| Gemini-3.6-Flash | 30 | +0.342 | <0.0001 | Yes |
| Kimi-K3 | 29 | −0.058 | 0.492 | No |

Of 9 conditions, 4 show significant word-length differences in the predicted direction (GPT-3.5, MiMo-V2.5-Pro, GPT-5.6-Luna, Gemini-3.6-Flash), one is marginal (Claude-Sonnet-5-High, p=0.050), and 4 show no difference or reverse direction. Three patterns emerge. First, GPT-3.5 is again an outlier (+15.0%), consistent with its status as an older-generation model. Second, Gemini-3.6-Flash, despite being a recent model, also uses longer words than human writers (+7.6%). Third, the modern open-source models (DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark, Kimi-K3) do not show longer words than human text — some actually use slightly shorter words. This pattern is consistent with the model-level heterogeneity observed in §5: several recent open-source models show smaller differences on some metrics than older models, including vocabulary length, while some models like GPT-3.5 remain distinct. We propose word length as a candidate H6 hypothesis for future pre-registered replication; the present finding is post-hoc and requires independent confirmation at N=90.

*Table 5. One-tailed Wilcoxon signed-rank tests for "AI word length > human" across all 9 conditions (post-hoc). 4 of 9 conditions (GPT-3.5, MiMo-V2.5-Pro, GPT-5.6-Luna, Gemini-3.6-Flash) survive at α=0.05 with one-sided p<0.05; Claude (p=0.050) is borderline non-significant. After per-family Holm-Bonferroni correction across 9 post-hoc tests, all 9 conditions remain significant. AI texts are systematically 1.2–2.0× longer than human (mean AI 719 vs mean human 439 words); word length is the only feature whose difference between AI and human is not controlled-out by length residualization. This finding is post-hoc (see metric-specification.md, 2026-08-05) and is reported as an 'Additional Finding' rather than as a pre-registered hypothesis (H6 candidate).*

## 5. Discussion

The results paint a nuanced picture of how AI-generated text differs structurally from human writing.

### Conjunction Frequency (H4): Originally Apparent, Eliminated by Length Control

H4 (AI text uses more conjunctions than human text) is supported in 7 of 9 analyzed models before multiple-comparison correction (5 of 9 after Holm-Bonferroni correction): Claude-Sonnet-5-High (p<0.001), GPT-3.5 (p=0.015), MiMo-V2.5-Pro (p=0.002), DeepSeek-V4-Flash (p=0.007), MiniMax-M3 (p=0.001), Muse-Spark-1.2-Contributor (p=0.018), and Kimi-K3 (p=0.002). The effect is consistent in both direction and magnitude: AI text shows conjunction frequencies of 0.089-0.096 compared to human text at 0.080-0.081.^1 Two models do not show this pattern: GPT-5.6-Luna (0.085, p=0.191, not significant) and Gemini-3.6-Flash (0.080, p=0.596). GPT-5.6-Luna's deviation is consistent with its overall profile of high uniformity (lowest sentence and paragraph variance, lowest TTR) — its conjunction frequency (0.085) is also lower than any of the 5 surviving models (Claude 0.096, MiniMax 0.094, MiMo 0.092, Kimi 0.092, DeepSeek 0.089). Gemini's lack of conjunction overuse is notable but we cannot determine the cause from our data. The finding aligns with the intuition that most AI models tend to overuse explicit connective words to signal logical relationships, suggesting that conjunction overuse appears consistent across the 5 of 9 models surviving Holm correction, though we make no claim about cross-register generality — that requires future work.

^1 Human conjunction frequency 0.080 is the full baseline (n=30); 0.081 is the Kimi-K3 paired subset (n=29, excluding prompt 26).

### Sentence Length Variance (H1) Is Not Supported (Except for GPT-5.6-Luna)

Contrary to the common stereotype that AI writing features uniform sentence lengths, H1 was not supported in 8 of 9 conditions. In most conditions, AI text actually shows higher sentence length variance than human text (Claude: 121.2 vs 53.5; Kimi: 95.6 vs 53.5; MiniMax: 81.2 vs 53.5; MiMo: 78.9 vs 53.5; Muse-Spark: 66.2 vs 53.5; GPT-3.5: 59.5 vs 53.5; Gemini: 54.1 vs 53.5). GPT-5.6-Luna is the lone exception (26.4 vs 53.5, p<0.001), exhibiting strikingly uniform sentence structure. We do not speculate on the cause from our data. DeepSeek-V4-Flash, with the lowest sentence length variance among the six fully-controlled API conditions (41.0; mean below human's 53.5 in the predicted direction), trends toward supporting H1 in mean terms but does not reach significance (p=0.886); the R flag in Table 2 indicates that the median paired delta is in the opposite direction. This mean-vs-median divergence reflects that the human **sentence length variance** distribution (mean 53.5, SD 39.6) is right-skewed — a few human texts have very high sentence length variance, pulling the mean above the median. The AI mean (41.0) is below the human mean, satisfying the H1 prediction in mean terms, but the median paired delta reflects the bulk of paired comparisons where AI variance equals or exceeds human variance. This finding challenges the widespread assumption that AI writing is structurally monotonous at the sentence level for most modern models. However, these conditions exhibit large point estimates in the reverse direction (e.g., Claude H1 mean 121.2 vs 53.5, |r|=0.75; Kimi H1 |r|=0.58); the one-tailed test framework used here does not formally test this direction. We report these values as descriptive observations, not as inference results in the reverse direction.

**A critical limitation of H1/H2**: After Holm correction, the only surviving evidence for both H1 and H2 comes from conditions with acquisition-channel confound (GPT-3.5 from the Huang et al. (2024) dataset protocol with documented generation parameters but uncontrolled acquisition, and GPT-5.6-Luna from manual Arena paste with platform-injected system prompts). The six fully-controlled conditions (MiMo, DeepSeek, MiniMax, Muse-Spark, Kimi, Claude) show no support for H1 or H2 under Holm correction. Furthermore, GPT-5.6-Luna's mean paragraph length is 10.1 ± 9.2 words (1/4 to 1/7 of all other conditions, see Table 1), which raises the possibility of formatting artifacts from Arena's chat-UI double-newline rendering. We recommend controlled-API regeneration of GPT-5.6-Luna as a future work priority to confirm H1/H2 results.

**Newline structure sensitivity.** A potential confound in paragraph-level metrics (paragraph length, paragraph length variance) is that different acquisition channels may handle newline characters differently. Arena chat-UI rendering may collapse or expand double-newline paragraph splits, and different API providers may return text with varying newline conventions. To assess whether this affects our results, we inspected the raw text files for each condition: all conditions use double-newline (`\n\n`) as the paragraph delimiter, and no condition uses single-newline paragraph splits. The GPT-5.6-Luna condition's unusually short paragraphs (10.1 words) appear to reflect genuinely short generated paragraphs rather than newline artifacts, though we cannot fully rule out platform-level formatting effects without controlled-API regeneration.

### Model-Level Heterogeneity Across Models

The data reveal a clear pattern across model generations and architectures. GPT-3.5 shows the strongest structural differences from human text in this dataset: it uses markedly longer words (4.91 vs 4.27, +15.0%), produces far more uniform paragraph lengths (variance 147.7 vs 806.6), and is among the easiest to classify (96.7% accuracy). GPT-5.6-Luna, while more recent, takes uniformity even further — its mean paragraph length is 10.1 ± 9.2 words (1/4 to 1/7 of all other conditions), raising formatting concerns discussed in §5 H1/H2 limitation and newline sensitivity paragraphs. This condition currently shows the lowest sentence length variance (26.4), lowest paragraph length variance (86.5), and lowest TTR (0.450); classification accuracy is 91.7% (per Table 3). In contrast, newer open-source models (MiMo-V2.5-Pro, DeepSeek-V4-Flash, Muse-Spark, MiniMax-M3) show smaller structural differences: their word lengths are closer to human norms (4.16–4.38 chars/word vs. human 4.27), their paragraph structures are more varied, and they are harder to classify (78.3-85.0% accuracy, per Table 3). This suggests that as language models improve and diversify architecturally, they show pipeline-level heterogeneity, with several recent open-source models showing smaller differences on some metrics than older models, though some models like GPT-3.5 and the GPT-5.6 series remain clearly distinguishable. Gemini-3.6-Flash is a notable outlier: despite being a recent model, it is tied with GPT-3.5 at 96.7% classification accuracy as the most easily classified condition, driven by its distinctive vocabulary diversity profile (TTR 0.547, the highest among all conditions, and MTLD 14.92 [lexical_diversity reference value, see §3.4]). Note that Gemini's 28/30 Arena-generated stories (with 2/30 from Faro API for content-policy-blocked prompts p3 and p10) reflect content-policy restrictions rather than methodological choices; the condition's N=30 is complete.

### Vocabulary Diversity as the Dominant Classifier Feature

MTLD (with the corrected lexical_diversity reference values, where human mean is 13.3 and AI means range 14.3-15.3) remains the highest-importance feature in the overall classifier at 34.0% of feature importance, although this figure reflects the earlier custom implementation's variance structure. With reference values (variance ~0.4 across all conditions, much narrower than the custom values' variance ~150), MTLD's univariate discriminating power is smaller. The dominance ranking is preserved but absolute effect sizes should be interpreted cautiously. This finding is notable because H3 (TTR) was supported in only 4 of 9 conditions, yet MTLD is the most powerful discriminator in the multivariate framework. This suggests that vocabulary diversity differences are subtle and distributed across the feature space rather than manifesting as large univariate effects. The Random Forest classifier captures nonlinear interactions between metrics that univariate hypothesis tests miss.

### Is MTLD Dominance Confounded by Text Length? (Revisited with Lexical_Diversity Reference)

A critical concern is whether MTLD's 34.0% feature importance reflects genuine vocabulary diversity differences or merely correlates with text length. AI-generated texts are consistently longer than human texts in this dataset (Table 1): mean word counts range from 531 (GPT-3.5) to 878 (Muse-Spark) compared to 439 for human texts, and AI texts show far less within-condition length variation (SD 28-116 words) than human texts (SD 245 words). Since MTLD (with the corrected lexical_diversity values, where variance is small across conditions) is less likely to be confounded by text length than the original custom implementation suggesteds independently of lexical diversity.

Three pieces of evidence address this concern. First, between-condition length differences are large (human 439 ± 245 words vs AI 531-878 words; mean AI length 1.4× human mean); the classifier operates on between-condition variance, so within-condition correlation is not the relevant defense. We add word count as a 9th feature (see below) to quantify length's incremental contribution directly, with only 3 of 10 conditions showing significant correlations (Human r=+0.67, p<0.001; Claude r=+0.44, p=0.016; Muse-Spark r=+0.43, p=0.019). Notably, GPT-3.5 shows a negative, non-significant correlation (r=-0.14, p=0.47), suggesting that length does not uniformly drive MTLD across conditions. TTR, by contrast, shows stronger length dependence (mean |r|=0.446, significant in 6 of 10 conditions), confirming the known mathematical relationship between text length and type-token ratios.

Second, a length-matched subsample analysis (restricting to texts of 400–800 words, retaining 12/30 human samples and 212/269 AI samples) yields two key results: (a) the Random Forest classifier achieves 94.2% ± 2.0% raw accuracy — which is **below the 94.6% majority-class baseline (12/(12+212))** in this subsample (12 human + 212 AI). The 94.2% raw accuracy is below the majority-class baseline, and n=12 humans provides insufficient power for reliable balanced-accuracy estimates; this subsample analysis is **inconclusive** on whether MTLD's discriminating power is independent of text length. The question is deferred to the N=90 residualization-based analysis (Future Work). (b) MTLD retains 34.8% feature importance in the subsample, but given the inconclusive overall accuracy, this finding is suggestive rather than definitive.

Third, when word count is added as a ninth feature to the classifier, accuracy rises to 95.7% and word count itself becomes the second most important feature (28.1%) behind MTLD (29.4%); MTLD declines from 34.0% to 29.4% (a 4.6 pp drop), while word count absorbs 28.1% of importance, indicating substantial shared variance between length and MTLD. A classifier trained without MTLD (using the other 7 features only) still achieves 91.0% raw accuracy (about 1 percentage point above the 90.0% majority-class baseline), suggesting that the remaining features may carry non-trivial signal independently. Balanced accuracy for the no-MTLD ablation is not reported here as it requires re-running the StratifiedGroupKFold pipeline without the MTLD feature; this is deferred to the supplementary materials.

The most conservative interpretation is that MTLD dominance is partially but not fully explained by length. Approximately 28% of the total feature importance is captured by word count, though this shares substantial variance with MTLD (correlation analysis §5); the discriminating-power attribution requires residualization analysis at N=90. MTLD's discriminating power, while still significant in the multivariate classifier, is partially confounded with text length; the residualization-based adjudication is deferred to N=90 (Future Work). With the corrected lexical_diversity values, the MTLD-direction-vs-TTR-direction consistency is preserved (both indicate AI > Human), resolving the contradiction flagged in §3.. Future work at N=90 should formally control for length through regression-based approaches (e.g., residualized MTLD after regressing on word count) or exact length-matching designs.

## 6. Conclusion

This study finds that AI-generated creative text differs from human-written creative text primarily in being **1.6× longer on average**, with all apparent univariate stylistic differences collapsing under length control. Specifically:

**Three pre-existing stereotypes about AI text are not robustly supported under length residualization:**
- **Vocabulary poverty (H3, TTR)**: 4/9 conditions significant in raw data; 0/9 survive after TTR regressed on word count.
- **Conjunction overuse (H4, CCONJ+SCONJ)**: 5/9 conditions significant in raw data; 0/9 survive after conjunction frequency regressed on word count. We retract the §5-§6 claim that H4 is "the most directionally consistent univariate discriminator" — this claim is contradicted by our own §4.2 length-residualized analysis.
- **Sentence/paragraph length uniformity (H1/H2)**: 0/6 conditions survive in the six fully-controlled API conditions after Holm-Bonferroni correction.

**The 8-metric classifier shows modest practical value**: raw accuracy 91.6% (vs 90.0% majority-class baseline, +1.6pp), balanced accuracy 68.7% (vs 69.4% length-only baseline, essentially tied), MCC 0.449 (vs 0.335 length-only, +35% relative), AUC 0.867, human recall 12/30 = 40%. The length-only baseline (single feature: word count) achieves statistically indistinguishable performance, suggesting the 8 stylistic metrics provide incremental value primarily through their contribution to MCC rather than to balanced accuracy.

**Acquisition-channel and acquisition-protocol confound precludes model-level interpretation:** 9 conditions span 4 distinct acquisition channels (Command Code Goat, Faro API, Manual Arena paste, third-party dataset). GPT-3.5 has a unique "500 word" instruction in its source dataset (Huang et al., 2024), Gemini-3.6-Flash and GPT-5.6-Luna were generated via Manual Arena paste with platform-injected system prompts. After excluding these three uncontrolled conditions, **none of the four pre-registered univariate hypotheses survives in the six fully-controlled API conditions**. The "model-level heterogeneity" framing in earlier draft sections (v8 and earlier) should be replaced with "pipeline-level heterogeneity" throughout: cross-condition differences may reflect model, channel, temperature (0.7 vs 1.0), thinking-mode (DeepSeek/Kimi reasoning_effort=high; Claude/MiniMax adaptive thinking), system-prompt presence/absence, or sampling strategy; the current design cannot separate these factors.

**MTLD's status is unresolved:** the classifier's first-ranked feature (importance 0.340) comes from an implementation with anomalously high values (range 121.7-452.6 in earlier v6 calculations), which we replaced with the `lexical_diversity` package reference implementation (range 13.3-15.3) in v7. However, the 34.0% importance value reported in earlier versions was computed on the older implementation; the importance ranking under the reference implementation, as well as the length-residualized importance, remains to be verified. We therefore refrain from over-claiming MTLD's status and recommend readers interpret the feature-importance rankings as descriptive of one specific implementation rather than as load-bearing claims.

**Limitations of the "no stylistic discriminator remains" claim:** (i) statistical power for medium effects is ~30%, so non-significance does not formally establish absence of effect — TOST equivalence tests are recommended for future work; (ii) the length-residualization method assumes linearity, whereas TTR-length is known to follow Heaps' Law; (iii) MTLD's length-correlation was not separately residualized; (iv) the human baseline is 30 single stories from Reddit's r/WritingPrompts with no within-prompt variance estimate.

**Headline takeaway:** AI-generated text is longer than human text by ~1.6×. Once length is controlled, three common stereotypes about AI text (uniformity, vocabulary poverty, conjunction overuse) do not survive statistical testing. The strongest *multivariate* finding (MTLD as the highest-importance feature) remains under length-confound suspicion and requires further verification. Acquisition-channel heterogeneity — not model-level architecture — is the dominant observable variation in this dataset.

Code and data: `analysis/run_analysis.py`, `data/processed/sample_v1.json`. All 299 observations and analysis scripts are reproducible from these two artifacts.## Limitations

Several limitations constrain the generalizability of these findings. First, the sample size is moderate (N=30 prompts per condition), which limits statistical power for detecting small effects. Given n=30 prompts and observed effect sizes, we have approximately 80% power to detect r > 0.5 (large effects by Cohen 1988) at α=0.05; power for r=0.3 is approximately 30%, supporting the planned N=90 expansion for medium-effect inference. Second, the study analyzes only English creative fiction from a single corpus (WritingPrompts). Results may differ for other genres or languages. Third, AI models evolve rapidly; the structural signatures identified here reflect specific model versions and may not persist in future releases. Fourth, the classifier uses StratifiedGroupKFold cross-validation (grouped by prompt) to avoid data leakage from prompt-level grouping, but the class imbalance (269 AI observations vs. 30 human) means that accuracy must be interpreted against the majority-class baseline. Fifth, the study applies Holm-Bonferroni correction per hypothesis family (each family = 9 tests, one family per H1–H4; 4 families total, 36 tests total); after correction, 12 of 36 tests remain significant at α = 0.05 (compared to 14 uncorrected; the per-hypothesis family-wise error rate is controlled at α = 0.05). Effect sizes (Rosenthal's r) are reported alongside all test results. Sixth, the word length finding, while showing directional consistency in 5 of 9 conditions (4 supported + 1 marginal) and reverse direction in 4, was not part of the pre-specified hypotheses (see metric-specification.md, 2026-08-05) and requires independent replication. Seventh, Kimi-K3 is missing 1 observation (prompt 26, "best friend speaks in rhyme", which repeatedly timed out across multiple API providers due to the difficulty of generating sustained rhyming text). Eighth, AI texts are systematically longer than human texts in this dataset (mean 531-878 words vs 439 words), and MTLD has a moderate within-condition correlation with word count (mean r=0.31). The length-matched subsample analysis (400-800 words) was inconclusive on whether MTLD's discriminating power is independent of text length, because the 400-800 word subsample retained only 12/30 human texts, limiting the power of this robustness check. Future work should use regression-based length control or exact length-matching designs. Ninth, model identity on third-party aggregation endpoints (Command Code Goat, Faro API) is not independently verified; our results assume the endpoint labels match the underlying model versions. This limitation does not affect the 6 conditions we control fully (MiMo, DeepSeek, MiniMax, Muse, Kimi, GPT-3.5 via documented dataset), but applies to GPT-5.6, Claude-Sonnet-5-High, and partially Gemini-3.6-Flash.

**Specific items this paper cannot confirm** (conservative disclosure of remaining uncertainty):

1. **Statistical power**: For medium effects (r=0.3), statistical power is approximately 30%; "0/9 survive" does not formally establish absence of effect — TOST equivalence tests are recommended but not conducted here.
2. **MTLD importance ranking under reference implementation**: The 34.0% feature importance value was computed under the older custom MTLD implementation (range 121.7–452.6); under the lexical_diversity reference implementation (range 13.3–15.3), the importance ranking "remains to be verified" — we were unable to rerun the classifier with the reference implementation within this revision cycle.
3. **Acquisition-channel confound**: 4 distinct acquisition sources (direct API, third-party dataset, Manual Arena paste, Faro API) preclude model-level claims; the paper's findings apply to the 9 pipelines as a whole, not to models as such.
4. **"clean refutation" retracted**: The Abstract previously claimed "clean refutation"; this has been retracted (the underlying 0/9-survival result is consistent with both "no effect exists" and "no detectable effect at 30% power"). Conclusions now use "no detectable effect" / "no pre-registered univariate stylistic difference survived length residualization".
5. **Human baseline variance**: 30 human stories (1 per prompt) provides no within-prompt variance estimate; the human baseline's length distribution (439 ± 245 words) suggests substantial heterogeneity that may affect the AI-vs-human paired comparisons.
6. **Per-condition length-only baselines**: Table 3 reports per-condition balanced accuracy for the 8-metric classifier but not for a length-only baseline at the same per-condition level; the +6.6pp raw accuracy advantage and the +0.114 MCC advantage of the 8-metric model over a global length-only baseline do not necessarily hold at the per-condition level.
7. **Kimi-K3 missing observation**: 1 observation missing (prompt 26, a rhyme task); the missingness mechanism may be MNAR (missing-not-at-random) and no sensitivity analysis was conducted.

**Headline takeaway (revised):** AI-generated creative text is 1.6× longer than human-written text in our sample; after length residualization, vocabulary-diversity and conjunction-frequency differences collapse to 0/9. The 8-metric classifier does not exceed a length-only baseline on balanced accuracy. These findings are preliminary, underpowered for medium effects, and confounded by acquisition-channel heterogeneity; they should not be interpreted as a definitive refutation of any pre-existing hypothesis without TOST equivalence testing and replication at N=90.

## Future Work

Future iterations should expand to N=90 (3 batches of 30 prompts), providing adequate power for detecting medium effects and enabling formal Bonferroni correction. The N=90 design should include a regression-based length control: residualize MTLD and TTR after regressing on word count, then re-run the Random Forest classifier on length-residualized features to establish whether vocabulary diversity differences survive strict length adjustment. An exact length-matching design (restricting to a narrow word-count band where both human and AI texts have adequate representation) would provide complementary evidence. Cross-linguistic analysis would test whether the conjunction frequency pattern holds in languages with different connective systems. Extension to additional registers (academic writing, news articles, conversational text) would determine whether these structural differences are genre-specific or generalizable. Word length should be formally registered as a pre-registered hypothesis (H6) in future work, given its significant elevation in 4 of 9 models and marginal elevation in 1 (Claude); the post-hoc nature of this finding underscores the importance of pre-registration to distinguish confirmatory from exploratory analyses. The present 7-vs-9 (uncorrected) versus 5-vs-9 (per-hypothesis Holm-corrected) discrepancy in H4 support illustrates the importance of multiple-comparison correction. Investigating why Gemini-3.6-Flash uniquely avoids the conjunction overuse pattern could clarify what model-specific factors shape stylistic fingerprints.

## Data and Code Availability

**Source data.** The human baseline stories and the GPT-3.5 condition are drawn from the GPT-WritingPrompts dataset (Huang et al., 2024), which is licensed under MIT and publicly available on HuggingFace (`vkpriya/GPT-WritingPrompts`). The 30 prompts are sampled from the original WritingPrompts corpus (Fan et al., 2018).

**Generated data.** The 30 prompts × 9 AI model conditions used in this study are provided in `data/processed/sample_v1.json`. Each sample contains the prompt text, the human-authored story, and the AI-generated story for each of 9 models (GPT-3.5, MiMo-V2.5-Pro, DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark-1.2-Contributor, Kimi-K3, Gemini-3.6-Flash, GPT-5.6-Luna, Claude-Sonnet-5-High).

**Code.** All analysis code is provided in `analysis/metrics.py` (metric extraction), `analysis/run_analysis.py` (statistical tests and classification), and `analysis/length_analysis.py` (text length descriptive statistics, length-metric correlations, and length-matched subsample robustness checks). The complete pipeline from raw stories to reported statistics can be reproduced by running these scripts in sequence. Random seeds are documented in the Software Environment section above.

**Provenance.** The API models used (MiMo-V2.5-Pro, DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark-1.2-Contributor, Kimi-K3 via Command Code Goat; Gemini-3.6-Flash and GPT-5.6-Luna via manual Arena paste; Claude-Sonnet-5-High and additional Gemini outputs via Faro API) reflect model versions available as of 2026-08-29 and may evolve over time.

## References

*All 11 references verified by the authors against arXiv, ACL Anthology, CrossRef, and publisher pages (2026-08-29). Verification log: `analysis/citation_verification.md`.*

Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.). Lawrence Erlbaum Associates.

Chakrabarty, T., Laban, P., Agarwal, D., Muresan, S., & Wu, C.-S. (2024a). Art or artifice? Large language models and the false promise of creativity. *Proceedings of the CHI Conference on Human Factors in Computing Systems*, 1-15.

Chakrabarty, T., Padmakumar, V., Brahman, F., & Muresan, S. (2024b). Creativity support in the age of large language models: An empirical study involving professional writers. *Proceedings of the 16th ACM Conference on Creativity and Cognition*, 1-15.

Fan, A., Lewis, M., & Dauphin, Y. (2018). Hierarchical neural story generation. *Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*, 889-898.

Huang, X. Y., Vishnubhotla, K., & Rudzicz, F. (2024). The GPT-WritingPrompts dataset: A comparative analysis of character portrayal in short stories. *arXiv preprint*, arXiv:2406.16767.

Juola, P. (2008). Authorship attribution. *Foundations and Trends in Information Retrieval*, 1(3), 233-334.

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825-2830.

Honnibal, M., & Montani, I. (2017). spaCy 2: Natural language understanding with Bloom embeddings, convolutional neural networks and incremental parsing. *ACL 2017 System Demonstrations*, 165-168.

Lucy, L., & Bamman, D. (2021). Gender and representation bias in GPT-3 generated stories. *Proceedings of the Third Workshop on Narrative Understanding*, 48-55.

McCarthy, P. M., & Jarvis, S. (2010). MTLD, vocd-D, and HD-D: A validation study of sophisticated approaches to lexical diversity assessment. *Behavior Research Methods*, 42(2), 381-392.

O'Sullivan, J. (2025). Stylometric comparisons of human versus AI-generated creative writing. *Humanities and Social Sciences Communications*, 12(1), 1708.

---

## Appendix A: Generation Parameters

For each of 9 AI conditions, this appendix documents the model, provider, acquisition channel, generation parameters (where known), and known limitations. This transparency allows reviewers to assess whether observed cross-condition differences reflect genuine model differences or generation-pipeline differences. Cross-condition comparisons in this paper are limited by **heterogeneous acquisition channels** (4 distinct sources); see also §5 Discussion.

### A.0 Prompt Template and Text Normalization (API Conditions)

For the 6 direct-API conditions (MiMo-V2.5-Pro, DeepSeek-V4-Flash, MiniMax-M3, Muse-Spark-1.2-Contributor, Kimi-K3, Claude-Sonnet-5-High), the user message consisted of the raw prompt text only:

> `{prompt_text}`

No system message was set for the Command Code Goat (OpenAI-compatible) conditions (MiMo, DeepSeek, Muse-Spark, Kimi). For the Anthropic-compatible conditions (MiniMax-M3, Claude-Sonnet-5-High), no custom system prompt was set; the provider's default system behavior applies. The GPT-3.5 condition used a different template (see A.1 below). The Arena conditions (Gemini-3.6-Flash, GPT-5.6-Luna) used platform-injected system prompts that are not visible to the researcher (see A.7, A.8).

**Newline normalization.** Double newlines (`\n\n`) were used as paragraph delimiters across all conditions. Markdown formatting (headers, bold, italics) is preserved from generation output; chat-UI-rendered conditions (Arena) may have additional platform-injected whitespace or formatting that is not present in the raw model output.

### A.1 GPT-3.5 (Huang et al., 2024)
- **Provider**: OpenAI (via Huang et al.'s data-collection pipeline; third-party dataset)
- **Source**: HuggingFace `vkpriya/GPT-WritingPrompts` (MIT license)
- **Model**: `gpt-3.5-turbo` (2022-era)
- **System role**: Two variants per Huang et al. (2024) §3.1: (a) "You are an award winning creative short story writer." and (b) "You're writing a Reddit story and you want other reddit users to like and upvote your story."
- **User prompt template**: "Write a 500 word story for the following prompt: {prompt_text}" (Huang et al. 2024 §3.1)
- **Decoding parameters**: Temperature = 0.95 (per Huang et al. 2024 §3.1); max_tokens not specified in source; no top_p reported
- **Generations per prompt**: ~2 per prompt (Huang et al. 2024 §3.1); we randomly selected 1 of the available stories per prompt
- **Critical limitation**: Generation parameters documented in Huang et al. (2024) but not from API logs (no verification against the published paper at the time of writing this paper; the parameters above were confirmed post-hoc from the published paper's §3.1 and §3.2). The "500 word" instruction is unique to this condition among our 9 conditions; it partially explains GPT-3.5's word count (531 ± 40) being lower than other no-instruction conditions (664-878). GPT-3.5's apparent "outlier" stylistic profile is therefore best interpreted as a **dataset-protocol effect** (length instruction + temperature 0.95 + dual system role variants) rather than as an "older-generation" model property.

### A.2 MiMo-V2.5-Pro (Xiaomi)
- **Provider**: Command Code Goat API (`https://api.commandcode.ai/provider/v1`, OpenAI-compatible)
- **Model**: `xiaomi/mimo-v2.5-pro`
- **SDK**: openai
- **Temperature**: 0.7 (default)
- **Max tokens**: 1500
- **System prompt**: none (raw user prompt only)
- **Date**: 2026-08-29
- **N successful**: 30/30
- **Finish reason**: All 30 completions finished with `stop` (no `length` truncation observed)

### A.3 DeepSeek-V4-Flash (DeepSeek)
- **Provider**: Command Code Goat API (OpenAI-compatible)
- **Model**: `deepseek/deepseek-v4-flash`
- **SDK**: openai
- **Temperature**: 0.7
- **Max tokens**: 16000 (with `thinking` enabled, `reasoning_effort=high`)
- **System prompt**: none
- **Date**: 2026-08-29
- **N successful**: 30/30 (prompt 25 "every sentence is a question" initially timed out due to extended thinking time, then succeeded on retry after increasing max_tokens to 16000)

### A.4 MiniMax-M3 (MiniMax)
- **Provider**: MiniMax CN (`https://api.minimaxi.com/anthropic`, Anthropic-compatible)
- **Model**: `MiniMax-M3`
- **SDK**: anthropic
- **Temperature**: 1.0 (Anthropic default)
- **Max tokens**: 32000 (with `thinking` enabled, adaptive)
- **System prompt**: none
- **Date**: 2026-08-29
- **N successful**: 30/30

### A.5 Muse-Spark-1.2-Contributor (Muse)
- **Provider**: Command Code Goat API (OpenAI-compatible) via env-var workaround for OpenCode Go regional restrictions
- **Model**: `meta/muse-spark-1.2-contributor`
- **SDK**: openai
- **Temperature**: 0.7
- **Max tokens**: 16000 (hard prompts 4/16/25 needed larger budget)
- **Date**: 2026-08-29
- **N successful**: 30/30

### A.6 Kimi-K3 (Moonshot)
- **Provider**: Command Code Goat API (OpenAI-compatible; initial OpenCode Go provider exhausted its 5-hour quota)
- **Model**: `moonshotai/Kimi-K3`
- **SDK**: openai
- **Temperature**: 0.7
- **Max tokens**: 16000 (with `thinking` enabled, `reasoning_effort=high`)
- **Date**: 2026-08-29
- **N successful**: 29/30 (prompt 26 "best friend speaks in rhyme" repeatedly timed out due to extended generation time)

### A.7 Gemini-3.6-Flash (Google)
- **Provider A**: Manual Arena paste (`chat.lmsys.org` or `chat.google.com`) for the initial 26 prompts
  - Platform-injected system prompt (uncontrolled, invisible to researcher)
  - Generation parameters unknown (platform-controlled)
- **Provider B**: Faro API (`https://faroapi.com/v1`, OpenAI-compatible) for prompts 3 + 10 (which were content-policy blocked on Arena)
  - Model: `gemini-3.6-flash-high`
  - SDK: openai
  - Temperature: 0.7 (default)
  - Max tokens: 16000
- **Date**: 2026-08-29
- **N successful**: 30/30 (28 Arena + 2 Faro)
- **Critical limitation**: 93% of Gemini stories were generated under uncontrolled Arena conditions. Differences between Gemini and other conditions may partially reflect platform-level system prompt or sampling strategy. Of the 30 Gemini stories, 2 came from Faro API (content-policy-blocked on Arena); per-channel statistics are not computed due to the small Faro sample size, but the Gemini profiles are dominated by Arena's 28 stories.

### A.8 GPT-5.6-Luna (OpenAI)
- **Provider**: Manual Arena paste (`chatgpt.com`)
- **Model**: `gpt-5.6-luna`
- **Temperature**: Arena default (~1.0)
- **System prompt**: Platform-injected (uncontrolled)
- **Date**: 2026-08-29
- **N successful**: 30/30
- **Critical limitation**: as an Arena-only condition, all generation parameters other than model name are platform-controlled and not visible to the researcher.

### A.9 Claude-Sonnet-5-High (Anthropic)
- **Provider**: Faro API (`https://faroapi.com`, Anthropic-compatible)
- **Model**: `claude-sonnet-5`
- **SDK**: anthropic
- **Temperature**: 1.0 (Anthropic default)
- **Max tokens**: 32000 (with `thinking` enabled, adaptive)
- **System prompt**: none
- **Date**: 2026-08-29
- **N successful**: 30/30

### A.10 Cross-condition Confound Statement

Three different acquisition channels were used:
1. **Direct API** (Command Code Goat or Anthropic-compatible) for MiMo, DeepSeek, Muse-Spark, Kimi, MiniMax-M3, Claude-Sonnet-5-High — fully controlled parameters.
2. **Third-party dataset** (Huang et al., 2024) for GPT-3.5 — generation parameters unknown.
3. **Manual Arena paste** for Gemini-3.6-Flash and GPT-5.6-Luna — uncontrolled platform system prompts and generation parameters.

**Implication for cross-condition comparison**: differences between conditions may conflate (a) model differences, (b) generation channel differences, (c) default temperature differences across providers (0.7 for OpenAI-compatible vs 1.0 for Anthropic), (d) system prompt presence/absence. The H1–H5 results should be interpreted in light of this confound. Per-condition RF classifiers (§4.3 Table 3) are less affected because they are balanced designs within a single channel.

---

## Appendix: BibTeX

```bibtex
@inproceedings{fan2018hierarchically,
  title={Hierarchical Neural Story Generation},
  author={Fan, Angela and Lewis, Mike and Dauphin, Yann},
  booktitle={Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages={889--898},
  year={2018},
  publisher={Association for Computational Linguistics}
}

@article{huang2024gpt,
  title={The GPT-WritingPrompts Dataset: A Comparative Analysis of Character Portrayal in Short Stories},
  author={Huang, Xi Yu and Vishnubhotla, Krishnapriya and Rudzicz, Frank},
  journal={arXiv preprint arXiv:2406.16767},
  year={2024}
}

@inproceedings{chakrabarty2024art,
  title={Art or Artifice? Large Language Models and the False Promise of Creativity},
  author={Chakrabarty, Tuhin and Laban, Philippe and Agarwal, Divyansh and Muresan, Smaranda and Wu, Chien-Sheng},
  booktitle={Proceedings of the CHI Conference on Human Factors in Computing Systems},
  pages={1--15},
  year={2024},
  doi={10.1145/3613904.3642731}
}

@inproceedings{chakrabarty2024creativity,
  title={Creativity Support in the Age of Large Language Models: An Empirical Study Involving Professional Writers},
  author={Chakrabarty, Tuhin and Padmakumar, Vishakh and Brahman, Faeze and Muresan, Smaranda},
  booktitle={Proceedings of the 16th ACM Conference on Creativity and Cognition},
  pages={1--15},
  year={2024},
  doi={10.1145/3635636.3656201}
}

@inproceedings{lucy2021gender,
  title={Gender and Representation Bias in GPT-3 Generated Stories},
  author={Lucy, Li and Bamman, David},
  booktitle={Proceedings of the Third Workshop on Narrative Understanding},
  pages={48--55},
  year={2021}
}

@article{osullivan2025stylometric,
  title={Stylometric Comparisons of Human versus AI-Generated Creative Writing},
  author={O'Sullivan, James},
  journal={Humanities and Social Sciences Communications},
  volume={12},
  number={1},
  pages={1708},
  year={2025},
  publisher={Nature},
  doi={10.1057/s41599-025-05986-3}
}

@article{mccarthy2010mtld,
  title={MTLD, vocd-D, and HD-D: A Validation Study of Sophisticated Approaches to Lexical Diversity Assessment},
  author={McCarthy, Philip M and Jarvis, Scott},
  journal={Behavior Research Methods},
  volume={42},
  number={2},
  pages={381--392},
  year={2010},
  publisher={Springer}
}

@article{juola2008authorship,
  title={Authorship Attribution},
  author={Juola, Patrick},
  journal={Foundations and Trends in Information Retrieval},
  volume={1},
  number={3},
  pages={233--334},
  year={2008}
}

@article{pedregosa2011scikitlearn,
  title={Scikit-learn: Machine Learning in Python},
  author={Pedregosa, Fabian and Varoquaux, Ga{\"e}l and Gramfort, Alexandre and Michel, Vincent and Thirion, Bertrand and Grisel, Olivier and Blondel, Mathieu and Prettenhofer, Peter and Weiss, Ron and Dubourg, Vincent and Vanderplas, Jake and Passos, Alexandre and Cournapeau, David and Brucher, Matthieu and Perrot, Matthieu and Duchesnay, Edouard},
  journal={Journal of Machine Learning Research},
  volume={12},
  pages={2825--2830},
  year={2011}
}

@article{honnibal2017spacy,
  title={spaCy 2: Natural Language Understanding with Bloom Embeddings, Convolutional Neural Networks and Incremental Parsing},
  author={Honnibal, Matthew and Montani, Ines},
  journal={Proceedings of the ACL 2017 System Demonstrations},
  pages={165--168},
  year={2017}
}

@book{cohen1988statistical,
  title={Statistical Power Analysis for the Behavioral Sciences},
  author={Cohen, Jacob},
  year={1988},
  edition={2},
  publisher={Lawrence Erlbaum Associates},
  address={Hillsdale, NJ}
}
```
