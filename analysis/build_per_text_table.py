#!/usr/bin/env python3
"""build_per_text_table.py — 生成「每篇文本一行」的数据表（王雅琴老师 2026-10-19 建议第 1 项）。

输出：
  analysis/per-text-table.csv          149 行 = 5 组 × 30 prompts − Kimi 缺 1 篇
  analysis/per-text-table-missing.csv  缺失清单（哪篇、缺什么）
  analysis/per-text-table.md           前 20 行预览 + 各组样本数 + 缺失清单

口径（与既有分析保持一致）：
  word_count            data/processed/metrics_filtered_alpha.json 的 word_count_alpha
                        （spaCy en_core_web_sm，词 = is_alpha token；与 metrics_extended 的 n_words 逐篇相同）
  MATTR                 由原文重算，窗口固定 100（lexical_diversity.lex_div.tokenize + 完整窗口平均），
                        与 analysis/mattr_group_ttest.py 口径一致
  mean_sentence_length  data/processed/metrics_results.json 的 sentence_length
  sentence_length_CV    analysis/metrics_extended_results.json 的 sentence_length_cv（pstdev / mean）
  mean_paragraph_length data/processed/metrics_results.json 的 paragraph_length

只保留 Human + 四模型（Claude / GPT / DeepSeek / Kimi），不混入其它模型。
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import numpy as np
from lexical_diversity import lex_div

BASE = Path(__file__).resolve().parent.parent
SAMPLE = BASE / "data" / "processed" / "sample_v1.json"
FILTERED = BASE / "data" / "processed" / "metrics_filtered_alpha.json"
RESULTS = BASE / "data" / "processed" / "metrics_results.json"
EXTENDED = BASE / "analysis" / "metrics_extended_results.json"

OUT_CSV = BASE / "analysis" / "per-text-table.csv"
OUT_MISSING = BASE / "analysis" / "per-text-table-missing.csv"
OUT_MD = BASE / "analysis" / "per-text-table.md"

MATTR_WINDOW = 100

# 展示顺序 = 任务指定的组顺序；sample 字段 / 结果文件键 / 展示名 / 国内国外
GROUPS = [
    {"label": "Human", "story_key": "human", "result_key": "human",
     "ext_key": "human", "group": "Human"},
    {"label": "Claude-Sonnet-5-High", "story_key": "Claude-Sonnet-5-High",
     "result_key": "Claude-Sonnet-5-High", "ext_key": "Claude-Sonnet-5-High", "group": "国外"},
    {"label": "GPT-5.6-Luna", "story_key": "GPT-5.6-Luna",
     "result_key": "GPT-5.6-Luna", "ext_key": "GPT-5.6-Luna", "group": "国外"},
    {"label": "DeepSeek-V4-Flash", "story_key": "DeepSeek-V4-Flash",
     "result_key": "DeepSeek-V4-Flash", "ext_key": "DeepSeek-V4-Flash", "group": "国内"},
    {"label": "Kimi-K3", "story_key": "Kimi-K3", "result_key": "Kimi-K3",
     "ext_key": "Kimi-K3", "group": "国内"},
]

FIELDS = [
    "prompt_id", "model", "group", "word_count", "MATTR",
    "mean_sentence_length", "sentence_length_CV", "mean_paragraph_length",
    "n_sentences", "n_paragraphs",
]

MISSING_FIELDS = [
    "prompt_id", "model", "group", "missing_fields", "note",
]


def mattr(tokens: list[str], window: int = MATTR_WINDOW) -> float | None:
    """滑动窗口平均 TTR（完整窗口平均），窗口大于文本长度时返回 None。"""
    n = len(tokens)
    if n < window:
        return None
    vals = [len(set(tokens[i:i + window])) / window for i in range(n - window + 1)]
    return float(np.mean(vals))


def fmt(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    sample = load_json(SAMPLE)
    filtered = load_json(FILTERED)
    results = load_json(RESULTS)
    extended = load_json(EXTENDED)

    # ---- 索引 ----
    samples = {s["prompt_id"]: s for s in sample["samples"]}
    wc = {(r["condition"].removesuffix("_story"), r["prompt_id"]): r["word_count_alpha"]
          for r in filtered}
    ext = {(r["condition"], r["prompt_id"]): r for r in extended}
    res = {r["prompt_id"]: r for r in results}

    rows: list[dict] = []
    missing: list[dict] = []

    for prompt_id in sorted(samples):
        for g in GROUPS:
            text = samples[prompt_id].get(f"{g['story_key']}_story")
            absent: list[str] = []

            if not text or not text.strip():
                missing.append({
                    "prompt_id": prompt_id,
                    "model": g["label"],
                    "group": g["group"],
                    "missing_fields": "text,word_count,MATTR,mean_sentence_length,"
                                      "sentence_length_CV,mean_paragraph_length",
                    "note": "语料中无该篇文本（sample_v1.json 无该字段或为空）",
                })
                continue

            word_count = wc.get((g["result_key"], prompt_id))
            if word_count is None:
                absent.append("word_count")

            mattr100 = mattr(lex_div.tokenize(text))
            if mattr100 is None:
                absent.append("MATTR(<100 tokens)")

            result = res.get(prompt_id, {}).get(g["result_key"]) or {}
            mean_sentence_length = result.get("sentence_length")
            mean_paragraph_length = result.get("paragraph_length")
            if mean_sentence_length is None:
                absent.append("mean_sentence_length")
            if mean_paragraph_length is None:
                absent.append("mean_paragraph_length")

            ext_row = ext.get((g["ext_key"], prompt_id)) or {}
            cv = (ext_row.get("metrics") or {}).get("sentence_length_cv")
            if cv is None:
                absent.append("sentence_length_CV")

            n_sentences = result.get("_n_sentences")
            n_paragraphs = result.get("_n_paragraphs")

            rows.append({
                "prompt_id": prompt_id,
                "model": g["label"],
                "group": g["group"],
                "word_count": "" if word_count is None else int(word_count),
                "MATTR": fmt(mattr100),
                "mean_sentence_length": fmt(mean_sentence_length),
                "sentence_length_CV": fmt(cv),
                "mean_paragraph_length": fmt(mean_paragraph_length),
                "n_sentences": "" if n_sentences is None else n_sentences,
                "n_paragraphs": "" if n_paragraphs is None else n_paragraphs,
            })

            if absent:
                missing.append({
                    "prompt_id": prompt_id,
                    "model": g["label"],
                    "group": g["group"],
                    "missing_fields": ",".join(absent),
                    "note": "该行保留，空值如上；可用字段已填",
                })

    # ---- 写出 CSV ----
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with OUT_MISSING.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MISSING_FIELDS)
        writer.writeheader()
        writer.writerows(missing)

    # ---- 校验 ----
    counts = {g["label"]: sum(1 for r in rows if r["model"] == g["label"]) for g in GROUPS}
    expected = {"Human": 30, "Claude-Sonnet-5-High": 30, "GPT-5.6-Luna": 30,
                "DeepSeek-V4-Flash": 30, "Kimi-K3": 29}
    assert counts == expected, f"组样本数不符：{counts} != {expected}"
    assert len(rows) == 149, f"行数应为 149，实际 {len(rows)}"

    # word_count 与独立的 metrics_extended n_words 全量核对
    wc_mismatch = []
    for r in rows:
        e = ext.get((next(g["ext_key"] for g in GROUPS if g["label"] == r["model"]), r["prompt_id"]))
        if e is None:
            wc_mismatch.append((r["prompt_id"], r["model"], "missing"))
        elif int(r["word_count"]) != int(e["n_words"]):
            wc_mismatch.append((r["prompt_id"], r["model"], r["word_count"], e["n_words"]))
    assert not wc_mismatch, f"word_count 与 metrics_extended 不一致：{wc_mismatch[:5]}"

    # MATTR 与既有组均值核对（mattr_group_ttest_results.json，窗口 100）
    canonical = load_json(BASE / "analysis" / "mattr_group_ttest_results.json")
    canon_human = canonical["summary"]["human_mean"]
    mattr_human = float(np.mean([float(r["MATTR"]) for r in rows if r["model"] == "Human"]))
    assert abs(mattr_human - canon_human) < 1e-6, (mattr_human, canon_human)

    # 抽 5 篇核对（固定 seed，便于复现）
    rng = random.Random(42)
    spot = rng.sample(rows, 5)
    print("抽 5 篇 word_count 核对（对照 metrics_extended_results.json 的 n_words）：")
    for r in spot:
        e = ext[(next(g["ext_key"] for g in GROUPS if g["label"] == r["model"]), r["prompt_id"])]
        print(f"  prompt {r['prompt_id']:2d} {r['model']:22s} "
              f"word_count={r['word_count']:>4} n_words={e['n_words']:>4} OK")

    # ---- 写出 Markdown ----
    by_group = {g["label"]: [r for r in rows if r["model"] == g["label"]] for g in GROUPS}
    group_rows = "\n".join(
        f"| {g['group']} | {g['label']} | {len(by_group[g['label']])} |"
        for g in GROUPS
    )
    preview_fields = FIELDS
    preview = "\n".join(
        "| " + " | ".join(str(r[f]) for f in preview_fields) + " |" for r in rows[:20]
    )
    header = "| " + " | ".join(preview_fields) + " |"
    sep = "|" + "|".join(["---"] * len(preview_fields)) + "|"
    missing_rows = "\n".join(
        f"| {m['prompt_id']} | {m['model']} | {m['group']} | {m['missing_fields']} | {m['note']} |"
        for m in missing
    ) or "| — | — | — | — | 无 |"

    md = f"""# 每篇文本一行（per-text table）

生成脚本：`analysis/build_per_text_table.py`（2026-10-23）。
数据源：`data/processed/sample_v1.json`、`metrics_filtered_alpha.json`、`metrics_results.json`、
`analysis/metrics_extended_results.json`。只含 Human 与四个模型，不含 gpt35 等其它条件。

## 口径

- `word_count`：spaCy `en_core_web_sm` 的字母词（`token.is_alpha`）计数，五组同一口径；
  与 `metrics_extended_results.json` 的 `n_words` 逐篇全等（149/149）。
- `MATTR`：移动平均类符形符比，窗口固定 **100**（`lexical_diversity.lex_div.tokenize`；
  仅对完整窗口取平均）。`metric-specification.md` 未规定 MATTR 窗口；此处沿用
  `analysis/mattr_group_ttest.py` 与报告 §3.4 的固定窗口 100。
- `mean_sentence_length`：句内字母词数的均值（`metrics_results.json: sentence_length`）。
- `sentence_length_CV`：句长 `pstdev / mean`（`metrics_extended_results.json`）。
- `mean_paragraph_length`：段内字母词数的均值（`metrics_results.json: paragraph_length`）。

## 各组样本数

| group | model | n |
|---|---|---|
{group_rows}
| **合计** | | **{len(rows)}** |

## 前 20 行预览

{header}
{sep}
{preview}

## 缺失清单

| prompt_id | model | group | 缺失字段 | 说明 |
|---|---|---|---|---|
{missing_rows}

Kimi-K3 缺 `prompt_id=26`（整篇无文本），因此 Kimi 组 n=29；该篇不进入任何按篇统计。
缺失清单同时以 CSV 形式保存在 `analysis/per-text-table-missing.csv`。

## 校验记录

- 行数 149 = 30 prompts × 5 组 − Kimi 缺 1 篇；各组 n 与上表一致。
- `word_count` 与独立汇总的 `metrics_extended_results.json: n_words` 逐篇相同（149/149）。
- Human 组 MATTR(100) 均值 = {mattr_human:.10f}，与
  `analysis/mattr_group_ttest_results.json` 的 `human_mean` = {canon_human:.10f} 一致（差 < 1e-6，来自 CSV 保留 6 位小数的舍入）。
- 抽 5 篇（seed=42）核对 `word_count`：{", ".join(f"p{r['prompt_id']}/{r['model']}={r['word_count']}" for r in spot)}。

## 备注

- Human 原文来自 HuggingFace 数据集，标点前后带空格；若用 `len(text.split())` 会把标点
  误计为词（如 prompt 0：split=339 vs 字母词=261）。本表统一用字母词口径，避免把
  语料的排版差异当成文本长度差异。
"""
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"\nwrote {OUT_CSV.relative_to(BASE)} ({len(rows)} rows)")
    print(f"wrote {OUT_MISSING.relative_to(BASE)} ({len(missing)} rows)")
    print(f"wrote {OUT_MD.relative_to(BASE)}")
    print("counts:", counts)


if __name__ == "__main__":
    main()
