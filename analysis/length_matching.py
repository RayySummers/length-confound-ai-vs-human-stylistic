#!/usr/bin/env python3
"""length_matching.py — 长度匹配子样本分析（RAY-614）。

设计（按 2026-10-26 组会决定，issue RAY-614）：
  1. 对每篇人类文本，在**同一 prompt、同一模型**的输出里找词数最接近的一篇。
     本语料每个 (prompt, model) 只有一篇输出，所以候选唯一；脚本仍按"最近邻"实现，
     以便将来同一 prompt 有多篇生成时可复用。
  2. 差值 <=10% 记为匹配；>10% 且 <=20% 记为放宽匹配并注明；>20% 视为配不上。
  3. 每个模型统计配对数、10% 内配对数、平均绝对差百分比。
  4. 只有配对数 >= 15 才对 MATTR / MTLD 做配对 t 检验（AI - Human），
     报 t、df、p、Cohen's d（配对 d = 均值差 / 差值标准差），四个模型做 Holm 校正。
     配对数 < 15 时**不做检验**，只报"样本不足以匹配"（issue 判据）。
  5. 附加：全样本（不筛长度）配对检验作为对照，用来判断"若匹配可做，结论是否会反转"；
     该对照不是匹配分析的结果，单独标注。另给容差敏感性网格，说明要凑够 15 对
     需要放宽到什么程度。

输入默认取仓库内 `analysis/per-text-table.csv`（150 行，含 mtld 列）。
若表的列里没有 mtld（例如 issue 里的 149 行快照），则从
`analysis/mattr_vs_mtld_results.json` 的 records 里按 (prompt_id, condition) 取。

用法：
    python3 analysis/length_matching.py
    python3 analysis/length_matching.py --table ~/length-confound-archive-ray588/analysis/per-text-table.csv \
        --mtld-json ~/length-confound-archive-ray588/analysis/mattr_vs_mtld_results.json \
        --out /tmp/length_matching_snapshot.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = BASE / "analysis" / "per-text-table.csv"
DEFAULT_MTLD_JSON = BASE / "analysis" / "mattr_vs_mtld_results.json"
DEFAULT_OUT = BASE / "analysis" / "length_matching_results.json"

MODELS = [
    "Claude-Sonnet-5-High",
    "GPT-5.6-Luna",
    "DeepSeek-V4-Flash",
    "Kimi-K3",
]

# 仓库主表的 model 列用短名；issue 快照用全名。统一到全名。
MODEL_ALIASES = {
    "human": "Human",
    "claude": "Claude-Sonnet-5-High",
    "claude-sonnet-5-high": "Claude-Sonnet-5-High",
    "gpt": "GPT-5.6-Luna",
    "gpt-5.6-luna": "GPT-5.6-Luna",
    "deepseek": "DeepSeek-V4-Flash",
    "deepseek-v4-flash": "DeepSeek-V4-Flash",
    "kimi": "Kimi-K3",
    "kimi-k3": "Kimi-K3",
}

TOLERANCES = [0.10, 0.20]          # 正式口径
MIN_PAIRS = 15                     # issue 判据；固定值，不提供命令行开关，避免事后放宽
SENSITIVITY_GRID = [0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00]


def canon_model(name: str) -> str:
    key = name.strip().lower()
    return MODEL_ALIASES.get(key, name.strip())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    """仓库内路径用相对路径记录，仓库外保留绝对路径。"""
    try:
        return str(path.resolve().relative_to(BASE))
    except ValueError:
        return str(path)


def holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down；返回与输入同序的校正 p。"""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running = max(running, val)
        adj[idx] = min(1.0, running)
    return adj


def cohen_d_paired(diffs: np.ndarray) -> float:
    sd = float(np.std(diffs, ddof=1))
    return float(np.mean(diffs) / sd) if sd > 0 else float("nan")


def mean_ci95(diffs: np.ndarray) -> tuple[float, float]:
    n = len(diffs)
    if n < 2:
        return (float("nan"), float("nan"))
    se = float(np.std(diffs, ddof=1) / math.sqrt(n))
    crit = float(stats.t.ppf(0.975, n - 1))
    m = float(np.mean(diffs))
    return (m - crit * se, m + crit * se)


def paired_test(human: list[float], model: list[float]) -> dict | None:
    """配对 t 检验（双尾），差值 = model - human。n<2 返回 None。"""
    n = len(human)
    if n < 2:
        return None
    h = np.asarray(human, dtype=float)
    m = np.asarray(model, dtype=float)
    diffs = m - h
    t, p = stats.ttest_rel(m, h)
    lo, hi = mean_ci95(diffs)
    try:
        lev_p = float(stats.levene(h, m, center="median").pvalue)
    except Exception:
        lev_p = None
    return {
        "n": n,
        "mean_human": float(np.mean(h)),
        "mean_model": float(np.mean(m)),
        "mean_diff": float(np.mean(diffs)),
        "sd_diff": float(np.std(diffs, ddof=1)),
        "t": float(t),
        "df": n - 1,
        "p": float(p),
        "cohens_d": cohen_d_paired(diffs),
        "ci95_mean_diff": [lo, hi],
        "levene_p_median_centered": lev_p,
    }


def load_rows(table_path: Path, mtld_json_path: Path | None) -> tuple[list[dict], dict, list[str]]:
    rows = []
    with table_path.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            model = canon_model(raw["model"])
            if model != "Human" and model not in MODELS:
                continue
            rows.append({
                "prompt_id": int(raw["prompt_id"]),
                "model": model,
                "word_count": int(raw["word_count"]),
                "mattr": float(raw["MATTR"]),
                "mtld": float(raw["mtld"]) if raw.get("mtld") not in (None, "") else None,
            })

    # 表里缺 mtld 时从 records 补
    missing = [r for r in rows if r["mtld"] is None]
    json_meta = {"used": False, "path": None, "sha256": None, "records": 0}
    warnings = []
    if missing:
        if mtld_json_path is None or not mtld_json_path.exists():
            raise SystemExit(
                f"{len(missing)} 行缺 mtld，且找不到 MTLD JSON：{mtld_json_path}"
            )
        payload = json.loads(mtld_json_path.read_text(encoding="utf-8"))
        records = payload["records"]
        index = {(int(rec["prompt_id"]), canon_model(rec["condition"])): rec for rec in records}
        for r in missing:
            rec = index.get((r["prompt_id"], r["model"]))
            if rec is None:
                warnings.append(f"MTLD 缺失：prompt {r['prompt_id']} / {r['model']}")
            else:
                r["mtld"] = float(rec["mtld"])
        json_meta = {
            "used": True,
            "path": display_path(mtld_json_path),
            "sha256": sha256(mtld_json_path),
            "records": len(records),
        }
    return rows, json_meta, warnings


def build_index(rows: list[dict]) -> tuple[dict[int, dict], dict[str, list[dict]]]:
    humans: dict[int, dict] = {}
    outputs: dict[str, list[dict]] = {m: [] for m in MODELS}
    for r in rows:
        if r["model"] == "Human":
            humans[r["prompt_id"]] = r
        else:
            outputs[r["model"]].append(r)
    return humans, outputs


def match_model(model: str, humans: dict[int, dict], outputs: dict[str, list[dict]]) -> dict:
    pairs, unmatched = [], []
    for pid in sorted(humans):
        h = humans[pid]
        cands = [o for o in outputs[model] if o["prompt_id"] == pid]
        if not cands:
            unmatched.append({"prompt_id": pid, "reason": "missing_model_output"})
            continue
        best = min(cands, key=lambda o: abs(o["word_count"] - h["word_count"]))
        ratio = abs(best["word_count"] - h["word_count"]) / h["word_count"]
        if ratio <= TOLERANCES[0]:
            tol = "10%"
        elif ratio <= TOLERANCES[1]:
            tol = "20%"
        else:
            unmatched.append({
                "prompt_id": pid,
                "reason": "over_20pct",
                "human_wc": h["word_count"],
                "model_wc": best["word_count"],
                "diff_pct": round(ratio * 100, 1),
            })
            continue
        pairs.append({
            "prompt_id": pid,
            "human_wc": h["word_count"],
            "model_wc": best["word_count"],
            "diff_pct": round(ratio * 100, 1),
            "tolerance": tol,
            "mattr_human": h["mattr"],
            "mattr_model": best["mattr"],
            "mtld_human": h["mtld"],
            "mtld_model": best["mtld"],
        })

    n_candidates = sum(1 for pid in humans if any(o["prompt_id"] == pid for o in outputs[model]))
    ratios = [
        o["word_count"] / humans[o["prompt_id"]]["word_count"]
        for o in outputs[model] if o["prompt_id"] in humans
    ]
    diffs = [p["diff_pct"] for p in pairs]
    return {
        "n_candidates": n_candidates,
        "n_human_texts": len(humans),
        "n_pairs": len(pairs),
        "n_within_10pct": sum(1 for p in pairs if p["tolerance"] == "10%"),
        "n_within_10_to_20pct": sum(1 for p in pairs if p["tolerance"] == "20%"),
        "pairing_rate_pct": round(100 * len(pairs) / len(humans), 1) if humans else None,
        "n_unmatched": len(unmatched),
        "mean_abs_diff_pct_matched": round(float(np.mean(diffs)), 2) if diffs else None,
        "median_abs_diff_pct_matched": round(float(np.median(diffs)), 2) if diffs else None,
        "median_word_count_ratio_model_over_human": (
            round(float(np.median(ratios)), 2) if ratios else None
        ),
        "word_count_ratio_range": (
            [round(min(ratios), 2), round(max(ratios), 2)] if ratios else None
        ),
        "eligible_for_test": len(pairs) >= MIN_PAIRS,
        "pairs": pairs,
        "unmatched": unmatched,
    }


def describe_pairs(pairs: list[dict]) -> dict:
    """配对样本的描述统计；不做检验，只用于说明方向。"""
    out = {"descriptive_only": True, "n": len(pairs)}
    for metric in ("mattr", "mtld"):
        vals = [(p[f"{metric}_human"], p[f"{metric}_model"]) for p in pairs
                if p.get(f"{metric}_human") is not None and p.get(f"{metric}_model") is not None]
        if not vals:
            out[metric] = None
            continue
        h = np.asarray([v[0] for v in vals], dtype=float)
        m = np.asarray([v[1] for v in vals], dtype=float)
        out[metric] = {
            "mean_human": float(np.mean(h)),
            "mean_model": float(np.mean(m)),
            "mean_diff_model_minus_human": float(np.mean(m - h)),
            "n_model_gt_human": int(np.sum(m > h)),
        }
    return out


def run_tests(block: dict) -> dict:
    mattr_h = [p["mattr_human"] for p in block["pairs"] if p["mattr_human"] is not None]
    mattr_m = [p["mattr_model"] for p in block["pairs"] if p["mattr_human"] is not None]
    mtld_pairs = [
        p for p in block["pairs"]
        if p.get("mtld_human") is not None and p.get("mtld_model") is not None
    ]
    tests = {}
    mt = paired_test(mattr_h, mattr_m)
    if mt:
        tests["mattr"] = mt
    mt2 = paired_test([p["mtld_human"] for p in mtld_pairs],
                      [p["mtld_model"] for p in mtld_pairs])
    if mt2:
        tests["mtld"] = mt2
    return tests


def apply_holm(results: dict[str, dict]) -> None:
    """对 MATTR / MTLD 各做一次跨模型 Holm，并另给 8 个检验合并校正。"""
    all_tests = []
    for metric in ("mattr", "mtld"):
        entries = []
        for m in MODELS:
            tests = (results.get(m) or {}).get("tests") or {}
            if tests.get(metric):
                entries.append((m, tests[metric]))
        if entries:
            adj = holm([t["p"] for _, t in entries])
            for (m, t), a in zip(entries, adj):
                t["p_holm_within_metric"] = float(a)
                t["sig_holm_within_metric"] = bool(a < 0.05)
                all_tests.append((metric, m, t))
    if all_tests:
        adj_all = holm([t["p"] for _, _, t in all_tests])
        for (_, _, t), a in zip(all_tests, adj_all):
            t["p_holm_all_8"] = float(a)
            t["sig_holm_all_8"] = bool(a < 0.05)


def audit(humans, outputs, min_pairs: int) -> tuple[dict, dict]:
    results = {}
    for model in MODELS:
        block = match_model(model, humans, outputs)
        block["test_status"] = (
            "run" if block["n_pairs"] >= min_pairs else "not_run_insufficient_pairs"
        )
        block["matched_descriptives"] = describe_pairs(block["pairs"])
        block["tests"] = None
        if block["n_pairs"] >= min_pairs:
            block["tests"] = run_tests(block)
            block["reason"] = None
        else:
            block["reason"] = (
                f"可配对数 {block['n_pairs']} < 判据 {min_pairs}；按预设不做正式检验。"
            )
        results[model] = block
    apply_holm(results)
    return results


def tolerance_sensitivity(humans, outputs) -> dict:
    grid = {}
    for tol in SENSITIVITY_GRID:
        counts = {}
        for model in MODELS:
            n = 0
            for pid, h in humans.items():
                cands = [o for o in outputs[model] if o["prompt_id"] == pid]
                if not cands:
                    continue
                best = min(cands, key=lambda o: abs(o["word_count"] - h["word_count"]))
                if abs(best["word_count"] - h["word_count"]) / h["word_count"] <= tol:
                    n += 1
            counts[model] = n
        grid[f"{int(tol * 100)}"] = {
            "tolerance_pct": int(tol * 100),
            "n_pairs_by_model": counts,
            "models_reaching_15": [m for m, n in counts.items() if n >= 15],
        }

    # 每个模型达到 15 对所需的最小容差（1% 步进，上限 500%）
    min_tol = {}
    for model in MODELS:
        need = None
        for pct in range(1, 501):
            n = 0
            for pid, h in humans.items():
                cands = [o for o in outputs[model] if o["prompt_id"] == pid]
                if not cands:
                    continue
                best = min(cands, key=lambda o: abs(o["word_count"] - h["word_count"]))
                if abs(best["word_count"] - h["word_count"]) / h["word_count"] <= pct / 100:
                    n += 1
            if n >= MIN_PAIRS:
                need = pct
                break
        min_tol[model] = need
    return {"grid": grid, "min_tolerance_pct_for_15_pairs": min_tol}


def full_sample_reference(humans, outputs) -> dict:
    """全样本（不筛长度）配对检验，仅作"匹配前"对照。"""
    ref = {}
    for model in MODELS:
        pairs = []
        for pid, h in humans.items():
            cands = [o for o in outputs[model] if o["prompt_id"] == pid]
            if not cands:
                continue
            best = min(cands, key=lambda o: abs(o["word_count"] - h["word_count"]))
            pairs.append({
                "prompt_id": pid,
                "human_wc": h["word_count"],
                "model_wc": best["word_count"],
                "mattr_human": h["mattr"],
                "mattr_model": best["mattr"],
                "mtld_human": h["mtld"],
                "mtld_model": best["mtld"],
            })
        block = {"n_pairs": len(pairs), "pairs": pairs, "tests": run_tests({"pairs": pairs})}
        ref[model] = block
    apply_holm(ref)
    return {
        "note": "全样本同 prompt 配对（不做长度筛选），只作匹配前的对照；"
                "不是长度匹配分析的结果，不能用来宣称长度已被控制。",
        "models": ref,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--mtld-json", type=Path, default=DEFAULT_MTLD_JSON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows, json_meta, warnings = load_rows(args.table, args.mtld_json)
    humans, outputs = build_index(rows)
    matched = audit(humans, outputs, MIN_PAIRS)
    full = full_sample_reference(humans, outputs)
    sens = tolerance_sensitivity(humans, outputs)

    eligible = [m for m in MODELS if matched[m]["eligible_for_test"]]
    if eligible:
        conclusion = (
            f"可配对模型：{len(eligible)}/4，已按判据做配对检验并做 Holm 校正。"
        )
    else:
        conclusion = (
            f"四个模型在 ±20% 口径下只配到 "
            f"{' / '.join(str(matched[m]['n_pairs']) for m in MODELS)} 对，"
            f"均低于 {MIN_PAIRS} 对判据；按预设不做正式检验，"
            "当前语料无法回答“去掉长度差异后是否仍显著”。"
        )

    reversal = None
    if not eligible:
        reversal = {
            "detected": None,
            "reason": "匹配样本不足以做检验，无法判定结论是否反转。",
        }

    payload = {
        "analysis": "length_matching_subsample",
        "issue": "RAY-614",
        "script": "analysis/length_matching.py",
        "method": {
            "design": "同一 prompt、同一模型内按词数最近邻配对（每篇人类文本至多一篇模型文本）",
            "word_count_source": "per-text-table.csv: word_count",
            "tolerance": "<=10% 匹配；>10% 且 <=20% 放宽匹配；>20% 配不上",
            "min_pairs_for_test": MIN_PAIRS,
            "test": "配对 t 检验（双尾，AI - Human），Cohen's d = 均值差 / 差值 SD；"
                    "仅当每模型配对数 >= 15 时执行；Holm-Bonferroni 校正"
                    "（每个指标跨 4 个模型；另给 8 个检验合并校正）",
            "mattr": "per-text-table.csv: MATTR（窗口 100，与 RAY-599 同口径）",
            "mtld": "per-text-table.csv: mtld 列（阈值 0.72，与 RAY-599 同口径）；"
                    "表内无该列时取 mattr_vs_mtld_results.json 的 records",
        },
        "inputs": {
            "table": {
                "path": display_path(args.table),
                "sha256": sha256(args.table),
                "n_rows": len(rows),
                "n_human": len(humans),
                "models": {m: sum(1 for r in rows if r["model"] == m) for m in MODELS},
            },
            "mtld_json": json_meta,
            "warnings": warnings,
        },
        "models": matched,
        "tolerance_sensitivity": sens,
        "reference_full_sample": full,
        "conclusion": {
            "sentence": conclusion,
            "matched_test_performed": bool(eligible),
            "models_eligible": eligible,
            "reversal_check": reversal,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # ---- 终端摘要 ----
    print(f"输入：{args.table}  ({len(rows)} 行 / 人类 {len(humans)})")
    print(f"输出：{args.out}\n")
    print(f"{'模型':<24}{'候选':>5}{'≤10%':>7}{'10–20%':>7}{'>20%/缺':>9}"
          f"{'配对':>5}{'平均差%':>8}{'中位长度比':>10}{'可检验':>7}")
    for m in MODELS:
        r = matched[m]
        print(f"{m:<24}{r['n_candidates']:>5}{r['n_within_10pct']:>6}"
              f"{r['n_within_10_to_20pct']:>6}{r['n_unmatched']:>9}{r['n_pairs']:>5}"
              f"{(r['mean_abs_diff_pct_matched'] or 0):>8.1f}"
              f"{(r['median_word_count_ratio_model_over_human'] or 0):>10.2f}"
              f"{'是' if r['eligible_for_test'] else '否':>7}")
    print("\n容差敏感性（各模型配对数）：")
    for pct, g in sens["grid"].items():
        counts = g["n_pairs_by_model"]
        print(f"  ±{pct:>3}%: " + "  ".join(f"{m.split('-')[0]}={counts[m]}" for m in MODELS))
    print("\n达到 15 对所需最小容差：" + "  ".join(
        f"{m.split('-')[0]}={sens['min_tolerance_pct_for_15_pairs'][m]}%"
        for m in MODELS))
    print("\n全样本对照（未做长度筛选）：")
    for m in MODELS:
        t = full["models"][m]["tests"]
        print(f"  {m:<24} n={full['models'][m]['n_pairs']:>2}  "
              + (f"MATTR p={t['mattr']['p']:.4g} d={t['mattr']['cohens_d']:.2f}  "
                 f"MTLD p={t['mtld']['p']:.4g} d={t['mtld']['cohens_d']:.2f}"
                 if t and "mattr" in t and "mtld" in t else "检验不完整"))
    print(f"\n结论：{conclusion}")


if __name__ == "__main__":
    main()
