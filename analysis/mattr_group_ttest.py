#!/usr/bin/env python3
"""MATTR 组间对比分析 —— 按王雅琴老师 2026-09-21 组会指定的方案。

老师指定的口径：
  1. MATTR 窗口统一取 100（不再跨窗口比较、不筛最优窗口）
  2. 把同一模型的全部样本作为一组、人类文本作为一组，做整体组间对比
     （禁止单样本逐个配对对比）
  3. 优先独立样本 t 检验；不满足正态假设时用 Wilcoxon 非参数检验（秩和）
  4. 必须同时汇报 P 值 + 效应量
  5. 补充比较 AI 组与人类组的组内方差（验证 AI 文本的同质性）

输出：analysis/mattr_group_ttest_results.json
"""
import json
import numpy as np
from scipy import stats
from lexical_diversity import lex_div

SAMPLE = "data/processed/sample_v1.json"
OUT = "analysis/mattr_group_ttest_results.json"
WINDOW = 100  # 老师指定

CONDITIONS = [
    ("human", "Human"),
    ("gpt35", "GPT-3.5"),
    ("MiMo-V2.5-Pro", "MiMo-V2.5-Pro"),
    ("DeepSeek-V4-Flash", "DeepSeek-V4-Flash"),
    ("MiniMax-M3", "MiniMax-M3"),
    ("Muse-Spark-1.2-Contributor", "Muse-Spark-1.2-Contributor"),
    ("GPT-5.6-Luna", "GPT-5.6-Luna"),
    ("Claude-Sonnet-5-High", "Claude-Sonnet-5-High"),
    ("Gemini-3.6-Flash", "Gemini-3.6-Flash"),
    ("Kimi-K3", "Kimi-K3"),
]


def mattr(tokens, window=WINDOW):
    """滑动窗口平均 TTR。窗口大于文本长度时返回 None。"""
    n = len(tokens)
    if n < window:
        return None
    vals = []
    for i in range(n - window + 1):
        seg = tokens[i:i + window]
        vals.append(len(set(seg)) / window)
    return float(np.mean(vals))


def cohens_d(a, b):
    """独立样本 Cohen's d（合并标准差）。"""
    na, nb = len(a), len(b)
    sd_pooled = np.sqrt(((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2))
    return float((np.mean(a) - np.mean(b)) / sd_pooled) if sd_pooled > 0 else float("nan")


def main():
    sample = json.load(open(SAMPLE))
    groups = {lab: [] for _, lab in CONDITIONS}

    for s in sample["samples"]:
        for fk, lab in CONDITIONS:
            st = s.get(f"{fk}_story")
            if not st or len(st.strip()) < 100:
                continue
            m = mattr(lex_div.tokenize(st))
            if m is not None:
                groups[lab].append(m)

    human = np.array(groups["Human"], dtype=float)
    rows = []
    for _, lab in CONDITIONS:
        if lab == "Human":
            continue
        ai = np.array(groups[lab], dtype=float)
        # 独立样本 t 检验（Welch，不假设方差齐）
        t_stat, t_p = stats.ttest_ind(ai, human, equal_var=False)
        # 非参数替代：Wilcoxon 秩和检验（= Mann-Whitney U）
        u_stat, u_p = stats.mannwhitneyu(ai, human, alternative="two-sided")
        d = cohens_d(ai, human)
        # 组内方差比较
        lev_stat, lev_p = stats.levene(ai, human, center="median")
        rows.append({
            "condition": lab,
            "n_ai": len(ai), "n_human": len(human),
            "ai_mean": float(np.mean(ai)), "ai_sd": float(np.std(ai, ddof=1)),
            "human_mean": float(np.mean(human)), "human_sd": float(np.std(human, ddof=1)),
            "mean_diff": float(np.mean(ai) - np.mean(human)),
            "welch_t": float(t_stat), "ttest_p": float(t_p),
            "mannwhitney_u": float(u_stat), "wilcoxon_ranksum_p": float(u_p),
            "cohens_d": d,
            "variance_ratio_ai_over_human": float(np.var(ai, ddof=1) / np.var(human, ddof=1)),
            "levene_stat": float(lev_stat), "levene_p": float(lev_p),
            "ttest_sig_005": bool(t_p < 0.05),
            "nonparam_sig_005": bool(u_p < 0.05),
        })

    n_sig_t = sum(1 for r in rows if r["ttest_sig_005"])
    n_sig_u = sum(1 for r in rows if r["nonparam_sig_005"])
    agree = sum(1 for r in rows if r["ttest_sig_005"] == r["nonparam_sig_005"])

    summary = {
        "window": WINDOW,
        "design": "independent samples, model group (n) vs human group (n), two-tailed",
        "n_conditions": len(rows),
        "human_mean": float(np.mean(human)),
        "human_sd": float(np.std(human, ddof=1)),
        "human_variance": float(np.var(human, ddof=1)),
        "ttest_significant": f"{n_sig_t}/{len(rows)}",
        "nonparam_significant": f"{n_sig_u}/{len(rows)}",
        "method_agreement": f"{agree}/{len(rows)}",
    }
    json.dump({"summary": summary, "rows": rows}, open(OUT, "w"), indent=2)

    print("=" * 100)
    print(f"MATTR 窗口 = {WINDOW}   设计：独立样本组间对比（模型组 vs 人类组），双尾")
    print(f"人类组：n={len(human)}  M={summary['human_mean']:.4f}  SD={summary['human_sd']:.4f}")
    print(f"独立样本 t 检验显著：{summary['ttest_significant']}   "
          f"Wilcoxon 秩和显著：{summary['nonparam_significant']}   "
          f"两法一致：{summary['method_agreement']}")
    print("=" * 100)
    hdr = (f"{'模型':<30}{'M(AI)':>9}{'SD(AI)':>8}{'ΔM':>9}{'t':>8}{'p':>9}{'d':>7}"
           f"{'U-p':>9}{'Var比':>7}{'Levene-p':>10}")
    print(hdr)
    for r in rows:
        print(f"{r['condition']:<30}{r['ai_mean']:>9.4f}{r['ai_sd']:>8.4f}{r['mean_diff']:>+9.4f}"
              f"{r['welch_t']:>8.2f}{r['ttest_p']:>9.4f}{r['cohens_d']:>7.2f}"
              f"{r['wilcoxon_ranksum_p']:>9.4f}{r['variance_ratio_ai_over_human']:>7.2f}"
              f"{r['levene_p']:>10.4f}")
    print("=" * 100)
    print("注：ΔM 为正 = AI 组词汇多样性高于人类组；Var比 < 1 = AI 组内部更同质")
    n_levene_sig = sum(1 for r in rows if r["levene_p"] < 0.05)
    print(f"Levene 方差齐性检验显著（p<0.05）的模型数：{n_levene_sig}/{len(rows)}")
    print(f"Var比 < 1（AI 内部方差更小）的模型数：{sum(1 for r in rows if r['variance_ratio_ai_over_human'] < 1)}/{len(rows)}")


if __name__ == "__main__":
    main()
