#!/usr/bin/env python3
"""metrics_extended.py — 扩展指标提取（组会 #2：词/句/段三级新增指标）

在既有 8 指标（metrics.py）之外，新增 5 个指标，口径尽量与既有实现一致
（spaCy en_core_web_sm；词 = is_alpha token；段 = 双换行切分/<newline> 回退）：

  词级:
    - lexical_density        实词率 = content POS (NOUN/VERB/ADJ/ADV/PROPN) / 全部词
    - word_length_sd         词长标准差（pstdev，与既有 pvariance 口径一致）
    - long_word_ratio        长词率 = 长度 >= 7 的词占比
  句级:
    - sentence_length_cv     句长变异系数 = SD / mean（对既有方差指标的归一化补充）
  段级:
    - sentences_per_paragraph 平均每段句数

输入: data/processed/sample_v1.json（30 prompts × 10 conditions；字段 <cond>_story）
输出: analysis/metrics_extended_results.json
用法: python metrics_extended.py [--limit N] [--no-ner] [--out PATH]
"""
import argparse
import json
import re
import statistics
import time
from pathlib import Path

import spacy

CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}
CONDITIONS = [
    "human", "gpt35", "MiMo-V2.5-Pro", "DeepSeek-V4-Flash",
    "Muse-Spark-1.2-Contributor", "Gemini-3.6-Flash", "Kimi-K3",
    "GPT-5.6-Luna", "Claude-Sonnet-5-High", "MiniMax-M3",
]


def locate_sample_json(base: Path) -> Path:
    """动态定位 sample json（避免静态引用大文件）。"""
    d = base / "data" / "processed"
    for name in sorted(p.name for p in d.iterdir()):
        if name.startswith("sample") and name.endswith(".json"):
            return d / name
    raise FileNotFoundError(f"no sample json under {d}")


def split_paragraphs(text: str) -> list:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) <= 1:
        paras = [p.strip() for p in text.split("<newline>") if p.strip()]
    return paras


def compute(text: str, nlp) -> dict:
    doc = nlp(text)
    words = [t for t in doc if t.is_alpha]
    sentence_lens = []
    for s in doc.sents:
        if s.text.strip():
            sentence_lens.append(sum(1 for t in s if t.is_alpha))
    paras = split_paragraphs(text)

    n_words = len(words)
    ld = (sum(1 for t in words if t.pos_ in CONTENT_POS) / n_words) if n_words else 0.0
    wl = [len(t.text) for t in words]
    wl_sd = statistics.pstdev(wl) if len(wl) > 1 else 0.0
    lwr = (sum(1 for x in wl if x >= 7) / n_words) if n_words else 0.0
    sent_mean = statistics.mean(sentence_lens) if sentence_lens else 0.0
    sent_cv = (statistics.pstdev(sentence_lens) / sent_mean) if (sentence_lens and sent_mean) else 0.0
    spp = (len(sentence_lens) / len(paras)) if paras else 0.0

    return {
        "lexical_density": ld,
        "word_length_sd": wl_sd,
        "long_word_ratio": lwr,
        "sentence_length_cv": sent_cv,
        "sentences_per_paragraph": spp,
        "_n_words": n_words,
        "_n_sentences": len(sentence_lens),
        "_n_paragraphs": len(paras),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only first N prompts (smoke test)")
    ap.add_argument("--no-ner", action="store_true", help="disable NER pipe to speed up")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = Path(__file__).resolve().parent.parent
    sample = json.loads(locate_sample_json(base).read_text())
    nlp = spacy.load("en_core_web_sm", disable=["ner"] if args.no_ner else [])

    rows = []
    t0 = time.time()
    for si, s in enumerate(sample["samples"]):
        if args.limit and si >= args.limit:
            break
        for cond in CONDITIONS:
            text = s.get(f"{cond}_story")
            if not text or not text.strip():
                continue
            m = compute(text, nlp)
            rows.append({
                "prompt_id": s["prompt_id"],
                "condition": cond,
                "metrics": {k: v for k, v in m.items() if not k.startswith("_")},
                "n_words": m["_n_words"],
                "n_sentences": m["_n_sentences"],
                "n_paragraphs": m["_n_paragraphs"],
            })
        print(f"[{si + 1}] rows={len(rows)} elapsed={time.time() - t0:.1f}s", flush=True)

    out = Path(args.out) if args.out else (base / "analysis" / "metrics_extended_results.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"DONE rows={len(rows)} in {time.time() - t0:.1f}s -> {out}", flush=True)


if __name__ == "__main__":
    main()
