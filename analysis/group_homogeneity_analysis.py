#!/usr/bin/env python3
"""全指标组间对比 + AI 同质性分析 —— 按王雅琴老师 2026-09-21 组会要求。

老师的两条要求：
  A. 独立样本 t 检验：AI 组（某模型 30 个文本）vs 人类组（30 个文本），
     同时汇报 P 值 + 效应量（不用做多重比较校正）。
  B. 同质性：逐指标看「AI 组内部方差是否比人类组小」，并做方差齐性检验。
     ⚠️ 老师明确：同一个 AI 内部 30 个文本自己比，不要拿 AI 跟别的 AI 比。

覆盖 8 个既有指标 + MATTR(窗口 100)。

输出：analysis/group_homogeneity_results.json
"""
import json
import numpy as np
from scipy import stats
from lexical_diversity import lex_div

SAMPLE = "data/processed/sample_v1.json"
RES = "data/processed/results_v1.json"
OUT = "analysis/group_homogeneity_results.json"
MATTR_WINDOW = 100

METRICS = [
    ("mattr_w100", "MATTR (window 100)"),
    ("word_length", "Word Length"),
    ("sentence_length", "Sentence Length"),
    ("sentence_length_var", "Sentence Length Variance"),
    ("ttr", "Type-Token Ratio"),
    ("mtld", "MTLD"),
    ("conj_freq", "Conjunction Frequency"),
    ("paragraph_length", "Paragraph Length"),
    ("paragraph_length_var", "Paragraph Length Variance"),
]

CONDITIONS = [
    ("gpt35", "GPT-3.5"),
    ("MiMo-V2.5-Pro", "MiMo-V2.5-Pro"),
    ("DeepSeek-V4-Flash", "DeepSeek-V4-Flash"),
    ("MiniMax-M3", "MiniMax-M3"),
    ("Muse-Spark-1.2-Contributor", "Muse-Spark-1.2"),
    ("GPT-5.6-Luna", "GPT-5.6-Luna"),
    ("Claude-Sonnet-5-High", "Claude-Sonnet-5-High"),
    ("Gemini-3.6-Flash", "Gemini-3.6-Flash"),
    ("Kimi-K3", "Kimi-K3"),
]


def mattr(tokens, window=MATTR_WINDOW):
    n = len(tokens)
    if n < window:
        return None
    return float(np.mean([len(set(tokens[i:i + window])) / window for i in range(n - window + 1)]))


def cohens_d(a, b):
    na, nb = len(a), len(b)
    sd = np.sqrt(((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2))
    return float((np.mean(a) - np.mean(b)) / sd) if sd > 0 else float("nan")


def main():
    sample = json.load(open(SAMPLE))
    res = json.load(open(RES))

    # MATTR(w100) 现算；其余 8 个指标直接取 results_v1.json 的 per_sample_metrics
    vals = {lab: {m: {} for m, _ in METRICS} for _, lab in CONDITIONS}
    vals["Human"] = {m: {} for m, _ in METRICS}

    for s in sample["samples"]:
        pid = s.get("prompt_id")
        # 模型组 + 人类组都要算（人类组漏算会让 MATTR 那一行整体缺席）
        for fk, lab in [("human", "Human")] + list(CONDITIONS):
            st = s.get(f"{fk}_story")
            if st and len(st.strip()) >= 100:
                m = mattr(lex_div.tokenize(st))
                if m is not None:
                    vals[lab]["mattr_w100"][pid] = m

    for rec in res["per_sample_metrics"]:
        pid, cond = rec["prompt_id"], rec["condition"]
        lab = "Human" if cond == "human" else dict(CONDITIONS).get(cond)
        if lab is None or lab not in vals:
            continue
        for mk, _ in METRICS:
            if mk == "mattr_w100":
                continue
            if mk in rec["metrics"]:
                vals[lab][mk][pid] = rec["metrics"][mk]

    rows = []
    for mk, label in METRICS:
        for _, lab in CONDITIONS:
            a = np.array(list(vals[lab][mk].values()), float)
            h = np.array(list(vals["Human"][mk].values()), float)
            if len(a) < 3 or len(h) < 3:
                continue
            t, tp = stats.ttest_ind(a, h, equal_var=False)
            u, up = stats.mannwhitneyu(a, h, alternative="two-sided")
            lv, lvp = stats.levene(a, h, center="median")
            rows.append({
                "metric": mk, "metric_label": label, "condition": lab,
                "n_ai": len(a), "n_human": len(h),
                "ai_mean": float(np.mean(a)), "human_mean": float(np.mean(h)),
                "ai_var": float(np.var(a, ddof=1)), "human_var": float(np.var(h, ddof=1)),
                "var_ratio": float(np.var(a, ddof=1) / np.var(h, ddof=1)),
                "ttest_t": float(t), "ttest_p": float(tp),
                "ranksum_p": float(up), "cohens_d": cohens_d(a, h),
                "levene_p": float(lvp),
                "ttest_sig": bool(tp < 0.05),
                "levene_sig": bool(lvp < 0.05),
            })

    # 按指标汇总
    by_metric = {}
    for mk, label in METRICS:
        sub = [r for r in rows if r["metric"] == mk]
        if not sub:
            continue
        by_metric[mk] = {
            "label": label,
            "n_models": len(sub),
            "mean_diff_sig": f"{sum(1 for r in sub if r['ttest_sig'])}/{len(sub)}",
            "var_ratio_lt_1": f"{sum(1 for r in sub if r['var_ratio'] < 1)}/{len(sub)}",
            "levene_sig": f"{sum(1 for r in sub if r['levene_sig'])}/{len(sub)}",
            "median_var_ratio": float(np.median([r["var_ratio"] for r in sub])),
            "median_cohens_d": float(np.median([r["cohens_d"] for r in sub])),
        }

    summary = {
        "design": "independent samples, model group vs human group, two-tailed, no correction (per advisor)",
        "mattr_window": MATTR_WINDOW,
        "n_rows": len(rows),
        "by_metric": by_metric,
    }
    json.dump({"summary": summary, "rows": rows}, open(OUT, "w"), indent=2)

    print("=" * 108)
    print("全指标组间对比（独立样本 Welch t 检验，双尾，未校正）+ AI 组内同质性")
    print("=" * 108)
    print(f"{'指标':<32}{'均值差异显著':>14}{'AI方差更小':>13}{'方差齐性显著':>14}"
          f"{'中位方差比':>12}{'中位d':>9}")
    for mk, _ in METRICS:
        b = by_metric.get(mk)
        if not b:
            continue
        print(f"{b['label']:<32}{b['mean_diff_sig']:>14}{b['var_ratio_lt_1']:>13}"
              f"{b['levene_sig']:>14}{b['median_var_ratio']:>12.2f}{b['median_cohens_d']:>9.2f}")
    print("=" * 108)
    print("注：AI方差更小 一列的分母是该指标下模型数（9）；中位方差比 < 1 表示 AI 组内部更同质")


if __name__ == "__main__":
    main()
