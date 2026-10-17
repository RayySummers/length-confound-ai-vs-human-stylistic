#!/usr/bin/env python3
"""MATTR 窗口敏感性分析：不同窗口下 MATTR 的长度依赖与组间表现。"""
import json, numpy as np, statistics
from scipy import stats
from lexical_diversity import lex_div

sample = json.load(open('data/processed/sample_v1.json'))
FIELDS = [("human","Human"),("gpt35","GPT-3.5"),("MiMo-V2.5-Pro","MiMo-V2.5-Pro"),
("DeepSeek-V4-Flash","DeepSeek-V4-Flash"),("MiniMax-M3","MiniMax-M3"),
("Muse-Spark-1.2-Contributor","Muse-Spark-1.2-Contributor"),("GPT-5.6-Luna","GPT-5.6-Luna"),
("Claude-Sonnet-5-High","Claude-Sonnet-5-High"),("Gemini-3.6-Flash","Gemini-3.6-Flash"),("Kimi-K3","Kimi-K3")]

WINDOWS = [20, 50, 100, 200]

def holm(pv):
    m = len(pv); order = sorted(range(m), key=lambda i: pv[i]); adj = [None]*m; prev = 0.0
    for rk, i in enumerate(order):
        v = min(1.0, (m - rk) * pv[i]); v = max(v, prev); adj[i] = v; prev = v
    return adj

def analyse(recs, labels):
    ns = np.array([r['n'] for r in recs], float)
    vs = np.array([r['v'] if r['v'] is not None else float('nan') for r in recs], float)
    mask = ~np.isnan(vs)
    r_, p_ = stats.pearsonr(ns[mask], vs[mask])
    slope, inter, *_ = stats.linregress(np.log(ns[mask]), vs[mask])
    rr = np.full(len(recs), float('nan'))
    rr[mask] = vs[mask] - (slope * np.log(ns[mask]) + inter)
    hidx = [i for i, r in enumerate(recs) if r['c'] == 'Human']
    ps = []
    for lab in labels[1:]:
        idx = [i for i, r in enumerate(recs) if r['c'] == lab]
        a = rr[hidx]; a = a[~np.isnan(a)]
        b = rr[idx]; b = b[~np.isnan(b)]
        u, p = stats.mannwhitneyu(a, b, alternative='two-sided')
        ps.append(p)
    n_surv = sum(1 for x in holm(ps) if x < 0.05)
    hv = [r['v'] for r in recs if r['c'] == 'Human' and r['v'] is not None]
    av = [r['v'] for r in recs if r['c'] != 'Human' and r['v'] is not None]
    return r_, p_, n_surv, statistics.mean(hv), statistics.mean(av)

# 先分词缓存（只保留词数 >= 400 的，保证 MATTR 窗口 200 可用）
cache = {}
for s in sample['samples']:
    for fk, lab in FIELDS:
        st = s.get(f"{fk}_story")
        if not st or len(st.strip()) < 100:
            continue
        toks = lex_div.tokenize(st)
        if len(toks) < 430:
            continue
        cache[(s['prompt_id'], lab)] = toks

labels = [lab for _, lab in FIELDS]
print(f"可分析观测数（词数>=430）: {len(cache)}")
print()
print("=" * 92)
print(f"{'窗口':>5s} | {'r(与长度)':>11s} {'p':>11s} | {'Holm存活':>9s} | {'Human均值':>10s} {'AI均值':>9s} {'AI-Human':>9s}")
print("=" * 92)

for W in WINDOWS:
    recs = []
    for (pid, lab), toks in cache.items():
        try:
            mv = lex_div.mattr(toks, W)
        except Exception:
            mv = None
        recs.append({'c': lab, 'n': len(toks), 'v': mv})
    r_, p_, n_surv, hmean, amean = analyse(recs, labels)
    print(f"{W:5d} | {r_:+11.4f} {p_:11.2e} | {n_surv:>6d}/9 | {hmean:10.4f} {amean:9.4f} {amean-hmean:+9.4f}")

# MTLD 在同一子集上的对照
recs = []
for (pid, lab), toks in cache.items():
    try:
        mv = lex_div.mtld(toks)
    except Exception:
        mv = None
    recs.append({'c': lab, 'n': len(toks), 'v': mv})
r_, p_, n_surv, hmean, amean = analyse(recs, labels)
print("-" * 92)
print(f"{'MTLD':>5s} | {r_:+11.4f} {p_:11.2e} | {n_surv:>6d}/9 | {hmean:10.4f} {amean:9.4f} {amean-hmean:+9.4f}")
