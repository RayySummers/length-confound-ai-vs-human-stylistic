#!/usr/bin/env python3
"""检验不同窗口下的相关系数是否显著不同（Fisher z 两两比较）。"""
import json, numpy as np, statistics
from scipy import stats
from lexical_diversity import lex_div

sample = json.load(open('data/processed/sample_v1.json'))
FIELDS = [("human","Human"),("gpt35","GPT-3.5"),("MiMo-V2.5-Pro","MiMo-V2.5-Pro"),
("DeepSeek-V4-Flash","DeepSeek-V4-Flash"),("MiniMax-M3","MiniMax-M3"),
("Muse-Spark-1.2-Contributor","Muse-Spark-1.2-Contributor"),("GPT-5.6-Luna","GPT-5.6-Luna"),
("Claude-Sonnet-5-High","Claude-Sonnet-5-High"),("Gemini-3.6-Flash","Gemini-3.6-Flash"),("Kimi-K3","Kimi-K3")]
WINDOWS = [20, 50, 100, 200]

# 同一子集（词数 >= 430，窗 200 才可用）
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
print(f"子集观测数: {len(cache)}")

ns = np.array([len(v) for v in cache.values()], dtype=float)
print(f"词数范围: {ns.min():.0f} - {ns.max():.0f}，中位数 {np.median(ns):.0f}")

def corr(vals):
    mask = ~np.isnan(vals)
    r, p = stats.pearsonr(ns[mask], vals[mask])
    return r, p, mask.sum()

print()
print("="*78)
print("各指标/窗口下 与长度的 Pearson r")
print("="*78)
res = {}
vals_mattr = {}
for W in WINDOWS:
    v = np.array([lex_div.mattr(t, W) for t in cache.values()], dtype=float)
    vals_mattr[W] = v
    r, p, n = corr(v)
    res[f"MATTR{W}"] = (r, n)
    print(f"  MATTR 窗 {W:3d}: r = {r:+.4f}  p = {p:.3e}  n = {n}")
v = np.array([lex_div.mtld(t) for t in cache.values()], dtype=float)
r, p, n = corr(v)
res["MTLD"] = (r, n)
print(f"  MTLD      : r = {r:+.4f}  p = {p:.3e}  n = {n}")
v = np.array([len(set(t))/len(t) for t in cache.values()], dtype=float)
r, p, n = corr(v)
res["TTR"] = (r, n)
print(f"  TTR       : r = {r:+.4f}  p = {p:.3e}  n = {n}")

print()
print("="*78)
print("Fisher z 两两比较 —— 任意两个窗口的 r 是否显著不同？")
print("="*78)
keys = [f"MATTR{W}" for W in WINDOWS] + ["MTLD", "TTR"]
print(f"{'':16s}" + "".join(f"{k:>12s}" for k in keys))
for i, a in enumerate(keys):
    row = f"{a:16s}"
    for j, b in enumerate(keys):
        if j <= i:
            row += " " * 12
            continue
        ra, na = res[a]; rb, nb = res[b]
        za, zb = np.arctanh(ra), np.arctanh(rb)
        se = np.sqrt(1/(na-3) + 1/(nb-3))
        z = (za - zb)/se
        p = 2*(1-stats.norm.cdf(abs(z)))
        mark = "**" if p < 0.05 else ("~" if p < 0.10 else "ns")
        row += f"{p:>10.3f}{mark:>2s}"
    print(row)
print()
print("** p<.05 显著不同；~ p<.10 边缘；ns = 不显著")

print()
print("="*78)
print("窗口内 两两比较（MATTR 窗 20 vs 200 的直接对照）")
print("="*78)
for a, b in [("MATTR20","MATTR50"), ("MATTR20","MATTR200"), ("MATTR50","MATTR100"), ("MATTR50","MATTR200"), ("MATTR100","MATTR200")]:
    ra, na = res[a]; rb, nb = res[b]
    za, zb = np.arctanh(ra), np.arctanh(rb)
    se = np.sqrt(1/(na-3) + 1/(nb-3))
    z = (za - zb)/se
    p = 2*(1-stats.norm.cdf(abs(z)))
    verdict = "显著不同" if p < 0.05 else ("边缘" if p < 0.10 else "无显著差异")
    print(f"  {a:9s} (r={ra:+.4f})  vs  {b:9s} (r={rb:+.4f}):  z = {z:+6.3f}  p = {p:.3f}   {verdict}")
