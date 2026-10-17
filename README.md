# Length as a Primary Confound in AI-vs-Human Stylistic Comparisons

A **conservative preliminary report** documenting a length confound in cross-condition stylometric comparisons of AI- and human-generated creative text.

## What this paper says

- A **supplementary set of five exploratory indicators** (lexical density, word-length SD, long-word ratio, sentence-length CV, sentences per paragraph) is reported in §4.5, bringing the analysed indicators to 13 (14 with MATTR); the locked eight-metric set is unchanged.

- AI-generated creative text is **1.6× longer** than human-written text (mean 719 vs 439 words across 30 prompts).
- After **length-residualization** (TTR and conjunction frequency regressed on word count), **0 of 9 conditions survive** per-family Holm-Bonferroni correction, suggesting these apparent differences are length-attributable rather than independent stylistic markers.
- The 8-metric Random Forest classifier achieves 91.6% raw accuracy but only 68.7% balanced accuracy (MCC=0.449, AUC=0.867, human recall 12/30=40%), **essentially tied with a length-only baseline** at 69.4% balanced accuracy.

## What this paper does NOT claim

- This paper does **not** claim a "clean refutation" of any pre-existing hypothesis.
- Statistical power for medium effects (r=0.3) is ~30%; "0/9 survive" does not formally establish absence of effect.
- Acquisition-channel heterogeneity (4 distinct sources: direct API, third-party dataset, Manual Arena paste, Faro API) precludes model-level claims.
- Specific items the paper cannot confirm are listed in §6 of `proposal_v12.pdf`.

## Contents

```
├── proposal_v12.md          ← markdown source (75 KB)
├── proposal_v12.pdf          ← rendered PDF (23 pages)
├── README.md                 ← this file
├── requirements.txt          ← Python dependencies
├── analysis/                 ← 8 metrics + Wilcoxon + Holm + StratifiedGroupKFold
├── data/processed/           ← 299 observations (sample_v1.json)
└── docs/                     ← methodology, metric spec, literature review
```

## Reproducing

```bash
pip install -r requirements.txt
python analysis/run_analysis.py   # full Wilcoxon + Holm pipeline
python analysis/metrics.py        # 8 metrics on raw data
```

## Dataset

- **Human stories**: 30 Reddit r/WritingPrompts top-voted stories (Fan et al. 2018, ACL)
- **AI stories**: 9 model-pipeline conditions × 30 prompts (some conditions with 28–29 due to one model refusal)
- **License**: MIT (Fan 2018) + MIT (KristinHuang/gpt-writing-prompts) — see `analysis/citation_verification.md`

## Citation

This paper has not been published in a peer-reviewed venue. If you reference it, cite as:

```
Ray Summers (2026). Length as a Primary Confound in AI-vs-Human Stylistic
Comparisons: A Conservative Preliminary Report.
GitHub: https://github.com/RayySummers/length-confound-ai-vs-human-stylistic
```

## Status

**Public archive, no further updates planned.** This was a summer 2026 research pilot. The author expects no follow-up work.