#!/usr/bin/env python3
"""
mattr_vs_mtld.py — 用 MATTR 跑和 MTLD 的对比

目的：王雅琴老师 9/14 组会建议用 MATTR（Moving-Average TTR）替代/补充 MTLD。
本脚本用与 mtld_reference_results.json 相同的口径（lexical_diversity 库）
计算 MATTR，并与 MTLD 对比三件事：

  1. 各条件的组间均值/标准差（可否区分 AI vs Human）
  2. 与文本长度（词数）的相关性 —— 看长度混淆（length confound）有多强
  3. 长度残差化后，组间差异是否还活着

输入：data/processed/sample_v1.json
输出：analysis/mattr_vs_mtld_results.json
"""
import json
import statistics
from pathlib import Path
from scipy import stats
import numpy as np

from lexical_diversity import lex_div

BASE = Path(__file__).parent.parent
SAMPLE = BASE / "data" / "processed" / "sample_v1.json"
OUT = Path(__file__).parent / "mattr_vs_mtld_results.json"

CONDITION_FIELDS = [
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

MATTR_WINDOW = 50   # 常用默认


def main():
    with open(SAMPLE) as f:
        sample = json.load(f)

    records = []  # 每条 = 一个 (prompt, condition) 观测

    for s in sample["samples"]:
        pid = s["prompt_id"]
        for field_key, label in CONDITION_FIELDS:
            story = s.get(f"{field_key}_story")
            if not story or len(story.strip()) < 100:
                continue
            toks = lex_div.tokenize(story)
            n = len(toks)
            if n < MATTR_WINDOW * 2:
                continue
            try:
                m_mattr = lex_div.mattr(toks, MATTR_WINDOW)
            except Exception as e:
                m_mattr = None
            try:
                m_mtld = lex_div.mtld(toks)
            except Exception as e:
                m_mtld = None
            records.append({
                "prompt_id": pid,
                "condition": label,
                "n_tokens": n,
                "mattr50": m_mattr,
                "mtld": m_mtld,
                "ttr": len(set(toks)) / n if n else None,
            })

    print(f"共 {len(records)} 条观测\n")

    # ---------- 1. 组间均值 ----------
    print("=" * 78)
    print(f"{'条件':32s} {'n':>3s} {'词数':>8s} {'MATTR50':>9s} {'MTLD':>8s} {'TTR':>7s}")
    print("=" * 78)
    summary = {}
    for field_key, label in CONDITION_FIELDS:
        sub = [r for r in records if r["condition"] == label]
        if not sub:
            continue
        def m(k):
            vals = [r[k] for r in sub if r[k] is not None]
            return statistics.mean(vals) if vals else float("nan")
        summary[label] = {
            "n": len(sub),
            "n_tokens_mean": m("n_tokens"),
            "mattr50_mean": m("mattr50"),
            "mtld_mean": m("mtld"),
            "ttr_mean": m("ttr"),
        }
        print(f"{label:32s} {len(sub):3d} {m('n_tokens'):8.0f} "
              f"{m('mattr50'):9.4f} {m('mtld'):8.3f} {m('ttr'):7.4f}")

    # ---------- 2. 与长度的相关 ----------
    print("\n" + "=" * 78)
    print("与文本长度的相关性（Pearson r）—— 越大越说明该指标被长度混淆")
    print("=" * 78)
    ns = np.array([r["n_tokens"] for r in records], dtype=float)
    corr = {}
    for k in ["mattr50", "mtld", "ttr"]:
        vs = np.array([r[k] if r[k] is not None else np.nan for r in records], dtype=float)
        mask = ~np.isnan(vs)
        r_, p_ = stats.pearsonr(ns[mask], vs[mask])
        corr[k] = {"r": float(r_), "p": float(p_)}
        print(f"  {k:10s}  r = {r_:+.4f}   p = {p_:.3e}   n = {mask.sum()}")

    # ---------- 3. 长度残差化后 AI vs Human ----------
    print("\n" + "=" * 78)
    print("长度残差化后：Human vs 各 AI 条件的 Mann-Whitney U 检验")
    print("=" * 78)
    # 对每个指标做 log 长度上的线性回归，取残差
    resid = {}
    for k in ["mattr50", "mtld", "ttr"]:
        vs = np.array([r[k] if r[k] is not None else np.nan for r in records], dtype=float)
        mask = ~np.isnan(vs)
        slope, intercept, *_ = stats.linregress(np.log(ns[mask]), vs[mask])
        rr = np.full(len(records), float("nan"))
        rr[mask] = vs[mask] - (slope * np.log(ns[mask]) + intercept)
        resid[k] = rr

    human_idx = [i for i, r in enumerate(records) if r["condition"] == "Human"]
    print(f"{'条件':32s} {'MATTR残差 p':>14s} {'MTLD残差 p':>13s} {'TTR残差 p':>12s}")
    print("-" * 78)
    tests = {}
    for field_key, label in CONDITION_FIELDS:
        if label == "Human":
            continue
        idx = [i for i, r in enumerate(records) if r["condition"] == label]
        row = {}
        cells = []
        for k in ["mattr50", "mtld", "ttr"]:
            a = resid[k][human_idx]
            b = resid[k][idx]
            a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
            if len(a) > 2 and len(b) > 2:
                u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
                row[k] = float(p)
                cells.append(f"{p:14.4f}" if k == "mattr50" else f"{p:13.4f}" if k == "mtld" else f"{p:12.4f}")
            else:
                cells.append(" " * 12)
        tests[label] = row
        print(f"{label:32s} " + " ".join(cells))

    out = {
        "method": "lexical_diversity.lex_div.mattr / .mtld",
        "mattr_window": MATTR_WINDOW,
        "n_observations": len(records),
        "summary": summary,
        "length_correlation": corr,
        "residualized_mannwhitney_p": tests,
        "records": records,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n✓ 已写 {OUT}")


if __name__ == "__main__":
    main()
