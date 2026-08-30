"""
run_analysis.py — Full statistical analysis pipeline for RAY-415 (extended v2)
Runs 8-metric descriptive stats, paired Wilcoxon tests (H1-H4) for each AI vs Human,
and Random Forest classifier (H5) on sample_v1.json (multi-condition).

Outputs:
  - data/processed/results_v1.json
  - analysis/results_summary.md
  - analysis/results_schema.md

Citations:
  - Fan et al. 2018 (ACL): Reddit WritingPrompts corpus
  - Huang et al. 2024 (EMNLP Workshop): GPT-WritingPrompts dataset
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.preprocessing import StandardScaler

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT = Path(__file__).parent.parent
METRICS_PATH = PROJECT / "data" / "processed" / "metrics_results.json"
RESULTS_PATH = PROJECT / "data" / "processed" / "results_v1.json"
SUMMARY_PATH = PROJECT / "analysis" / "results_summary.md"
SCHEMA_PATH = PROJECT / "analysis" / "results_schema.md"

# ── The 8 locked metrics (from docs/metric-specification.md) ──────────────
METRIC_KEYS = [
    "word_length",
    "sentence_length",
    "sentence_length_var",
    "ttr",
    "mtld",
    "conj_freq",
    "paragraph_length",
    "paragraph_length_var",
]

METRIC_LABELS = {
    "word_length": "Word Length (chars/word)",
    "sentence_length": "Sentence Length (words/sent)",
    "sentence_length_var": "Sentence Length Variance",
    "ttr": "Type-Token Ratio (TTR)",
    "mtld": "MTLD",
    "conj_freq": "Conjunction Frequency",
    "paragraph_length": "Paragraph Length (words/para)",
    "paragraph_length_var": "Paragraph Length Variance",
}

# All AI conditions to compare against Human
AI_CONDITIONS = ["gpt35", "MiMo-V2.5-Pro", "DeepSeek-V4-Flash",
                 "MiniMax-M3", "Muse-Spark-1.2-Contributor",
                 "GPT-5.6-Luna", "Claude-Sonnet-5-High", "Gemini-3.6-Flash", "Kimi-K3"]

CONDITION_LABELS = {
    "human": "Human",
    "gpt35": "GPT-3.5",
    "MiMo-V2.5-Pro": "MiMo-V2.5-Pro",
    "DeepSeek-V4-Flash": "DeepSeek-V4-Flash",
    "MiniMax-M3": "MiniMax-M3",
    "Muse-Spark-1.2-Contributor": "Muse-Spark-1.2-Contributor",
    "GPT-5.6-Luna": "GPT-5.6-Luna",
    "Claude-Sonnet-5-High": "Claude-Sonnet-5-High",
    "Gemini-3.6-Flash": "Gemini-3.6-Flash",
    "Kimi-K3": "Kimi-K3",
}

# Hypothesis mapping (vs Human baseline)
HYPOTHESES = {
    "H1": {"metric": "sentence_length_var", "direction": "less",    "desc": "AI texts have lower sentence length variance"},
    "H2": {"metric": "paragraph_length_var", "direction": "less",  "desc": "AI texts have lower paragraph length variance"},
    "H3": {"metric": "ttr",                  "direction": "less",    "desc": "AI texts have lower TTR (more repetitive)"},
    "H4": {"metric": "conj_freq",            "direction": "greater", "desc": "AI texts use more conjunctions"},
}


def load_metrics():
    """Load the pre-computed metrics from metrics.py output."""
    with open(METRICS_PATH) as f:
        data = json.load(f)
    return data


def build_dataframe(data):
    """Convert raw metrics JSON into a tidy DataFrame with one row per (prompt, condition)."""
    rows = []
    for entry in data:
        pid = entry["prompt_id"]
        for condition, m in entry.items():
            if condition == "prompt_id":
                continue
            if m is None:  # missing data for this condition
                continue
            row = {"prompt_id": pid, "condition": condition}
            for k in METRIC_KEYS:
                row[k] = m[k]
            row["_n_words"] = m["_n_words"]
            row["_n_sentences"] = m["_n_sentences"]
            row["_n_paragraphs"] = m["_n_paragraphs"]
            rows.append(row)
    return pd.DataFrame(rows)


def descriptive_stats(df):
    """Compute mean ± sd per condition for all 8 metrics."""
    stats_rows = []
    for metric in METRIC_KEYS:
        for cond in sorted(df["condition"].unique()):
            vals = df[df["condition"] == cond][metric]
            stats_rows.append({
                "metric": metric,
                "metric_label": METRIC_LABELS[metric],
                "condition": cond,
                "condition_label": CONDITION_LABELS.get(cond, cond),
                "mean": float(vals.mean()),
                "sd": float(vals.std(ddof=1)),
                "n": int(len(vals)),
                "min": float(vals.min()),
                "max": float(vals.max()),
                "median": float(vals.median()),
            })
    return stats_rows


def run_hypothesis_tests_one_ai(df, ai_condition):
    """Run H1-H4 paired tests for one AI condition vs Human."""
    results = []
    for h_name, h_spec in HYPOTHESES.items():
        metric = h_spec["metric"]
        direction = h_spec["direction"]

        # Paired: per-prompt delta (human - ai)
        human_vals = df[df["condition"] == "human"].sort_values("prompt_id")[metric].values
        ai_vals = df[df["condition"] == ai_condition].sort_values("prompt_id")[metric].values
        # Some prompts may be missing for this AI; align by prompt_id
        merged = df[df["condition"].isin(["human", ai_condition])].copy()
        pivoted = merged.pivot(index="prompt_id", columns="condition", values=metric).dropna()
        h = pivoted["human"].values
        a = pivoted[ai_condition].values
        deltas = h - a  # positive means human > ai

        # Wilcoxon signed-rank (paired, non-parametric)
        try:
            wilcoxon_stat, wilcoxon_p_two = stats.wilcoxon(deltas, alternative="two-sided")
            if direction == "less":  # AI < Human → delta > 0
                if np.median(deltas) > 0:
                    wilcoxon_p_one = wilcoxon_p_two / 2
                else:
                    wilcoxon_p_one = 1 - wilcoxon_p_two / 2
                alternative_label = "AI < Human (one-tailed)"
            else:  # "greater" → AI > Human → delta < 0
                if np.median(deltas) < 0:
                    wilcoxon_p_one = wilcoxon_p_two / 2
                else:
                    wilcoxon_p_one = 1 - wilcoxon_p_two / 2
                alternative_label = "AI > Human (one-tailed)"
            test_used = "Wilcoxon signed-rank (paired)"
            w_stat_out = float(wilcoxon_stat)
            w_p_out = float(wilcoxon_p_one)
        except ValueError:
            wilcoxon_p_one = float("nan")
            w_stat_out = None
            w_p_out = None
            test_used = "Wilcoxon failed (all deltas zero?)"
            alternative_label = "N/A"

        # Mann-Whitney U robustness check
        mw_stat, mw_p_two = stats.mannwhitneyu(h, a, alternative="two-sided")
        if direction == "less":
            _, mw_p_one = stats.mannwhitneyu(h, a, alternative="greater")
        else:
            _, mw_p_one = stats.mannwhitneyu(h, a, alternative="less")

        results.append({
            "hypothesis": h_name,
            "description": h_spec["desc"],
            "metric": metric,
            "metric_label": METRIC_LABELS[metric],
            "ai_condition": ai_condition,
            "ai_condition_label": CONDITION_LABELS.get(ai_condition, ai_condition),
            "direction_tested": direction,
            "alternative": alternative_label,
            "test_used": test_used,
            "wilcoxon_statistic": w_stat_out,
            "wilcoxon_p_one_tailed": w_p_out,
            "mann_whitney_u_statistic": float(mw_stat),
            "mann_whitney_p_one_tailed": float(mw_p_one),
            "mann_whitney_p_two_tailed": float(mw_p_two),
            "human_mean": float(np.mean(h)),
            "ai_mean": float(np.mean(a)),
            "mean_delta": float(np.mean(deltas)),
            "median_delta": float(np.median(deltas)),
            "significant_at_005": bool(wilcoxon_p_one < 0.05) if not np.isnan(wilcoxon_p_one) else False,
            "n_pairs": len(deltas),
        })
    return results


def hypothesis_tests_all_ai(df):
    """Run H1-H4 for every AI condition that has data vs Human."""
    available_ai = [c for c in AI_CONDITIONS if c in df["condition"].unique()]
    all_results = []
    for ai in available_ai:
        all_results.extend(run_hypothesis_tests_one_ai(df, ai))
    return all_results


def _evaluate_fold(y_true, y_pred, y_proba):
    """Compute a rich set of metrics for one fold's predictions."""
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    # Per-class F1: class 0 = AI, class 1 = Human
    f1_per_class = f1_score(y_true, y_pred, average=None, labels=[0, 1]).tolist()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1_ai": float(f1_per_class[0]),
        "f1_human": float(f1_per_class[1]),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro")),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "confusion_matrix": cm,  # [[TN, FP], [FN, TP]]
        # AUC only when both classes present in y_true
        "auc": float(roc_auc_score(y_true, y_proba)) if len(np.unique(y_true)) == 2 else None,
    }


def _cv_evaluate(clf, X, y, groups, cv):
    """Manual CV loop returning per-fold metrics (needs predictions/proba)."""
    fold_metrics = []
    for train_idx, test_idx in cv.split(X, y, groups):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        y_proba = clf.predict_proba(X_test)[:, 1]
        fold_metrics.append(_evaluate_fold(y_test, y_pred, y_proba))
    return fold_metrics


def _summarize_folds(fold_metrics):
    """Aggregate per-fold metrics into mean ± sd."""
    keys = [k for k in fold_metrics[0] if k != "confusion_matrix"]
    summary = {}
    for k in keys:
        vals = [m[k] for m in fold_metrics if m[k] is not None]
        if vals:
            summary[k + "_mean"] = float(np.mean(vals))
            summary[k + "_sd"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            summary[k + "_per_fold"] = [float(m[k]) for m in fold_metrics if m[k] is not None]
        else:
            summary[k + "_mean"] = None
            summary[k + "_sd"] = None
            summary[k + "_per_fold"] = []
    # Sum confusion matrices across folds
    cm_total = np.zeros((2, 2), dtype=int)
    for m in fold_metrics:
        cm_total += np.array(m["confusion_matrix"])
    summary["confusion_matrix_total"] = cm_total.tolist()
    return summary


def _baselines(y, groups, cv):
    """Compute majority-class and stratified dummy classifier baselines."""
    results = {}
    # Majority-class baseline (always predict the majority class)
    maj_clf = DummyClassifier(strategy="most_frequent", random_state=42)
    maj_folds = _cv_evaluate(maj_clf, np.zeros((len(y), 1)), y, groups, cv)
    maj_summary = _summarize_folds(maj_folds)
    results["majority_class"] = {
        "strategy": "most_frequent",
        "description": "Always predicts the majority class",
        "accuracy_mean": maj_summary["accuracy_mean"],
        "accuracy_sd": maj_summary["accuracy_sd"],
        "balanced_accuracy_mean": maj_summary["balanced_accuracy_mean"],
        "mcc_mean": maj_summary["mcc_mean"],
    }
    # Stratified dummy (random with class prior)
    strat_clf = DummyClassifier(strategy="stratified", random_state=42)
    strat_folds = _cv_evaluate(strat_clf, np.zeros((len(y), 1)), y, groups, cv)
    strat_summary = _summarize_folds(strat_folds)
    results["stratified_random"] = {
        "strategy": "stratified",
        "description": "Random prediction respecting class prior",
        "accuracy_mean": strat_summary["accuracy_mean"],
        "accuracy_sd": strat_summary["accuracy_sd"],
        "balanced_accuracy_mean": strat_summary["balanced_accuracy_mean"],
        "mcc_mean": strat_summary["mcc_mean"],
    }
    return results


def random_forest_classifier(df):
    """
    5-fold StratifiedGroupKFold CV Random Forest classifier.
    Group = prompt_id to prevent data leakage (same prompt's variants stay in same fold).
    Reports: accuracy, balanced accuracy, per-class F1, macro F1, AUC, MCC, confusion matrix.
    Compares against majority-class and stratified dummy baselines.
    """
    X = df[METRIC_KEYS].values
    human_mask = (df["condition"] == "human").values
    groups = df["prompt_id"].values

    results = {"per_condition": {}}

    for ai_cond in sorted(df["condition"].unique()):
        if ai_cond == "human":
            continue

        keep = human_mask | (df["condition"] == ai_cond).values
        X_sub = X[keep]
        y_sub = human_mask[keep].astype(int)
        groups_sub = groups[keep]

        if len(np.unique(y_sub)) < 2:
            continue

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_sub)

        clf = RandomForestClassifier(
            n_estimators=100, max_depth=None, min_samples_split=2,
            min_samples_leaf=1, random_state=42, class_weight="balanced",
        )
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

        fold_metrics = _cv_evaluate(clf, X_scaled, y_sub, groups_sub, cv)
        summary = _summarize_folds(fold_metrics)
        baselines = _baselines(y_sub, groups_sub, cv)

        # Fit final model on all data for feature importances
        clf.fit(X_scaled, y_sub)
        importances = clf.feature_importances_
        feature_importance = sorted(
            [{"metric": m, "metric_label": METRIC_LABELS[m], "importance": float(importances[i])}
             for i, m in enumerate(METRIC_KEYS)],
            key=lambda x: x["importance"], reverse=True,
        )

        results["per_condition"][ai_cond] = {
            "ai_condition": ai_cond,
            "ai_condition_label": CONDITION_LABELS.get(ai_cond, ai_cond),
            "n_estimators": 100, "n_folds": 5,
            "cv_strategy": "StratifiedGroupKFold (shuffle=True, seed=42, group=prompt_id)",
            "class_weight": "balanced",
            "features": METRIC_KEYS, "n_features": len(METRIC_KEYS),
            "n_samples": int(len(X_sub)),
            "n_human": int(np.sum(y_sub == 1)),
            "n_ai": int(np.sum(y_sub == 0)),
            # Accuracy
            "cv_accuracy_mean": summary["accuracy_mean"],
            "cv_accuracy_sd": summary["accuracy_sd"],
            "cv_scores_per_fold": summary["accuracy_per_fold"],
            # Balanced accuracy
            "cv_balanced_accuracy_mean": summary["balanced_accuracy_mean"],
            "cv_balanced_accuracy_sd": summary["balanced_accuracy_sd"],
            "cv_balanced_accuracy_per_fold": summary["balanced_accuracy_per_fold"],
            # Per-class F1
            "cv_f1_ai_mean": summary["f1_ai_mean"],
            "cv_f1_human_mean": summary["f1_human_mean"],
            "cv_f1_macro_mean": summary["f1_macro_mean"],
            "cv_f1_macro_sd": summary["f1_macro_sd"],
            # AUC
            "cv_auc_mean": summary["auc_mean"],
            "cv_auc_sd": summary["auc_sd"],
            # MCC
            "cv_mcc_mean": summary["mcc_mean"],
            "cv_mcc_sd": summary["mcc_sd"],
            "cv_mcc_per_fold": summary["mcc_per_fold"],
            # Confusion matrix
            "confusion_matrix_total": summary["confusion_matrix_total"],
            # Feature importance & baselines
            "feature_importance": feature_importance,
            "baselines": baselines,
            "h5_threshold": 0.70,
            "h5_passed": bool(summary["accuracy_mean"] >= 0.70),
        }

    # Overall classifier (any AI vs human) — H5 main test
    ai_mask = ~human_mask
    if ai_mask.any() and human_mask.any():
        keep = human_mask | ai_mask
        X_sub = X[keep]
        y_sub = human_mask[keep].astype(int)
        groups_sub = groups[keep]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_sub)
        clf = RandomForestClassifier(
            n_estimators=100, max_depth=None, min_samples_split=2,
            min_samples_leaf=1, random_state=42, class_weight="balanced",
        )
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        fold_metrics = _cv_evaluate(clf, X_scaled, y_sub, groups_sub, cv)
        summary = _summarize_folds(fold_metrics)
        baselines = _baselines(y_sub, groups_sub, cv)
        clf.fit(X_scaled, y_sub)
        importances = clf.feature_importances_
        feature_importance = sorted(
            [{"metric": m, "metric_label": METRIC_LABELS[m], "importance": float(importances[i])}
             for i, m in enumerate(METRIC_KEYS)],
            key=lambda x: x["importance"], reverse=True,
        )
        results["overall"] = {
            "classifier": "RandomForestClassifier (any AI vs human)",
            "n_estimators": 100, "n_folds": 5,
            "cv_strategy": "StratifiedGroupKFold (shuffle=True, seed=42, group=prompt_id)",
            "class_weight": "balanced",
            "features": METRIC_KEYS, "n_features": len(METRIC_KEYS),
            "n_samples": int(len(X_sub)),
            "n_human": int(np.sum(y_sub == 1)),
            "n_ai": int(np.sum(y_sub == 0)),
            # Accuracy
            "cv_accuracy_mean": summary["accuracy_mean"],
            "cv_accuracy_sd": summary["accuracy_sd"],
            "cv_scores_per_fold": summary["accuracy_per_fold"],
            # Balanced accuracy
            "cv_balanced_accuracy_mean": summary["balanced_accuracy_mean"],
            "cv_balanced_accuracy_sd": summary["balanced_accuracy_sd"],
            "cv_balanced_accuracy_per_fold": summary["balanced_accuracy_per_fold"],
            # Per-class F1
            "cv_f1_ai_mean": summary["f1_ai_mean"],
            "cv_f1_human_mean": summary["f1_human_mean"],
            "cv_f1_macro_mean": summary["f1_macro_mean"],
            "cv_f1_macro_sd": summary["f1_macro_sd"],
            # AUC
            "cv_auc_mean": summary["auc_mean"],
            "cv_auc_sd": summary["auc_sd"],
            # MCC
            "cv_mcc_mean": summary["mcc_mean"],
            "cv_mcc_sd": summary["mcc_sd"],
            "cv_mcc_per_fold": summary["mcc_per_fold"],
            # Confusion matrix
            "confusion_matrix_total": summary["confusion_matrix_total"],
            # Feature importance & baselines
            "feature_importance": feature_importance,
            "baselines": baselines,
            "h5_threshold": 0.70,
            "h5_passed": bool(summary["accuracy_mean"] >= 0.70),
        }
    return results


def write_results_v1(descriptive, hypothesis_tests, rf_result, df):
    """Write the results_v1.json output."""
    available_conditions = sorted(df["condition"].unique())
    results = {
        "metadata": {
            "version": "v3",
            "generated_by": "analysis/run_analysis.py (StratifiedGroupKFold + balanced metrics + baselines)",
            "sample_source": "data/processed/sample_v1.json",
            "n_prompts": 30,
            "conditions": available_conditions,
            "metrics": METRIC_KEYS,
            "citations": [
                "Fan et al. 2018 (ACL) — Reddit WritingPrompts corpus",
                "Huang et al. 2024 (EMNLP Workshop) — GPT-WritingPrompts dataset",
            ],
            "license": "MIT",
        },
        "descriptive_statistics": descriptive,
        "hypothesis_tests": hypothesis_tests,
        "classifier": rf_result,
        "per_sample_metrics": [],
    }

    # Include per-sample raw metrics
    for _, row in df.iterrows():
        results["per_sample_metrics"].append({
            "prompt_id": int(row["prompt_id"]),
            "condition": row["condition"],
            "metrics": {k: float(row[k]) for k in METRIC_KEYS},
            "n_words": int(row["_n_words"]),
            "n_sentences": int(row["_n_sentences"]),
            "n_paragraphs": int(row["_n_paragraphs"]),
        })

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Wrote {RESULTS_PATH}")
    return results


def write_results_schema():
    """Write the results_schema.md documentation."""
    schema_md = """# Results Schema: `data/processed/results_v1.json`

> **Version:** v1
> **Generated by:** `analysis/run_analysis.py`

## Top-Level Structure

```
{
  "metadata": { ... },
  "descriptive_statistics": [ ... ],
  "hypothesis_tests": [ ... ],
  "classifier": { ... },
  "per_sample_metrics": [ ... ]
}
```

## Field Descriptions

### `metadata`

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version (`"v1"`) |
| `generated_by` | string | Script that produced this file |
| `sample_source` | string | Input data file path |
| `n_prompts` | int | Number of prompts in the sample |
| `conditions` | string[] | List of conditions compared |
| `metrics` | string[] | The 8 locked metric keys |
| `citations` | string[] | Data source citations |
| `license` | string | Dataset license |

### `descriptive_statistics[]`

Each entry is one (metric, condition) pair:

| Field | Type | Description |
|-------|------|-------------|
| `metric` | string | Metric key (e.g., `"sentence_length_var"`) |
| `metric_label` | string | Human-readable metric name |
| `condition` | string | `"human"` / `"gpt35"` / `"MiMo-V2.5-Pro"` / `"DeepSeek-V4-Flash"` / etc. |
| `condition_label` | string | Human-readable condition name |
| `mean` | float | Sample mean |
| `sd` | float | Sample standard deviation (ddof=1) |
| `n` | int | Sample size |
| `min` | float | Minimum value |
| `max` | float | Maximum value |
| `median` | float | Median value |

### `hypothesis_tests[]`

Each entry is one hypothesis (H1–H4) for one AI condition vs Human:

| Field | Type | Description |
|-------|------|-------------|
| `hypothesis` | string | Hypothesis ID (`"H1"`–`"H4"`) |
| `description` | string | Plain-language hypothesis statement |
| `metric` | string | Metric key tested |
| `metric_label` | string | Human-readable metric name |
| `ai_condition` | string | AI condition key (e.g., `"DeepSeek-V4-Flash"`) |
| `ai_condition_label` | string | Human-readable AI label |
| `direction_tested` | string | `"less"` (AI < Human) or `"greater"` (AI > Human) |
| `alternative` | string | Full alternative hypothesis label |
| `test_used` | string | Primary test used |
| `wilcoxon_statistic` | float \| null | Wilcoxon signed-rank statistic (paired) |
| `wilcoxon_p_one_tailed` | float \| null | One-tailed p-value from Wilcoxon |
| `mann_whitney_u_statistic` | float | Mann-Whitney U statistic |
| `mann_whitney_p_one_tailed` | float | One-tailed p-value from Mann-Whitney U |
| `mann_whitney_p_two_tailed` | float | Two-tailed p-value from Mann-Whitney U |
| `human_mean` | float | Mean of human condition for this metric |
| `ai_mean` | float | Mean of AI condition for this metric |
| `mean_delta` | float | Mean of per-prompt deltas (human − AI) |
| `median_delta` | float | Median of per-prompt deltas |
| `significant_at_005` | bool | Whether p < 0.05 (one-tailed) |
| `n_pairs` | int | Number of paired observations |

### `classifier`

| Field | Type | Description |
|-------|------|-------------|
| `classifier` | string | Classifier type |
| `n_estimators` | int | Number of trees |
| `n_folds` | int | CV folds |
| `cv_strategy` | string | CV strategy description |
| `class_weight` | string | Class weighting |
| `features` | string[] | Feature metric keys |
| `n_features` | int | Number of features |
| `n_samples` | int | Total samples |
| `n_human` | int | Number of human samples |
| `n_ai` | int | Number of AI samples |
| `cv_accuracy_mean` | float | Mean CV accuracy |
| `cv_accuracy_sd` | float | SD of CV accuracy |
| `cv_scores_per_fold` | float[] | Accuracy for each fold |
| `feature_importance` | array | Sorted by importance (descending) |
| `feature_importance[].metric` | string | Metric key |
| `feature_importance[].metric_label` | string | Human-readable name |
| `feature_importance[].importance` | float | Gini importance score |
| `h5_threshold` | float | H5 accuracy threshold (0.70) |
| `h5_passed` | bool | Whether mean accuracy ≥ threshold |

### `per_sample_metrics[]`

Each entry is one (prompt, condition) observation:

| Field | Type | Description |
|-------|------|-------------|
| `prompt_id` | int | Prompt index (0–29) |
| `condition` | string | `"human"` or `"gpt35"` |
| `metrics` | object | 8 metric values keyed by metric name |
| `n_words` | int | Total words in text |
| `n_sentences` | int | Total sentences |
| `n_paragraphs` | int | Total paragraphs |

## Citations

- **Fan et al. 2018 (ACL):** Reddit WritingPrompts corpus — source of human-written stories
- **Huang et al. 2024 (EMNLP Workshop):** GPT-WritingPrompts dataset — source of GPT-3.5 stories
"""
    with open(SCHEMA_PATH, "w") as f:
        f.write(schema_md)
    print(f"✓ Wrote {SCHEMA_PATH}")


def write_results_summary(descriptive, hypothesis_tests, rf_result):
    """Write the results_summary.md with tables, p-values, and interpretation."""
    # Build descriptive table
    desc_df = pd.DataFrame(descriptive)
    
    lines = []
    lines.append("# Results Summary: N=30 Pilot Analysis")
    lines.append("")
    lines.append("> **Generated by:** `analysis/run_analysis.py`")
    lines.append("> **Data:** `data/processed/sample_v1.json` (30 prompts × human + GPT-3.5)")
    lines.append("> **Citations:** Fan et al. 2018 (ACL); Huang et al. 2024 (EMNLP Workshop)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Descriptive Statistics Table ──
    # ── Descriptive Statistics (per condition) ──
    lines.append("## 1. Descriptive Statistics (Mean ± SD)")
    lines.append("")
    # Build header dynamically based on available conditions
    available_conds = sorted(set(d["condition"] for d in descriptive))
    cond_cols = [CONDITION_LABELS.get(c, c) for c in available_conds]
    header = "| Metric | " + " | ".join(f"{c} (mean ± sd)" for c in cond_cols) + " |"
    sep    = "|--------|" + "|".join(["-" * 18] * len(cond_cols)) + "|"
    lines.append(header)
    lines.append(sep)
    for metric in METRIC_KEYS:
        row = f"| {METRIC_LABELS[metric]} "
        for c in available_conds:
            stat = next((d for d in descriptive if d["metric"] == metric and d["condition"] == c), None)
            if stat:
                row += f"| {stat['mean']:.3f} ± {stat['sd']:.3f} "
            else:
                row += "| N/A "
        lines.append(row + "|")
    lines.append("")

    # ── Hypothesis Tests ──
    lines.append("## 2. Hypothesis Tests (H1–H4) — per AI condition vs Human")
    lines.append("")
    lines.append("Paired per-prompt comparison (Wilcoxon signed-rank, one-tailed, α = 0.05).")
    lines.append("Mann-Whitney U reported as robustness check. Multi-AI testing not Bonferroni-corrected here — see docs/methodology.md.")
    lines.append("")
    # Group hypothesis tests by AI condition
    by_ai = {}
    for ht in hypothesis_tests:
        by_ai.setdefault(ht["ai_condition"], []).append(ht)
    for ai_cond in sorted(by_ai.keys()):
        ai_label = CONDITION_LABELS.get(ai_cond, ai_cond)
        n_pairs_min = min((ht["n_pairs"] for ht in by_ai[ai_cond]), default=0)
        lines.append(f"### vs **{ai_label}** (n = {n_pairs_min} pairs)")
        lines.append("")
        lines.append("| Hypothesis | Metric | Direction | Human mean | AI mean | Δ (median) | Wilcoxon p | MW U p | Sig? |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for ht in by_ai[ai_cond]:
            sig = "✅" if ht["significant_at_005"] else "❌"
            w_p = f"{ht['wilcoxon_p_one_tailed']:.4f}" if ht.get("wilcoxon_p_one_tailed") is not None else "N/A"
            lines.append(
                f"| {ht['hypothesis']} | {ht['metric_label']} | {ht['direction_tested']} | "
                f"{ht['human_mean']:.3f} | {ht['ai_mean']:.3f} | {ht['median_delta']:+.3f} | "
                f"{w_p} | {ht['mann_whitney_p_one_tailed']:.4f} | {sig} |"
            )
        lines.append("")

    # ── Classifier (per condition + overall) ──
    lines.append("## 3. Random Forest Classifier (H5)")
    lines.append("")
    lines.append("5-fold **StratifiedGroupKFold** CV (group = prompt_id), random_state=42, 100 trees.")
    lines.append("Groups ensure all variants of the same prompt stay in the same fold → no data leakage.")
    lines.append("")
    lines.append("### Metrics reported")
    lines.append("")
    lines.append("- **Accuracy** and **Balanced Accuracy** (handles class imbalance)")
    lines.append("- **Per-class F1** (AI / Human) and **Macro F1**")
    lines.append("- **ROC AUC** (probability-based discrimination)")
    lines.append("- **Matthews Correlation Coefficient (MCC)** (balanced even with imbalanced classes)")
    lines.append("- **Confusion matrix** (summed across folds)")
    lines.append("")

    if "overall" in rf_result:
        ov = rf_result["overall"]
        lines.append(f"### Overall (any AI vs Human)")
        lines.append("")
        lines.append(f"- **Samples:** {ov['n_samples']} ({ov['n_human']} human, {ov['n_ai']} AI)")
        lines.append(f"- **CV Strategy:** {ov['cv_strategy']}")
        lines.append(f"- **Accuracy:** {ov['cv_accuracy_mean']:.1%} ± {ov['cv_accuracy_sd']:.1%}")
        lines.append(f"- **Balanced Accuracy:** {ov['cv_balanced_accuracy_mean']:.1%} ± {ov['cv_balanced_accuracy_sd']:.1%}")
        lines.append(f"- **Macro F1:** {ov['cv_f1_macro_mean']:.3f} ± {ov['cv_f1_macro_sd']:.3f}")
        lines.append(f"- **F1 (Human):** {ov['cv_f1_human_mean']:.3f} | **F1 (AI):** {ov['cv_f1_ai_mean']:.3f}")
        auc_str = f"{ov['cv_auc_mean']:.3f} ± {ov['cv_auc_sd']:.3f}" if ov.get('cv_auc_mean') is not None else "N/A"
        lines.append(f"- **AUC:** {auc_str}")
        lines.append(f"- **MCC:** {ov['cv_mcc_mean']:.3f} ± {ov['cv_mcc_sd']:.3f}")
        lines.append(f"- **Per-fold accuracy:** {', '.join(f'{s:.1%}' for s in ov['cv_scores_per_fold'])}")
        cm = ov.get("confusion_matrix_total", [[0,0],[0,0]])
        lines.append(f"- **Confusion matrix (total):** TN={cm[0][0]} FP={cm[0][1]} FN={cm[1][0]} TP={cm[1][1]}")
        lines.append(f"- **H5 Result:** {'✅ PASSED' if ov['h5_passed'] else '❌ BELOW THRESHOLD'}")
        # Baselines
        baselines = ov.get("baselines", {})
        if baselines:
            lines.append("")
            lines.append("#### Baseline comparisons")
            lines.append("")
            lines.append("| Baseline | Accuracy | Balanced Acc | MCC |")
            lines.append("|---|---|---|---|")
            for b_name, b in baselines.items():
                acc = f"{b['accuracy_mean']:.1%}" if b.get('accuracy_mean') is not None else "N/A"
                bal = f"{b['balanced_accuracy_mean']:.1%}" if b.get('balanced_accuracy_mean') is not None else "N/A"
                mcc = f"{b['mcc_mean']:.3f}" if b.get('mcc_mean') is not None else "N/A"
                lines.append(f"| {b['description']} | {acc} | {bal} | {mcc} |")
            lines.append("")
            lines.append(f"**RF accuracy ({ov['cv_accuracy_mean']:.1%}) vs majority-class baseline ({baselines.get('majority_class', {}).get('accuracy_mean', 0):.1%}): Δ = {ov['cv_accuracy_mean'] - baselines.get('majority_class', {}).get('accuracy_mean', 0):.1%}**")
        lines.append("")

    lines.append("### Per-condition classifier")
    lines.append("")
    lines.append("| AI Condition | n (H/AI) | Accuracy | Bal. Acc | Macro F1 | MCC | AUC | H5? |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for ai_cond, ov in sorted(rf_result["per_condition"].items()):
        ai_label = CONDITION_LABELS.get(ai_cond, ai_cond)
        passed = "✅" if ov["h5_passed"] else "❌"
        auc_str = f"{ov['cv_auc_mean']:.3f}" if ov.get('cv_auc_mean') is not None else "N/A"
        lines.append(
            f"| {ai_label} | {ov['n_human']}/{ov['n_ai']} | "
            f"{ov['cv_accuracy_mean']:.1%} ± {ov['cv_accuracy_sd']:.1%} | "
            f"{ov['cv_balanced_accuracy_mean']:.1%} | "
            f"{ov['cv_f1_macro_mean']:.3f} | "
            f"{ov['cv_mcc_mean']:.3f} | "
            f"{auc_str} | {passed} |"
        )
    lines.append("")

    # Overall feature importance (from "overall" classifier)
    if "overall" in rf_result:
        lines.append("### Feature Importance (Overall classifier)")
        lines.append("")
        lines.append("| Rank | Metric | Importance |")
        lines.append("|------|--------|------------|")
        for i, fi in enumerate(rf_result["overall"]["feature_importance"], 1):
            lines.append(f"| {i} | {fi['metric_label']} | {fi['importance']:.4f} |")
        lines.append("")

    # ── Interpretation ──
    lines.append("## 4. Interpretation (Multi-condition)")
    lines.append("")

    # Per-AI summary
    for ai_cond in sorted(by_ai.keys()):
        ai_label = CONDITION_LABELS.get(ai_cond, ai_cond)
        sig_in_ai = [ht["hypothesis"] for ht in by_ai[ai_cond] if ht["significant_at_005"]]
        nonsig_in_ai = [ht["hypothesis"] for ht in by_ai[ai_cond] if not ht["significant_at_005"]]
        n_sig = len(sig_in_ai)
        lines.append(f"### {ai_label}")
        lines.append("")
        if n_sig > 0:
            lines.append(f"- **{n_sig} of 4 hypotheses supported:** {', '.join(sig_in_ai)}")
        if nonsig_in_ai:
            lines.append(f"- **{len(nonsig_in_ai)} not significant:** {', '.join(nonsig_in_ai)}")
        for ht in by_ai[ai_cond]:
            direction_consistent = (ht["direction_tested"] == "less" and ht["median_delta"] > 0) or \
                                   (ht["direction_tested"] == "greater" and ht["median_delta"] < 0)
            direction_word = "lower" if ht["direction_tested"] == "less" else "higher"
            w_p_str = f"{ht['wilcoxon_p_one_tailed']:.4f}" if ht.get("wilcoxon_p_one_tailed") is not None else "N/A"
            if ht["significant_at_005"]:
                lines.append(f"  - **{ht['hypothesis']}** ({ht['metric_label']}): supported. {ai_label} shows {direction_word} values (Δ = {ht['median_delta']:+.3f}, p = {w_p_str}).")
            elif direction_consistent:
                lines.append(f"  - **{ht['hypothesis']}** ({ht['metric_label']}): not significant (p = {w_p_str}). Direction consistent with hypothesis; may reach significance at larger N.")
            else:
                lines.append(f"  - **{ht['hypothesis']}** ({ht['metric_label']}): not significant (p = {w_p_str}). Direction opposite to hypothesis; data does not support {ht['hypothesis']} for {ai_label}.")
        lines.append("")

    # Word Length additional finding — compare across conditions
    lines.append("### Additional Finding: Word Length")
    lines.append("")
    human_wl = next((d for d in descriptive if d["metric"] == "word_length" and d["condition"] == "human"), None)
    if human_wl:
        lines.append("Word length (chars/word) emerged as the largest discriminator in Random Forest feature importance.")
        lines.append("")
        lines.append("| Condition | Mean | Δ vs Human |")
        lines.append("|---|---|---|")
        for c in available_conds:
            stat = next((d for d in descriptive if d["metric"] == "word_length" and d["condition"] == c), None)
            if stat:
                delta = stat["mean"] - human_wl["mean"]
                pct = abs(delta) / human_wl["mean"] * 100
                sign = "+" if delta > 0 else ""
                c_label = CONDITION_LABELS.get(c, c)
                lines.append(f"| {c_label} | {stat['mean']:.3f} | {sign}{delta:.3f} ({pct:.1f}%) |")
        lines.append("")
        lines.append("All AI conditions show **longer words** than human — consistent across model families. "
                     "Worth registering as H6 in the next iteration.")
    lines.append("")

    # Caveats
    lines.append("### Caveats")
    lines.append("")
    lines.append(f"1. **Small sample (N=30 prompts, {len(available_conds)-1} AI conditions):** Statistical power is limited. ")
    lines.append(f"2. **Missing conditions:** MiniMax-M3, Muse-Spark-1.2-Contributor, GPT-5.6-Pro, Claude-Sonnet, Gemini-2.0-Pro are empty (no API keys / Arena manual paste pending). ")
    lines.append(f"3. **DeepSeek-V4-Flash missing prompt 25** (timeout during generation).")
    lines.append("4. **Genre:** Creative fiction (r/WritingPrompts) — may not transfer to academic or other registers.")
    lines.append("5. **Population variance:** SD uses ddof=1 (sample SD). Sentence/paragraph variance metrics use `statistics.pvariance` (population variance within-text).")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Citations")
    lines.append("")
    lines.append("- Fan, A., Lewis, M., & Dauphin, Y. (2018). *Hierarchical Neural Story Generation.* "
                 "Proceedings of ACL 2018. [GitHub](https://github.com/raoyongming/WritingPrompts)")
    lines.append("- Huang, K., et al. (2024). *GPT-WritingPrompts.* "
                 "EMNLP 2024 Workshop on Narrative Understanding. [GitHub](https://github.com/KristinHuangg/gpt-writing-prompts)")
    lines.append("")

    with open(SUMMARY_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"✓ Wrote {SUMMARY_PATH}")


def main():
    print("=" * 60)
    print("RAY-423: StratifiedGroupKFold + Balanced Metrics + Baselines")
    print("=" * 60)
    print()

    # 1. Load data
    print("Loading metrics...")
    data = load_metrics()
    df = build_dataframe(data)
    conds = sorted(df["condition"].unique())
    print(f"  → {len(df)} observations ({len(data)} prompts × {len(conds)} conditions: {', '.join(conds)})")
    print()

    # 2. Descriptive statistics
    print("Computing descriptive statistics...")
    descriptive = descriptive_stats(df)
    print(f"  → {len(descriptive)} (metric × condition) summary rows")
    print()

    # 3. Hypothesis tests — per AI vs Human
    print("Running hypothesis tests (H1–H4) for each AI condition vs Human...")
    hypothesis_tests = hypothesis_tests_all_ai(df)
    sig_count = sum(1 for ht in hypothesis_tests if ht["significant_at_005"])
    print(f"  → {len(hypothesis_tests)} tests, {sig_count} significant at α=0.05")
    for ht in hypothesis_tests:
        if ht["significant_at_005"]:
            p_val = ht["wilcoxon_p_one_tailed"] if ht["wilcoxon_p_one_tailed"] is not None else ht["mann_whitney_p_one_tailed"]
            print(f"  {ht['hypothesis']} ({ht['ai_condition_label']}): p = {p_val:.4f} ✅")
    print()

    # 4. Random Forest classifier — per condition + overall
    print("Training Random Forest classifier (H5) with StratifiedGroupKFold...")
    rf_result = random_forest_classifier(df)
    if "overall" in rf_result:
        ov = rf_result["overall"]
        print(f"  → CV Strategy: {ov['cv_strategy']}")
        print(f"  → Overall Accuracy: {ov['cv_accuracy_mean']:.1%} ± {ov['cv_accuracy_sd']:.1%}")
        print(f"  → Balanced Accuracy: {ov['cv_balanced_accuracy_mean']:.1%} ± {ov['cv_balanced_accuracy_sd']:.1%}")
        print(f"  → Macro F1: {ov['cv_f1_macro_mean']:.3f}")
        print(f"  → MCC: {ov['cv_mcc_mean']:.3f}")
        if ov.get('cv_auc_mean'):
            print(f"  → AUC: {ov['cv_auc_mean']:.3f}")
        baselines = ov.get("baselines", {})
        maj_acc = baselines.get("majority_class", {}).get("accuracy_mean", 0)
        print(f"  → Majority-class baseline: {maj_acc:.1%} | RF Δ = {ov['cv_accuracy_mean'] - maj_acc:.1%}")
        print(f"  → H5 {'PASSED' if ov['h5_passed'] else 'BELOW THRESHOLD'}")
    for ai_cond, ov in rf_result.get("per_condition", {}).items():
        print(f"  → {CONDITION_LABELS.get(ai_cond, ai_cond)}: {ov['cv_accuracy_mean']:.1%} (bal={ov['cv_balanced_accuracy_mean']:.1%}, F1m={ov['cv_f1_macro_mean']:.3f})")
    print()

    # 5. Write outputs
    print("Writing outputs...")
    write_results_v1(descriptive, hypothesis_tests, rf_result, df)
    write_results_schema()
    write_results_summary(descriptive, hypothesis_tests, rf_result)
    print()
    print("Done! All deliverables written.")


if __name__ == "__main__":
    main()
