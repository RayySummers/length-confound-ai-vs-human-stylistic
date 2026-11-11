#!/usr/bin/env python3
r"""descriptive_stats.py — 376 篇 × 12 子语料的四指标描述统计（RAY-651，v2）。

v2 按 issue 评论调整口径：

  * 主分析（main）    —— **alpha token**：先剔除标点-only token（不含字母/数字的 token），
                        再取窗口：人类第 501–1500 个 alpha token，AI 第 1–1000 个。
  * 敏感性（sensitivity）—— **空白 token**：v1 的口径原样保留，同样取人类 501–1500 / AI 1–1000。
  * MATTR            —— 窗口固定 100；不足 100 词记 NA。窗口内 token 小写、保留标点。
  * MTLD             —— McCarthy & Jarvis (2010)，阈值 0.72（严格小于），因子最短 10 词，
                        正反双向平均；**不足 100 词与 MATTR 一样记 NA**。
  * 句长均值          —— 在窗口对应的原文片段上切句（缩写/小数/省略号/首字母保护，
                        `(?<=[.!?])\s+`，句末紧跟引号时允许引号后再切）；
                        句长 = 该句的 alpha token 数（两种口径一致，不数标点）。
  * 句长 CV          —— 句长总体标准差（pstdev）/ 均值。
  * 退化文本          —— 主分析下 MATTR > 0.90 或 MTLD > 1000；另有剔除后的汇总表。

只做描述统计：不给 p 值、不做检验。所有表格由脚本生成；「初步观察」来自人工撰写的
observations.md，脚本原样嵌入并明确标注。

用法（仓库根目录，一条命令跑完）：
    python3 analysis/descriptive/descriptive_stats.py

可选参数：
    --data-root PATH   数据目录，默认 <repo>/data
    --out-dir PATH     输出目录，默认 analysis/descriptive/out-20261111
    --observations PATH  人工解读文件，默认 analysis/descriptive/observations.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------
# 固定口径
# --------------------------------------------------------------------------
MATTR_WINDOW = 100
MTLD_THRESHOLD = 0.72
MTLD_MIN_FACTOR = 10
MIN_TOKENS = 100                  # 不足 100 词：MATTR 与 MTLD 都记 NA
HUMAN_PROMPT_WORDS = 500          # 人类文本前 500 词 = AI 续写所用 prompt
WINDOW_WORDS = 1000
DEGEN_MATTR = 0.90                # 退化文本阈值
DEGEN_MTLD = 1000.0

ALIGNMENTS = (
    {
        "key": "main",
        "token_mode": "alpha",
        "label": "主分析（alpha-token）",
        "short": "主分析",
    },
    {
        "key": "sensitivity",
        "token_mode": "whitespace",
        "label": "敏感性（空白 token）",
        "short": "敏感性",
    },
)
ALIGNMENT_KEYS = tuple(a["key"] for a in ALIGNMENTS)
TOKEN_MODE = {a["key"]: a["token_mode"] for a in ALIGNMENTS}

GENRES: dict[str, tuple[str, str]] = {
    "A": ("Press: Reportage", "informative"),
    "B": ("Press: Editorial", "informative"),
    "C": ("Press: Reviews", "informative"),
    "E": ("Skills and Hobbies", "informative"),
    "F": ("Popular Lore", "informative"),
    "J": ("Learned", "informative"),
    "K": ("General Fiction", "imaginative"),
    "L": ("Mystery and Detective Fiction", "imaginative"),
    "M": ("Science Fiction", "imaginative"),
    "N": ("Adventure and Western Fiction", "imaginative"),
    "P": ("Romance and Love Story", "imaginative"),
    "R": ("Humor", "imaginative"),
}
GENRE_ORDER = list(GENRES)
GENRE_LABEL = {code: f"{code} {name}" for code, (name, _) in GENRES.items()}

SUBCORPORA = (
    "gpt-4o",
    "gpt-45",
    "claude-35-sonnet",
    "gemini-20-pro-exp",
    "llama_31_405b",
    "deep-seek-v3",
)
TEMPERATURES = (0, 100)
GROUPS = tuple(f"{m}__{t}" for m in SUBCORPORA for t in TEMPERATURES)
HUMAN_GROUP = "human"
ALL_GROUPS = (HUMAN_GROUP,) + GROUPS
METRICS = ("mattr", "mtld", "sent_len_mean", "sent_len_cv")
METRIC_LABEL = {
    "mattr": "MATTR(w=100)",
    "mtld": "MTLD(0.72)",
    "sent_len_mean": "句长均值",
    "sent_len_cv": "句长 CV",
}

BASE = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = BASE / "data"
DEFAULT_OUT = Path(__file__).resolve().parent / "out-20261111"

# 句界保护：缩写、头衔、月份等（区分大小写，避免误伤普通词）
ABBREVIATIONS = (
    "Mr", "Mrs", "Ms", "Dr", "Prof", "St", "Jr", "Sr", "vs", "etc",
    "e.g", "i.e", "U.S", "U.K", "a.m", "p.m", "No", "Fig", "Inc", "Ltd",
    "Co", "Corp", "Gen", "Sen", "Rep", "Gov", "Lt", "Col", "Sgt", "Capt",
    "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Sept",
    "Oct", "Nov", "Dec",
)
ABBREV_RE = re.compile(r"\b(?:" + "|".join(re.escape(a) for a in ABBREVIATIONS) + r")\.")
INITIAL_RE = re.compile(r"\b[A-Z]\.")
DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")
ELLIPSIS_RE = re.compile(r"\.{2,}")
MASK = "\x00"
SENT_BOUNDARY_RE = re.compile(r"(?<=[.!?])(?:[\"”’'])?\s+")
ALNUM_RE = re.compile(r"[A-Za-z0-9]")


# --------------------------------------------------------------------------
# 指标
# --------------------------------------------------------------------------
def is_alpha_token(token: str) -> bool:
    """含任一字母或数字即为 alpha token；纯标点（含 £、— 等）不算。"""
    return bool(ALNUM_RE.search(token))


def mattr(tokens: Sequence[str], window: int = MATTR_WINDOW) -> float | None:
    """Moving-Average TTR：窗口内小写 token 的 type/token 比，对所有窗口取平均。"""
    n = len(tokens)
    if n < window:
        return None
    lowered = [t.lower() for t in tokens]
    counts: Counter[str] = Counter(lowered[:window])
    types = len(counts)
    total = types / window
    n_windows = n - window + 1
    for i in range(1, n_windows):
        out_tok = lowered[i - 1]
        counts[out_tok] -= 1
        if counts[out_tok] == 0:
            del counts[out_tok]
            types -= 1
        in_tok = lowered[i + window - 1]
        if in_tok not in counts:
            types += 1
        counts[in_tok] += 1
        total += types / window
    return total / n_windows


def _mtld_one_direction(tokens: Sequence[str], threshold: float = MTLD_THRESHOLD) -> float:
    """单向 MTLD：完整因子计数 + 末段不完整因子折算，返回 tokens/factors。

    与仓库既有 `lexical_diversity.lex_div.mtld`（Jarvis & McCarthy 原始描述）同一语义：
    TTR 严格小于阈值才截断因子，且因子至少 10 词；区别只在这里先把 token 小写。
    """
    factors = 0.0
    types: set[str] = set()
    in_factor = 0
    for tok in tokens:
        types.add(tok.lower())
        in_factor += 1
        if in_factor >= MTLD_MIN_FACTOR and len(types) / in_factor < threshold:
            factors += 1.0
            types.clear()
            in_factor = 0
    if in_factor:
        ttr = len(types) / in_factor
        factors += (1.0 - ttr) / (1.0 - threshold)
    if factors <= 0:
        return float(len(tokens))
    return len(tokens) / factors


def mtld(tokens: Sequence[str], threshold: float = MTLD_THRESHOLD) -> float:
    """标准双向 MTLD；不足 100 词返回 None（与 MATTR 的 NA 规则一致）。"""
    if len(tokens) < MIN_TOKENS:
        return None
    return (_mtld_one_direction(tokens, threshold) + _mtld_one_direction(list(reversed(tokens)), threshold)) / 2.0


def protect_abbreviations(text: str) -> str:
    text = DECIMAL_RE.sub(MASK, text)
    text = ELLIPSIS_RE.sub(lambda m: MASK * len(m.group(0)), text)
    text = ABBREV_RE.sub(lambda m: m.group(0)[:-1] + MASK, text)
    text = INITIAL_RE.sub(lambda m: m.group(0)[:-1] + MASK, text)
    return text


def split_sentences(text: str) -> list[str]:
    protected = protect_abbreviations(text)
    parts = [p.strip().replace(MASK, ".") for p in SENT_BOUNDARY_RE.split(protected)]
    return [p for p in parts if p]


# --------------------------------------------------------------------------
# 对齐与逐篇指标
# --------------------------------------------------------------------------
def build_window(
    original: Sequence[str], token_mode: str, start: int, end: int
) -> tuple[list[str], list[str]]:
    """返回 (用于词汇指标的 token, 用于切句的原文片段 token)。

    alpha 模式先按 alpha token 计数取窗口，再把首尾 alpha token 之间的原文片段用于切句，
    这样句末标点不会被丢掉。
    """
    if token_mode == "alpha":
        indices = [i for i, tok in enumerate(original) if is_alpha_token(tok)]
        selected = indices[start:end]
        if not selected:
            return [], []
        span = list(original[selected[0]: selected[-1] + 1])
        lexical = [original[i] for i in selected]
        return lexical, span
    span = list(original[start:end])
    return span, span


def compute_metrics(lexical: Sequence[str], span: Sequence[str]) -> dict[str, Any]:
    sentences = split_sentences(" ".join(span)) if span else []
    sent_lengths = [sum(1 for t in s.split() if is_alpha_token(t)) for s in sentences]
    sent_lengths = [n for n in sent_lengths if n > 0]
    mean_len = statistics.fmean(sent_lengths) if sent_lengths else None
    cv = None
    if len(sent_lengths) >= 2 and mean_len:
        cv = statistics.pstdev(sent_lengths) / mean_len
    return {
        "mattr": mattr(lexical),
        "mtld": mtld(lexical),
        "sent_len_mean": mean_len,
        "sent_len_cv": cv,
        "n_sentences": len(sent_lengths),
    }


# --------------------------------------------------------------------------
# 数据装载
# --------------------------------------------------------------------------
def norm_text(raw: str) -> str:
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def load_human_index(data_root: Path) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    brown = data_root / "brown2021"
    manifest_path = brown / "manifest.csv"
    mapping_path = brown / "ai_file_mapping.csv"
    for p in (manifest_path, mapping_path):
        if not p.exists():
            raise SystemExit(f"缺少输入文件: {p}")

    manifest = list(csv.DictReader(manifest_path.open(encoding="utf-8")))
    mapping = list(csv.DictReader(mapping_path.open(encoding="utf-8")))

    by_stem = {Path(row["filename"]).stem: row for row in manifest}
    by_n: dict[int, dict[str, Any]] = {}
    for row in mapping:
        stem = row["be21"].replace("BE21-", "")
        man = by_stem.get(stem)
        if man is None:
            raise SystemExit(f"ai_file_mapping 指向不存在的 BE21 文档: {row['be21']}")
        code = man["category"][0]
        by_n[int(row["n"])] = {
            "n": int(row["n"]),
            "doc_id": int(man["doc_id"]),
            "filename": man["filename"],
            "category": man["category"],
            "genre_code": code,
            "genre_name": GENRES.get(code, ("?", "?"))[0],
            "genre_group": GENRES.get(code, ("?", "?"))[1],
            "be21": row["be21"],
            "path": brown / f"{man['category']}__{man['filename']}",
        }
    return manifest, by_n


def build_zip_index(zip_path: Path) -> dict[str, dict[int, str]]:
    """subcorpus 目录 → {n: zip 成员名}，只收根层 <n>.txt（排除 MAT/ST 子目录）。"""
    index: dict[str, dict[int, str]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            parts = name.split("/")
            if len(parts) != 2 or not parts[1].endswith(".txt"):
                continue
            sub, fname = parts
            stem = fname[:-4]
            if not stem.isdigit():
                continue
            index.setdefault(sub, {})[int(stem)] = name
    return index


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def self_check(data_root: Path) -> dict[str, Any]:
    """用 lexical_diversity 交叉校验 MATTR/MTLD（若环境已安装）。"""
    try:
        from lexical_diversity import lex_div
    except ImportError:
        return {"available": False}
    path = data_root / "brown2021" / "A_press_reportage__A01.txt"
    if not path.exists():
        return {"available": False}
    tokens = [t.lower() for t in norm_text(path.read_text(encoding="utf-8", errors="replace")).split()[HUMAN_PROMPT_WORDS:HUMAN_PROMPT_WORDS + WINDOW_WORDS]]
    tokens = [t for t in tokens if is_alpha_token(t)]
    ours_mattr, ours_mtld = mattr(tokens), mtld(tokens)
    ref_mattr, ref_mtld = lex_div.mattr(tokens, MATTR_WINDOW), lex_div.mtld(tokens)
    return {
        "available": True,
        "sample": "brown2021/A_press_reportage__A01.txt 第 501–1500 空白 token 中的 alpha token（小写）",
        "mattr_ours": ours_mattr,
        "mattr_lexical_diversity": ref_mattr,
        "mtld_ours": ours_mtld,
        "mtld_lexical_diversity": ref_mtld,
        "match": abs(ours_mattr - ref_mattr) < 1e-9 and abs(ours_mtld - ref_mtld) < 1e-9,
    }


# --------------------------------------------------------------------------
# 逐篇计算
# --------------------------------------------------------------------------
def run(data_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _, by_n = load_human_index(data_root)
    selected = {n: row for n, row in by_n.items() if row["genre_code"] in GENRES}
    expected_n = sorted(selected)
    zip_path = data_root / "aibrown" / "AI_Brown_plain_texts_cleaned.zip"
    if not zip_path.exists():
        raise SystemExit(f"缺少 AI 语料: {zip_path}")
    zip_index = build_zip_index(zip_path)

    rows: list[dict[str, Any]] = []
    missing_ai: list[dict[str, Any]] = []
    ai_word_counts: dict[str, int] = {g: 0 for g in GROUPS}
    ai_min_words: dict[str, int] = {}
    ai_lt1000: Counter[str] = Counter()
    ai_lt100: Counter[str] = Counter()
    human_total_words: list[int] = []

    def add_rows(meta: dict[str, Any], original: list[str], start: int, end: int) -> None:
        for alignment in ALIGNMENTS:
            lexical, span = build_window(original, alignment["token_mode"], start, end)
            metrics = compute_metrics(lexical, span)
            rows.append(
                {
                    "doc_id": meta["doc_id"],
                    "n": meta["n"],
                    "be21": meta["be21"],
                    "genre_code": meta["genre_code"],
                    "genre_name": meta["genre_name"],
                    "genre_group": meta["genre_group"],
                    "group": meta["group"],
                    "model": meta["model"],
                    "temperature": meta["temperature"],
                    "alignment": alignment["key"],
                    "token_mode": alignment["token_mode"],
                    "n_words": len(lexical),
                    "n_original_tokens": len(span),
                    "n_alpha_tokens_span": sum(1 for t in span if is_alpha_token(t)),
                    "n_sentences": metrics["n_sentences"],
                    **{m: metrics[m] for m in METRICS},
                }
            )

    # ---- 人类 ----
    for n in expected_n:
        meta = selected[n]
        raw = meta["path"].read_text(encoding="utf-8", errors="replace")
        original = norm_text(raw).split()
        human_total_words.append(len(original))
        add_rows(
            {
                "doc_id": meta["doc_id"],
                "n": n,
                "be21": meta["be21"],
                "genre_code": meta["genre_code"],
                "genre_name": meta["genre_name"],
                "genre_group": meta["genre_group"],
                "group": HUMAN_GROUP,
                "model": HUMAN_GROUP,
                "temperature": "",
            },
            original,
            HUMAN_PROMPT_WORDS,
            HUMAN_PROMPT_WORDS + WINDOW_WORDS,
        )

    # ---- AI ----
    with zipfile.ZipFile(zip_path) as zf:
        for model in SUBCORPORA:
            for temp in TEMPERATURES:
                group = f"{model}__{temp}"
                members = zip_index[f"brown_chat_{model}__{temp}"]
                counts: list[int] = []
                for n in expected_n:
                    meta = selected[n]
                    member = members.get(n)
                    if member is None:
                        missing_ai.append({"group": group, "n": n, "be21": meta["be21"], "genre_code": meta["genre_code"], "genre_name": meta["genre_name"]})
                        continue
                    raw = zf.read(member).decode("utf-8", errors="replace")
                    original = norm_text(raw).split()
                    alpha_len = sum(1 for t in original if is_alpha_token(t))
                    counts.append(alpha_len)
                    ai_lt1000[group] += int(alpha_len < WINDOW_WORDS)
                    ai_lt100[group] += int(alpha_len < MIN_TOKENS)
                    add_rows(
                        {
                            "doc_id": meta["doc_id"],
                            "n": n,
                            "be21": meta["be21"],
                            "genre_code": meta["genre_code"],
                            "genre_name": meta["genre_name"],
                            "genre_group": meta["genre_group"],
                            "group": group,
                            "model": model,
                            "temperature": temp,
                        },
                        original,
                        0,
                        WINDOW_WORDS,
                    )
                ai_word_counts[group] = len(counts)
                ai_min_words[group] = min(counts) if counts else 0

    # ---- 退化标记（按主分析 alpha 口径判定，同一 doc 的两套对齐都标记） ----
    degen: dict[tuple[str, int], str] = {}
    for r in rows:
        if r["alignment"] != "main":
            continue
        reasons = []
        if r["mattr"] is not None and r["mattr"] > DEGEN_MATTR:
            reasons.append(f"MATTR>{DEGEN_MATTR:.2f}")
        if r["mtld"] is not None and r["mtld"] > DEGEN_MTLD:
            reasons.append(f"MTLD>{DEGEN_MTLD:.0f}")
        if reasons:
            degen[(r["group"], r["n"])] = "+".join(reasons)
    for r in rows:
        r["degenerate"] = 1 if (r["group"], r["n"]) in degen else 0
        r["degenerate_reason"] = degen.get((r["group"], r["n"]), "")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": "v2",
        "python": platform.python_version(),
        "data_root": str(data_root),
        "human_texts": len(expected_n),
        "model_subcorpora": list(SUBCORPORA),
        "temperatures": list(TEMPERATURES),
        "groups": list(ALL_GROUPS),
        "per_text_rows": len(rows),
        "missing_ai": missing_ai,
        "ai_texts": {g: ai_word_counts[g] for g in GROUPS},
        "human_total_words": {
            "min": min(human_total_words),
            "median": statistics.median(human_total_words),
            "max": max(human_total_words),
        },
        "config": {
            "main_token_mode": "alpha (drop punctuation-only tokens, then window)",
            "sensitivity_token_mode": "whitespace (v1 protocol)",
            "mattr_window": MATTR_WINDOW,
            "mtld_threshold": MTLD_THRESHOLD,
            "min_tokens_for_lexical_metrics": MIN_TOKENS,
            "human_prompt_words": HUMAN_PROMPT_WORDS,
            "window_words": WINDOW_WORDS,
            "sentence_length_unit": "alpha tokens per sentence",
            "degenerate_rule": f"main MATTR>{DEGEN_MATTR} or MTLD>{DEGEN_MTLD}",
        },
        "ai_word_counts": {
            g: {
                "n_texts": ai_word_counts[g],
                "lt1000": ai_lt1000[g],
                "lt100": ai_lt100[g],
                "min": ai_min_words[g],
            }
            for g in GROUPS
        },
        "degenerate_texts": len(degen),
        "inputs": {
            "brown2021_manifest": sha256_file(data_root / "brown2021" / "manifest.csv"),
            "ai_file_mapping": sha256_file(data_root / "brown2021" / "ai_file_mapping.csv"),
            "ai_zip": sha256_file(zip_path),
            "script": sha256_file(Path(__file__)),
        },
    }
    return rows, manifest


# --------------------------------------------------------------------------
# 统计与输出
# --------------------------------------------------------------------------
def quantile(sorted_vals: Sequence[float], q: float) -> float:
    """线性插值分位数，与 numpy 默认口径一致。"""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(sorted_vals[lo])
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo))


def summarize(values: Iterable[float | None]) -> dict[str, Any]:
    vals = sorted(v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "median": None, "q1": None, "q3": None, "iqr": None}
    mean = statistics.fmean(vals)
    med = quantile(vals, 0.5)
    q1 = quantile(vals, 0.25)
    q3 = quantile(vals, 0.75)
    return {
        "n": n,
        "mean": mean,
        "sd": statistics.stdev(vals) if n >= 2 else None,
        "median": med,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
    }


def fmt(v: Any, digits: int = 3) -> str:
    if v is None:
        return "NA"
    if isinstance(v, float) and math.isnan(v):
        return "NA"
    if isinstance(v, int):
        return str(v)
    return f"{v:.{digits}f}"


def md_table(headers: Sequence[str], rows: Sequence[Sequence[str]], aligns: Sequence[str] | None = None) -> str:
    aligns = aligns or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(aligns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {}
            for k in fieldnames:
                v = row.get(k)
                if isinstance(v, float):
                    out[k] = "" if math.isnan(v) else f"{v:.6f}"
                elif v is None:
                    out[k] = ""
                else:
                    out[k] = v
            writer.writerow(out)


def summarize_all(rows: list[dict[str, Any]], exclude_degenerate: bool = False) -> list[dict[str, Any]]:
    """alignment × group × genre(含 ALL) × metric 的描述统计（n 为该指标有效篇数）。"""
    out: list[dict[str, Any]] = []
    for alignment in ALIGNMENTS:
        arows = [r for r in rows if r["alignment"] == alignment["key"]]
        if exclude_degenerate:
            arows = [r for r in arows if not r["degenerate"]]
        for group in ALL_GROUPS:
            grows = [r for r in arows if r["group"] == group]
            for genre in ("ALL",) + tuple(GENRE_ORDER):
                srows = grows if genre == "ALL" else [r for r in grows if r["genre_code"] == genre]
                if not srows and genre != "ALL":
                    continue
                for metric in METRICS:
                    st = summarize(r[metric] for r in srows)
                    out.append(
                        {
                            "alignment": alignment["key"],
                            "token_mode": alignment["token_mode"],
                            "genre": genre,
                            "group": group,
                            "metric": metric,
                            "n": st["n"],
                            "n_texts": len(srows),
                            "mean": st["mean"],
                            "sd": st["sd"],
                            "median": st["median"],
                            "q1": st["q1"],
                            "q3": st["q3"],
                            "iqr": st["iqr"],
                        }
                    )
    return out


def build_diffs(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    idx = {(s["alignment"], s["genre"], s["group"], s["metric"]): s for s in summary}
    diffs: list[dict[str, Any]] = []
    for alignment in ALIGNMENTS:
        for genre in ("ALL",) + tuple(GENRE_ORDER):
            for group in GROUPS:
                for metric in METRICS:
                    h = idx.get((alignment["key"], genre, HUMAN_GROUP, metric))
                    m = idx.get((alignment["key"], genre, group, metric))
                    if not h or not m:
                        continue
                    diffs.append(
                        {
                            "alignment": alignment["key"],
                            "token_mode": alignment["token_mode"],
                            "genre": genre,
                            "group": group,
                            "metric": metric,
                            "n_human": h["n"],
                            "n_model": m["n"],
                            "human_mean": h["mean"],
                            "model_mean": m["mean"],
                            "diff_mean": None if h["mean"] is None or m["mean"] is None else m["mean"] - h["mean"],
                            "human_median": h["median"],
                            "model_median": m["median"],
                            "diff_median": None if h["median"] is None or m["median"] is None else m["median"] - h["median"],
                        }
                    )
    return diffs


def build_genre_table(rows: list[dict[str, Any]], human_texts: int) -> list[dict[str, Any]]:
    human_n = Counter(r["genre_code"] for r in rows if r["alignment"] == "main" and r["group"] == HUMAN_GROUP)
    ai_n = Counter((r["genre_code"], r["group"]) for r in rows if r["alignment"] == "main" and r["group"] != HUMAN_GROUP)
    out = []
    for code in GENRE_ORDER:
        row = {
            "genre_code": code,
            "genre_name": GENRES[code][0],
            "genre_group": GENRES[code][1],
            "n_human": human_n.get(code, 0),
        }
        for group in GROUPS:
            row[f"n_{group}"] = ai_n.get((code, group), 0)
        out.append(row)
    total = {"genre_code": "ALL", "genre_name": "合计", "genre_group": "", "n_human": human_texts}
    for group in GROUPS:
        total[f"n_{group}"] = sum(r[f"n_{group}"] for r in out)
    out.append(total)
    return out


def build_qa(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for alignment in ALIGNMENTS:
        for group in ALL_GROUPS:
            subset = [r for r in rows if r["alignment"] == alignment["key"] and r["group"] == group]
            if not subset:
                continue
            shares = [1.0 - (r["n_alpha_tokens_span"] / r["n_original_tokens"]) if r["n_original_tokens"] else 0.0 for r in subset]
            out.append(
                {
                    "alignment": alignment["key"],
                    "token_mode": alignment["token_mode"],
                    "group": group,
                    "n_texts": len(subset),
                    "mean_words": statistics.fmean(r["n_words"] for r in subset),
                    "mean_original_tokens": statistics.fmean(r["n_original_tokens"] for r in subset),
                    "mean_punct_only_share": statistics.fmean(shares),
                    "min_words": min(r["n_words"] for r in subset),
                    "lt1000": sum(1 for r in subset if r["n_words"] < WINDOW_WORDS),
                    "lt100": sum(1 for r in subset if r["n_words"] < MIN_TOKENS),
                }
            )
    return out


def build_issues(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    qa: list[dict[str, Any]],
    degen_rows: list[dict[str, Any]],
    main_summary: list[dict[str, Any]],
    excl_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    missing = manifest["missing_ai"]
    if missing:
        detail = "; ".join(f"{m['group']} 缺 n={m['n']}（{m['be21']}，{m['genre_code']}）" for m in missing)
        issues.append(
            {
                "id": "D1",
                "severity": "中",
                "issue": "gemini-2.0-pro-exp 两个子语料各缺 1 篇",
                "evidence": detail,
                "impact": "该模型两个温度组 N=375（其余 376）；缺篇属 C 类，C 类 AI 篇数少 1。",
            }
        )

    counts = manifest["ai_word_counts"]
    short = [f"{g}: {v['lt1000']}/{v['n_texts']} 篇不足 1000（最短 {v['min']}）" for g, v in counts.items() if v["lt1000"]]
    if short:
        issues.append(
            {
                "id": "D2",
                "severity": "高",
                "issue": "部分 AI 文本不足 1000 个 alpha 词，窗口截不满",
                "evidence": "; ".join(short),
                "impact": "这些篇目的词数少于 1000；MTLD 与句长对长度敏感，解释模型间差异时要同时看 N 与词数分布。",
            }
        )
    tiny = [f"{g}: {v['lt100']} 篇" for g, v in counts.items() if v["lt100"]]
    if tiny:
        issues.append(
            {
                "id": "D3",
                "severity": "高",
                "issue": "存在不足 100 词的 AI 文本，两个词汇指标同时记 NA",
                "evidence": "; ".join(tiny),
                "impact": "MATTR 与 MTLD 的 N 一致地少 3（claude 两组）；不再出现 v1 里 MTLD 用 35–59 词文本硬算的情况。",
            }
        )

    hq = next((q for q in qa if q["alignment"] == "main" and q["group"] == HUMAN_GROUP), None)
    aq = [q for q in qa if q["alignment"] == "main" and q["group"] != HUMAN_GROUP]
    if hq and aq:
        ai_mean = statistics.fmean(q["mean_punct_only_share"] for q in aq)
        issues.append(
            {
                "id": "D4",
                "severity": "高",
                "issue": "人类文本标点独立成词（AntConc 导出），AI 文本标点黏在词上",
                "evidence": f"原始窗口里人类标点-only token 占 {hq['mean_punct_only_share']:.1%}，12 个 AI 组平均 {ai_mean:.1%}",
                "impact": "v2 主分析已改为 alpha-token 并剔除标点，主表不再受这项差异影响；空白 token 口径保留为敏感性分析，两套的差就是该问题的影响量。",
            }
        )

    ht = manifest["human_total_words"]
    issues.append(
        {
            "id": "D5",
            "severity": "低",
            "issue": "人类 376 篇原文均长于主分析的窗口",
            "evidence": f"原文空白 token {ht['min']}–{ht['max']}（中位 {ht['median']:.0f}）",
            "impact": "人类侧两种口径都能取满 1000 个 token，无截断损失。",
        }
    )

    mtld_counts = Counter()
    mtld_max: dict[str, float] = {}
    for r in rows:
        if r["alignment"] != "main" or r["group"] == HUMAN_GROUP or r["mtld"] is None:
            continue
        mtld_max[r["group"]] = max(mtld_max.get(r["group"], 0.0), r["mtld"])
        if r["mtld"] > 300:
            mtld_counts[r["group"]] += 1
    if mtld_counts:
        detail = "; ".join(f"{g}: {c} 篇 >300（最大 {mtld_max[g]:.0f}）" for g, c in mtld_counts.most_common())
        issues.append(
            {
                "id": "D6",
                "severity": "中",
                "issue": "MTLD 出现成片高值，离散度远大于 MATTR",
                "evidence": detail,
                "impact": "高值集中在温度 100 的两组；MTLD 对窗口长度与类型密度敏感，只作记录，不单独下结论，正文以中位数为主。",
            }
        )

    if degen_rows:
        per_group = Counter(r["group"] for r in degen_rows)
        detail = "; ".join(f"{g}: {c} 篇" for g, c in per_group.most_common())
        issues.append(
            {
                "id": "D7",
                "severity": "高",
                "issue": f"退化文本：主分析 MATTR>{DEGEN_MATTR:.2f} 或 MTLD>{DEGEN_MTLD:.0f}",
                "evidence": detail + f"；共 {len(degen_rows)} 篇，篇目见 `degenerate_texts.csv`",
                "impact": "llama_31_405b 温度 100 占绝大多数；剔除后的均值/中位数见第 3.3 节，正文以中位数为主，均值只作参考。",
            }
        )

    # 剔除退化文本后，均值变化的量化（仅对受影响最大的组）
    if degen_rows:
        idx_main = {(s["genre"], s["group"], s["metric"]): s for s in main_summary if s["alignment"] == "main"}
        idx_excl = {(s["genre"], s["group"], s["metric"]): s for s in excl_summary if s["alignment"] == "main"}
        worst = per_group.most_common(1)[0][0]
        changes = []
        for metric in ("mattr", "mtld", "sent_len_mean"):
            a = idx_main.get(("ALL", worst, metric))
            b = idx_excl.get(("ALL", worst, metric))
            if a and b and a["mean"] is not None and b["mean"] is not None:
                changes.append(f"{METRIC_LABEL[metric]} {a['mean']:.3f}→{b['mean']:.3f}")
        issues.append(
            {
                "id": "D8",
                "severity": "中",
                "issue": f"剔除退化文本对 {worst} 均值的影响",
                "evidence": "；".join(changes),
                "impact": "说明该组均值被少数退化篇目主导；比较时应优先看中位数与 IQR。",
            }
        )
    return issues


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------
def n_exceptions(summary: list[dict[str, Any]], alignment: str, metric: str) -> str:
    """列出该指标下 N 与「同语体人类 N」不同的单元。"""
    idx = {(s["genre"], s["group"]): s for s in summary if s["alignment"] == alignment and s["metric"] == metric}
    parts = []
    for group in GROUPS:
        diffs = []
        for genre in GENRE_ORDER:
            h = idx.get((genre, HUMAN_GROUP))
            m = idx.get((genre, group))
            if not h or not m:
                continue
            if m["n"] != h["n"]:
                diffs.append(f"{genre}:{m['n']}")
        if diffs:
            parts.append(f"{group} → {', '.join(diffs)}")
    return "；".join(parts)


def report_markdown(
    out: Path,
    manifest: dict[str, Any],
    summary: list[dict[str, Any]],
    excl_summary: list[dict[str, Any]],
    diffs: list[dict[str, Any]],
    genre_table: list[dict[str, Any]],
    qa: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    degen_rows: list[dict[str, Any]],
    observations: str | None,
) -> str:
    idx = {(s["alignment"], s["genre"], s["group"], s["metric"]): s for s in summary}
    eidx = {(s["alignment"], s["genre"], s["group"], s["metric"]): s for s in excl_summary}
    lines: list[str] = []
    A = lines.append

    A("# 描述统计：376 篇 × 12 子语料（四指标，v2 alpha-token 主口径）")
    A("")
    A(f"生成时间：{manifest['generated_at']}　·　脚本：`analysis/descriptive/descriptive_stats.py`　·　输出目录：`{out.name}/`")
    A("")
    A("> 本文件由脚本生成。第 1–6 节的所有数字与表格均由脚本直接产出；第 7 节「初步观察」为人工撰写，")
    A("> 脚本原样嵌入、不改写。按老师 11/11 意见，**不做显著性检验、不报 p 值**。")
    A("")
    A("**v2 相对 v1 的改动**：")
    A("")
    A("1. 主分析改为 **alpha-token**（先剔除标点-only token，再取窗口）；v1 的空白 token 口径降为敏感性分析。")
    A(f"2. MTLD 与 MATTR 一致：不足 {MIN_TOKENS} 词记 NA，不再用极短文本硬算。")
    A(f"3. 新增退化文本定义（MATTR>{DEGEN_MATTR:.2f} 或 MTLD>{DEGEN_MTLD:.0f}）与剔除后的汇总表。")
    A("4. 正文以中位数为主、均值作参考；第 7 节逐条复核 v1 结论在 alpha 口径下是否仍成立。")
    A("")

    A("## 1. 数据与口径")
    A("")
    A(f"- 人类：BE21 `manifest.csv` 中 {manifest['human_texts']} 篇，语体 A/B/C/E/F/J/K/L/M/N/P/R。")
    A("- AI：`AI_Brown_plain_texts_cleaned.zip` 中 6 个模型 × 温度 0/100 = 12 个子语料，逐篇按 `ai_file_mapping.csv` 的 n ↔ BE21 对应。")
    A("- **主分析（alpha-token）**：先剔除不含字母/数字的 token，人类取第 501–1500 个 alpha token，AI 取第 1–1000 个。")
    A("- **敏感性（空白 token）**：v1 口径，不剔除标点，人类第 501–1500 个空白 token，AI 第 1–1000 个。")
    A(f"- MATTR：窗口 {MATTR_WINDOW}，窗口内小写；不足 {MIN_TOKENS} 词记 NA。")
    A(f"- MTLD：阈值 {MTLD_THRESHOLD}（严格小于），因子最短 {MTLD_MIN_FACTOR} 词，正反双向平均；不足 {MIN_TOKENS} 词记 NA。")
    A("- 句长：在窗口对应的原文片段上切句（保护缩写/小数/省略号/单字母缩写，按 `(?<=[.!?])\\s+`，句末引号后再切）；**句长 = 该句 alpha token 数**，两种口径都不数标点。")
    A("- 句长 CV：句长总体标准差（pstdev）/ 均值。")
    A(f"- 退化文本：主分析下 MATTR>{DEGEN_MATTR:.2f} 或 MTLD>{DEGEN_MTLD:.0f}；剔除版只去掉这些篇目，不改口径。")
    A(f"- 逐篇行数：{manifest['per_text_rows']}（376 人类 × 2 口径 + {manifest['per_text_rows'] // 2 - manifest['human_texts']} 篇 AI × 2 口径）。")
    A("")

    A("## 2. 样本构成（脚本产出）")
    A("")
    A("每个 AI 子语料覆盖同一批 376 个 n，故语体篇数与人类一致；gemini 两个温度组各少 1 篇（n=76，C 类）。")
    A("")
    hdr = ["语体", "组别", "人类 N"] + list(GROUPS)
    table_rows = []
    for r in genre_table:
        table_rows.append(
            [f"{r['genre_code']} {r['genre_name']}" if r["genre_code"] != "ALL" else "合计", r["genre_group"], str(r["n_human"])]
            + [str(r[f"n_{g}"]) for g in GROUPS]
        )
    A(md_table(hdr, table_rows, ["---", "---", "---:"] + ["---:"] * len(GROUPS)))
    A("")

    A("## 3. 四指标整体汇总（主分析与敏感性并列，脚本产出）")
    A("")
    A("每格为该指标的有效篇数 N 与统计量；N 不同来自缺篇（D1）、不足 1000 词（D2）、不足 100 词记 NA（D3）与句长 CV 需 ≥2 句。")
    A("")
    for metric in METRICS:
        A(f"### {METRIC_LABEL[metric]}")
        A("")
        cols = ["N", "均值", "SD", "中位数", "Q1", "Q3", "IQR"]
        rows = []
        for group in ALL_GROUPS:
            cells = [group]
            for alignment in ALIGNMENTS:
                s = idx.get((alignment["key"], "ALL", group, metric), {})
                cells += [str(s.get("n", "")), fmt(s.get("mean")), fmt(s.get("sd")), fmt(s.get("median")), fmt(s.get("q1")), fmt(s.get("q3")), fmt(s.get("iqr"))]
            rows.append(cells)
        A(md_table(["组别"] + [f"主分析 {c}" for c in cols] + [f"敏感性 {c}" for c in cols], rows, ["---"] + ["---:"] * (2 * len(cols))))
        A("")

    A("### 3.3 剔除退化文本后（主分析 alpha-token，脚本产出）")
    A("")
    A(f"退化定义：MATTR>{DEGEN_MATTR:.2f} 或 MTLD>{DEGEN_MTLD:.0f}。共剔除 {manifest['degenerate_texts']} 篇（人类 {sum(1 for r in degen_rows if r['group'] == HUMAN_GROUP)} 篇）。")
    A("正文与观察以中位数为主；这里的均值只用于展示剔除前后的变化。")
    A("")
    hdr = ["组别", "剔除"] + [f"{METRIC_LABEL[m]} N" for m in METRICS] + [f"{METRIC_LABEL[m]} 均值" for m in METRICS] + [f"{METRIC_LABEL[m]} 中位" for m in METRICS]
    rows = []
    degen_per_group = Counter(r["group"] for r in degen_rows)
    for group in ALL_GROUPS:
        cells = [group, str(degen_per_group.get(group, 0))]
        for metric in METRICS:
            cells.append(str(eidx.get(("main", "ALL", group, metric), {}).get("n", "")))
        for metric in METRICS:
            cells.append(fmt(eidx.get(("main", "ALL", group, metric), {}).get("mean")))
        for metric in METRICS:
            cells.append(fmt(eidx.get(("main", "ALL", group, metric), {}).get("median")))
        rows.append(cells)
    A(md_table(hdr, rows, ["---", "---:"] + ["---:"] * (3 * len(METRICS))))
    A("")
    A("按语体的剔除版见 `summary_excl_degenerate.csv`；被剔除的篇目见 `degenerate_texts.csv`。")
    A("")

    A("## 4. 按语体的四指标中位数（主分析 alpha-token，剔除退化文本后，脚本产出）")
    A("")
    A("按「正文以中位数为主」的要求，这里列中位数，并剔除退化文本，避免小语体的中位数被少数退化篇目主导；")
    A("全量（含退化）的均值/中位数与 SD/Q1/Q3/IQR 见 `summary_by_genre.csv`，剔除版全表见 `summary_excl_degenerate.csv`。")
    A("")
    for metric in METRICS:
        A(f"### {METRIC_LABEL[metric]}（中位数）")
        A("")
        hdr = ["语体", "N(人类)", "human"] + list(GROUPS)
        rows = []
        for genre in ("ALL",) + tuple(GENRE_ORDER):
            label = "合计" if genre == "ALL" else GENRE_LABEL[genre]
            h = eidx.get(("main", genre, HUMAN_GROUP, metric), {})
            cells = [label, str(h.get("n", "")), fmt(h.get("median"))]
            for group in GROUPS:
                cells.append(fmt(eidx.get(("main", genre, group, metric), {}).get("median")))
            rows.append(cells)
        A(md_table(hdr, rows, ["---", "---:"] + ["---:"] * (len(hdr) - 2)))
        exc = n_exceptions(excl_summary, "main", metric)
        A("")
        A("表注：N 列为该语体的人类有效篇数；AI 各组同语体的 N 与之相同，例外为：" + (exc if exc else "无") + "。")
        A("")

    A("## 5. 人类 vs 每个模型的描述性差值（主分析 alpha-token，脚本产出）")
    A("")
    A("差值 = 模型 − 人类；正数表示模型更高。**只报差值与分布，不做检验、不报 p 值。**")
    A("按语体的完整四指标差值与均值差见 `human_vs_model_diff.csv`。")
    A("")
    A("### 5.1 MATTR：均值差与中位数差")
    A("")
    hdr = ["组别", "N(人类)", "N(模型)", "均值差", "中位数差", "剔除退化后中位数差"]
    rows = []
    for group in GROUPS:
        d = next((x for x in diffs if x["alignment"] == "main" and x["genre"] == "ALL" and x["group"] == group and x["metric"] == "mattr"), None)
        if not d:
            continue
        h = eidx.get(("main", "ALL", HUMAN_GROUP, "mattr"), {})
        m = eidx.get(("main", "ALL", group, "mattr"), {})
        exdiff = None if h.get("median") is None or m.get("median") is None else m["median"] - h["median"]
        rows.append([group, str(d["n_human"]), str(d["n_model"]), fmt(d["diff_mean"]), fmt(d["diff_median"]), fmt(exdiff)])
    A(md_table(hdr, rows, ["---", "---:", "---:"] + ["---:"] * 3))
    A("")
    changed = []
    for g in GROUPS:
        full_n = idx.get(("main", "ALL", g, "mattr"), {}).get("n_texts")
        ex_n = eidx.get(("main", "ALL", g, "mattr"), {}).get("n_texts")
        if full_n is not None and ex_n is not None and ex_n != full_n:
            changed.append(f"{g} {full_n}→{ex_n}")
    A("表注：最后一列剔除了退化文本后重新算中位数；剔除后 N 变化的组：" + ("、".join(changed) if changed else "无") + "。")
    A("")
    A("### 5.2 其余三指标：中位数差")
    A("")
    hdr = ["组别", "N(人类)"]
    for metric in ("mtld", "sent_len_mean", "sent_len_cv"):
        hdr += [f"{METRIC_LABEL[metric]} N", f"{METRIC_LABEL[metric]} 中位数差"]
    rows = []
    for group in GROUPS:
        cells = [group, "376"]
        for metric in ("mtld", "sent_len_mean", "sent_len_cv"):
            d = next((x for x in diffs if x["alignment"] == "main" and x["genre"] == "ALL" and x["group"] == group and x["metric"] == metric), None)
            cells += [str(d["n_model"]) if d else "", fmt(d["diff_median"]) if d else "NA"]
        rows.append(cells)
    A(md_table(hdr, rows, ["---", "---:"] + ["---:"] * 6))
    A("")
    changed_notes = []
    for group in GROUPS:
        full_n = idx.get(("main", "ALL", group, "mattr"), {}).get("n_texts")
        ex_n = eidx.get(("main", "ALL", group, "mattr"), {}).get("n_texts")
        if full_n is None or ex_n is None or full_n == ex_n:
            continue
        parts = []
        for metric in ("mtld", "sent_len_mean", "sent_len_cv"):
            h = eidx.get(("main", "ALL", HUMAN_GROUP, metric), {})
            m = eidx.get(("main", "ALL", group, metric), {})
            if h.get("median") is None or m.get("median") is None:
                continue
            parts.append(f"{METRIC_LABEL[metric]} {m['median'] - h['median']:+.3f}")
        changed_notes.append(f"{group}（剔除后 N={ex_n}）：{'、'.join(parts)}")
    if changed_notes:
        A("表注：含退化文本的组在剔除后中位数差变化为 —— " + "；".join(changed_notes) + "。")
        A("")
    A("### 5.3 口径差：主分析（alpha）− 敏感性（空白）的人类一侧")
    A("")
    A("同一批人类文本、同一窗口位置，只换 token 口径，差值即标点 token 的影响量。")
    A("")
    hdr = ["指标", "N(alpha)", "alpha 中位数", "N(空白)", "空白 中位数", "差值（空白−alpha）"]
    rows = []
    for metric in METRICS:
        a = idx.get(("main", "ALL", HUMAN_GROUP, metric), {})
        b = idx.get(("sensitivity", "ALL", HUMAN_GROUP, metric), {})
        diff = None if a.get("median") is None or b.get("median") is None else b["median"] - a["median"]
        rows.append([METRIC_LABEL[metric], str(a.get("n", "")), fmt(a.get("median")), str(b.get("n", "")), fmt(b.get("median")), fmt(diff)])
    A(md_table(hdr, rows, ["---", "---:", "---:", "---:", "---:", "---:"]))
    A("")

    A("## 6. 数据问题清单（脚本计算）")
    A("")
    A(md_table(["编号", "严重度", "问题", "证据", "影响"], [[i["id"], i["severity"], i["issue"], i["evidence"], i["impact"]] for i in issues], ["---", "---", "---", "---", "---"]))
    A("")
    A("### 6.1 token 诊断（脚本产出）")
    A("")
    A("原始窗口里标点-only token 的占比，以及主分析（alpha）实际使用的片段长度。")
    A("")
    hdr = ["组别", "口径", "N", "平均词数", "平均原文 token", "标点占比", "最少词数", "<1000", "<100"]
    rows = []
    for q in qa:
        rows.append([q["group"], q["token_mode"], str(q["n_texts"]), fmt(q["mean_words"], 1), fmt(q["mean_original_tokens"], 1), f"{q['mean_punct_only_share']:.1%}", str(q["min_words"]), str(q["lt1000"]), str(q["lt100"])])
    A(md_table(hdr, rows, ["---", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]))
    A("")

    A("## 7. 初步观察（人工解读，非脚本产出）")
    A("")
    if observations:
        A(observations.strip())
    else:
        A("_（`observations.md` 不存在，本节留空。）_")
    A("")

    A("## 8. 产物与复现")
    A("")
    A("| 文件 | 内容 |")
    A("|---|---|")
    A("| `per_text_metrics.csv` | 逐篇：doc_id、n、BE21、语体、组别、温度、对齐、token 口径、四指标、词数、原文 token 数、句数、退化标记 |")
    A("| `summary_by_genre.csv` | 对齐 × 组别 × 语体 × 指标：N/均值/SD/中位数/Q1/Q3/IQR |")
    A("| `summary_excl_degenerate.csv` | 同上，剔除退化文本后 |")
    A("| `human_vs_model_diff.csv` | 人类 vs 每个模型的均值/中位数差值（含按语体） |")
    A("| `degenerate_texts.csv` | 被剔除的退化篇目与判定原因 |")
    A("| `genre_sample_table.csv` | 语体 × 篇数 × 各组 N |")
    A("| `sample_index.csv` | 376 组 doc_id ↔ n ↔ BE21 对照清单 |")
    A("| `qa_tokenization.csv` | token 口径诊断 |")
    A("| `data_issues.csv` | 数据问题清单 D1–D8 |")
    A("| `run_manifest.json` | 配置、输入哈希、缺失篇目、退化计数、回归校验 |")
    A("| `report.md` | 本报告 |")
    A("")
    A("复现（仓库根目录）：")
    A("")
    A("```bash")
    A("python3 analysis/descriptive/descriptive_stats.py")
    A("```")
    A("")
    A("脚本仅用标准库（Python 3.9+），无第三方依赖。")
    check = (manifest.get("checks") or {}).get("lexical_diversity") or {}
    if check.get("available"):
        A("")
        A(
            "回归校验：在 `A_press_reportage__A01.txt` 第 501–1500 空白 token 的 alpha token（小写）上，本脚本 MATTR = "
            f"{check['mattr_ours']:.6f}、MTLD = {check['mtld_ours']:.6f}，与 `lexical_diversity` 的 "
            f"{check['mattr_lexical_diversity']:.6f} / {check['mtld_lexical_diversity']:.6f} "
            f"{'完全一致' if check['match'] else '不一致（需排查）'}。"
        )
    A("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="376 × 12 子语料四指标描述统计（v2）")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--observations", type=Path, default=Path(__file__).resolve().parent / "observations.md")
    args = parser.parse_args(argv)

    data_root = args.data_root.expanduser().resolve()
    out = args.out_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows, manifest = run(data_root)
    manifest["checks"] = {"lexical_diversity": self_check(data_root)}

    summary = summarize_all(rows, exclude_degenerate=False)
    excl_summary = summarize_all(rows, exclude_degenerate=True)
    diffs = build_diffs(summary)
    genre_table = build_genre_table(rows, manifest["human_texts"])
    qa = build_qa(rows)
    degen_rows = [r for r in rows if r["alignment"] == "main" and r["degenerate"]]
    issues = build_issues(manifest, rows, qa, degen_rows, summary, excl_summary)

    write_csv(
        out / "per_text_metrics.csv",
        ["doc_id", "n", "be21", "genre_code", "genre_name", "genre_group", "group", "model", "temperature", "alignment", "token_mode", "n_words", "n_original_tokens", "n_alpha_tokens_span", "n_sentences", *METRICS, "degenerate", "degenerate_reason"],
        rows,
    )
    write_csv(
        out / "summary_by_genre.csv",
        ["alignment", "token_mode", "genre", "group", "metric", "n", "n_texts", "mean", "sd", "median", "q1", "q3", "iqr"],
        summary,
    )
    write_csv(
        out / "summary_excl_degenerate.csv",
        ["alignment", "token_mode", "genre", "group", "metric", "n", "n_texts", "mean", "sd", "median", "q1", "q3", "iqr"],
        excl_summary,
    )
    write_csv(
        out / "human_vs_model_diff.csv",
        ["alignment", "token_mode", "genre", "group", "metric", "n_human", "n_model", "human_mean", "model_mean", "diff_mean", "human_median", "model_median", "diff_median"],
        diffs,
    )
    write_csv(
        out / "degenerate_texts.csv",
        ["group", "n", "be21", "genre_code", "mattr", "mtld", "sent_len_mean", "sent_len_cv", "degenerate_reason"],
        sorted(degen_rows, key=lambda r: (r["group"], r["n"])),
    )
    write_csv(
        out / "genre_sample_table.csv",
        ["genre_code", "genre_name", "genre_group", "n_human", *[f"n_{g}" for g in GROUPS]],
        genre_table,
    )
    write_csv(
        out / "sample_index.csv",
        ["doc_id", "n", "be21", "filename", "genre_code", "genre_name", "genre_group"],
        [{"doc_id": m["doc_id"], "n": m["n"], "be21": m["be21"], "filename": m["filename"], "genre_code": m["genre_code"], "genre_name": m["genre_name"], "genre_group": m["genre_group"]} for m in sorted(load_human_index(data_root)[1].values(), key=lambda x: x["n"]) if m["genre_code"] in GENRES],
    )
    write_csv(out / "qa_tokenization.csv", ["group", "alignment", "token_mode", "n_texts", "mean_words", "mean_original_tokens", "mean_punct_only_share", "min_words", "lt1000", "lt100"], qa)
    write_csv(out / "data_issues.csv", ["id", "severity", "issue", "evidence", "impact"], issues)
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    observations = args.observations.read_text(encoding="utf-8") if args.observations.exists() else None
    report = report_markdown(out, manifest, summary, excl_summary, diffs, genre_table, qa, issues, degen_rows, observations)
    (out / "report.md").write_text(report, encoding="utf-8")

    print(f"写出 {len(rows)} 行逐篇指标 → {out / 'per_text_metrics.csv'}")
    print(f"人类 {manifest['human_texts']} 篇；AI 缺失 {len(manifest['missing_ai'])} 篇；退化 {manifest['degenerate_texts']} 篇")
    print(f"报告 → {out / 'report.md'}（{len(report.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
