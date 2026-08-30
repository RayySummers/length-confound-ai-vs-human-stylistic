"""
holm_bonferroni_correction.py — Multiplicity correction + effect sizes for RAY-425

Applies Holm-Bonferroni correction across 36 hypothesis tests (4 H × 9 AI conditions),
computes rank-biserial correlation r for each Wilcoxon test as effect size,
and computes 95% bootstrap CIs for median Δ (AI − Human).

Outputs:
  - Updated results_v1.json (adds corrected p-values, effect sizes, bootstrap CIs)
  - Updated proposal_v1.md Table 2, §4.2 Summary, and Limitations
  - analysis/holm_correction_report.md (standalone report)
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT = Path(__file__).parent.parent
METRICS_PATH = PROJECT / "data" / "processed" / "metrics_results.json"
RESULTS_PATH = PROJECT / "data" / "processed" / "results_v1.json"
PROPOSAL_PATH = PROJECT / "proposal_v1.md"
REPORT_PATH = PROJECT / "analysis" / "holm_correction_report.md"

# ── The 8 locked metrics ──────────────────────────────────────────────────
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

# Short labels for Table 2
SHORT_LABELS = {
    "gpt35": "GPT-3.5",
    "MiMo-V2.5-Pro": "MiMo",
    "DeepSeek-V4-Flash": "DeepSeek",
    "MiniMax-M3": "MiniMax",
    "Muse-Spark-1.2-Contributor": "Muse-Spark",
    "GPT-5.6-Luna": "GPT-5.6",
    "Claude-Sonnet-5-High": "Claude",
    "Gemini-3.6-Flash": "Gemini",
    "Kimi-K3": "Kimi",
}

HYPOTHESES = {
    "H1": {"metric": "sentence_length_var", "direction": "less",    "desc": "AI texts have lower sentence length variance"},
    "H2": {"metric": "paragraph_length_var", "direction": "less",  "desc": "AI texts have lower paragraph length variance"},
    "H3": {"metric": "ttr",                  "direction": "less",    "desc": "AI texts have lower TTR (more repetitive)"},
    "H4": {"metric": "conj_freq",            "direction": "greater", "desc": "AI texts use more conjunctions"},
}


def load_metrics():
    with open(METRICS_PATH) as f:
        return json.load(f)


def build_dataframe(data):
    rows = []
    for entry in data:
        pid = entry["prompt_id"]
        for condition, m in entry.items():
            if condition == "prompt_id" or m is None:
                continue
            row = {"prompt_id": pid, "condition": condition}
            for k in METRIC_KEYS:
                row[k] = m[k]
            row["_n_words"] = m["_n_words"]
            rows.append(row)
    return pd.DataFrame(rows)


def compute_rank_biserial(deltas):
    """
    Compute rank-biserial correlation r for paired Wilcoxon signed-rank test.
    
    r = (2 * W_plus) / (n * (n+1)) - 1
    
    Where W_plus is the sum of ranks of positive differences.
    Equivalent to: proportion of concordant pairs minus discordant pairs.
    
    Effect size interpretation: |r| < 0.1 negligible, 0.1-0.3 small, 0.3-0.5 medium, > 0.5 large.
    """
    # Remove zeros (they don't contribute to Wilcoxon)
    nonzero = deltas[deltas != 0]
    n = len(nonzero)
    if n == 0:
        return 0.0
    
    # Compute ranks of absolute values
    abs_deltas = np.abs(nonzero)
    ranks = stats.rankdata(abs_deltas)
    
    # W_plus = sum of ranks where delta > 0
    w_plus = np.sum(ranks[nonzero > 0])
    w_minus = np.sum(ranks[nonzero < 0])
    
    # Rank-biserial correlation
    # r = (W_plus - W_minus) / (W_plus + W_minus)
    # Since W_plus + W_minus = n*(n+1)/2
    # r = (2*W_plus - n*(n+1)/2) / (n*(n+1)/2) = 4*W_plus/(n*(n+1)) - 1
    r = (2 * w_plus - n * (n + 1) / 2) / (n * (n + 1) / 2)
    return float(r)


def bootstrap_ci_median(deltas, n_boot=10000, ci=0.95, seed=42):
    """
    Compute bootstrap CI for median of deltas.
    Returns (lower, upper, bootstrap_se).
    """
    rng = np.random.RandomState(seed)
    n = len(deltas)
    boot_medians = np.array([
        np.median(rng.choice(deltas, size=n, replace=True))
        for _ in range(n_boot)
    ])
    alpha = (1 - ci) / 2
    lower = float(np.percentile(boot_medians, 100 * alpha))
    upper = float(np.percentile(boot_medians, 100 * (1 - alpha)))
    se = float(np.std(boot_medians, ddof=1))
    return lower, upper, se


def holm_bonferroni(p_values):
    """
    Apply Holm-Bonferroni correction to a list of p-values.
    Returns corrected p-values (capped at 1.0).
    """
    n = len(p_values)
    # Sort p-values, keeping track of original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1] if not np.isnan(x[1]) else float('inf'))
    corrected = np.full(n, np.nan)
    
    for rank, (idx, p) in enumerate(indexed):
        if np.isnan(p):
            corrected[idx] = np.nan
            continue
        # Holm multiplier: (n - rank)
        corrected_p = p * (n - rank)
        # Ensure monotonicity: corrected p >= previous corrected p
        if rank > 0:
            prev_corrected = corrected[indexed[rank - 1][0]]
            if not np.isnan(prev_corrected):
                corrected_p = max(corrected_p, prev_corrected)
        corrected[idx] = min(corrected_p, 1.0)
    
    return corrected


def run_all_tests(df):
    """Run all 36 hypothesis tests with effect sizes and bootstrap CIs."""
    results = []
    
    for h_name, h_spec in HYPOTHESES.items():
        metric = h_spec["metric"]
        direction = h_spec["direction"]
        
        for ai_cond in AI_CONDITIONS:
            if ai_cond not in df["condition"].unique():
                continue
            
            # Paired: per-prompt delta (human - ai)
            merged = df[df["condition"].isin(["human", ai_cond])].copy()
            pivoted = merged.pivot(index="prompt_id", columns="condition", values=metric).dropna()
            h = pivoted["human"].values
            a = pivoted[ai_cond].values
            deltas = h - a  # positive means human > ai
            
            # Wilcoxon signed-rank (paired, non-parametric)
            try:
                wilcoxon_stat, wilcoxon_p_two = stats.wilcoxon(deltas, alternative="two-sided")
                if direction == "less":  # AI < Human → delta > 0
                    if np.median(deltas) > 0:
                        wilcoxon_p_one = wilcoxon_p_two / 2
                    else:
                        wilcoxon_p_one = 1 - wilcoxon_p_two / 2
                else:  # "greater" → AI > Human → delta < 0
                    if np.median(deltas) < 0:
                        wilcoxon_p_one = wilcoxon_p_two / 2
                    else:
                        wilcoxon_p_one = 1 - wilcoxon_p_two / 2
                w_stat_out = float(wilcoxon_stat)
                w_p_out = float(wilcoxon_p_one)
            except ValueError:
                w_stat_out = None
                w_p_out = float("nan")
            
            # Rank-biserial effect size
            r_rb = compute_rank_biserial(deltas)
            
            # Bootstrap CI for median delta
            boot_lower, boot_upper, boot_se = bootstrap_ci_median(deltas)
            
            # Mann-Whitney U (robustness check)
            mw_stat, mw_p_two = stats.mannwhitneyu(h, a, alternative="two-sided")
            if direction == "less":
                _, mw_p_one = stats.mannwhitneyu(h, a, alternative="greater")
            else:
                _, mw_p_one = stats.mannwhitneyu(h, a, alternative="less")
            
            results.append({
                "hypothesis": h_name,
                "metric": metric,
                "metric_label": METRIC_LABELS[metric],
                "ai_condition": ai_cond,
                "ai_condition_label": CONDITION_LABELS.get(ai_cond, ai_cond),
                "direction_tested": direction,
                "wilcoxon_statistic": w_stat_out,
                "wilcoxon_p_one_tailed": w_p_out,
                "mann_whitney_p_one_tailed": float(mw_p_one),
                "human_mean": float(np.mean(h)),
                "ai_mean": float(np.mean(a)),
                "mean_delta": float(np.mean(deltas)),
                "median_delta": float(np.median(deltas)),
                "n_pairs": len(deltas),
                # New fields
                "rank_biserial_r": r_rb,
                "bootstrap_ci_lower": boot_lower,
                "bootstrap_ci_upper": boot_upper,
                "bootstrap_se": boot_se,
                "significant_at_005": bool(w_p_out < 0.05) if not np.isnan(w_p_out) else False,
            })
    
    # Apply Holm-Bonferroni correction
    # Strategy 1: Global correction across all 36 tests
    p_values = [r["wilcoxon_p_one_tailed"] for r in results]
    corrected_global = holm_bonferroni(p_values)
    
    # Strategy 2: Per-hypothesis correction (9 tests each)
    corrected_per_h = {}
    for h_name in HYPOTHESES:
        indices = [i for i, r in enumerate(results) if r["hypothesis"] == h_name]
        p_subset = [results[i]["wilcoxon_p_one_tailed"] for i in indices]
        corrected_subset = holm_bonferroni(p_subset)
        for idx, corr_p in zip(indices, corrected_subset):
            corrected_per_h[idx] = corr_p
    
    for i, r in enumerate(results):
        r["holm_corrected_p_global"] = float(corrected_global[i]) if not np.isnan(corrected_global[i]) else None
        r["holm_corrected_p_per_hypothesis"] = float(corrected_per_h[i]) if not np.isnan(corrected_per_h[i]) else None
        r["significant_holm_global"] = bool(corrected_global[i] < 0.05) if not np.isnan(corrected_global[i]) else False
        r["significant_holm_per_hypothesis"] = bool(corrected_per_h[i] < 0.05) if not np.isnan(corrected_per_h[i]) else False
    
    return results


def update_results_json(test_results):
    """Update results_v1.json with corrected fields."""
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    
    # Add corrected test results
    results["hypothesis_tests_corrected"] = test_results
    
    # Add summary stats
    raw_sig = sum(1 for r in test_results if r["significant_at_005"])
    holm_global_sig = sum(1 for r in test_results if r["significant_holm_global"])
    holm_per_h_sig = sum(1 for r in test_results if r["significant_holm_per_hypothesis"])
    
    results["multiplicity_correction"] = {
        "method": "Holm-Bonferroni",
        "total_tests": len(test_results),
        "raw_significant_at_005": raw_sig,
        "holm_global_significant": holm_global_sig,
        "holm_per_hypothesis_significant": holm_per_h_sig,
        "expected_false_positives_uncorrected": len(test_results) * 0.05,
        "note": "Global corrects across all 36 tests simultaneously; per-hypothesis corrects within each H (9 tests each)."
    }
    
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Updated {RESULTS_PATH}")


def format_p(p):
    """Format p-value for display."""
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "N/A"
    if p < 0.0001:
        return "<0.0001"
    elif p < 0.001:
        return f"{p:.4f}"
    elif p < 0.01:
        return f"{p:.3f}"
    else:
        return f"{p:.3f}"


def format_r(r):
    """Format effect size r."""
    if r is None or (isinstance(r, float) and np.isnan(r)):
        return "N/A"
    return f"{r:.3f}"


def effect_size_label(r):
    """Label effect size magnitude."""
    if r is None or (isinstance(r, float) and np.isnan(r)):
        return ""
    ar = abs(r)
    if ar < 0.1:
        return "negligible"
    elif ar < 0.3:
        return "small"
    elif ar < 0.5:
        return "medium"
    else:
        return "large"


def generate_report(test_results):
    """Generate standalone report markdown."""
    lines = []
    lines.append("# Holm-Bonferroni Correction & Effect Size Report")
    lines.append("")
    lines.append("> **Generated by:** `analysis/holm_bonferroni_correction.py`")
    lines.append("> **Data:** `data/processed/results_v1.json`")
    lines.append("> **Method:** Holm-Bonferroni step-down correction")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary counts
    raw_sig = sum(1 for r in test_results if r["significant_at_005"])
    holm_global_sig = sum(1 for r in test_results if r["significant_holm_global"])
    holm_per_h_sig = sum(1 for r in test_results if r["significant_holm_per_hypothesis"])
    
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total tests:** {len(test_results)} (4 hypotheses × 9 AI conditions)")
    lines.append(f"- **Uncorrected significant (p < 0.05):** {raw_sig}/36")
    lines.append(f"- **Holm-corrected significant (global, 36 tests):** {holm_global_sig}/36")
    lines.append(f"- **Holm-corrected significant (per-hypothesis, 9 tests each):** {holm_per_h_sig}/36")
    lines.append(f"- **Expected false positives (uncorrected):** {len(test_results) * 0.05:.1f}")
    lines.append("")
    
    # ── Table 2: Corrected results ──
    lines.append("## Table 2: Hypothesis Tests with Holm-Bonferroni Correction")
    lines.append("")
    lines.append("| AI Condition | Hyp. | Metric | Dir. | Median Δ | Effect Size r | Bootstrap 95% CI | Raw p | Holm p (global) | Holm p (per-H) | Sig? |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    
    # Group by AI condition
    by_ai = {}
    for r in test_results:
        by_ai.setdefault(r["ai_condition"], []).append(r)
    
    for ai_cond in AI_CONDITIONS:
        if ai_cond not in by_ai:
            continue
        ai_label = SHORT_LABELS.get(ai_cond, ai_cond)
        for r in by_ai[ai_cond]:
            h = r["hypothesis"]
            metric_short = r["metric_label"].split("(")[0].strip()
            direction = "AI<Human" if r["direction_tested"] == "less" else "AI>Human"
            med_delta = f"{r['median_delta']:+.3f}"
            r_str = format_r(r["rank_biserial_r"])
            r_label = effect_size_label(r["rank_biserial_r"])
            ci = f"[{r['bootstrap_ci_lower']:+.3f}, {r['bootstrap_ci_upper']:+.3f}]"
            raw_p = format_p(r["wilcoxon_p_one_tailed"])
            holm_g = format_p(r["holm_corrected_p_global"])
            holm_h = format_p(r["holm_corrected_p_per_hypothesis"])
            
            # Determine significance marker
            if r["significant_holm_global"]:
                sig = "✅ global"
            elif r["significant_holm_per_hypothesis"]:
                sig = "✅ per-H"
            elif r["significant_at_005"]:
                sig = "⚠️ raw only"
            else:
                sig = "❌"
            
            lines.append(f"| {ai_label} | {h} | {metric_short} | {direction} | {med_delta} | {r_str} ({r_label}) | {ci} | {raw_p} | {holm_g} | {holm_h} | {sig} |")
    
    lines.append("")
    lines.append("*Effect size r: rank-biserial correlation. |r| < 0.1 negligible, 0.1–0.3 small, 0.3–0.5 medium, > 0.5 large.*")
    lines.append("*Bootstrap 95% CI: percentile bootstrap (B=10000) for median Δ.*")
    lines.append("*Holm p (global): corrected across all 36 tests. Holm p (per-H): corrected within each hypothesis (9 tests).*")
    lines.append("*Sig: ✅ global = significant after global Holm; ✅ per-H = significant after per-hypothesis Holm; ⚠️ raw only = significant uncorrected only; ❌ = not significant.*")
    lines.append("")
    
    # ── Per-hypothesis summary ──
    lines.append("## Per-Hypothesis Summary")
    lines.append("")
    for h_name in ["H1", "H2", "H3", "H4"]:
        h_results = [r for r in test_results if r["hypothesis"] == h_name]
        raw = sum(1 for r in h_results if r["significant_at_005"])
        holm_g = sum(1 for r in h_results if r["significant_holm_global"])
        holm_h = sum(1 for r in h_results if r["significant_holm_per_hypothesis"])
        
        lines.append(f"### {h_name}: {HYPOTHESES[h_name]['desc']}")
        lines.append("")
        lines.append(f"- Raw significant: **{raw}/9**")
        lines.append(f"- Holm-corrected (global): **{holm_g}/9**")
        lines.append(f"- Holm-corrected (per-hypothesis): **{holm_h}/9**")
        
        # List the ones that survive
        surviving_global = [r for r in h_results if r["significant_holm_global"]]
        surviving_per_h = [r for r in h_results if r["significant_holm_per_hypothesis"] and not r["significant_holm_global"]]
        
        if surviving_global:
            conds = ", ".join(f"{SHORT_LABELS.get(r['ai_condition'], r['ai_condition'])} (p={format_p(r['holm_corrected_p_global'])}, r={format_r(r['rank_biserial_r'])})" for r in surviving_global)
            lines.append(f"  - Survive global Holm: {conds}")
        if surviving_per_h:
            conds = ", ".join(f"{SHORT_LABELS.get(r['ai_condition'], r['ai_condition'])} (p={format_p(r['holm_corrected_p_per_hypothesis'])}, r={format_r(r['rank_biserial_r'])})" for r in surviving_per_h)
            lines.append(f"  - Survive per-H Holm only: {conds}")
        
        # Lost to correction
        lost = [r for r in h_results if r["significant_at_005"] and not r["significant_holm_per_hypothesis"]]
        if lost:
            conds = ", ".join(f"{SHORT_LABELS.get(r['ai_condition'], r['ai_condition'])} (raw p={format_p(r['wilcoxon_p_one_tailed'])})" for r in lost)
            lines.append(f"  - Lost to per-H correction: {conds}")
        
        lines.append("")
    
    # ── Effect size distribution ──
    lines.append("## Effect Size Distribution")
    lines.append("")
    lines.append("| Category | Count | Conditions |")
    lines.append("|---|---|---|")
    
    for threshold, label in [(0.5, "Large (|r| ≥ 0.5)"), (0.3, "Medium (0.3 ≤ |r| < 0.5)"), 
                              (0.1, "Small (0.1 ≤ |r| < 0.3)"), (0.0, "Negligible (|r| < 0.1)")]:
        upper = 1.0 if threshold == 0.5 else (0.5 if threshold == 0.3 else (0.3 if threshold == 0.1 else 0.1))
        matches = [r for r in test_results if threshold <= abs(r["rank_biserial_r"]) < upper or (threshold == 0.5 and abs(r["rank_biserial_r"]) >= 0.5)]
        if matches:
            conds = ", ".join(f"{r['hypothesis']}/{SHORT_LABELS.get(r['ai_condition'], r['ai_condition'])}" for r in matches)
            lines.append(f"| {label} | {len(matches)} | {conds} |")
    
    lines.append("")
    
    # ── Limitations update ──
    lines.append("## Updated Limitations Text")
    lines.append("")
    lines.append("For proposal §6 Limitations, replace the current multiplicity note with:")
    lines.append("")
    lines.append("> Fourth, the study applies Holm-Bonferroni correction to address multiplicity across "
                 "36 hypothesis-condition tests (4 hypotheses × 9 AI conditions). After correction, "
                 f"{holm_global_sig} of {len(test_results)} tests remain significant at α = 0.05 "
                 f"(compared to {raw_sig} uncorrected). The expected number of false positives "
                 f"under the null is {len(test_results) * 0.05:.1f}. Effect sizes (rank-biserial r) "
                 "are reported alongside all test results to enable readers to judge practical significance "
                 "independently of multiplicity correction.")
    lines.append("")
    
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"✓ Wrote {REPORT_PATH}")
    return lines


def update_proposal(test_results):
    """Update proposal_v1.md Table 2, §4.2 Summary, and Limitations."""
    with open(PROPOSAL_PATH) as f:
        content = f.read()
    
    # ── Build new Table 2 ──
    new_table_lines = []
    new_table_lines.append("| AI Condition | H1 (Sent. Var.) | H2 (Para. Var.) | H3 (TTR) | H4 (Conj. Freq.) |")
    new_table_lines.append("|--------------|-----------------|-----------------|----------|-------------------|")
    
    # Sort conditions to match original table order
    table_order = ["gpt35", "MiMo-V2.5-Pro", "DeepSeek-V4-Flash", "MiniMax-M3",
                   "Muse-Spark-1.2-Contributor", "Gemini-3.6-Flash", "Kimi-K3",
                   "GPT-5.6-Luna", "Claude-Sonnet-5-High"]
    
    by_ai = {}
    for r in test_results:
        by_ai.setdefault(r["ai_condition"], []).append(r)
    
    for ai_cond in table_order:
        if ai_cond not in by_ai:
            continue
        ai_label = SHORT_LABELS.get(ai_cond, ai_cond)
        n = by_ai[ai_cond][0]["n_pairs"]
        
        row = f"| {ai_label} (n={n}) "
        for h_name in ["H1", "H2", "H3", "H4"]:
            r = next(x for x in by_ai[ai_cond] if x["hypothesis"] == h_name)
            raw_p = r["wilcoxon_p_one_tailed"]
            holm_p = r["holm_corrected_p_per_hypothesis"]
            rb_r = r["rank_biserial_r"]
            
            if r["significant_holm_per_hypothesis"]:
                p_str = format_p(raw_p)
                row += f"| Supported (p={p_str}, r={format_r(rb_r)}, Holm-corrected) "
            elif r["significant_at_005"]:
                p_str = format_p(raw_p)
                holm_str = format_p(holm_p)
                row += f"| Not supported (p={p_str}, Holm p={holm_str}, r={format_r(rb_r)}) "
            else:
                p_str = format_p(raw_p)
                row += f"| Not supported (p={p_str}, r={format_r(rb_r)}) "
        new_table_lines.append(row + "|")
    
    new_table = "\n".join(new_table_lines)
    
    # Replace old Table 2 in proposal
    # Find the table between the Table 2 header and the footnote
    old_table_pattern = r'(\| AI Condition \| H1 \(Sent\. Var\.\) \| H2 \(Para\. Var\.\) \| H3 \(TTR\) \| H4 \(Conj\. Freq\. \|\n\|[-|]+\n(?:\|.*\n)+)\*Table 2\. Hypothesis test results.*?\*'
    
    # Use a more targeted approach: find the old table and replace it
    table_start_marker = "| AI Condition | H1 (Sent. Var.) | H2 (Para. Var.) | H3 (TTR) | H4 (Conj. Freq.) |"
    table_footnote_marker = "*Table 2. Hypothesis test results"
    
    start_idx = content.find(table_start_marker)
    footnote_idx = content.find(table_footnote_marker, start_idx)
    
    if start_idx >= 0 and footnote_idx >= 0:
        # Find end of footnote line
        end_of_footnote = content.find("\n", footnote_idx)
        if end_of_footnote == -1:
            end_of_footnote = len(content)
        else:
            end_of_footnote += 1  # include the newline
        
        new_table_section = new_table + "\n\n"
        new_table_section += "*Table 2. Hypothesis test results across all 9 analyzed AI conditions. "
        new_table_section += "Wilcoxon signed-rank test, one-tailed. Effect size r = rank-biserial correlation "
        new_table_section += "(|r| < 0.1 negligible, 0.1–0.3 small, 0.3–0.5 medium, > 0.5 large). "
        new_table_section += '"Supported" indicates p < 0.05 after per-hypothesis Holm-Bonferroni correction (9 tests per hypothesis). '
        new_table_section += '"Not supported (Holm p=...)" indicates raw p < 0.05 but significance lost after correction.*'
        
        content = content[:start_idx] + new_table_section + content[end_of_footnote:]
        print("✓ Updated Table 2 in proposal")
    else:
        print("⚠ Could not find Table 2 markers in proposal")
    
    # ── Build new §4.2 Summary ──
    raw_sig = sum(1 for r in test_results if r["significant_at_005"])
    holm_global_sig = sum(1 for r in test_results if r["significant_holm_global"])
    holm_per_h_sig = sum(1 for r in test_results if r["significant_holm_per_hypothesis"])
    
    # Count per-hypothesis after correction
    h4_per_h = sum(1 for r in test_results if r["hypothesis"] == "H4" and r["significant_holm_per_hypothesis"])
    h3_per_h = sum(1 for r in test_results if r["hypothesis"] == "H3" and r["significant_holm_per_hypothesis"])
    h2_per_h = sum(1 for r in test_results if r["hypothesis"] == "H2" and r["significant_holm_per_hypothesis"])
    h1_per_h = sum(1 for r in test_results if r["hypothesis"] == "H1" and r["significant_holm_per_hypothesis"])
    
    h4_raw = sum(1 for r in test_results if r["hypothesis"] == "H4" and r["significant_at_005"])
    h3_raw = sum(1 for r in test_results if r["hypothesis"] == "H3" and r["significant_at_005"])
    
    # Get H4 effect sizes for surviving conditions
    h4_surviving = [r for r in test_results if r["hypothesis"] == "H4" and r["significant_holm_per_hypothesis"]]
    h4_lost = [r for r in test_results if r["hypothesis"] == "H4" and r["significant_at_005"] and not r["significant_holm_per_hypothesis"]]
    
    new_summary = f"""**Summary.** Of 36 hypothesis-condition combinations (4 hypotheses times 9 conditions), {raw_sig} were statistically significant at alpha=0.05 before multiplicity correction, and {holm_per_h_sig} remain significant after per-hypothesis Holm-Bonferroni correction (expected false positives under the null: 1.8). After global correction across all 36 tests, {holm_global_sig} tests remain significant.

**H4 (conjunction frequency)** remains the most robust finding after correction. {h4_per_h} of 9 conditions support H4 after per-hypothesis Holm correction (down from {h4_raw} uncorrected)"""
    
    if h4_lost:
        lost_conds = ", ".join(SHORT_LABELS.get(r['ai_condition'], r['ai_condition']) for r in h4_lost)
        new_summary += f"; {lost_conds} lost significance after correction"
    
    surviving_h4 = [r for r in test_results if r["hypothesis"] == "H4" and r["significant_holm_per_hypothesis"]]
    if surviving_h4:
        conds_list = []
        for r in surviving_h4:
            label = SHORT_LABELS.get(r["ai_condition"], r["ai_condition"])
            conds_list.append(f"{label} (p={format_p(r['wilcoxon_p_one_tailed'])}, r={format_r(r['rank_biserial_r'])})")
        new_summary += ". Surviving conditions: " + ", ".join(conds_list)
    
    new_summary += ". Effect sizes range from small to medium (rank-biserial r = "
    h4_r_vals = [abs(r["rank_biserial_r"]) for r in test_results if r["hypothesis"] == "H4" and r["significant_holm_per_hypothesis"]]
    if h4_r_vals:
        new_summary += f"{min(h4_r_vals):.2f}–{max(h4_r_vals):.2f}). "
    else:
        new_summary += "N/A). "
    
    new_summary += f"H3 (TTR) is supported in {h3_per_h} of 9 conditions after correction (down from {h3_raw} uncorrected). "
    new_summary += f"H2 is supported in {h2_per_h} conditions, and H1 in {h1_per_h}."
    
    # Replace old §4.2 Summary
    old_summary_start = "**Summary.** Of 36 hypothesis-condition"
    summary_end_marker = "### 4.3 Random Forest"
    
    start_idx = content.find(old_summary_start)
    end_idx = content.find(summary_end_marker, start_idx)
    
    if start_idx >= 0 and end_idx >= 0:
        content = content[:start_idx] + new_summary + "\n\n" + content[end_idx:]
        print("✓ Updated §4.2 Summary in proposal")
    else:
        print("⚠ Could not find §4.2 Summary markers in proposal")
    
    # ── Update Limitations ──
    old_limitation = "the study uses population variance for within-text metrics and does not apply Bonferroni correction for multi-AI comparisons"
    new_limitation = (f"the study applies Holm-Bonferroni correction to address multiplicity across "
                     f"36 hypothesis-condition tests (4 hypotheses × 9 AI conditions); after correction, "
                     f"{holm_per_h_sig} of 36 tests remain significant at α = 0.05 "
                     f"(compared to {raw_sig} uncorrected, expected false positives: 1.8). "
                     f"Effect sizes (rank-biserial r) are reported alongside all test results")
    
    if old_limitation in content:
        content = content.replace(old_limitation, new_limitation)
        print("✓ Updated Limitations in proposal")
    else:
        print("⚠ Could not find Limitations marker in proposal")
    
    # ── Update Abstract ──
    old_abstract_h4 = "Conjunction frequency is the most robust discriminator, supported in 7 of 9 analyzed conditions."
    new_abstract_h4 = (f"Conjunction frequency is the most robust discriminator, supported in {h4_per_h} of 9 analyzed conditions "
                      f"after Holm-Bonferroni correction for multiplicity.")
    
    if old_abstract_h4 in content:
        content = content.replace(old_abstract_h4, new_abstract_h4)
        print("✓ Updated Abstract in proposal")
    
    with open(PROPOSAL_PATH, "w") as f:
        f.write(content)
    print(f"✓ Updated {PROPOSAL_PATH}")


def print_summary(test_results):
    """Print console summary."""
    print()
    print("=" * 70)
    print("HOLM-BONFERRONI CORRECTION RESULTS")
    print("=" * 70)
    print()
    
    raw_sig = sum(1 for r in test_results if r["significant_at_005"])
    holm_global_sig = sum(1 for r in test_results if r["significant_holm_global"])
    holm_per_h_sig = sum(1 for r in test_results if r["significant_holm_per_hypothesis"])
    
    print(f"Total tests: {len(test_results)}")
    print(f"Raw significant (p < 0.05): {raw_sig}")
    print(f"Holm-corrected significant (global, 36 tests): {holm_global_sig}")
    print(f"Holm-corrected significant (per-hypothesis, 9 tests each): {holm_per_h_sig}")
    print(f"Expected false positives (uncorrected): {len(test_results) * 0.05:.1f}")
    print()
    
    # Per hypothesis
    for h_name in ["H1", "H2", "H3", "H4"]:
        h_results = [r for r in test_results if r["hypothesis"] == h_name]
        raw = sum(1 for r in h_results if r["significant_at_005"])
        holm_h = sum(1 for r in h_results if r["significant_holm_per_hypothesis"])
        print(f"{h_name}: raw {raw}/9 → per-H Holm {holm_h}/9")
    
    print()
    
    # Lost tests
    lost = [r for r in test_results if r["significant_at_005"] and not r["significant_holm_per_hypothesis"]]
    if lost:
        print(f"Tests lost to per-hypothesis Holm correction ({len(lost)}):")
        for r in lost:
            label = SHORT_LABELS.get(r["ai_condition"], r["ai_condition"])
            print(f"  {r['hypothesis']}/{label}: raw p={format_p(r['wilcoxon_p_one_tailed'])}, "
                  f"Holm p={format_p(r['holm_corrected_p_per_hypothesis'])}, r={format_r(r['rank_biserial_r'])}")
    print()
    
    # Surviving tests
    surviving = [r for r in test_results if r["significant_holm_per_hypothesis"]]
    print(f"Tests surviving per-hypothesis Holm correction ({len(surviving)}):")
    for r in surviving:
        label = SHORT_LABELS.get(r["ai_condition"], r["ai_condition"])
        print(f"  {r['hypothesis']}/{label}: raw p={format_p(r['wilcoxon_p_one_tailed'])}, "
              f"Holm p={format_p(r['holm_corrected_p_per_hypothesis'])}, r={format_r(r['rank_biserial_r'])} "
              f"({effect_size_label(r['rank_biserial_r'])})")


def main():
    print("=" * 60)
    print("RAY-425: Holm-Bonferroni Correction + Effect Sizes")
    print("=" * 60)
    print()
    
    # 1. Load data
    print("Loading metrics...")
    data = load_metrics()
    df = build_dataframe(data)
    print(f"  → {len(df)} observations ({len(data)} prompts)")
    print()
    
    # 2. Run all tests with corrections
    print("Running 36 hypothesis tests with effect sizes & bootstrap CIs...")
    test_results = run_all_tests(df)
    print(f"  → {len(test_results)} tests completed")
    print()
    
    # 3. Apply Holm-Bonferroni (already done in run_all_tests)
    print("Holm-Bonferroni correction applied (global + per-hypothesis)")
    print()
    
    # 4. Print summary
    print_summary(test_results)
    
    # 5. Update results_v1.json
    print("Updating results_v1.json...")
    update_results_json(test_results)
    
    # 6. Generate standalone report
    print("Generating standalone report...")
    generate_report(test_results)
    
    # 7. Update proposal
    print("Updating proposal_v1.md...")
    update_proposal(test_results)
    
    print()
    print("Done! All deliverables updated.")


if __name__ == "__main__":
    main()
