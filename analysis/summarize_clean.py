#!/usr/bin/env python3
"""在清洗后的数据上重算四指标，段落不可信的组标 N/A。

输入  data/processed/sample_v1_clean.json
输出  analysis/summary-clean.csv, analysis/summary-clean.md
"""
from __future__ import annotations

import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "sample_v1_clean.json"
CSV_OUT = ROOT / "analysis" / "summary-clean.csv"
MD_OUT = ROOT / "analysis" / "summary-clean.md"

MODEL_KEYS = [
    ("Human", "human_story"),
    ("Claude", "Claude-Sonnet-5-High_story"),
    ("GPT", "GPT-5.6-Luna_story"),
    ("DeepSeek", "DeepSeek-V4-Flash_story"),
    ("Kimi", "Kimi-K3_story"),
]


def words(t):
    import re
    return re.findall(r"[A-Za-z']+", t)


def sentences(t):
    import re
    return [s for s in re.split(r"(?<=[.!?])[\"'”]?\s+", t.strip()) if s.strip()]


def paragraphs(t):
    import re
    return [p for p in re.split(r"\n\s*\n", t.strip()) if p.strip()]


def mattr(ws, w=100):
    if len(ws) < w:
        return len(set(ws)) / len(ws) if ws else 0.0
    return sum(len(set(ws[i:i + w])) / w for i in range(len(ws) - w + 1)) / (len(ws) - w + 1)


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for s in data["samples"]:
        for group, key in MODEL_KEYS:
            t = s.get(key)
            if not t:
                continue
            ws, ss, ps = words(t), sentences(t), paragraphs(t)
            sl = [len(words(x)) for x in ss if words(x)]
            mean_sl = st.mean(sl) if sl else 0
            sd_sl = st.pstdev(sl) if len(sl) > 1 else 0
            cv = sd_sl / mean_sl if mean_sl else 0
            rows.append({
                "prompt_id": s["prompt_id"], "group": group,
                "n_words": len(ws), "MATTR": mattr(ws),
                "mean_sentence_length": mean_sl, "sentence_cv": cv,
                "mean_paragraph_length": len(ws) / len(ps) if ps else 0,
                "sentences_per_paragraph": len(ss) / len(ps) if ps else 0,
            })

    groups = [g for g, _ in MODEL_KEYS]
    out = []
    for g in groups:
        rs = [r for r in rows if r["group"] == g]
        if not rs:
            continue
        rel_para = sum(1 for r in rs if 1.3 <= r["sentences_per_paragraph"] <= 12) / len(rs)
        def ms(k):
            vals = [r[k] for r in rs]
            return st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0
        rec = {"group": g, "n": len(rs)}
        for k in ("MATTR", "mean_sentence_length", "sentence_cv", "mean_paragraph_length"):
            m, sd = ms(k)
            rec[k] = round(m, 4); rec[k + "_sd"] = round(sd, 4)
        rec["paragraph_reliable"] = round(rel_para, 2)
        out.append(rec)

    with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    lines = ["# 清洗后四指标汇总（描述统计）", "",
             "数据：`data/processed/sample_v1_clean.json`。段落列仅在 ≥70% 文本段落结构可信时给出，否则 N/A。", "",
             "| 组 | n | MATTR | 平均句长 | 句长 CV | 平均段长 | 段落可信比例 |",
             "|---|---|---|---|---|---|---|"]
    for r in out:
        para = f"{r['mean_paragraph_length']:.1f} ± {r['mean_paragraph_length_sd']:.1f}" if r["paragraph_reliable"] >= 0.7 else "N/A"
        lines.append(f"| {r['group']} | {r['n']} | {r['MATTR']:.3f} ± {r['MATTR_sd']:.3f} | "
                     f"{r['mean_sentence_length']:.2f} ± {r['mean_sentence_length_sd']:.2f} | "
                     f"{r['sentence_cv']:.3f} ± {r['sentence_cv_sd']:.3f} | {para} | {r['paragraph_reliable']:.0%} |")
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n写入 {CSV_OUT} 与 {MD_OUT}")


if __name__ == "__main__":
    main()
