#!/usr/bin/env python3
"""逐条检查 149 篇文本的格式，找出切分/空白异常。

输出：
  analysis/text-format-report.csv   每篇一行，带 flags
  stdout                            按模型汇总的异常计数

判定依据（阈值可改）：
  - 平均句长 < 8 词 → segmentation_suspect（多半是句号缺失或被换行切断）
  - 平均段长 < 15 词 → paragraph_suspect
  - 段落里出现单换行（\n 但非 \n\n）→ soft_linebreak
  - 文本含 markdown 标记（**、##、- 、1. ）→ markdown_residue
  - 连续空格 / 制表符 / 首尾空白 → whitespace_issue
  - 结尾无 . ! ? " → no_final_punct
  - 与其他文本完全重复 → duplicate
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "processed" / "sample_v1.json"
OUT = ROOT / "analysis" / "text-format-report.csv"

MODEL_KEYS = [
    ("Human", "human_story"),
    ("Claude", "Claude-Sonnet-5-High_story"),
    ("GPT", "GPT-5.6-Luna_story"),
    ("DeepSeek", "DeepSeek-V4-Flash_story"),
    ("Kimi", "Kimi-K3_story"),
]


def words(t: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", t)


def check(text: str) -> dict:
    t = text or ""
    ws = words(t)
    n_words = len(ws)
    paras = [p for p in re.split(r"\n\s*\n", t.strip()) if p.strip()]
    n_paras = len(paras)
    # 句号/问号/感叹号切句
    sents = [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s.strip()]
    n_sents = len(sents)
    mean_sent = n_words / n_sents if n_sents else 0
    mean_para = n_words / n_paras if n_paras else 0
    single_nl = bool(re.search(r"[^\n]\n(?!\n)", t.strip()))
    flags = []
    if mean_sent < 8:
        flags.append("segmentation_suspect")
    if mean_para < 15:
        flags.append("paragraph_suspect")
    if single_nl:
        flags.append("soft_linebreak")
    if re.search(r"(\*\*|^#{1,3} |^- |^\d+\. )", t, re.M):
        flags.append("markdown_residue")
    if re.search(r"[ \t]{2,}", t) or t != t.strip():
        flags.append("whitespace_issue")
    if not re.search(r'[.!?"”]\s*$', t.strip()):
        flags.append("no_final_punct")
    return {
        "n_words": n_words,
        "n_paragraphs": n_paras,
        "n_sentences": n_sents,
        "mean_sentence_length": round(mean_sent, 2),
        "mean_paragraph_length": round(mean_para, 2),
        "flags": ";".join(flags),
    }


def main() -> int:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    rows = []
    hashes = defaultdict(list)
    for s in data["samples"]:
        pid = s["prompt_id"]
        for group, key in MODEL_KEYS:
            text = s.get(key)
            if text is None:
                rows.append({"prompt_id": pid, "group": group, "present": 0,
                             "n_words": 0, "n_paragraphs": 0, "n_sentences": 0,
                             "mean_sentence_length": 0, "mean_paragraph_length": 0,
                             "flags": "missing"})
                continue
            r = check(text)
            r.update({"prompt_id": pid, "group": group, "present": 1})
            rows.append(r)
            hashes[hash(text.strip())].append((pid, group))

    dups = {h: v for h, v in hashes.items() if len(v) > 1}
    for r in rows:
        pass  # duplicate 标记在下面按 prompt 输出

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["prompt_id", "group", "present", "n_words", "n_paragraphs",
            "n_sentences", "mean_sentence_length", "mean_paragraph_length", "flags"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = __import__("csv").DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})

    # 汇总
    by_group = defaultdict(Counter)
    for r in rows:
        for flag in (r["flags"].split(";") if r["flags"] else []):
            by_group[r["group"]][flag] += 1
    print(f"写出 {OUT}（{len(rows)} 行）\n")
    print(f"{'组':10s} {'n':>3s} {'seg':>4s} {'para':>5s} {'softNL':>7s} {'md':>3s} {'ws':>3s} {'noEnd':>6s} {'missing':>8s}")
    for group, _ in MODEL_KEYS:
        c = by_group[group]
        n = sum(1 for r in rows if r["group"] == group and r["present"])
        missing = sum(1 for r in rows if r["group"] == group and not r["present"])
        print(f"{group:10s} {n:3d} {c['segmentation_suspect']:4d} {c['paragraph_suspect']:5d} "
              f"{c['soft_linebreak']:7d} {c['markdown_residue']:3d} {c['whitespace_issue']:3d} "
              f"{c['no_final_punct']:6d} {missing:8d}")
    if dups:
        print("\n完全重复的文本：")
        for v in dups.values():
            print("  ", v)
    # 最可疑的十篇
    sus = [r for r in rows if "segmentation_suspect" in r["flags"]]
    if sus:
        print(f"\n平均句长 < 8 词的文本（{len(sus)} 篇），前 10：")
        for r in sorted(sus, key=lambda x: x["mean_sentence_length"])[:10]:
            print(f"  {r['group']:8s} prompt {r['prompt_id']:>2d}  句长 {r['mean_sentence_length']:>5.1f}  段长 {r['mean_paragraph_length']:>6.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
