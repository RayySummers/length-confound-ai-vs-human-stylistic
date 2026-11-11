#!/usr/bin/env python3
r"""descriptive_stats.py — 376 篇 × 12 子语料的四指标描述统计（RAY-651）。

口径由 2026-11-11 issue 锁定，脚本不自行调整：

  * 词（word）       —— 空白切分后的 token，原样保留标点（`str.split()`）。
  * 对齐（主分析）    —— 人类取第 501–1500 词（跳过 500 词 prompt），AI 取第 1–1000 词。
  * 对齐（敏感性）    —— 人类取第 1–1000 词，AI 取第 1–1000 词。
  * MATTR            —— 窗口固定 100；不足 100 词记 NA。窗口内 token 小写、保留标点。
  * MTLD             —— McCarthy & Jarvis (2010) 标准算法，TTR 阈值 0.72（严格小于），
                        因子最短 10 词，正向 + 反向取平均；末段不完整因子按
                        (1 - TTR) / (1 - 0.72) 折算。语义与仓库既有
                        `lexical_diversity.lex_div.mtld` 一致，只是 token 先小写。
  * 句长均值          —— 先用缩写/小数/省略号/首字母保护，再按 `(?<=[.!?])\s+` 切句
                        （句末紧跟引号时允许引号后再切）；句长 = 该句空白 token 数。
  * 句长 CV          —— 句长总体标准差（pstdev）/ 均值。

只做描述统计：不给 p 值、不做检验。所有表格由本脚本生成，报告里的「初步观察」
来自人工撰写的 observations.md，脚本原样嵌入并明确标注。

用法（仓库根目录，一条命令跑完）：
    python3 analysis/descriptive/descriptive_stats.py

可选参数：
    --data-root PATH   数据目录，默认 <repo>/data
    --out-dir PATH     输出目录，默认 analysis/descriptive/out-20261111
    --no-appendix      跳过「标点 token 影响」诊断附录

输出见 README.md。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import statistics
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------
# 固定口径
# --------------------------------------------------------------------------
MATTR_WINDOW = 100
MTLD_THRESHOLD = 0.72
MTLD_MIN_FACTOR = 10               # 与 lexical_diversity.lex_div.mtld 一致的最小因子长度
HUMAN_PROMPT_WORDS = 500          # 人类文本前 500 词 = AI 续写所用 prompt
WINDOW_WORDS = 1000

ALIGNMENTS = (
    # key, 显示名, 人类窗口 (start, end)
    ("main", "主分析（人类 501–1500 词）", (HUMAN_PROMPT_WORDS, HUMAN_PROMPT_WORDS + WINDOW_WORDS)),
    ("sensitivity", "敏感性（人类 1–1000 词）", (0, WINDOW_WORDS)),
)

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

# 子语料名（与 AI_Brown zip 内目录一致）
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
ABBREV_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(a) for a in ABBREVIATIONS) + r")\."
)
INITIAL_RE = re.compile(r"\b[A-Z]\.")
DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")
ELLIPSIS_RE = re.compile(r"\.{2,}")
MASK = "\x00"
SENT_BOUNDARY_RE = re.compile(r"(?<=[.!?])(?:[\"”’'])?\s+")


# --------------------------------------------------------------------------
# 指标
# --------------------------------------------------------------------------
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

    与仓库既有 `lexical_diversity.lex_div.mtld`（Jarvis & McCarthy 原始描述）保持同一语义：
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
    """标准双向 MTLD：正向与反向各算一次，取算术平均。"""
    if not tokens:
        return float("nan")
    return (_mtld_one_direction(tokens, threshold) + _mtld_one_direction(list(reversed(tokens)), threshold)) / 2.0


def protect_abbreviations(text: str) -> str:
    """把不该断句的句点替换成掩码，切句后再还原。"""
    text = DECIMAL_RE.sub(MASK, text)
    text = ELLIPSIS_RE.sub(lambda m: MASK * len(m.group(0)), text)
    text = ABBREV_RE.sub(lambda m: m.group(0)[:-1] + MASK, text)
    text = INITIAL_RE.sub(lambda m: m.group(0)[:-1] + MASK, text)
    return text


def split_sentences(text: str) -> list[str]:
    protected = protect_abbreviations(text)
    parts = [p.strip().replace(MASK, ".") for p in SENT_BOUNDARY_RE.split(protected)]
    return [p for p in parts if p]


def compute_metrics(tokens: Sequence[str]) -> dict[str, Any]:
    """对一段已对齐的空白 token 序列计算四指标 + 句子诊断。"""
    text = " ".join(tokens)
    sentences = split_sentences(text) if text else []
    sent_lengths = [len(s.split()) for s in sentences]
    mean_len = statistics.fmean(sent_lengths) if sent_lengths else None
    cv = None
    if len(sent_lengths) >= 2 and mean_len:
        cv = statistics.pstdev(sent_lengths) / mean_len
    return {
        "mattr": mattr(tokens),
        "mtld": mtld(tokens) if tokens else None,
        "sent_len_mean": mean_len,
        "sent_len_cv": cv,
        "n_sentences": len(sent_lengths),
        "max_sentence_len": max(sent_lengths) if sent_lengths else None,
    }


# --------------------------------------------------------------------------
# 数据装载
# --------------------------------------------------------------------------
def norm_text(raw: str) -> str:
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def load_human_index(data_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
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
    ours_mattr, ours_mtld = mattr(tokens), mtld(tokens)
    ref_mattr, ref_mtld = lex_div.mattr(tokens, MATTR_WINDOW), lex_div.mtld(tokens)
    return {
        "available": True,
        "sample": "brown2021/A_press_reportage__A01.txt 第 501–1500 词（小写）",
        "mattr_ours": ours_mattr,
        "mattr_lexical_diversity": ref_mattr,
        "mtld_ours": ours_mtld,
        "mtld_lexical_diversity": ref_mtld,
        "match": abs(ours_mattr - ref_mattr) < 1e-9 and abs(ours_mtld - ref_mtld) < 1e-9,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# 逐篇计算
# --------------------------------------------------------------------------
def run(data_root: Path, appendix: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    _, by_n = load_human_index(data_root)
    selected = {n: row for n, row in by_n.items() if row["genre_code"] in GENRES}
    expected_n = sorted(selected)
    zip_path = data_root / "aibrown" / "AI_Brown_plain_texts_cleaned.zip"
    if not zip_path.exists():
        raise SystemExit(f"缺少 AI 语料: {zip_path}")
    zip_index = build_zip_index(zip_path)

    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    appendix_rows: list[dict[str, Any]] = []
    missing_ai: list[dict[str, Any]] = []
    ai_word_counts: dict[str, list[int]] = {g: [] for g in GROUPS}
    human_total_words: list[int] = []

    def add_row(meta: dict[str, Any], alignment: str, tokens: list[str], metrics: dict[str, Any]) -> None:
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
                "alignment": alignment,
                "n_words": len(tokens),
                "n_sentences": metrics["n_sentences"],
                **{m: metrics[m] for m in METRICS},
            }
        )
        if appendix:
            alpha = [t for t in tokens if re.search(r"[A-Za-z0-9]", t)]
            am = compute_metrics(alpha)
            appendix_rows.append(
                {
                    "group": meta["group"],
                    "genre_code": meta["genre_code"],
                    "alignment": alignment,
                    "n_words": len(tokens),
                    "n_alpha_words": len(alpha),
                    **{m: am[m] for m in METRICS},
                }
            )

    # ---- 人类 ----
    for n in expected_n:
        meta = selected[n]
        raw = meta["path"].read_text(encoding="utf-8", errors="replace")
        tokens = norm_text(raw).split()
        human_total_words.append(len(tokens))
        base_meta = {
            "doc_id": meta["doc_id"],
            "n": n,
            "be21": meta["be21"],
            "genre_code": meta["genre_code"],
            "genre_name": meta["genre_name"],
            "genre_group": meta["genre_group"],
            "group": HUMAN_GROUP,
            "model": HUMAN_GROUP,
            "temperature": "",
        }
        for key, _label, (start, end) in ALIGNMENTS:
            window = tokens[start:end]
            if len(window) < WINDOW_WORDS:
                issues.append(
                    f"人类 {meta['be21']} ({meta['filename']}) 在 {key} 窗口只有 {len(window)} 词，不足 1000"
                )
            add_row(base_meta, key, window, compute_metrics(window))

    # ---- AI ----
    with zipfile.ZipFile(zip_path) as zf:
        for model in SUBCORPORA:
            for temp in TEMPERATURES:
                group = f"{model}__{temp}"
                sub = f"brown_chat_{model}__{temp}"
                members = zip_index.get(sub)
                if not members:
                    raise SystemExit(f"zip 内找不到子语料目录: {sub}")
                for n in expected_n:
                    meta = selected[n]
                    member = members.get(n)
                    if member is None:
                        missing_ai.append({"group": group, "n": n, "be21": meta["be21"], "genre_code": meta["genre_code"]})
                        continue
                    raw = zf.read(member).decode("utf-8", errors="replace")
                    tokens = norm_text(raw).split()
                    ai_word_counts[group].append(len(tokens))
                    base_meta = {
                        "doc_id": meta["doc_id"],
                        "n": n,
                        "be21": meta["be21"],
                        "genre_code": meta["genre_code"],
                        "genre_name": meta["genre_name"],
                        "genre_group": meta["genre_group"],
                        "group": group,
                        "model": model,
                        "temperature": temp,
                    }
                    window = tokens[:WINDOW_WORDS]
                    metrics = compute_metrics(window)
                    for key, _label, _ in ALIGNMENTS:  # AI 两种对齐取同一段
                        add_row(base_meta, key, window, metrics)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "data_root": str(data_root),
        "human_texts": len(expected_n),
        "model_subcorpora": list(SUBCORPORA),
        "temperatures": list(TEMPERATURES),
        "groups": list(ALL_GROUPS),
        "per_text_rows": len(rows),
        "missing_ai": missing_ai,
        "ai_word_counts": {g: {"min": min(v), "median": statistics.median(v), "lt1000": sum(1 for x in v if x < 1000), "lt100": sum(1 for x in v if x < 100)} for g, v in ai_word_counts.items()},
        "human_total_words": {
            "min": min(human_total_words),
            "median": statistics.median(human_total_words),
            "max": max(human_total_words),
        },
        "config": {
            "mattr_window": MATTR_WINDOW,
            "mtld_threshold": MTLD_THRESHOLD,
            "human_prompt_words": HUMAN_PROMPT_WORDS,
            "window_words": WINDOW_WORDS,
            "token_definition": "whitespace split, punctuation retained",
        },
        "inputs": {
            "brown2021_manifest": sha256_file(data_root / "brown2021" / "manifest.csv"),
            "ai_file_mapping": sha256_file(data_root / "brown2021" / "ai_file_mapping.csv"),
            "ai_zip": sha256_file(zip_path),
            "script": sha256_file(Path(__file__)),
        },
        "warnings": issues,
    }
    return rows, appendix_rows, manifest


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
    sd = statistics.stdev(vals) if n >= 2 else None
    med = quantile(vals, 0.5)
    q1 = quantile(vals, 0.25)
    q3 = quantile(vals, 0.75)
    return {"n": n, "mean": mean, "sd": sd, "median": med, "q1": q1, "q3": q3, "iqr": q3 - q1}


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


def summarize_all(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """alignment × group × genre(含 ALL) × metric 的描述统计。"""
    out: list[dict[str, Any]] = []
    for alignment, _label, _ in ALIGNMENTS:
        arows = [r for r in rows if r["alignment"] == alignment]
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
                            "alignment": alignment,
                            "genre": genre,
                            "group": group,
                            "metric": metric,
                            "n": st["n"],
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
    for alignment, _label, _ in ALIGNMENTS:
        for genre in ("ALL",) + tuple(GENRE_ORDER):
            for group in GROUPS:
                for metric in METRICS:
                    h = idx.get((alignment, genre, HUMAN_GROUP, metric))
                    m = idx.get((alignment, genre, group, metric))
                    if not h or not m:
                        continue
                    diffs.append(
                        {
                            "alignment": alignment,
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


def build_genre_table(rows: list[dict[str, Any]], missing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 以主分析 human 行为样本基准（每种对齐人类窗口都覆盖同样的 376 个 n）
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
    total = {"genre_code": "ALL", "genre_name": "合计", "genre_group": ""}
    for key in [k for k in out[0] if k.startswith("n_")]:
        total[key] = sum(r[key] for r in out)
    out.append(total)
    return out


def build_qa(rows_with_tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for alignment, _l, _ in ALIGNMENTS:
        for group in ALL_GROUPS:
            subset = [r for r in rows_with_tokens if r["alignment"] == alignment and r["group"] == group]
            if not subset:
                continue
            shares = [r["punct_share"] for r in subset]
            alpha = [r["n_alpha"] for r in subset]
            out.append(
                {
                    "alignment": alignment,
                    "group": group,
                    "n_texts": len(subset),
                    "mean_words": statistics.fmean(r["n_words"] for r in subset),
                    "mean_punct_only_share": statistics.fmean(shares),
                    "min_words": min(r["n_words"] for r in subset),
                    "lt1000": sum(1 for r in subset if r["n_words"] < 1000),
                    "lt100": sum(1 for r in subset if r["n_words"] < 100),
                    "mean_alpha_words": statistics.fmean(alpha),
                }
            )
    return out


def build_issues(manifest: dict[str, Any], qa: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    # 1. gemini 缺篇
    missing = manifest["missing_ai"]
    if missing:
        per_group = Counter(m["group"] for m in missing)
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
    # 2. AI 短于 1000 词
    short = manifest["ai_word_counts"]
    lines = [f"{g}: {v['lt1000']}/376 篇 <1000 词（最短 {v['min']}，中位 {v['median']}）" for g, v in short.items() if v["lt1000"]]
    if lines:
        worst = max(short.items(), key=lambda kv: kv[1]["lt1000"])
        issues.append(
            {
                "id": "D2",
                "severity": "高",
                "issue": "部分 AI 文本不足 1000 词，无法截满 1,000 词窗口",
                "evidence": "; ".join(lines),
                "impact": f"这些篇目实际窗口更短（{worst[0]} 最严重），MTLD/句长对长度敏感，模型间比较需带词数分布一起看。",
            }
        )
    # 3. 极短文本
    tiny = {g: v for g, v in short.items() if v["lt100"]}
    if tiny:
        issues.append(
            {
                "id": "D3",
                "severity": "高",
                "issue": "存在不足 100 词的 AI 文本",
                "evidence": "; ".join(f"{g}: {v['lt100']} 篇（最短 {v['min']}）" for g, v in tiny.items()),
                "impact": "MATTR 记 NA、MTLD 极不稳定；已保留逐篇明细，汇总时按实际非 NA 篇数计 N。",
            }
        )
    # 4. 人类标点 token
    hq = next((q for q in qa if q["alignment"] == "main" and q["group"] == HUMAN_GROUP), None)
    aq = [q for q in qa if q["alignment"] == "main" and q["group"] != HUMAN_GROUP]
    if hq and aq:
        ai_mean = statistics.fmean(q["mean_punct_only_share"] for q in aq)
        ai_alpha = statistics.fmean(q["mean_alpha_words"] for q in aq)
        issues.append(
            {
                "id": "D4",
                "severity": "高",
                "issue": "人类 txt 的标点独立成词（AntConc 导出），AI 文本标点黏在词上",
                "evidence": f"人类窗口内标点-only token 占比 {hq['mean_punct_only_share']:.1%}，12 个 AI 组平均 {ai_mean:.1%}；实词数人类 {hq['mean_alpha_words']:.0f}，AI 组平均 {ai_alpha:.0f}",
                "impact": f"按锁定的空白切分口径，人类 1,000 token 的实词量只有 AI 的 {hq['mean_alpha_words'] / ai_alpha:.0%}；MATTR/句长均值会被系统性抬高。本报告按协议口径产出，另附标点剥离后的诊断表（非协议口径）。",
            }
        )
    # 5. 人类长度下限
    ht = manifest["human_total_words"]
    issues.append(
        {
            "id": "D5",
            "severity": "低",
            "issue": "人类 376 篇原文均长于主分析的 1,500 词窗口",
            "evidence": f"原文词数 {ht['min']}–{ht['max']}（中位 {ht['median']:.0f}）",
            "impact": "人类侧两种对齐窗口都是完整 1,000 词，无截断损失。",
        }
    )

    # 6. MTLD 异常高值
    main_rows = [r for r in rows if r["alignment"] == "main" and r["group"] != HUMAN_GROUP]
    mtld_counts = Counter()
    mtld_max: dict[str, float] = {}
    for r in main_rows:
        if r["mtld"] is None:
            continue
        mtld_max[r["group"]] = max(mtld_max.get(r["group"], 0.0), r["mtld"])
        if r["mtld"] > 300:
            mtld_counts[r["group"]] += 1
    if mtld_counts:
        detail = "; ".join(f"{g}: {c}/376 篇 >300（最大 {mtld_max[g]:.0f}）" for g, c in mtld_counts.most_common())
        issues.append(
            {
                "id": "D6",
                "severity": "中",
                "issue": "MTLD 出现成片高值，与人类组差距远大于 MATTR",
                "evidence": detail,
                "impact": "高值集中在温度 100 的两组，与短文本/高类型密度同现；MTLD 对窗口长度和类型密度极敏感，只作记录，不单独下结论。",
            }
        )

    # 7. llama 温度 100 的退化文本
    degen = Counter()
    examples: dict[str, str] = {}
    for r in main_rows:
        if r["mattr"] is not None and r["mattr"] > 0.90:
            degen[r["group"]] += 1
            examples.setdefault(r["group"], f"n={r['n']}（{r['be21']}）")
    if degen:
        detail = "; ".join(f"{g}: {c}/376 篇 MATTR>0.90，如 {examples[g]}" for g, c in degen.most_common())
        issues.append(
            {
                "id": "D7",
                "severity": "高",
                "issue": "llama_31_405b 温度 100 含明显退化的词语堆叠文本",
                "evidence": detail + "；抽查 n=8 出现 `such fluctuating east Heavy level heads believed automat Springfield properties job ill Mari` 一类片段",
                "impact": "该组均值与方差被少数退化篇目拉高（MTLD、句长 CV 尤甚），组间比较需同时看中位数与 IQR，不能只看均值。",
            }
        )
    return issues


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------
def report_markdown(
    out: Path,
    manifest: dict[str, Any],
    summary: list[dict[str, Any]],
    diffs: list[dict[str, Any]],
    genre_table: list[dict[str, Any]],
    qa: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    appendix_summary: list[dict[str, Any]],
    observations: str | None,
) -> str:
    s_idx = {(s["alignment"], s["genre"], s["group"], s["metric"]): s for s in summary}
    lines: list[str] = []
    A = lines.append

    A("# 描述统计：376 篇 × 12 子语料（四指标）")
    A("")
    A(f"生成时间：{manifest['generated_at']}　·　脚本：`analysis/descriptive/descriptive_stats.py`　·　输出目录：`{out.name}/`")
    A("")
    A("> 本文件由脚本生成。第 1–6 节的所有数字与表格均由脚本直接产出；第 7 节「初步观察」为人工撰写，")
    A("> 脚本原样嵌入、不改写，二者边界在文中标明。按老师 11/11 意见，**不做显著性检验、不报 p 值**。")
    A("")

    A("## 1. 数据与口径")
    A("")
    A(f"- 人类：BE21 `manifest.csv` 中 {manifest['human_texts']} 篇，语体 A/B/C/E/F/J/K/L/M/N/P/R。")
    A("- AI：`AI_Brown_plain_texts_cleaned.zip` 中 6 个模型 × 温度 0/100 = 12 个子语料，逐篇按 `ai_file_mapping.csv` 的 n ↔ BE21 对应。")
    A("- 词：`str.split()` 的空白 token，标点原样保留。")
    A(f"- 主分析：人类第 {HUMAN_PROMPT_WORDS + 1}–{HUMAN_PROMPT_WORDS + WINDOW_WORDS} 词（跳过 prompt）；AI 第 1–{WINDOW_WORDS} 词。")
    A(f"- 敏感性：人类第 1–{WINDOW_WORDS} 词；AI 第 1–{WINDOW_WORDS} 词（与主分析相同）。")
    A(f"- MATTR：窗口 {MATTR_WINDOW}，不足 {MATTR_WINDOW} 词记 NA；窗口内小写。")
    A(f"- MTLD：阈值 {MTLD_THRESHOLD}，正反双向平均，末段不完整因子按 (1−TTR)/(1−{MTLD_THRESHOLD}) 折算。")
    A("- 句长：先保护缩写/小数/省略号/单字母缩写，再按 `(?<=[.!?])\\s+` 切句；句长 = 该句空白 token 数；CV = 总体 SD / 均值。")
    ai_rows = manifest["per_text_rows"] - manifest["human_texts"] * len(ALIGNMENTS)
    A(f"- 逐篇行数：{manifest['per_text_rows']}（376 人类 × 2 对齐 + {ai_rows // 2} 篇 AI × 2 对齐）。")
    A("")

    A("## 2. 样本构成（脚本产出）")
    A("")
    A("每个 AI 子语料覆盖同一批 376 个 n，故语体篇数与人类一致；gemini 两个温度组各少 1 篇（n=76，C 类）。")
    A("")
    hdr = ["语体", "组别", "人类 N"] + list(GROUPS)
    table_rows = []
    for r in genre_table:
        table_rows.append([f"{r['genre_code']} {r['genre_name']}" if r["genre_code"] != "ALL" else "合计", r["genre_group"], str(r["n_human"])] + [str(r[f"n_{g}"]) for g in GROUPS])
    A(md_table(hdr, table_rows, ["---", "---", "---:"] + ["---:"] * len(GROUPS)))
    A("")

    A("## 3. 四指标整体汇总（主分析与敏感性并列，脚本产出）")
    A("")
    for metric in METRICS:
        A(f"### {METRIC_LABEL[metric]}")
        A("")
        cols = ["N", "均值", "SD", "中位数", "Q1", "Q3", "IQR"]
        rows = []
        for group in ALL_GROUPS:
            main = s_idx.get(("main", "ALL", group, metric), {})
            sens = s_idx.get(("sensitivity", "ALL", group, metric), {})
            rows.append(
                [group]
                + [str(main.get("n", "")), fmt(main.get("mean")), fmt(main.get("sd")), fmt(main.get("median")), fmt(main.get("q1")), fmt(main.get("q3")), fmt(main.get("iqr"))]
                + [str(sens.get("n", "")), fmt(sens.get("mean")), fmt(sens.get("sd")), fmt(sens.get("median")), fmt(sens.get("q1")), fmt(sens.get("q3")), fmt(sens.get("iqr"))]
            )
        A(md_table(["组别"] + [f"主分析 {c}" for c in cols] + [f"敏感性 {c}" for c in cols], rows, ["---"] + ["---:"] * (2 * len(cols))))
        A("")

    A("## 4. 按语体的四指标均值（主分析，脚本产出）")
    A("")
    A("完整 N/SD/中位数/IQR 见 `summary_by_genre.csv`；此处只列均值，`NA` 表示该格无可用篇目。")
    A("")
    for metric in METRICS:
        A(f"### {METRIC_LABEL[metric]}（均值）")
        A("")
        hdr = ["语体", "human"] + list(GROUPS)
        rows = []
        for genre in ("ALL",) + tuple(GENRE_ORDER):
            label = "合计" if genre == "ALL" else GENRE_LABEL[genre]
            cells = [fmt((s_idx.get(("main", genre, HUMAN_GROUP, metric)) or {}).get("mean"))]
            for group in GROUPS:
                cells.append(fmt((s_idx.get(("main", genre, group, metric)) or {}).get("mean")))
            rows.append([label] + cells)
        A(md_table(hdr, rows, ["---"] + ["---:"] * (len(hdr) - 1)))
        A("")

    A("## 5. 人类 vs 每个模型的描述性差值（脚本产出）")
    A("")
    A("差值 = 模型均值 − 人类均值（正数表示模型更高）。按语体分组的完整四指标差值与中位数差值见 `human_vs_model_diff.csv`；")
    A("这里只列跨语体合计（ALL）。**只报差值与分布，不做检验、不报 p 值。**")
    A("")
    for alignment, label, _ in ALIGNMENTS:
        A(f"### {label}")
        A("")
        hdr = ["组别"] + [METRIC_LABEL[m] for m in METRICS]
        rows = []
        for group in GROUPS:
            cells = []
            for metric in METRICS:
                d = next((x for x in diffs if x["alignment"] == alignment and x["genre"] == "ALL" and x["group"] == group and x["metric"] == metric), None)
                cells.append(fmt(d["diff_mean"]) if d else "NA")
            rows.append([group] + cells)
        A(md_table(hdr, rows, ["---"] + ["---:"] * len(METRICS)))
        A("")

    A("## 6. 数据问题清单（脚本计算）")
    A("")
    A(md_table(["编号", "严重度", "问题", "证据", "影响"], [[i["id"], i["severity"], i["issue"], i["evidence"], i["impact"]] for i in issues], ["---", "---", "---", "---", "---"]))
    A("")
    A("### 6.1 标点 token 诊断（脚本产出）")
    A("")
    A("人类 txt 由 AntConc 导出，标点前后带空格；AI 文本标点黏在词上。按协议用空白切分时，人类窗口里会混入约一成标点 token，")
    A("实际实词量少于 AI。此表只量化差异，不改协议口径。")
    A("")
    hdr = ["组别", "对齐", "N", "平均窗口词数", "标点-only 占比", "最短", "<1000 词", "<100 词", "平均实词数"]
    rows = []
    for q in qa:
        rows.append([q["group"], q["alignment"], str(q["n_texts"]), fmt(q["mean_words"], 1), f"{q['mean_punct_only_share']:.1%}", str(q["min_words"]), str(q["lt1000"]), str(q["lt100"]), fmt(q["mean_alpha_words"], 1)])
    A(md_table(hdr, rows, ["---", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]))
    A("")

    if appendix_summary:
        A("### 6.2 附：剥离标点-only token 后的诊断（非协议口径，仅供评估 D4）")
        A("")
        A("在同一窗口内删去不含字母数字的 token 后重算 MATTR / MTLD（主分析），按组汇总均值。")
        A("句长不在此重算：句末标点本身会被剥离，切句会失效，句长仍看协议口径的主表。")
        A("**这不是协议口径，不进入主表、不作结论依据。**")
        A("")
        hdr = ["组别", "N", "MATTR(w=100)", "MTLD(0.72)", "实词数"]
        rows = []
        for group in ALL_GROUPS:
            vals = [r for r in appendix_summary if r["group"] == group and r["alignment"] == "main"]
            if not vals:
                continue
            rows.append(
                [
                    group,
                    str(len(vals)),
                    fmt(summarize(v["mattr"] for v in vals)["mean"]),
                    fmt(summarize(v["mtld"] for v in vals)["mean"]),
                    fmt(statistics.fmean(v["n_alpha_words"] for v in vals), 1),
                ]
            )
        A(md_table(hdr, rows, ["---", "---:", "---:", "---:", "---:"]))
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
    A("| `per_text_metrics.csv` | 逐篇明细：doc_id、n、BE21、语体、组别、温度、对齐、四指标、词数、句数 |")
    A("| `summary_by_genre.csv` | 对齐 × 组别 × 语体 × 指标 的 N/均值/SD/中位数/Q1/Q3/IQR |")
    A("| `human_vs_model_diff.csv` | 人类 vs 每个模型的均值/中位数差值（含按语体） |")
    A("| `genre_sample_table.csv` | 语体 × 篇数 × 各组 N |")
    A("| `sample_index.csv` | 376 组 doc_id ↔ n ↔ BE21 对照清单 |")
    A("| `qa_tokenization.csv` | 标点 token 诊断 |")
    A("| `data_issues.csv` | 数据问题清单 |")
    A("| `appendix_alpha_tokens.csv` | 剥离标点后的诊断（非协议口径） |")
    A("| `run_manifest.json` | 配置、输入哈希、缺失篇目、词数分布 |")
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
            "回归校验：在 `A_press_reportage__A01.txt` 第 501–1500 词（小写）上，本脚本 MATTR = "
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
    parser = argparse.ArgumentParser(description="376 × 12 子语料四指标描述统计")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-appendix", action="store_true", help="跳过标点剥离诊断附录")
    parser.add_argument("--observations", type=Path, default=Path(__file__).resolve().parent / "observations.md")
    args = parser.parse_args(argv)

    data_root = args.data_root.expanduser().resolve()
    out = args.out_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows, appendix_rows, manifest = run(data_root, appendix=not args.no_appendix)
    manifest["checks"] = {"lexical_diversity": self_check(data_root)}

    # QA 需要 token 层面的标点占比：在 rows 之外单独重算（只依赖已装载数据）
    _, by_n = load_human_index(data_root)
    selected = {n: r for n, r in by_n.items() if r["genre_code"] in GENRES}
    qa_rows: list[dict[str, Any]] = []

    def qa_add(group: str, alignment: str, tokens: list[str]) -> None:
        punct = sum(1 for t in tokens if not re.search(r"[A-Za-z0-9]", t))
        qa_rows.append(
            {
                "group": group,
                "alignment": alignment,
                "n_words": len(tokens),
                "punct_share": punct / len(tokens) if tokens else 0.0,
                "n_alpha": len(tokens) - punct,
            }
        )

    for n, meta in selected.items():
        tokens = norm_text(meta["path"].read_text(encoding="utf-8", errors="replace")).split()
        for key, _l, (start, end) in ALIGNMENTS:
            qa_add(HUMAN_GROUP, key, tokens[start:end])
    zip_path = data_root / "aibrown" / "AI_Brown_plain_texts_cleaned.zip"
    zip_index = build_zip_index(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        for model in SUBCORPORA:
            for temp in TEMPERATURES:
                group = f"{model}__{temp}"
                members = zip_index[f"brown_chat_{model}__{temp}"]
                for n in selected:
                    member = members.get(n)
                    if member is None:
                        continue
                    tokens = norm_text(zf.read(member).decode("utf-8", errors="replace")).split()[:WINDOW_WORDS]
                    for key, _l, _ in ALIGNMENTS:
                        qa_add(group, key, tokens)

    qa = build_qa(qa_rows)
    summary = summarize_all(rows)
    diffs = build_diffs(summary)
    genre_table = build_genre_table(rows, manifest["missing_ai"])
    issues = build_issues(manifest, qa, rows)

    # ---- 落盘 ----
    write_csv(
        out / "per_text_metrics.csv",
        ["doc_id", "n", "be21", "genre_code", "genre_name", "genre_group", "group", "model", "temperature", "alignment", "n_words", "n_sentences", *METRICS],
        rows,
    )
    write_csv(
        out / "summary_by_genre.csv",
        ["alignment", "genre", "group", "metric", "n", "mean", "sd", "median", "q1", "q3", "iqr"],
        summary,
    )
    write_csv(
        out / "human_vs_model_diff.csv",
        ["alignment", "genre", "group", "metric", "n_human", "n_model", "human_mean", "model_mean", "diff_mean", "human_median", "model_median", "diff_median"],
        diffs,
    )
    write_csv(
        out / "genre_sample_table.csv",
        ["genre_code", "genre_name", "genre_group", "n_human", *[f"n_{g}" for g in GROUPS]],
        genre_table,
    )
    write_csv(
        out / "sample_index.csv",
        ["doc_id", "n", "be21", "filename", "genre_code", "genre_name", "genre_group"],
        [{"doc_id": m["doc_id"], "n": m["n"], "be21": m["be21"], "filename": m["filename"], "genre_code": m["genre_code"], "genre_name": m["genre_name"], "genre_group": m["genre_group"]} for m in sorted(selected.values(), key=lambda x: x["n"])],
    )
    write_csv(out / "qa_tokenization.csv", ["group", "alignment", "n_texts", "mean_words", "mean_punct_only_share", "min_words", "lt1000", "lt100", "mean_alpha_words"], qa)
    write_csv(out / "data_issues.csv", ["id", "severity", "issue", "evidence", "impact"], issues)
    if appendix_rows:
        write_csv(
            out / "appendix_alpha_tokens.csv",
            ["group", "genre_code", "alignment", "n_words", "n_alpha_words", *METRICS],
            appendix_rows,
        )
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    observations = None
    if args.observations.exists():
        observations = args.observations.read_text(encoding="utf-8")

    report = report_markdown(out, manifest, summary, diffs, genre_table, qa, issues, appendix_rows, observations)
    (out / "report.md").write_text(report, encoding="utf-8")

    print(f"写出 {len(rows)} 行逐篇指标 → {out / 'per_text_metrics.csv'}")
    print(f"人类 {manifest['human_texts']} 篇；AI 缺失 {len(manifest['missing_ai'])} 篇")
    print(f"报告 → {out / 'report.md'}（{len(report.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
