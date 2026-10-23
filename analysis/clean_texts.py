#!/usr/bin/env python3
"""清洗 149 篇文本的格式问题，并重新统计基础指标。

做四件事：
  1. 去掉 markdown 残留：行首 #、**、- 、1. 、``` 围栏
  2. 修标点空格：去掉标点前的空格（HuggingFace 数据集的痕迹），补标点后的空格
  3. 合并多余空白：连续空格/制表符 → 单空格，段内单换行 → 空格
  4. 判定段落是否可信：若「句数/段数」中位数 < 1.3，说明这是每句一段，段长指标不可用

输入  data/processed/sample_v1.json
输出  data/processed/sample_v1_clean.json
      analysis/cleaning-report.csv
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "sample_v1.json"
DST = ROOT / "data" / "processed" / "sample_v1_clean.json"
REPORT = ROOT / "analysis" / "cleaning-report.csv"

MODEL_KEYS = [
    ("Human", "human_story"),
    ("Claude", "Claude-Sonnet-5-High_story"),
    ("GPT", "GPT-5.6-Luna_story"),
    ("DeepSeek", "DeepSeek-V4-Flash_story"),
    ("Kimi", "Kimi-K3_story"),
]


def strip_markdown(t: str) -> tuple[str, bool]:
    before = t
    t = re.sub(r"```[a-zA-Z]*\n?", "", t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)      # 行首标题
    t = re.sub(r"^\s{0,3}[-*+]\s+", "", t, flags=re.M)       # 列表符号
    t = re.sub(r"^\s{0,3}\d+[.)]\s+", "", t, flags=re.M)     # 有序列表
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", t)   # 斜体
    return t, t != before


def normalize_punct(t: str) -> tuple[str, bool]:
    before = t
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)                   # 标点前空格
    t = re.sub(r"([,.;:!?])(?=[A-Za-z\"'“”])", r"\1 ", t)    # 标点后缺空格
    t = t.replace(" ,", ",").replace(" .", ".")
    return t, t != before


def normalize_ws(t: str) -> str:
    t = t.replace("\r\n", "\n").replace("\t", " ")
    t = re.sub(r"[ ]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r" *\n *", "\n", t)
    return t.strip()


def words(t: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", t)


def sentences(t: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])[\"'”]?\s+", t.strip()) if s.strip()]


def paragraphs(t: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", t.strip()) if p.strip()]


def mattr(ws: list[str], window: int = 100) -> float:
    if len(ws) < window:
        return len(set(ws)) / len(ws) if ws else 0.0
    vals = []
    for i in range(len(ws) - window + 1):
        seg = ws[i:i + window]
        vals.append(len(set(seg)) / window)
    return sum(vals) / len(vals)


def stats(t: str) -> dict:
    ws = words(t)
    ss = sentences(t)
    ps = paragraphs(t)
    return {
        "n_words": len(ws),
        "n_sentences": len(ss),
        "n_paragraphs": len(ps),
        "mean_sentence_length": round(len(ws) / len(ss), 2) if ss else 0,
        "mean_paragraph_length": round(len(ws) / len(ps), 2) if ps else 0,
        "sentences_per_paragraph": round(len(ss) / len(ps), 2) if ps else 0,
        "MATTR": round(mattr(ws), 4),
    }


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    report = []
    changed = defaultdict(int)
    for s in data["samples"]:
        pid = s["prompt_id"]
        for group, key in MODEL_KEYS:
            raw = s.get(key)
            if raw is None:
                continue
            t = normalize_ws(raw)
            t, md = strip_markdown(t)
            t, punct = normalize_punct(t)
            t = normalize_ws(t)
            s[key] = t
            st = stats(t)
            unreliable = not (1.3 <= st["sentences_per_paragraph"] <= 12)
            report.append({
                "prompt_id": pid, "group": group,
                "markdown_removed": int(md), "punct_fixed": int(punct),
                **st,
                "paragraph_unreliable": int(unreliable),
            })
            if md:
                changed["markdown"] += 1
            if punct:
                changed["punct"] += 1
    DST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with REPORT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)

    print(f"清洗后写入 {DST}")
    print(f"报告写入 {REPORT}（{len(report)} 行）")
    print(f"改动统计：{dict(changed)}")
    print("\n各组清洗后概览（中位数）")
    print(f"{'组':10s}{'n':>4s}{'词数':>7s}{'句长':>7s}{'段长':>8s}{'句/段':>7s}{'MATTR':>8s}{'段不可信':>9s}")
    for group, _ in MODEL_KEYS:
        rs = [r for r in report if r["group"] == group]
        if not rs:
            continue
        med = lambda k: sorted(r[k] for r in rs)[len(rs) // 2]
        bad = sum(r["paragraph_unreliable"] for r in rs)
        print(f"{group:10s}{len(rs):4d}{med('n_words'):7.0f}{med('mean_sentence_length'):7.1f}"
              f"{med('mean_paragraph_length'):8.1f}{med('sentences_per_paragraph'):7.2f}"
              f"{med('MATTR'):8.3f}{bad:9d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
