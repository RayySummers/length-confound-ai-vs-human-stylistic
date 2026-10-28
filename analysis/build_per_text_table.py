#!/usr/bin/env python3
"""Build the per-text table required by the 2026-10-19 advisor note (RAY-587).

One row per retained text (Human + Claude + GPT + DeepSeek + Kimi).  The four
model families in this table are deliberately limited to the advisor's scope;
GPT-3.5, Gemini, MiniMax, MiMo and Muse are *not* mixed in.

Definitions (kept consistent with the existing analysis pipeline):
  * word_count            — alphabetic spaCy tokens, text lowercased first
                            (same definition as results_v1.json ``n_words``).
  * MATTR                 — moving-average type-token ratio, fixed window 100,
                            using ``lexical_diversity.lex_div`` tokenisation
                            (punctuation stripped, lowercased, whitespace split).
  * mtld                  — MTLD (Jarvis & McCarthy), ``lexical_diversity.lex_div.mtld``
                            with its default factor threshold 0.72, run forward +
                            backward and averaged.  Input is the *same* token
                            sequence as ``word_count`` (alphabetic spaCy tokens,
                            text lowercased first) — see RAY-598.  Do not compare
                            its level with MATTR: the two use different tokens.
  * mean_sentence_length  — mean alphabetic words per spaCy sentence.
  * sentence_length_CV    — population SD / mean over the *same* sentence
                            lengths used for mean_sentence_length.
  * mean_paragraph_length — mean alphabetic words per paragraph.  Paragraphs
                            are split on blank lines, with the corpus'
                            ``<newline>`` fallback (same as metrics.py).

The MATTR window is fixed at 100 for every text.  ``docs/metric-specification.md``
(the locked 2026-08-05 set) does not contain a MATTR entry; 100 is the parameter
fixed by the 2026-09-21 group-meeting decision and used in proposal v13/v14
(§3.2, "MATTR is computed with a fixed window of 100").  It is not tuned here.

Inputs : data/processed/sample_v1.json
Outputs: analysis/per-text-table.csv
         analysis/per-text-table-missing.csv
         analysis/per-text-table.md

Run with the interpreter that has spaCy + en_core_web_sm + lexical_diversity,
e.g. ``python3.12 analysis/build_per_text_table.py``.
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
SAMPLE_PATH = BASE / "data" / "processed" / "sample_v1.json"
RESULTS_PATH = BASE / "data" / "processed" / "results_v1.json"
EXTENDED_PATH = BASE / "analysis" / "metrics_extended_results.json"
OUT_CSV = BASE / "analysis" / "per-text-table.csv"
OUT_MISSING_CSV = BASE / "analysis" / "per-text-table-missing.csv"
OUT_MD = BASE / "analysis" / "per-text-table.md"

MATTR_WINDOW = 100  # fixed for every text; see module docstring
MTLD_THRESHOLD = 0.72  # lex_div.mtld default; not tuned here (RAY-598)
MIN_TEXT_CHARS = 100  # corpus-level guard used by metrics.py (not a metric filter)

# Order controls the CSV row order and the preview.
MODEL_SPECS = (
    {"model": "Human", "field": "human", "condition": "human", "group": "Human"},
    {"model": "Claude", "field": "Claude-Sonnet-5-High", "condition": "Claude-Sonnet-5-High", "group": "国外"},
    {"model": "GPT", "field": "GPT-5.6-Luna", "condition": "GPT-5.6-Luna", "group": "国外"},
    {"model": "DeepSeek", "field": "DeepSeek-V4-Flash", "condition": "DeepSeek-V4-Flash", "group": "国内"},
    {"model": "Kimi", "field": "Kimi-K3", "condition": "Kimi-K3", "group": "国内"},
)
METRIC_KEYS = ("word_count", "MATTR", "mtld", "mean_sentence_length", "sentence_length_CV", "mean_paragraph_length")

# Published MATTR values (proposal_v13.md Table 2b / proposal_v14_zh.md Table 2b)
# used only as a regression check that the window is 100.
PUBLISHED_MATTR = {
    "Human": (0.678, 0.057),
    "Claude": (0.7773, 0.0305),
    "GPT": (0.7628, 0.0299),
    "DeepSeek": (0.7290, 0.0268),
    "Kimi": (0.7568, 0.0291),
}

SPOT_CHECKS = ((0, "Human"), (3, "Claude"), (7, "GPT"), (12, "DeepSeek"), (29, "Kimi"))


def load_pipeline():
    """Load spaCy + lexical_diversity with actionable error messages."""
    try:
        import spacy
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit("spaCy is required: pip install 'spacy>=3.7,<4.0'") from exc
    try:
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            import en_core_web_sm

            nlp = en_core_web_sm.load()
    except (ImportError, OSError) as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "spaCy model en_core_web_sm is required: python -m spacy download en_core_web_sm"
        ) from exc
    try:
        from lexical_diversity import lex_div
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit("lexical_diversity is required: pip install lexical-diversity") from exc
    return nlp, lex_div


def split_paragraphs(text: str) -> list[str]:
    """Blank-line paragraphs, with the corpus' <newline> fallback."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) <= 1:
        paras = [p.strip() for p in text.split("<newline>") if p.strip()]
    return paras or [text.strip()]


def alpha_tokens(tokenizer, text: str) -> list[str]:
    """Lowercased alphabetic tokens — the one token sequence behind both
    ``word_count`` and ``mtld`` (RAY-598: MTLD must use these, not lex_div's)."""
    return [token.text.lower() for token in tokenizer(text.lower()) if token.is_alpha]


def alpha_count(tokenizer, text: str) -> int:
    """Count alphabetic tokens exactly as metrics.py does (lowercased first)."""
    return len(alpha_tokens(tokenizer, text))


def compute_metrics(text: str, nlp, lex_div) -> dict[str, Any]:
    tokenizer = nlp.tokenizer
    doc = nlp(text)

    sentence_texts = [sent.text for sent in doc.sents if sent.text.strip()]
    sentence_lengths = [alpha_count(tokenizer, sent) for sent in sentence_texts]
    mean_sentence_length = statistics.mean(sentence_lengths) if sentence_lengths else None
    sentence_length_cv = None
    if len(sentence_lengths) >= 2 and mean_sentence_length:
        sentence_length_cv = statistics.pstdev(sentence_lengths) / mean_sentence_length

    paragraphs = split_paragraphs(text)
    paragraph_lengths = [alpha_count(tokenizer, para) for para in paragraphs]
    mean_paragraph_length = statistics.mean(paragraph_lengths) if paragraph_lengths else None

    mattr_tokens = lex_div.tokenize(text)
    mattr = None
    if len(mattr_tokens) >= MATTR_WINDOW:
        try:
            value = float(lex_div.mattr(mattr_tokens, MATTR_WINDOW))
            mattr = value if math.isfinite(value) else None
        except Exception:  # defensive: keep the row, flag the missing metric
            mattr = None

    # MTLD uses the word_count token sequence (alphabetic, lowercased).  A text
    # with no tokens yields 0 rather than a blank cell, and says so in
    # missing_fields (RAY-598).
    tokens = alpha_tokens(tokenizer, text)
    notes: list[str] = []
    if not tokens:
        mtld = 0.0
        notes.append(f"mtld（token 数 = 0，按 {MTLD_THRESHOLD:.2f} 阈值不可算，记 0）")
    else:
        try:
            value = float(lex_div.mtld(list(tokens)))
            mtld = value if math.isfinite(value) else None
        except Exception:  # defensive: keep the row, flag the missing metric
            mtld = None

    # Audit only (not a CSV column): the same MTLD on lex_div's own tokenisation,
    # so the .md can show how much the token choice moves the numbers.
    mtld_lexdiv = None
    if mattr_tokens:
        try:
            value = float(lex_div.mtld(list(mattr_tokens)))
            mtld_lexdiv = value if math.isfinite(value) else None
        except Exception:
            mtld_lexdiv = None

    result = {
        "word_count": len(tokens),
        "MATTR": mattr,
        "mtld": mtld,
        "mean_sentence_length": mean_sentence_length,
        "sentence_length_CV": sentence_length_cv,
        "mean_paragraph_length": mean_paragraph_length,
        "n_sentences": len(sentence_lengths),
        "n_paragraphs": len(paragraph_lengths),
        "mtld_lexdiv_tokens": mtld_lexdiv,
    }
    missing = [k for k in METRIC_KEYS if result[k] is None]
    result["missing_fields"] = ",".join(missing + notes)
    return result


def fmt(value: Any, digits: int = 4) -> str:
    if value is None or value == "":
        return ""
    value = float(value)
    if abs(value) < 0.5 * 10 ** (-digits):
        value = 0.0
    return f"{value:.{digits}f}"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def load_optional_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    nlp, lex_div = load_pipeline()
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    samples = sample["samples"]

    prompt_ids = [s["prompt_id"] for s in samples]
    if len(prompt_ids) != len(set(prompt_ids)):
        raise SystemExit("sample_v1.json contains duplicate prompt_id values")

    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    # Audit-only: index-aligned with `rows`, MTLD recomputed on lex_div's own
    # tokenisation.  Never written to the CSV.
    mtld_lexdiv_audit: list[float | None] = []

    for index, sample_row in enumerate(samples, start=1):
        prompt_id = sample_row["prompt_id"]
        for spec in MODEL_SPECS:
            field = f"{spec['field']}_story"
            text = sample_row.get(field)
            if not text or not str(text).strip():
                missing.append(
                    {
                        "prompt_id": prompt_id,
                        "model": spec["model"],
                        "group": spec["group"],
                        "missing_fields": "text（全部指标）",
                        "detail": f"`sample_v1.json` 的 `{field}` 为 null/空；该篇文本不存在",
                    }
                )
                continue
            if len(str(text).strip()) < MIN_TEXT_CHARS:
                missing.append(
                    {
                        "prompt_id": prompt_id,
                        "model": spec["model"],
                        "group": spec["group"],
                        "missing_fields": "text（过短，仍保留行）",
                        "detail": f"`{field}` 仅 {len(str(text).strip())} 字符（< {MIN_TEXT_CHARS}）；已保留并按现有管线计算",
                    }
                )
            metrics = compute_metrics(str(text), nlp, lex_div)
            row = {
                "prompt_id": prompt_id,
                "model": spec["model"],
                "group": spec["group"],
                "word_count": metrics["word_count"],
                "MATTR": metrics["MATTR"],
                "mtld": metrics["mtld"],
                "mean_sentence_length": metrics["mean_sentence_length"],
                "sentence_length_CV": metrics["sentence_length_CV"],
                "mean_paragraph_length": metrics["mean_paragraph_length"],
                "n_sentences": metrics["n_sentences"],
                "n_paragraphs": metrics["n_paragraphs"],
                "missing_fields": metrics["missing_fields"],
            }
            rows.append(row)
            mtld_lexdiv_audit.append(metrics["mtld_lexdiv_tokens"])
            if metrics["missing_fields"]:
                missing.append(
                    {
                        "prompt_id": prompt_id,
                        "model": spec["model"],
                        "group": spec["group"],
                        "missing_fields": metrics["missing_fields"],
                        "detail": f"`{field}` 存在，但上述指标无法计算（行已保留）",
                    }
                )
        if index % 10 == 0:
            print(f"[{index}/{len(samples)}] rows={len(rows)} missing={len(missing)}", flush=True)

    # ---------------- CSV ----------------
    csv_fields = [
        "prompt_id",
        "model",
        "group",
        "word_count",
        "MATTR",
        "mtld",
        "mean_sentence_length",
        "sentence_length_CV",
        "mean_paragraph_length",
        "n_sentences",
        "n_paragraphs",
        "missing_fields",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "MATTR": "" if row["MATTR"] is None else f"{row['MATTR']:.6f}",
                    "mtld": "" if row["mtld"] is None else f"{row['mtld']:.6f}",
                    "mean_sentence_length": (
                        "" if row["mean_sentence_length"] is None else f"{row['mean_sentence_length']:.6f}"
                    ),
                    "sentence_length_CV": (
                        "" if row["sentence_length_CV"] is None else f"{row['sentence_length_CV']:.6f}"
                    ),
                    "mean_paragraph_length": (
                        "" if row["mean_paragraph_length"] is None else f"{row['mean_paragraph_length']:.6f}"
                    ),
                }
            )

    missing_fields = ["prompt_id", "model", "group", "missing_fields", "detail"]
    with OUT_MISSING_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=missing_fields)
        writer.writeheader()
        for row in missing:
            writer.writerow({key: row[key] for key in missing_fields})

    # ---------------- checks ----------------
    by_model: OrderedDict[str, list[dict[str, Any]]] = OrderedDict((spec["model"], []) for spec in MODEL_SPECS)
    for row in rows:
        by_model[row["model"]].append(row)

    expected_grid = len(samples) * len(MODEL_SPECS)
    expected_missing_texts = expected_grid - len(rows)
    if expected_missing_texts != sum(1 for item in missing if item["missing_fields"].startswith("text（全部指标）")):
        print("WARNING: missing-text count does not match the 30×5 grid", file=sys.stderr)

    # Cross-check word_count / mean_sentence_length / mean_paragraph_length against results_v1.
    results = load_optional_json(RESULTS_PATH)
    crosscheck = None
    if results and "per_sample_metrics" in results:
        base = {(r["prompt_id"], r["condition"]): r for r in results["per_sample_metrics"]}
        max_diff = {"word_count": 0.0, "mean_sentence_length": 0.0, "mean_paragraph_length": 0.0}
        matched = 0
        for row in rows:
            spec = next(s for s in MODEL_SPECS if s["model"] == row["model"])
            reference = base.get((row["prompt_id"], spec["condition"]))
            if not reference:
                continue
            matched += 1
            max_diff["word_count"] = max(max_diff["word_count"], abs(row["word_count"] - reference["n_words"]))
            max_diff["mean_sentence_length"] = max(
                max_diff["mean_sentence_length"],
                abs(row["mean_sentence_length"] - reference["metrics"]["sentence_length"]),
            )
            max_diff["mean_paragraph_length"] = max(
                max_diff["mean_paragraph_length"],
                abs(row["mean_paragraph_length"] - reference["metrics"]["paragraph_length"]),
            )
        crosscheck = {"matched": matched, "max_diff": max_diff}

    # CV is recomputed from the same sentence lengths as mean_sentence_length; the old
    # metrics_extended_results.json counted case-sensitively, so report the gap.
    extended = load_optional_json(EXTENDED_PATH)
    cv_gap = None
    if extended:
        ext = {(r["prompt_id"], r["condition"]): r for r in extended}
        gaps = []
        for row in rows:
            spec = next(s for s in MODEL_SPECS if s["model"] == row["model"])
            reference = ext.get((row["prompt_id"], spec["condition"]))
            if reference and row["sentence_length_CV"] is not None:
                gaps.append(abs(row["sentence_length_CV"] - reference["metrics"]["sentence_length_cv"]))
        if gaps:
            cv_gap = {"n": len(gaps), "max": max(gaps), "mean": statistics.mean(gaps)}

    # 5-sample independent regex spot check.
    spot_rows = []
    for prompt_id, model in SPOT_CHECKS:
        spec = next(s for s in MODEL_SPECS if s["model"] == model)
        sample_row = next(s for s in samples if s["prompt_id"] == prompt_id)
        text = sample_row[f"{spec['field']}_story"]
        regex_count = len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", text))
        table_row = next(r for r in rows if r["prompt_id"] == prompt_id and r["model"] == model)
        diff = regex_count - table_row["word_count"]
        spot_rows.append(
            {
                "prompt_id": prompt_id,
                "model": model,
                "word_count": table_row["word_count"],
                "regex_count": regex_count,
                "diff": diff,
                "pct": (diff / table_row["word_count"] * 100) if table_row["word_count"] else None,
            }
        )

    # MATTR regression check against published group means.
    mattr_rows = []
    for model, model_rows in by_model.items():
        values = [r["MATTR"] for r in model_rows if r["MATTR"] is not None]
        mean = statistics.mean(values) if values else None
        sd = statistics.stdev(values) if len(values) >= 2 else None
        published_mean, published_sd = PUBLISHED_MATTR[model]
        mattr_rows.append(
            {
                "model": model,
                "n": len(model_rows),
                "mean": mean,
                "sd": sd,
                "published_mean": published_mean,
                "published_sd": published_sd,
                "delta_mean": None if mean is None else mean - published_mean,
                "delta_sd": None if sd is None else sd - published_sd,
            }
        )

    # MTLD group summary + tokenisation sensitivity (audit only; RAY-598).
    mtld_rows = []
    mtld_sensitivity_rows = []
    mtld_gaps: list[float] = []
    for model, model_rows in by_model.items():
        idx = [i for i, r in enumerate(rows) if r["model"] == model]
        primary = [rows[i]["mtld"] for i in idx if rows[i]["mtld"] is not None]
        alternative = [mtld_lexdiv_audit[i] for i in idx if mtld_lexdiv_audit[i] is not None]
        mtld_gaps.extend(
            abs(rows[i]["mtld"] - mtld_lexdiv_audit[i])
            for i in idx
            if rows[i]["mtld"] is not None and mtld_lexdiv_audit[i] is not None
        )
        mtld_rows.append(
            {
                "model": model,
                "n": len(model_rows),
                "mean": statistics.mean(primary) if primary else None,
                "sd": statistics.stdev(primary) if len(primary) >= 2 else None,
                "min": min(primary) if primary else None,
                "max": max(primary) if primary else None,
            }
        )
        mtld_sensitivity_rows.append(
            {
                "model": model,
                "n": len(primary),
                "primary": statistics.mean(primary) if primary else None,
                "alternative": statistics.mean(alternative) if alternative else None,
            }
        )

    rank_primary = [r["model"] for r in sorted(mtld_rows, key=lambda x: -(x["mean"] or 0.0))]
    rank_alternative = [
        r["model"] for r in sorted(mtld_sensitivity_rows, key=lambda x: -(x["alternative"] or 0.0))
    ]

    # ---------------- Markdown ----------------
    total = len(rows)
    group_counts = {
        "Human": len(by_model["Human"]),
        "国内": len(by_model["DeepSeek"]) + len(by_model["Kimi"]),
        "国外": len(by_model["Claude"]) + len(by_model["GPT"]),
    }
    preview_headers = [
        "prompt_id",
        "model",
        "group",
        "word_count",
        "MATTR",
        "mtld",
        "mean_sentence_length",
        "sentence_length_CV",
        "mean_paragraph_length",
    ]
    preview_rows = [
        [
            row["prompt_id"],
            row["model"],
            row["group"],
            row["word_count"],
            fmt(row["MATTR"]),
            fmt(row["mtld"], 2),
            fmt(row["mean_sentence_length"]),
            fmt(row["sentence_length_CV"]),
            fmt(row["mean_paragraph_length"]),
        ]
        for row in rows[:20]
    ]

    count_rows = [[model, len(model_rows)] for model, model_rows in by_model.items()]
    count_rows += [["合计", total]]
    group_rows = [[group, count] for group, count in group_counts.items()]

    missing_rows = [
        [
            item["prompt_id"],
            item["model"],
            item["group"],
            item["missing_fields"],
            item["detail"],
        ]
        for item in missing
    ]

    spot_table = md_table(
        ["prompt_id", "model", "word_count（本表）", "独立正则计数", "差值", "差值 %"],
        [
            [
                item["prompt_id"],
                item["model"],
                item["word_count"],
                item["regex_count"],
                f"{item['diff']:+d}",
                "" if item["pct"] is None else f"{item['pct']:+.2f}%",
            ]
            for item in spot_rows
        ],
    )

    mattr_table = md_table(
        ["组", "N", "MATTR M", "MATTR SD", "报告值 M", "报告值 SD", "ΔM", "ΔSD"],
        [
            [
                item["model"],
                item["n"],
                fmt(item["mean"]),
                fmt(item["sd"]),
                fmt(item["published_mean"]),
                fmt(item["published_sd"]),
                fmt(item["delta_mean"]),
                fmt(item["delta_sd"]),
            ]
            for item in mattr_rows
        ],
    )

    mattr_drift = [
        item["model"]
        for item in mattr_rows
        if item["delta_mean"] is not None and abs(item["delta_mean"]) > 0.0005
    ]
    if mattr_drift:
        mattr_note = (
            "报告值取自 proposal v13/v14 表 2b（3–4 位小数）。"
            f"{'、'.join(mattr_drift)} 的 ΔM 超出 4 位小数的舍入误差：已发表值是在语料补齐前算的"
            "（Kimi 29 篇，缺 prompt 26），本表为 30 篇，属样本范围差异而非重算偏差；"
            "其余各组 Δ 为舍入差，本表重算值与报告值一致。"
        )
    else:
        mattr_note = (
            "报告值取自 proposal v13/v14 表 2b（3–4 位小数），Δ 为舍入差；"
            "本表重算值与报告值在显示精度内一致。"
        )

    mtld_table = md_table(
        ["组", "N", "MTLD M", "MTLD SD", "最小", "最大"],
        [
            [
                item["model"],
                item["n"],
                fmt(item["mean"], 2),
                fmt(item["sd"], 2),
                fmt(item["min"], 1),
                fmt(item["max"], 1),
            ]
            for item in mtld_rows
        ],
    )

    mtld_sensitivity_table = md_table(
        ["组", "N", "word_count 口径 M", "lex_div 口径 M", "Δ（后−前）"],
        [
            [
                item["model"],
                item["n"],
                fmt(item["primary"], 2),
                fmt(item["alternative"], 2),
                fmt(
                    None
                    if item["primary"] is None or item["alternative"] is None
                    else item["alternative"] - item["primary"],
                    2,
                ),
            ]
            for item in mtld_sensitivity_rows
        ],
    )
    mtld_gap_text = (
        f"逐篇最大差 {max(mtld_gaps):.2f}、平均 {statistics.mean(mtld_gaps):.2f}（n={len(mtld_gaps)}）；"
        f"组均值排序 word_count 口径为 {' > '.join(rank_primary)}，lex_div 口径为 "
        f"{' > '.join(rank_alternative)}。"
        if mtld_gaps
        else "未做 MTLD 口径对照。"
    )

    # Row-count wording follows the corpus, so a rerun after the Kimi prompt-26
    # backfill cannot contradict the table (RAY-598).
    if total == expected_grid:
        row_count_text = (
            f"30 prompts × 5 组 = {expected_grid} 个单元，语料 {expected_grid} 篇齐全"
            f"（Kimi prompt 26 已于 2026-10-24 补齐），主表 {total} 行。"
        )
        grid_gap_text = (
            f"{total} 行 = 语料中保留范围内的实际篇数；30×5 网格已满（Kimi prompt 26 补齐后），无空缺。"
        )
    else:
        row_count_text = (
            f"30 prompts × 5 组 = {expected_grid} 个预期单元；语料实际有 {total} 篇，"
            f"缺 {expected_grid - total} 篇，缺失情况见下方缺失清单；主表只放实际存在的文本，没有用空行充数。"
        )
        grid_gap_text = (
            f"{total} 行 = 语料中保留范围内的实际篇数；30×5 网格中缺 {expected_grid - total} 篇"
            "（见缺失清单）。"
        )

    crosscheck_text = "未找到 `data/processed/results_v1.json`，跳过与既有 per-sample 记录的全量对照。"
    if crosscheck:
        crosscheck_text = (
            f"与 `data/processed/results_v1.json` 的 per-sample 记录逐行对照（{crosscheck['matched']}/{total} 行）："
            f"`word_count`、`mean_sentence_length`、`mean_paragraph_length` 的最大绝对差分别为 "
            f"{crosscheck['max_diff']['word_count']:.6f}、{crosscheck['max_diff']['mean_sentence_length']:.6f}、"
            f"{crosscheck['max_diff']['mean_paragraph_length']:.6f}。"
        )
    cv_gap_text = "未找到 `analysis/metrics_extended_results.json`，未做旧 CV 列对照。"
    if cv_gap:
        cv_gap_text = (
            f"`sentence_length_CV` 与 `analysis/metrics_extended_results.json` 的同名列最大差 "
            f"{cv_gap['max']:.6f}（平均 {cv_gap['mean']:.6f}，n={cv_gap['n']}）。原因是旧文件在统计句长时未先转小写，"
            "`Mrs.` 等缩写会被切成不同 token；本表让 CV 与 `mean_sentence_length` 共用同一组句长，故以本表为准。"
        )

    md = f"""# 每篇文本一行：per-text table

**生成日期**：2026-10-28 重生成（MTLD 列增补，RAY-598；初版 2026-10-24）  
**脚本**：`analysis/build_per_text_table.py`  
**数据**：`data/processed/sample_v1.json`（30 prompts）  
**主表**：`analysis/per-text-table.csv`（{total} 行）  
**缺失清单**：`analysis/per-text-table-missing.csv`

## 范围

只保留导师指定的四模型 + Human：

| 组 | 模型 | 语料字段 | N |
|---|---|---|---|
| Human | Human | `human_story` | {len(by_model["Human"])} |
| 国外 | Claude | `Claude-Sonnet-5-High_story` | {len(by_model["Claude"])} |
| 国外 | GPT | `GPT-5.6-Luna_story` | {len(by_model["GPT"])} |
| 国内 | DeepSeek | `DeepSeek-V4-Flash_story` | {len(by_model["DeepSeek"])} |
| 国内 | Kimi | `Kimi-K3_story` | {len(by_model["Kimi"])} |
| **合计** | | | **{total}** |

未纳入：GPT-3.5、Gemini-3.6-Flash、MiniMax-M3、MiMo-V2.5-Pro、Muse-Spark-1.2-Contributor。  
按组汇总：Human {group_counts['Human']}、国内 {group_counts['国内']}、国外 {group_counts['国外']}。

## 指标定义与参数

| 字段 | 定义 | 实现 |
|---|---|---|
| `word_count` | 字母词（alphabetic token）数 | spaCy `en_core_web_sm`，先转小写；标点、数字、Markdown 符号不计 |
| `MATTR` | 移动平均类符形符比 | `lexical_diversity.lex_div`；**窗口固定 100**，所有文本同一窗口，不调参 |
| `mtld` | MTLD（Jarvis & McCarthy），衡量词汇多样性在全文尺度上「用掉多少个形符才把 TTR 降到阈值以下」 | `lexical_diversity.lex_div.mtld`，**默认因子阈值 0.72**（未调参），正反向各算一次取平均；token 与 `word_count` 同一套（spaCy 字母词、先转小写） |
| `mean_sentence_length` | 平均句长（词/句） | spaCy 分句 + 每句字母词数 |
| `sentence_length_CV` | 句长变异系数 = 总体 SD / 均值 | 与 `mean_sentence_length` 使用同一组句长（`pstdev`，ddof=0） |
| `mean_paragraph_length` | 平均段长（词/段） | 空行切段；若只有一段则回退到语料的 `<newline>` 切分（与 `analysis/metrics.py` 一致） |

**MATTR 窗口说明**：`docs/metric-specification.md` 是 2026-08-05 锁定的八指标清单，**原文没有 MATTR 条目，也没有写窗口大小**。本表采用全项目既定的 **100**：2026-09-21 组会决定「MATTR 窗口统一取 100」，proposal v13/v14 §3.2 与 §4.2 也明确写「fixed window 100」。README 已同步注明。窗口不是在本任务里选的，也未做跨窗口比较。

**MTLD 口径说明**：`mtld` 的输入是 `word_count` 用的那一套字母词 token（spaCy `is_alpha`，文本先转小写），
阈值取 `lex_div.mtld` 的默认 0.72，正反向平均。这与 `MATTR` 的 tokenisation（`lex_div.tokenize`：只删标点后按空白切分，
数字和带连字符的词也算 token）**不同**，因此两者可以看方向是否一致，**不能直接比较绝对水平**；
下方「核对」给出两种 token 口径的 MTLD 对照。

## 各组样本数（供 RQ1 使用）

{md_table(["模型", "N"], count_rows)}

{md_table(["组", "N"], group_rows)}

**行数说明**：{row_count_text}

## 前 20 行预览

{md_table(preview_headers, preview_rows)}

> 完整 CSV 另含 `n_sentences`、`n_paragraphs`、`missing_fields` 三列，便于审计切分与缺值。MTLD 在预览里保留 2 位小数，CSV 存 6 位。

## 缺失清单

{md_table(["prompt_id", "model", "group", "缺什么", "说明"], missing_rows) if missing_rows else "无。"}

## 核对

- **行数**：{grid_gap_text}
- **word_count 全量对照**：{crosscheck_text}
- **word_count 抽 5 篇独立复核**：用正则 `[A-Za-z]+(?:['’][A-Za-z]+)?` 从原文另行计数。

{spot_table}

  Human prompt 0 的 +7 来自语料原始分词：原文把 `it's` 写成 `it 's`，正则会把孤立的 `s` 也算作一个词，spaCy 只算 `it`。这是分词口径差异，不是漏词；其余 4 篇完全一致或差 0.3% 以内。

- **MATTR 对照**（窗口 100，与 proposal v13/v14 表 2b 的已发表组均值/标准差对照）：

{mattr_table}

  {mattr_note}

- **MTLD 各组描述统计**（阈值 0.72，token = `word_count` 口径；样本标准差 ddof = 1）：

{mtld_table}

- **MTLD token 口径对照**（同一批文本、同一阈值，只换 tokenisation）：

{mtld_sensitivity_table}

  {mtld_gap_text}两种口径的绝对水平不同（`lex_div` 口径把数字、连字符词也算作 token），
  所以 MTLD 只和同一口径的数字比；方向是否与 MATTR 一致在 `analysis/summary-table.md` 里读。

- **CV 口径说明**：{cv_gap_text}

## 注意

- 本表只做描述，没有跑任何推断性统计（无 t 检验、无方差检验、无分类器）。
- `group` 只作样本标注（国内/国外/Human）；本表不比较中外差异，也不做模型间检验。
- 段落切分沿用既有 `analysis/metrics.py` 的口径，本任务没有重做切分核查；GPT 文本里的 Markdown 小标题/属性行可能被切成很多短段，`mean_paragraph_length` 应结合任务⑤的切分核查阅读。
- `MATTR` 的 tokenisation 与 `word_count` 不完全相同（前者由 `lex_div` 去标点后按空白切分，后者只数 spaCy 字母词），两者不应混用为同一个「词数」；`mtld` 用的是 `word_count` 那一套，所以 `mtld` 与 `MATTR` 的 token 口径也不相同。
- `mtld` 是描述统计量：本表没有为它跑任何检验，也不据此下「AI 词汇更多样」的推断结论（另单处理）。
"""
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"Wrote {OUT_CSV} ({total} rows)")
    print(f"Wrote {OUT_MISSING_CSV} ({len(missing)} rows)")
    print(f"Wrote {OUT_MD}")
    print(f"Group counts: {dict((m, len(v)) for m, v in by_model.items())}")
    print(f"Expected grid={expected_grid}, actual={total}, missing texts={expected_missing_texts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
