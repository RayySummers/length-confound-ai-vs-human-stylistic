#!/usr/bin/env python3
"""paired t-test vs Wilcoxon signed-rank on the same 36 paired tests.

Reads data/processed/results_v1.json (per_sample_metrics), recomputes paired
differences (AI - Human) per prompt, and runs both tests one-tailed in the
pre-registered direction. Holm-Bonferroni step-down applied per hypothesis
family (9 tests each), mirroring analysis/holm_bonferroni_correction.py.
"""
import json
from collections import defaultdict
import numpy as np
from scipy import stats

RES = "data/processed/results_v1.json"
OUT = "analysis/ttest_vs_wilcoxon_results.json"

HYP = {
    "H1": ("sentence_length_var", "less"),
    "H2": ("paragraph_length_var", "less"),
    "H3": ("ttr", "less"),
    "H4": ("conj_freq", "greater"),
}


def holm(pvals, alpha=0.05):
    """Step-down Holm. Returns (adjusted_p, rejected) in ORIGINAL order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    rejected = [False] * m
    running_max = 0.0
    still_rejecting = True
    for k, i in enumerate(order, start=1):
        factor = m - k + 1
        val = min(1.0, pvals[i] * factor)
        running_max = max(running_max, val)
        adj[i] = running_max
        if still_rejecting and pvals[i] <= alpha / factor:
            rejected[i] = True
        else:
            still_rejecting = False
    return adj, rejected


def main():
    d = json.load(open(RES))
    psm = d["per_sample_metrics"]
    conditions = [c for c in d["metadata"]["conditions"] if c != "human"]

    # prompt_id -> condition -> metrics
    by_prompt = defaultdict(dict)
    for rec in psm:
        by_prompt[rec["prompt_id"]][rec["condition"]] = rec["metrics"]

    rows = []
    for hyp, (metric, direction) in HYP.items():
        fam_w, fam_t = [], []
        start = len(rows)
        for cond in conditions:
            ai_vals, hum_vals = [], []
            for pid, m in sorted(by_prompt.items()):
                if "human" in m and cond in m:
                    ai_vals.append(m[cond][metric])
                    hum_vals.append(m["human"][metric])
            ai_vals = np.array(ai_vals, dtype=float)
            hum_vals = np.array(hum_vals, dtype=float)
            deltas = ai_vals - hum_vals
            n = len(deltas)
            alt = "less" if direction == "less" else "greater"
            w_stat, w_p = stats.wilcoxon(deltas, alternative=alt)
            t_stat, t_p = stats.ttest_rel(ai_vals, hum_vals, alternative=alt)
            # Cohen's dz for paired design
            dz = float(np.mean(deltas) / np.std(deltas, ddof=1)) if np.std(deltas, ddof=1) > 0 else float("nan")
            fam_w.append(w_p)
            fam_t.append(t_p)
            rows.append({
                "hypothesis": hyp, "metric": metric, "condition": cond, "n_pairs": n,
                "direction": direction, "mean_delta": float(np.mean(deltas)),
                "median_delta": float(np.median(deltas)),
                "wilcoxon_stat": float(w_stat), "wilcoxon_p": float(w_p),
                "ttest_stat": float(t_stat), "ttest_p": float(t_p),
                "cohens_dz": dz,
            })
        adj_w, rej_w = holm(fam_w)
        adj_t, rej_t = holm(fam_t)
        for r, aw, rw, at, rt in zip(rows[start:], adj_w, rej_w, adj_t, rej_t):
            r["wilcoxon_p_holm"] = float(aw)
            r["wilcoxon_sig_holm"] = bool(rw)
            r["ttest_p_holm"] = float(at)
            r["ttest_sig_holm"] = bool(rt)

    # ---- summary ----
    agree_holm = sum(1 for r in rows if r["wilcoxon_sig_holm"] == r["ttest_sig_holm"])
    agree_raw = sum(1 for r in rows if (r["wilcoxon_p"] < 0.05) == (r["ttest_p"] < 0.05))
    w_only = [r for r in rows if r["wilcoxon_sig_holm"] and not r["ttest_sig_holm"]]
    t_only = [r for r in rows if r["ttest_sig_holm"] and not r["wilcoxon_sig_holm"]]

    summary = {
        "n_tests": len(rows),
        "agreement_holm": f"{agree_holm}/{len(rows)}",
        "agreement_raw_005": f"{agree_raw}/{len(rows)}",
        "wilcoxon_sig_holm": sum(1 for r in rows if r["wilcoxon_sig_holm"]),
        "ttest_sig_holm": sum(1 for r in rows if r["ttest_sig_holm"]),
        "wilcoxon_only": [(r["hypothesis"], r["condition"]) for r in w_only],
        "ttest_only": [(r["hypothesis"], r["condition"]) for r in t_only],
    }

    json.dump({"summary": summary, "rows": rows}, open(OUT, "w"), indent=2)

    print("=" * 78)
    print(f"n tests: {summary['n_tests']}   (4 hypotheses x 9 conditions, Holm per family)")
    print(f"Holm-corrected significant:  Wilcoxon {summary['wilcoxon_sig_holm']}/36   "
          f"paired t {summary['ttest_sig_holm']}/36")
    print(f"agreement after Holm: {summary['agreement_holm']}    "
          f"agreement at raw p<.05: {summary['agreement_raw_005']}")
    if w_only:
        print(f"  significant ONLY under Wilcoxon: {w_only}")
    if t_only:
        print(f"  significant ONLY under t-test  : {t_only}")
    print("=" * 78)
    print(f"{'Hyp':<4}{'Condition':<32}{'meanD':>10}{'W p':>10}{'t p':>10}"
          f"{'W holm':>9}{'t holm':>9}  agree")
    for r in rows:
        flag = "OK" if r["wilcoxon_sig_holm"] == r["ttest_sig_holm"] else "**DIFF**"
        print(f"{r['hypothesis']:<4}{r['condition']:<32}{r['mean_delta']:>10.4f}"
              f"{r['wilcoxon_p']:>10.4f}{r['ttest_p']:>10.4f}"
              f"{r['wilcoxon_p_holm']:>9.4f}{r['ttest_p_holm']:>9.4f}  {flag}")


if __name__ == "__main__":
    main()
