"""
length_analysis.py — RAY-424: Text length descriptive stats + length-MTLD correlation
Analyze whether MTLD dominance (0.340 feature importance) is confounded by text length.

Actions:
  1. Compute mean ± SD word count per condition (human + 9 AI)
  2. Compute within-condition Pearson r between word count and each of the 8 metrics
  3. Length-matched subsample analysis (400-800 words): re-run H4 + RF
  4. Also try a broader match (300-900) to retain more human samples
  5. Partial correlation: MTLD vs condition controlling for word count

Output: structured JSON + console summary for proposal update.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT = Path(__file__).parent.parent
METRICS_PATH = PROJECT / "data" / "processed" / "metrics_results.json"
OUTPUT_PATH = PROJECT / "analysis" / "length_analysis_results.json"

METRIC_KEYS = [
    "word_length", "sentence_length", "sentence_length_var",
    "ttr", "mtld", "conj_freq",
    "paragraph_length", "paragraph_length_var",
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

AI_CONDITIONS = [
    "gpt35", "MiMo-V2.5-Pro", "DeepSeek-V4-Flash",
    "MiniMax-M3", "Muse-Spark-1.2-Contributor",
    "GPT-5.6-Luna", "Claude-Sonnet-5-High", "Gemini-3.6-Flash", "Kimi-K3",
]

CONDITION_LABELS = {
    "human": "Human", "gpt35": "GPT-3.5",
    "MiMo-V2.5-Pro": "MiMo", "DeepSeek-V4-Flash": "DeepSeek",
    "MiniMax-M3": "MiniMax", "Muse-Spark-1.2-Contributor": "Muse-Spark",
    "GPT-5.6-Luna": "GPT-5.6", "Claude-Sonnet-5-High": "Claude",
    "Gemini-3.6-Flash": "Gemini", "Kimi-K3": "Kimi",
}

HYPOTHESES = {
    "H1": {"metric": "sentence_length_var", "direction": "less"},
    "H2": {"metric": "paragraph_length_var", "direction": "less"},
    "H3": {"metric": "ttr", "direction": "less"},
    "H4": {"metric": "conj_freq", "direction": "greater"},
}


def load_data():
    with open(METRICS_PATH) as f:
        data = json.load(f)
    rows = []
    for entry in data:
        pid = entry["prompt_id"]
        for cond, m in entry.items():
            if cond == "prompt_id" or m is None:
                continue
            row = {"prompt_id": pid, "condition": cond, "n_words": m["_n_words"]}
            for k in METRIC_KEYS:
                row[k] = m[k]
            rows.append(row)
    return pd.DataFrame(rows)


def word_count_descriptive(df):
    """Action 1: Mean ± SD word count per condition."""
    results = []
    for cond in sorted(df["condition"].unique()):
        sub = df[df["condition"] == cond]["n_words"]
        results.append({
            "condition": cond,
            "condition_label": CONDITION_LABELS.get(cond, cond),
            "mean": float(sub.mean()),
            "sd": float(sub.std(ddof=1)),
            "min": int(sub.min()),
            "max": int(sub.max()),
            "median": float(sub.median()),
            "n": int(len(sub)),
        })
    return results


def within_condition_correlations(df):
    """Action 2: Pearson r between n_words and each metric, within each condition."""
    results = []
    for cond in sorted(df["condition"].unique()):
        sub = df[df["condition"] == cond]
        for metric in METRIC_KEYS:
            r, p = stats.pearsonr(sub["n_words"], sub[metric])
            results.append({
                "condition": cond,
                "condition_label": CONDITION_LABELS.get(cond, cond),
                "metric": metric,
                "metric_label": METRIC_LABELS[metric],
                "pearson_r": float(r),
                "p_value": float(p),
                "n": int(len(sub)),
                "significant_at_005": bool(p < 0.05),
            })
    return results


def aggregate_correlations(corr_results):
    """Aggregate: average |r| across conditions for each metric."""
    by_metric = {}
    for c in corr_results:
        by_metric.setdefault(c["metric"], []).append(c["pearson_r"])
    agg = []
    for metric, rs in by_metric.items():
        abs_rs = [abs(r) for r in rs]
        agg.append({
            "metric": metric,
            "metric_label": METRIC_LABELS[metric],
            "mean_abs_r": float(np.mean(abs_rs)),
            "max_abs_r": float(np.max(abs_rs)),
            "mean_r": float(np.mean(rs)),
            "n_conditions": len(rs),
        })
    agg.sort(key=lambda x: x["mean_abs_r"], reverse=True)
    return agg


def run_wilcoxon_one_ai(df, ai_condition):
    """Run H4 one-tailed Wilcoxon for one AI vs human."""
    results = []
    for h_name, h_spec in HYPOTHESES.items():
        metric = h_spec["metric"]
        direction = h_spec["direction"]
        merged = df[df["condition"].isin(["human", ai_condition])].copy()
        pivoted = merged.pivot(index="prompt_id", columns="condition", values=metric).dropna()
        h = pivoted["human"].values
        a = pivoted[ai_condition].values
        deltas = h - a
        try:
            _, p_two = stats.wilcoxon(deltas, alternative="two-sided")
            if direction == "less":
                p_one = p_two / 2 if np.median(deltas) > 0 else 1 - p_two / 2
            else:
                p_one = p_two / 2 if np.median(deltas) < 0 else 1 - p_two / 2
        except ValueError:
            p_one = float("nan")
        results.append({
            "hypothesis": h_name,
            "ai_condition": ai_condition,
            "wilcoxon_p_one_tailed": float(p_one) if not np.isnan(p_one) else None,
            "human_mean": float(np.mean(h)),
            "ai_mean": float(np.mean(a)),
            "median_delta": float(np.median(deltas)),
            "significant_at_005": bool(p_one < 0.05) if not np.isnan(p_one) else False,
            "n_pairs": len(deltas),
        })
    return results


def run_rf_classifier(df, label="full"):
    """Run overall RF classifier (any AI vs human)."""
    X = df[METRIC_KEYS].values
    human_mask = (df["condition"] == "human").values
    y = human_mask.astype(int)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=None, min_samples_split=2,
        min_samples_leaf=1, random_state=42, class_weight="balanced",
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X_scaled, y, cv=cv, scoring="accuracy")
    clf.fit(X_scaled, y)
    importances = clf.feature_importances_
    fi = []
    for i, metric in enumerate(METRIC_KEYS):
        fi.append({"metric": metric, "metric_label": METRIC_LABELS[metric], "importance": float(importances[i])})
    fi.sort(key=lambda x: x["importance"], reverse=True)
    return {
        "label": label,
        "n_samples": int(len(X)),
        "n_human": int(np.sum(y == 1)),
        "n_ai": int(np.sum(y == 0)),
        "cv_accuracy_mean": float(cv_scores.mean()),
        "cv_accuracy_sd": float(cv_scores.std(ddof=1)),
        "cv_scores_per_fold": [float(s) for s in cv_scores],
        "feature_importance": fi,
    }


def length_matched_analysis(df, low, high, label):
    """Re-run H4 + RF on a length-matched subsample."""
    mask = (df["n_words"] >= low) & (df["n_words"] <= high)
    sub = df[mask].copy()
    n_per_cond = sub.groupby("condition").size()
    conds_with_data = n_per_cond[n_per_cond >= 5].index.tolist()
    sub = sub[sub["condition"].isin(conds_with_data)]

    # Hypothesis tests for H4 only (most robust finding)
    available_ai = [c for c in AI_CONDITIONS if c in conds_with_data]
    h4_results = []
    for ai in available_ai:
        h4_results.extend(run_wilcoxon_one_ai(sub, ai))

    # RF classifier
    rf = run_rf_classifier(sub, label=label)

    return {
        "range": f"{low}-{high}",
        "label": label,
        "n_per_condition": {k: int(v) for k, v in n_per_cond.items()},
        "conditions_included": sorted(conds_with_data),
        "h4_tests": h4_results,
        "rf_classifier": rf,
    }


def main():
    print("=" * 60)
    print("RAY-424: Text Length + MTLD Confound Analysis")
    print("=" * 60)
    print()

    df = load_data()
    conds = sorted(df["condition"].unique())
    print(f"Loaded {len(df)} observations ({len(conds)} conditions)")
    print()

    # ── Action 1: Word count descriptive stats ──
    print("1. Word count descriptive statistics:")
    wc_stats = word_count_descriptive(df)
    for s in wc_stats:
        print(f"   {s['condition_label']:20s}: {s['mean']:7.1f} ± {s['sd']:6.1f}  (range {s['min']}-{s['max']}, n={s['n']})")
    print()

    # ── Action 2: Within-condition correlations ──
    print("2. Within-condition correlations (n_words vs each metric):")
    corr_results = within_condition_correlations(df)
    agg = aggregate_correlations(corr_results)
    print("   Aggregated mean |r| across all conditions:")
    for a in agg:
        sig_count = sum(1 for c in corr_results if c["metric"] == a["metric"] and c["significant_at_005"])
        print(f"   {a['metric_label']:35s}: mean |r|={a['mean_abs_r']:.3f}  max|r|={a['max_abs_r']:.3f}  sig in {sig_count}/10 conditions")
    print()

    # Detailed: MTLD and TTR correlations per condition
    print("   MTLD-word_count correlation per condition:")
    for c in corr_results:
        if c["metric"] == "mtld":
            sig = "*" if c["significant_at_005"] else ""
            print(f"     {c['condition_label']:20s}: r={c['pearson_r']:+.3f}  p={c['p_value']:.4f}  {sig}")
    print()
    print("   TTR-word_count correlation per condition:")
    for c in corr_results:
        if c["metric"] == "ttr":
            sig = "*" if c["significant_at_005"] else ""
            print(f"     {c['condition_label']:20s}: r={c['pearson_r']:+.3f}  p={c['p_value']:.4f}  {sig}")
    print()

    # ── Action 3: Full-sample RF (baseline) ──
    print("3. Full-sample RF classifier (baseline):")
    rf_full = run_rf_classifier(df, label="full")
    print(f"   Accuracy: {rf_full['cv_accuracy_mean']:.1%} ± {rf_full['cv_accuracy_sd']:.1%}")
    print(f"   MTLD importance: {next(f['importance'] for f in rf_full['feature_importance'] if f['metric'] == 'mtld'):.4f}")
    print()

    # ── Action 4: Length-matched subsample 400-800 ──
    print("4. Length-matched subsample (400-800 words):")
    lm_400_800 = length_matched_analysis(df, 400, 800, "400-800 words")
    for cond, n in sorted(lm_400_800["n_per_condition"].items()):
        label = CONDITION_LABELS.get(cond, cond)
        print(f"   {label:20s}: {n} samples")
    print(f"   RF accuracy: {lm_400_800['rf_classifier']['cv_accuracy_mean']:.1%} ± {lm_400_800['rf_classifier']['cv_accuracy_sd']:.1%}")
    mtld_imp = next(f['importance'] for f in lm_400_800['rf_classifier']['feature_importance'] if f['metric'] == 'mtld')
    print(f"   MTLD importance: {mtld_imp:.4f}")
    print()
    print("   H4 results in length-matched sample:")
    for ht in lm_400_800["h4_tests"]:
        if ht["hypothesis"] == "H4":
            sig = "✅" if ht["significant_at_005"] else "❌"
            label = CONDITION_LABELS.get(ht["ai_condition"], ht["ai_condition"])
            p_str = f"{ht['wilcoxon_p_one_tailed']:.4f}" if ht['wilcoxon_p_one_tailed'] is not None else "N/A"
            print(f"     {label:20s}: p={p_str}  {sig}  (n={ht['n_pairs']})")
    print()

    # ── Action 5: Broader match 300-900 ──
    print("5. Broader subsample (300-900 words):")
    lm_300_900 = length_matched_analysis(df, 300, 900, "300-900 words")
    for cond, n in sorted(lm_300_900["n_per_condition"].items()):
        label = CONDITION_LABELS.get(cond, cond)
        print(f"   {label:20s}: {n} samples")
    print(f"   RF accuracy: {lm_300_900['rf_classifier']['cv_accuracy_mean']:.1%} ± {lm_300_900['rf_classifier']['cv_accuracy_sd']:.1%}")
    mtld_imp_b = next(f['importance'] for f in lm_300_900['rf_classifier']['feature_importance'] if f['metric'] == 'mtld')
    print(f"   MTLD importance: {mtld_imp_b:.4f}")
    print()
    print("   H4 results in broader sample:")
    for ht in lm_300_900["h4_tests"]:
        if ht["hypothesis"] == "H4":
            sig = "✅" if ht["significant_at_005"] else "❌"
            label = CONDITION_LABELS.get(ht["ai_condition"], ht["ai_condition"])
            p_str = f"{ht['wilcoxon_p_one_tailed']:.4f}" if ht['wilcoxon_p_one_tailed'] is not None else "N/A"
            print(f"     {label:20s}: p={p_str}  {sig}  (n={ht['n_pairs']})")
    print()

    # ── Action 6: RF without MTLD (to test if other features carry signal) ──
    print("6. RF classifier WITHOUT MTLD (remaining 7 features):")
    METRIC_NO_MTLD = [k for k in METRIC_KEYS if k != "mtld"]
    X = df[METRIC_NO_MTLD].values
    human_mask = (df["condition"] == "human").values
    y = human_mask.astype(int)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=None, min_samples_split=2,
        min_samples_leaf=1, random_state=42, class_weight="balanced",
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X_scaled, y, cv=cv, scoring="accuracy")
    clf.fit(X_scaled, y)
    importances = clf.feature_importances_
    fi_no_mtld = []
    for i, metric in enumerate(METRIC_NO_MTLD):
        fi_no_mtld.append({"metric": metric, "metric_label": METRIC_LABELS[metric], "importance": float(importances[i])})
    fi_no_mtld.sort(key=lambda x: x["importance"], reverse=True)
    print(f"   Accuracy: {cv_scores.mean():.1%} ± {cv_scores.std(ddof=1):.1%}")
    for f in fi_no_mtld:
        print(f"     {f['metric_label']:35s}: {f['importance']:.4f}")
    print()

    # ── Action 7: RF with word_count as 9th feature ──
    print("7. RF classifier WITH word_count as 9th feature:")
    METRIC_PLUS_WC = METRIC_KEYS + ["n_words"]
    X = df[METRIC_PLUS_WC].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=None, min_samples_split=2,
        min_samples_leaf=1, random_state=42, class_weight="balanced",
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(clf, X_scaled, y, cv=cv, scoring="accuracy")
    clf.fit(X_scaled, y)
    importances = clf.feature_importances_
    fi_plus_wc = []
    for i, metric in enumerate(METRIC_PLUS_WC):
        fi_plus_wc.append({"metric": metric, "metric_label": METRIC_LABELS.get(metric, "Word Count"), "importance": float(importances[i])})
    fi_plus_wc.sort(key=lambda x: x["importance"], reverse=True)
    print(f"   Accuracy: {cv_scores.mean():.1%} ± {cv_scores.std(ddof=1):.1%}")
    for f in fi_plus_wc:
        print(f"     {f['metric_label']:35s}: {f['importance']:.4f}")
    print()

    # ── Write output ──
    output = {
        "word_count_descriptive": wc_stats,
        "within_condition_correlations": corr_results,
        "aggregate_correlations": agg,
        "rf_full": rf_full,
        "rf_no_mtld": {
            "cv_accuracy_mean": float(cv_scores.mean()),
            "cv_accuracy_sd": float(cv_scores.std(ddof=1)),
            "feature_importance": fi_no_mtld,
        },
        "rf_plus_word_count": {
            "cv_accuracy_mean": float(cv_scores.mean()),
            "cv_accuracy_sd": float(cv_scores.std(ddof=1)),
            "feature_importance": fi_plus_wc,
        },
        "length_matched_400_800": lm_400_800,
        "length_matched_300_900": lm_300_900,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"✓ Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
