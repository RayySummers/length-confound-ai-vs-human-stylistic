# Metric Specification: AI vs. Human Text Structural Analysis

> **Status:** Locked by user (2026-08-05). Do not add or remove metrics without discussion.

## Research Questions (Refined)

**RQ1 (Descriptive):** What are the distributions of structural features (word length, sentence length, paragraph length) in AI-generated vs. human-written text?

**RQ2 (Comparative):** Do AI-generated texts exhibit significantly lower sentence length variance and more uniform paragraph structure than human-written texts?

**RQ3 (Discriminant):** Which combination of structural metrics best discriminates between AI-generated and human-written text, and what is the classification accuracy?

---

## Locked Metric Set (8 Metrics)

| # | Metric | Formula | Implementation | Expected Direction |
|---|--------|---------|----------------|-------------------|
| 1 | **Word length** | mean(chars per word) per text | `len(word)` averaged over spaCy tokens | AI ≈ Human (neutral) |
| 2 | **Sentence length** | mean(words per sentence) per text | `len(tokens)` per spaCy sentence, averaged | AI slightly higher (more uniform) |
| 3 | **Sentence length variance** | var(words per sentence) within text | `numpy.var` over sentence lengths | **AI << Human** (key hypothesis) |
| 4 | **TTR** | unique_tokens / total_tokens | Type-Token Ratio per text | **AI < Human** (more repetitive) |
| 5 | **MTLD** | MTLD score | `pyphen` or manual implementation | **AI < Human** |
| 6 | **Conjunction frequency** | count(conjunctions) / total_words | spaCy POS tag `CONJ` + `CCONJ` | **AI > Human** (more connectors) |
| 7 | **Paragraph length** | mean(words per paragraph) per text | Split on `\n\n`, count words per block | AI ≈ Human or slightly higher |
| 8 | **Paragraph length variance** | var(paragraph word counts) | `numpy.var` over paragraph lengths | **AI << Human** |

---

## Hypotheses

| # | Hypothesis | Test | Expected p-value |
|---|-----------|------|-----------------|
| H1 | AI texts have lower sentence length variance than human texts | Mann-Whitney U (one-tailed) | p < 0.05 |
| H2 | AI texts have lower paragraph length variance than human texts | Mann-Whitney U (one-tailed) | p < 0.05 |
| H3 | AI texts have lower TTR than human texts | Mann-Whitney U (one-tailed) | p < 0.05 |
| H4 | AI texts use more conjunctions than human texts | Mann-Whitney U (one-tailed) | p < 0.05 |
| H5 | A classifier using metrics 1-8 can distinguish AI from human text with accuracy > 70% | Random Forest 5-fold CV | accuracy > 0.70 |

---

## AI Models (User-Confirmed)

| Model | Provider | Notes |
|-------|----------|-------|
| MiMo-V2.5-Pro | Xiaomi | |
| DeepSeek-V4-Flash | DeepSeek | |
| GPT-5.6 Sol | OpenAI | |
| GPT-5.6 Luna | OpenAI | |
| MiniMax M3 | MiniMax | |

**Text language:** English only

---

## Statistical Approach

1. **Descriptive:** Box plots + summary statistics for each metric, grouped by AI/Human
2. **Inferential:** Mann-Whitney U tests (non-parametric, no normality assumption needed for small samples)
3. **Discriminant:** Random Forest classifier with feature importance ranking
4. **Visualization:** Violin plots, PCA scatter plot, confusion matrix, feature importance bar chart
