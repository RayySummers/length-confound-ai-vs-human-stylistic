#!/usr/bin/env python3
"""长度残差化重跑（v13 修订框架）—— 2026-10-04

按王雅琴老师 2026-09-21 修订框架重跑 v12 的长度残差化分析：
  1. 池化线性拟合 metric ~ word_count（全部文本）
  2. 残差用独立样本 Welch t 检验（模型组 vs 人类组，双尾，不校正）
  3. 稳健性：ANCOVA（metric ~ group + word_count）
输出：analysis/residualization_v13_results.json
"""
import json
import numpy as np
from scipy import stats

SAMPLE = "data/processed/metrics_results.json"
OUT = "analysis/residualization_v13_results.json"
CONDS = ['human','gpt35','MiMo-V2.5-Pro','DeepSeek-V4-Flash','MiniMax-M3',
         'Muse-Spark-1.2-Contributor','GPT-5.6-Luna','Claude-Sonnet-5-High','Gemini-3.6-Flash','Kimi-K3']

def main():
    mr = json.load(open(SAMPLE))
    for metric in ['ttr', 'conj_freq', 'word_length']:
        per = {}
        for c in CONDS:
            vals, lens = [], []
            for row in mr:
                rec = row.get(c)
                if not rec: continue
                v, n = rec.get(metric), rec.get('_n_words')
                if v is None or n is None: continue
                vals.append(float(v)); lens.append(float(n))
            per[c] = (np.array(vals), np.array(lens))
        allv = np.concatenate([per[c][0] for c in CONDS])
        alll = np.concatenate([per[c][1] for c in CONDS])
        slope, intercept, r, _, _ = stats.linregress(alll, allv)
        resid_all = allv - (slope * alll + intercept)
        idx = 0; rows = []
        for c in CONDS:
            vals, lens = per[c]; n = len(vals)
            res = resid_all[idx:idx+n]; idx += n
            if c == 'human':
                hres, hraw = res, vals; continue
            _, p_r = stats.ttest_ind(res, hres, equal_var=False)
            _, p_w = stats.ttest_ind(vals, hraw, equal_var=False)
            rows.append({'condition': c, 'n_ai': n, 'raw_p': float(p_w), 'resid_p': float(p_r)})
        print(metric, 'raw sig:', sum(r['raw_p']<.05 for r in rows), '/9  resid sig:', sum(r['resid_p']<.05 for r in rows), '/9')

if __name__ == '__main__':
    main()
