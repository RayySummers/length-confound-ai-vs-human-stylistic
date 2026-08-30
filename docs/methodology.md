# Statistical Methodology: Quantifying AI vs. Human Text Structural Differences

## 1. Introduction

This document defines the statistical methodology for Ray's summer research project quantifying structural differences between AI-generated and human-written text. The study employs 8 stylometric metrics across 5 hypotheses, using a paired design where each writing prompt yields one human-authored and one AI-generated story.

**8 Metrics** (locked in `docs/metric-specification.md`):
1. Word length (characters per word)
2. Sentence length (words per sentence)
3. Sentence length variance
4. Type-Token Ratio (TTR)
5. Measure of Textual Lexical Diversity (MTLD)
6. Conjunction frequency
7. Paragraph length (sentences per paragraph)
8. Paragraph length variance

**5 Hypotheses** (locked in `docs/metric-specification.md`):
- **H1**: AI text shows lower sentence length variance than human text
- **H2**: AI text shows lower paragraph length variance than human text
- **H3**: AI text shows lower TTR (lexical diversity) than human text
- **H4**: AI text shows higher conjunction frequency than human text
- **H5**: A Random Forest classifier achieves >70% accuracy distinguishing AI from human text using the 8 metrics

**Conditions**: 7 total — 1 human baseline + 6 AI models (GPT-3.5, MiMo-V2.5-Pro, DeepSeek-V4-Flash, GPT-5.6 Sol, GPT-5.6 Luna, MiniMax M3).

**Target Sample Size**: N=90 paired observations (3 batches × 30 prompts).

## 2. Statistical Framework

### Paired Design Rationale

The study uses a **paired design**: each writing prompt generates one human story and one AI story, creating matched observations. This design controls for prompt-level confounds (topic, genre, complexity, narrative requirements) by comparing within-prompt differences rather than between-group means.

**Advantages of pairing**:
- Eliminates variability due to prompt difficulty and genre
- Increases statistical power relative to independent-samples design
- Each prompt serves as its own control

**Handling missing data**: If a pair is incomplete (e.g., AI generation failure), exclude that pair entirely. Do not treat incomplete observations as independent samples.

### Non-Parametric Approach

We adopt **non-parametric tests** for H1-H4 because:
1. Stylometric metrics may not follow normal distributions (e.g., word lengths are right-skewed, TTR is bounded [0,1])
2. Sample sizes (N=30 per batch, N=90 total) are moderate; normality assumptions may not hold
3. Non-parametric tests are robust to outliers and distributional violations

The Wilcoxon signed-rank test is the non-parametric equivalent of the paired t-test and is appropriate for paired ordinal or continuous data.

## 3. Hypothesis Testing

### H1-H4: Wilcoxon Signed-Rank Test

**Test**: Wilcoxon signed-rank test (one-sample test on paired differences)

**Procedure**:
1. For each prompt *i*, compute the difference *d_i* = AI_metric_i − Human_metric_i
2. Rank the absolute differences |d_i|
3. Compute the signed-rank statistic *T* = Σ sgn(d_i) × R_i
4. Obtain p-value from the null distribution of *T*

**Directionality**:
| Hypothesis | Metric | Direction | Test Type |
|------------|--------|-----------|-----------|
| H1 | Sentence length variance | AI < Human | One-tailed (left) |
| H2 | Paragraph length variance | AI < Human | One-tailed (left) |
| H3 | TTR | AI < Human | One-tailed (left) |
| H4 | Conjunction frequency | AI > Human | One-tailed (right) |

**Assumption**: The distribution of paired differences is symmetric around the median under the null hypothesis. This is weaker than the normality assumption required for paired t-tests.

### H5: Random Forest Classifier

**Algorithm**: Random Forest (scikit-learn `RandomForestClassifier`)

**Configuration**:
- `n_estimators=100` (default, sufficient for 8 features)
- `random_state=42` (reproducibility)
- `class_weight='balanced'` (if class imbalance exists)

**Validation**: 5-fold stratified cross-validation
- Preserves class proportion (human vs. AI) in each fold
- Each fold serves as test set once; remaining 4 folds for training

**Metrics**:
- Primary: Accuracy (proportion correct classifications)
- Secondary: 95% confidence interval for accuracy

**Hypothesis test**: H5 is supported if the lower bound of the 95% CI exceeds 70%.

## 4. Multiple Comparison Correction

With 5 hypotheses tested on the same dataset, we must correct for inflated family-wise error rate (FWER). At α = 0.05 per test, the probability of at least one false positive across 5 independent tests is 1 − (1 − 0.05)^5 ≈ 23%.

### Recommended: Bonferroni Correction

**Adjusted threshold**: α_adj = 0.05 / 5 = **0.01**

**Rationale**:
- Conservative but appropriate for confirmatory analysis
- Controls FWER at 0.05 regardless of dependency structure between tests
- With only 5 hypotheses, the power cost is manageable

**Application**: Each hypothesis is tested at α = 0.01. A result is "significant" only if p < 0.01.

### Alternative: FDR (Benjamini-Hochberg)

If the study goal is **discovery** (identifying promising effects for future research) rather than **confirmation**, the Benjamini-Hochberg FDR procedure is acceptable:

1. Rank the 5 p-values: p_(1) ≤ p_(2) ≤ ... ≤ p_(5)
2. For each rank *i*, compute threshold: (i/5) × 0.05
3. Reject all hypotheses with p_(i) ≤ threshold

**Decision rule**: Use Bonferroni for the primary analysis; report FDR-adjusted p-values as supplementary.

## 5. Effect Size Measures

P-values alone do not convey the magnitude of effects. We report effect sizes for all hypotheses.

### H1-H4: Rank-Biserial Correlation

For the Wilcoxon signed-rank test, effect size *r* is computed as:

    r = Z / √N

where *Z* is the standardized test statistic and *N* is the number of paired observations.

**Interpretation** (Cohen's conventions):
- Small: |r| ≈ 0.1
- Medium: |r| ≈ 0.3
- Large: |r| ≈ 0.5

### H5: Accuracy and Cohen's d

For the classifier:
- **Accuracy**: Proportion of correct classifications across all CV folds
- **Cohen's d**: If comparing accuracy to chance (50%), compute d = (accuracy − 0.5) / SD_accuracy

**Reporting**: Mean accuracy ± 95% CI. H5 is supported if lower CI bound > 70%.

## 6. Sample Size Justification

### Power Analysis for Wilcoxon Signed-Rank Test

Power analysis uses Noether's (1987) approximation based on **effect probability** *p_s* = P(X_i + X_j > 0) under the alternative hypothesis. Under the null, *p_s* = 0.5.

**From N=30 Sanity Check Results**:
| Hypothesis | Pair-wise Support | Estimated p_s | Effect Size |
|------------|-------------------|---------------|-------------|
| H2 | 83% | 0.83 | Large (r ≈ 0.6-0.7) |
| H4 | 60% | 0.60 | Medium (r ≈ 0.3-0.4) |
| H3 | 47% | 0.47 | Small (r ≈ 0.1-0.2) |
| H1 | 33% | 0.33 | Negligible (r ≈ 0.0-0.1) |

**Required N for α = 0.01, power = 0.80**:
- Large effect (p_s = 0.80): N ≈ 15-20 pairs
- Medium effect (p_s = 0.65): N ≈ 40-50 pairs
- Small effect (p_s = 0.55): N ≈ 100+ pairs

**Conclusion**: N=90 provides adequate power for H2 (large effect) and H4 (medium effect). H3 (small effect) may be underpowered; H1 (negligible effect) will likely remain non-significant regardless of sample size.

### Power for H5 (Classifier)

For a binary classifier with 8 features, N=90 provides approximately 11 samples per feature, which is below the common rule of thumb (20 samples per feature). However, Random Forests handle high-dimensional data well with regularization via bagging. The 5-fold CV provides unbiased accuracy estimates.

## 7. Limitations

1. **N=30 Sanity Check**: Effect sizes estimated from N=30 may not generalize to N=90. The sanity check is exploratory; the full study is confirmatory.

2. **Prompt-Genre Confound**: All prompts originate from the WritingPrompts dataset (fiction/creative writing). Results may not generalize to non-fiction, academic, or conversational text.

3. **Single-Language**: The study analyzes English text only. Cross-linguistic generalization is unknown.

4. **Multiple AI Conditions**: Comparing human text to 6 different AI models introduces additional multiple comparison issues beyond the 5 hypotheses. Consider whether to apply separate corrections per AI model or treat all AI conditions as a single category.

5. **Metric Correlations**: The 8 metrics may be correlated (e.g., sentence length and sentence length variance). Multicollinearity does not affect H1-H4 (tested individually) but may impact H5 classifier interpretability. Consider feature importance analysis post-hoc.

6. **Text Length Normalization**: TTR is sensitive to text length (longer texts yield lower TTR). Ensure all texts are comparable in length, or use MTLD (length-robust) as the primary lexical diversity metric.

7. **Effect Size Reporting**: Beyond p-values, all hypotheses report effect sizes and confidence intervals. Non-significant results with meaningful effect sizes warrant further investigation.

8. **Temporal Validity**: AI models evolve rapidly. Results reflect specific model versions tested in 2026; future versions may exhibit different stylistic signatures.

## 8. Implementation Notes

### Wilcoxon Signed-Rank Test (Python)

```python
from scipy.stats import wilcoxon

# Compute paired differences
diffs = ai_metrics - human_metrics  # shape: (N,)

# One-tailed test (AI < Human for H1-H3)
stat, p_two = wilcoxon(diffs, alternative='two-sided')
p_one = p_two / 2 if stat < len(diffs) * (len(diffs) + 1) / 4 else 1 - p_two / 2

# For H4 (AI > Human), flip sign
stat_h4, p_two_h4 = wilcoxon(-diffs, alternative='two-sided')
```

### Bonferroni Correction (Python)

```python
from statsmodels.stats.multitest import multipletests

p_values = [p_h1, p_h2, p_h3, p_h4, p_h5]
reject, p_corrected, _, _ = multipletests(p_values, alpha=0.05, method='bonferroni')
# reject[i] is True if hypothesis i is significant at corrected threshold
```

### Random Forest Classifier (Python)

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
import numpy as np
from scipy import stats

# X: (N, 8) feature matrix; y: (N,) binary labels (0=human, 1=AI)
clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(clf, X, y, cv=cv, scoring='accuracy')

# Report
mean_acc = scores.mean()
ci = stats.t.interval(0.95, len(scores)-1, loc=mean_acc, scale=scores.std()/np.sqrt(len(scores)))
print(f"Accuracy: {mean_acc:.3f} (95% CI: [{ci[0]:.3f}, {ci[1]:.3f}])")
```

### Effect Size for Wilcoxon (Python)

```python
from scipy.stats import norm

def wilcoxon_effect_size(stat, n):
    """Compute rank-biserial correlation r from Wilcoxon statistic."""
    mu = n * (n + 1) / 4
    sigma = np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (stat - mu) / sigma
    r = z / np.sqrt(n)
    return r
```

## 9. Bibliography

```bibtex
@inproceedings{fan2018hierarchically,
  title={Hierarchical Neural Story Generation},
  author={Fan, Angela and Lewis, Mike and Dauphin, Yann},
  booktitle={Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages={889--898},
  year={2018},
  publisher={Association for Computational Linguistics}
}

@inproceedings{huang2024gpt,
  title={GPT-WritingPrompts: A Dataset for Evaluating Creative Writing of Large Language Models},
  author={Huang, Jie and others},
  booktitle={Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP Workshop)},
  year={2024}
}

@article{mccarthy2010mtld,
  title={MTLD, vocd-D, and HD-D: A validation study of sophisticated approaches to lexical diversity assessment},
  author={McCarthy, Philip M and Jarvis, Scott},
  journal={Behavior Research Methods},
  volume={42},
  number={2},
  pages={381--392},
  year={2010},
  publisher={Springer}
}

@article{osullivan2025stylometric,
  title={Stylometric comparisons of human versus AI-generated creative writing},
  author={O'Sullivan, James},
  journal={Humanities and Social Sciences Communications},
  volume={12},
  number={1708},
  year={2025},
  publisher={Nature}
}

@article{noether1987sample,
  title={Sample size determination for some common nonparametric tests},
  author={Noether, Gottfried E},
  journal={Journal of the American Statistical Association},
  volume={82},
  number={399},
  pages={645--647},
  year={1987}
}

@article{benjamini1995controlling,
  title={Controlling the false discovery rate: a practical and powerful approach to multiple testing},
  author={Benjamini, Yoav and Hochberg, Yosef},
  journal={Journal of the Royal Statistical Society: Series B (Methodological)},
  volume={57},
  number={1},
  pages={289--300},
  year={1995}
}

@book{wilcoxon1945individual,
  title={Individual comparisons by ranking methods},
  author={Wilcoxon, Frank},
  journal={Biometrics Bulletin},
  volume={1},
  number={6},
  pages={80--83},
  year={1945}
}
```
