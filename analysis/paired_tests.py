#!/usr/bin/env python3
"""四指标配对 t 检验 + Levene 方差齐性 + Holm 校正（RAY-599）。

按王雅琴老师 2026-10-26 组会要求：
  1. 同一 prompt_id 下 AI 文本与 Human 文本配对（每模型 30 对），
     差值 = AI − Human；报均值差、t、df、p、配对 Cohen's d。
  2. 每个指标、每个模型与 Human 做 Levene 方差齐性检验：
     主口径 center="median"（Brown–Forsythe），同时给 center="mean" 作对照。
     任一版本 p < .05 的格子补非参数对照：配对 Wilcoxon signed-rank、
     组间 Mann–Whitney U（后者忽略配对，仅作参照）。
  3. 16 组（4 指标 × 4 模型）原始 p 一起做 Holm 逐步校正。
  4. 只报描述与检验结果，不做因果推断。

输入：analysis/per-text-table.csv（150 行 = 30 prompts × 5 组）
输出：analysis/tests-paired.csv（长表 16 行）
      analysis/tests-paired.md（表格 + 每指标一段结论 + 复算核对）

复现：python3 analysis/paired_tests.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent
INPUT_CSV = BASE / "per-text-table.csv"
OUTPUT_CSV = BASE / "tests-paired.csv"
OUTPUT_MD = BASE / "tests-paired.md"

HUMAN = "Human"
MODELS = ["Claude", "GPT", "DeepSeek", "Kimi"]
N_PAIRS = 30
ALPHA = 0.05

METRICS = [
    {
        "key": "MATTR",
        "label": "MATTR（窗口 100）",
        "short": "MATTR",
        "dec": 4,
        "caveat": (
            "MATTR 固定窗口 100，对文本长度不如 TTR 敏感；Human 组跨文本方差较大，"
            "均值差与 d 应结合方差齐性结果一起看。"
        ),
    },
    {
        "key": "mtld",
        "label": "MTLD",
        "short": "MTLD",
        "dec": 2,
        "caveat": (
            "MTLD 与 MATTR 使用不同的 token 口径（MTLD 只取字母词，剔除数字与带标点词），"
            "两者只比方向、不比绝对水平。"
        ),
    },
    {
        "key": "mean_sentence_length",
        "label": "平均句长",
        "short": "句长",
        "dec": 2,
        "caveat": (
            "平均句长的方向在四个模型上不一致，不能概括为「AI 句子更长」或「AI 句子更短」；"
            "句长依赖 spaCy 分句，缩写与省略号处可能有切分误差。"
        ),
    },
    {
        "key": "mean_paragraph_length",
        "label": "平均段长",
        "short": "段长",
        "dec": 2,
        "caveat": (
            "平均段长受段落切分与少数超长段落影响：Human 段长 SD 约 100 词、存在极端值，"
            "均值差与 d 的稳定性弱于其他指标；本表只作描述。"
        ),
    },
]


@dataclass
class Result:
    metric: str
    metric_label: str
    model: str
    n_pairs: int
    mean_diff: float
    sd_diff: float
    median_diff: float
    t: float
    df: int
    p_raw: float
    p_holm: float
    cohens_d: float
    levene_bf_stat: float
    levene_bf_p: float
    levene_mean_stat: float
    levene_mean_p: float
    wilcoxon_stat: float
    wilcoxon_p: float
    mwu_stat: float
    mwu_p: float
    shapiro_p: float


# ── 格式化 ────────────────────────────────────────────────────────────────

def fmt_num(value: float, dec: int, sign: bool = False) -> str:
    """固定小数位；避免 -0.00 这类负零。"""
    if abs(value) < 0.5 * 10 ** (-dec):
        value = 0.0
    return f"{value:+.{dec}f}" if sign else f"{value:.{dec}f}"


def _trim_leading_zero(text: str) -> str:
    """0.047 → .047；1.000 保持原样。"""
    return text[1:] if text.startswith("0.") else text


def fmt_p_short(p: float) -> str:
    """表格用：< .001 / .047 / 1.000。"""
    return "< .001" if p < 0.001 else _trim_leading_zero(f"{p:.3f}")


def fmt_p_apa(p: float) -> str:
    """正文用：p < .001 / p = .047 / p = 1.000。"""
    return "p < .001" if p < 0.001 else "p = " + _trim_leading_zero(f"{p:.3f}")


def fmt_p_sci(p: float) -> str:
    """报告正文用：保留 3 位有效数字的科学计数法。"""
    return f"{p:.3e}"


def fmt_p_csv(p: float) -> str:
    """CSV 用：保留 7 位有效数字，便于逐位复算。"""
    return f"{p:.6e}"


def join_models(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return "、".join(items[:-1]) + " 和 " + items[-1]


# ── 统计 ──────────────────────────────────────────────────────────────────

def holm_adjust(p_values: np.ndarray) -> np.ndarray:
    """Holm 逐步校正（含单调化），返回与输入同序的校正 p。"""
    p_values = np.asarray(p_values, dtype=float)
    m = p_values.size
    order = np.argsort(p_values, kind="mergesort")
    adjusted = np.empty(m, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = (m - rank) * p_values[idx]
        running = max(running, candidate)
        adjusted[idx] = min(1.0, running)
    return adjusted


def load_pairs(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"找不到输入文件：{path}")

    df = pd.read_csv(path)
    required = ["prompt_id", "model", *[m["key"] for m in METRICS]]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"输入缺少列：{missing}")

    expected_models = [HUMAN] + MODELS
    actual_models = sorted(df["model"].unique().tolist())
    if actual_models != sorted(expected_models):
        raise SystemExit(
            f"模型集合不符：期望 {sorted(expected_models)}，实际 {actual_models}"
        )

    if df.duplicated(["prompt_id", "model"]).any():
        dup = df.loc[df.duplicated(["prompt_id", "model"], keep=False), ["prompt_id", "model"]]
        raise SystemExit(f"存在重复的 (prompt_id, model)：\n{dup}")

    null_cols = [c for c in required if df[c].isna().any()]
    if null_cols:
        raise SystemExit(f"以下列存在空值/NaN，无法配对：{null_cols}")

    counts = df.groupby("model")["prompt_id"].nunique().reindex(expected_models)
    if not (counts == N_PAIRS).all():
        raise SystemExit(f"每组应有 {N_PAIRS} 个 prompt，实际：\n{counts}")

    per_prompt = df.groupby("prompt_id")["model"].nunique()
    if not (per_prompt == len(expected_models)).all():
        bad = per_prompt[per_prompt != len(expected_models)]
        raise SystemExit(f"以下 prompt 未凑齐五组：\n{bad}")

    prompt_sets = {name: set(group["prompt_id"]) for name, group in df.groupby("model")}
    human_prompts = prompt_sets[HUMAN]
    mismatched = {
        name: sorted(prompts ^ human_prompts)
        for name, prompts in prompt_sets.items()
        if prompts != human_prompts
    }
    if mismatched:
        raise SystemExit(f"各模型的 prompt_id 集合不一致，无法逐题配对：{mismatched}")

    return df


def compute_results(df: pd.DataFrame) -> list[Result]:
    results: list[Result] = []
    for metric in METRICS:
        key = metric["key"]
        wide = (
            df.pivot(index="prompt_id", columns="model", values=key)
            .sort_index()
            .reindex(columns=[HUMAN] + MODELS)
        )
        if wide.isna().any().any():
            raise SystemExit(f"{key} 的配对宽表存在缺失")

        human = wide[HUMAN].to_numpy(dtype=float)
        for model in MODELS:
            ai = wide[model].to_numpy(dtype=float)
            diff = ai - human
            n = diff.size
            mean_diff = float(np.mean(diff))
            sd_diff = float(np.std(diff, ddof=1))
            t_stat = mean_diff / (sd_diff / math.sqrt(n))
            dfree = n - 1
            p_raw = float(2 * stats.t.sf(abs(t_stat), dfree))
            d = mean_diff / sd_diff

            levene_bf = stats.levene(ai, human, center="median")
            levene_mean = stats.levene(ai, human, center="mean")
            wilcoxon = stats.wilcoxon(ai, human, alternative="two-sided")
            mwu = stats.mannwhitneyu(ai, human, alternative="two-sided")
            shapiro = stats.shapiro(diff)

            results.append(
                Result(
                    metric=key,
                    metric_label=metric["label"],
                    model=model,
                    n_pairs=n,
                    mean_diff=mean_diff,
                    sd_diff=sd_diff,
                    median_diff=float(np.median(diff)),
                    t=float(t_stat),
                    df=dfree,
                    p_raw=p_raw,
                    p_holm=float("nan"),  # 稍后统一填
                    cohens_d=float(d),
                    levene_bf_stat=float(levene_bf.statistic),
                    levene_bf_p=float(levene_bf.pvalue),
                    levene_mean_stat=float(levene_mean.statistic),
                    levene_mean_p=float(levene_mean.pvalue),
                    wilcoxon_stat=float(wilcoxon.statistic),
                    wilcoxon_p=float(wilcoxon.pvalue),
                    mwu_stat=float(mwu.statistic),
                    mwu_p=float(mwu.pvalue),
                    shapiro_p=float(shapiro.pvalue),
                )
            )

    adjusted = holm_adjust(np.array([r.p_raw for r in results]))
    for result, p_adj in zip(results, adjusted):
        result.p_holm = float(p_adj)

    if any(r.p_holm + 1e-15 < r.p_raw for r in results):
        raise SystemExit("Holm 校正结果小于原始 p，实现有误")
    if any(not all(math.isfinite(v) for v in (r.mean_diff, r.t, r.p_raw, r.p_holm, r.cohens_d)) for r in results):
        raise SystemExit("结果中出现 NaN/Inf")
    return results


def lev_flag(result: Result) -> str:
    if result.levene_bf_p < ALPHA and result.levene_mean_p < ALPHA:
        return "不齐"
    if result.levene_bf_p < ALPHA:
        return "不齐（仅中位数版）"
    if result.levene_mean_p < ALPHA:
        return "不齐（仅均值版）"
    return "齐"


def needs_nonparametric(result: Result) -> bool:
    return result.levene_bf_p < ALPHA or result.levene_mean_p < ALPHA


def build_note(result: Result) -> str:
    if not needs_nonparametric(result):
        return "方差齐性成立"

    if result.levene_bf_p < ALPHA and result.levene_mean_p < ALPHA:
        head = (
            "Levene 不齐（Brown–Forsythe 中位数版 "
            f"{fmt_p_apa(result.levene_bf_p)}；均值版 {fmt_p_apa(result.levene_mean_p)}）"
        )
    elif result.levene_bf_p < ALPHA:
        head = (
            "Levene 不齐（Brown–Forsythe 中位数版 "
            f"{fmt_p_apa(result.levene_bf_p)}；均值版未达显著，{fmt_p_apa(result.levene_mean_p)}）"
        )
    else:
        head = (
            "Levene 仅均值版不齐（中位数版 "
            f"{fmt_p_apa(result.levene_bf_p)} 未达显著；均值版 {fmt_p_apa(result.levene_mean_p)}）"
        )

    tail = (
        f"补充 Wilcoxon signed-rank {fmt_p_apa(result.wilcoxon_p)}；"
        f"Mann–Whitney U {fmt_p_apa(result.mwu_p)}（原始 p，未校正）"
    )
    return f"{head}；{tail}"


# ── Markdown ──────────────────────────────────────────────────────────────

def render_main_table(results: list[Result]) -> list[str]:
    lines = [
        "| 指标 | 模型 | n | 均值差（AI−Human） | 差值 SD | t(29) | p（原始） | p（Holm） | Cohen's d | Holm 后显著 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    by_metric = {m["key"]: m for m in METRICS}
    for result in results:
        dec = by_metric[result.metric]["dec"]
        lines.append(
            "| {metric} | {model} | {n} | {diff} | {sd} | {t} | {p_raw} | {p_holm} | {d} | {sig} |".format(
                metric=result.metric_label,
                model=result.model,
                n=result.n_pairs,
                diff=fmt_num(result.mean_diff, dec, sign=True),
                sd=fmt_num(result.sd_diff, dec),
                t=fmt_num(result.t, 2),
                p_raw=fmt_p_short(result.p_raw),
                p_holm=fmt_p_short(result.p_holm),
                d=fmt_num(result.cohens_d, 2, sign=True),
                sig="是" if result.p_holm < ALPHA else "否",
            )
        )
    return lines


def render_levene_table(results: list[Result]) -> list[str]:
    lines = [
        "| 指标 | 模型 | BF W | BF p（中位数） | Levene W（均值版） | p（均值版） | 判定 | 非参数补充 |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for result in results:
        lines.append(
            "| {metric} | {model} | {bfw} | {bfp} | {mw} | {mp} | {flag} | {supp} |".format(
                metric=result.metric_label,
                model=result.model,
                bfw=fmt_num(result.levene_bf_stat, 3),
                bfp=fmt_p_short(result.levene_bf_p),
                mw=fmt_num(result.levene_mean_stat, 3),
                mp=fmt_p_short(result.levene_mean_p),
                flag=lev_flag(result),
                supp="Wilcoxon + MWU" if needs_nonparametric(result) else "—",
            )
        )
    return lines


def render_nonparametric_table(results: list[Result]) -> list[str]:
    flagged = [r for r in results if needs_nonparametric(r)]
    if not flagged:
        return ["无需补充（两版 Levene 均未拒绝方差齐性）。"]
    lines = [
        "| 指标 | 模型 | 触发版本 | Wilcoxon W | Wilcoxon p | MWU U | MWU p | 与配对 t 判断一致 |",
        "|---|---|---|---:|---:|---:|---:|:---:|",
    ]
    for result in flagged:
        trigger = []
        if result.levene_bf_p < ALPHA:
            trigger.append("中位数")
        if result.levene_mean_p < ALPHA:
            trigger.append("均值")
        same = (result.wilcoxon_p < ALPHA) == (result.p_raw < ALPHA)
        lines.append(
            "| {metric} | {model} | {trigger} | {w} | {wp} | {u} | {up} | {same} |".format(
                metric=result.metric_label,
                model=result.model,
                trigger="+".join(trigger),
                w=fmt_num(result.wilcoxon_stat, 1),
                wp=fmt_p_short(result.wilcoxon_p),
                u=fmt_num(result.mwu_stat, 1),
                up=fmt_p_short(result.mwu_p),
                same="是" if same else "否",
            )
        )
    return lines


def render_metric_paragraph(metric: dict, results: list[Result]) -> str:
    dec = metric["dec"]
    diffs = [r.mean_diff for r in results]
    all_positive = all(v > 0 for v in diffs)
    all_negative = all(v < 0 for v in diffs)

    if all_positive or all_negative:
        word = "正" if all_positive else "负"
        lo = min(results, key=lambda r: r.mean_diff)
        hi = max(results, key=lambda r: r.mean_diff)
        if all_positive:
            first = (
                f"四个模型的均值差（AI − Human）均为{word}，"
                f"从 {fmt_num(lo.mean_diff, dec, sign=True)}（{lo.model}）"
                f"到 {fmt_num(hi.mean_diff, dec, sign=True)}（{hi.model}）。"
            )
        else:
            first = (
                f"四个模型的均值差（AI − Human）均为{word}，"
                f"在 {fmt_num(lo.mean_diff, dec, sign=True)}（{lo.model}）"
                f"到 {fmt_num(hi.mean_diff, dec, sign=True)}（{hi.model}）之间。"
            )
    else:
        parts = "、".join(
            f"{r.model} {fmt_num(r.mean_diff, dec, sign=True)}" for r in results
        )
        first = f"四个模型的均值差（AI − Human）方向不一致：{parts}。"

    sig_holm = [r for r in results if r.p_holm < ALPHA]
    raw_only = [r for r in results if r.p_raw < ALPHA <= r.p_holm]
    nonsig = [r for r in results if r.p_raw >= ALPHA]

    if not sig_holm:
        second = (
            "Holm 校正（16 组）后四组均不显著"
            f"（p_holm = {fmt_p_short(min(r.p_holm for r in results))}"
            f"–{fmt_p_short(max(r.p_holm for r in results))}）。"
        )
    else:
        details = "、".join(
            f"{r.model}（p_holm {fmt_p_short(r.p_holm)}）" for r in sig_holm
        )
        if len(sig_holm) == len(results):
            second = f"Holm 校正（16 组）后四组均仍显著：{details}。"
        else:
            second = f"Holm 校正（16 组）后 {details} 仍显著。"
        if raw_only:
            second += (
                f"{join_models([r.model for r in raw_only])} 仅原始 p 显著"
                f"（{fmt_p_apa(raw_only[0].p_raw)}，{fmt_p_apa(raw_only[0].p_holm)}）。"
            )
        if nonsig:
            second += (
                f"{join_models([r.model for r in nonsig])} 原始与校正后均不显著"
                f"（{fmt_p_apa(nonsig[0].p_raw)}）。"
            )

    bf_viol = [r for r in results if r.levene_bf_p < ALPHA]
    mean_viol = [r for r in results if r.levene_mean_p < ALPHA]
    mean_only = [r for r in mean_viol if r.levene_bf_p >= ALPHA]

    if not bf_viol and not mean_viol:
        third = (
            "方差齐性检验两版均未拒绝：Brown–Forsythe 版 "
            f"p = {fmt_p_short(min(r.levene_bf_p for r in results))}–"
            f"{fmt_p_short(max(r.levene_bf_p for r in results))}，"
            "均值版 "
            f"p = {fmt_p_short(min(r.levene_mean_p for r in results))}–"
            f"{fmt_p_short(max(r.levene_mean_p for r in results))}，无需补非参数检验。"
        )
    else:
        parts = []
        if bf_viol:
            parts.append(
                "Brown–Forsythe 版在 "
                + "、".join(f"{r.model}（{fmt_p_apa(r.levene_bf_p)}）" for r in bf_viol)
                + "上拒绝方差齐性"
            )
        if mean_viol:
            parts.append(
                "均值版在 "
                + "、".join(f"{r.model}（{fmt_p_apa(r.levene_mean_p)}）" for r in mean_viol)
                + "上拒绝方差齐性"
            )
        third = "方差齐性：" + "；".join(parts) + "。"
        if mean_only:
            detail = "、".join(
                f"{r.model}（BF {fmt_p_apa(r.levene_bf_p)}）" for r in mean_only
            )
            third += (
                f"其中 {detail}的中位数版未达显著，按均值版保守纳入补充检验。"
            )

    flagged = [r for r in results if needs_nonparametric(r)]
    if flagged:
        details = "；".join(
            f"{r.model}（Wilcoxon {fmt_p_apa(r.wilcoxon_p)}，MWU {fmt_p_apa(r.mwu_p)}）"
            for r in flagged
        )
        agree = all((r.wilcoxon_p < ALPHA) == (r.p_raw < ALPHA) for r in flagged)
        fourth = (
            f"补充非参数对照：{details}。"
            f"Wilcoxon 与配对 t 在 α = .05 下的显著性判断{'一致' if agree else '不一致'}（均为原始 p）；"
            "Mann–Whitney U 忽略配对，只作组间参照。"
        )
    else:
        fourth = ""

    return "".join(x for x in (first, second, third, fourth, metric["caveat"]) if x)


def manual_check(df: pd.DataFrame, metric: str, model: str) -> dict:
    """用纯 Python 逐项重算，绕开 pandas/numpy 的向量化实现。"""
    wide = (
        df.loc[df["model"].isin([HUMAN, model]), ["prompt_id", "model", metric]]
        .pivot(index="prompt_id", columns="model", values=metric)
        .sort_index()
    )
    diffs = [float(a) - float(h) for a, h in zip(wide[model], wide[HUMAN])]
    n = len(diffs)
    total = sum(diffs)
    mean = total / n
    ss = sum((x - mean) ** 2 for x in diffs)
    sd = math.sqrt(ss / (n - 1))
    t_stat = mean / (sd / math.sqrt(n))
    p_value = float(2 * stats.t.sf(abs(t_stat), n - 1))
    return {
        "n": n,
        "total": total,
        "mean": mean,
        "ss": ss,
        "sd": sd,
        "t": t_stat,
        "p": p_value,
        "d": mean / sd,
        "n_diff_zero": sum(1 for x in diffs if x == 0),
    }


def result_for(results: list[Result], metric: str, model: str) -> Result:
    return next(r for r in results if r.metric == metric and r.model == model)


def render_manual_check(
    df: pd.DataFrame,
    results: list[Result],
    metric: str,
    model: str,
) -> list[str]:
    info = next(m for m in METRICS if m["key"] == metric)
    dec = info["dec"]
    check = manual_check(df, metric, model)
    main = result_for(results, metric, model)
    diff_mean = abs(check["mean"] - main.mean_diff)
    diff_t = abs(check["t"] - main.t)
    diff_p = abs(check["p"] - main.p_raw)
    diff_d = abs(check["d"] - main.cohens_d)
    if max(diff_mean, diff_t, diff_d) > 1e-12 or diff_p > 1e-15:
        raise SystemExit(f"复算不一致：{metric} × {model}")

    return [
        f"**{info['label']} × {model}**",
        "",
        f"- {check['n']} 对差值之和 = {fmt_num(check['total'], 6)}，"
        f"均值 = {fmt_num(check['total'], 6)} / {check['n']} = {fmt_num(check['mean'], 6)}",
        f"- 样本 SD（ddof = 1）：平方和 {fmt_num(check['ss'], 6)} ÷ {check['n'] - 1} 后开方 = {fmt_num(check['sd'], 6)}",
        f"- t = {fmt_num(check['mean'], 6)} / ({fmt_num(check['sd'], 6)} / √{check['n']}) = {fmt_num(check['t'], 4)}，df = {check['n'] - 1}",
        f"- 双侧 p = {fmt_p_sci(check['p'])}；d = {fmt_num(check['mean'], 6)} / {fmt_num(check['sd'], 6)} = {fmt_num(check['d'], 4)}",
        f"- 与主表比对：均值差 {diff_mean:.1e}、t {diff_t:.1e}、p {diff_p:.1e}、d {diff_d:.1e}",
        "",
    ]


def render_normality_section(results: list[Result]) -> list[str]:
    """配对 t 的正态性诊断（附加，不在 CSV 主表内）。"""
    flagged = [r for r in results if r.shapiro_p < ALPHA]
    if not flagged:
        return ["配对差值的 Shapiro–Wilk 检验在 16 组中均未拒绝正态性（p ≥ .05）。"]
    lines = [
        "配对 t 的假设是**差值**近似正态，这与 Levene 检验的组间方差齐性不是同一件事。"
        "下表只列出 Shapiro–Wilk p < .05 的组，Wilcoxon 作为不依赖正态假设的参照；"
        "该诊断非老师要求，不进入 `tests-paired.csv`。",
        "",
        "| 指标 | 模型 | Shapiro–Wilk p | Wilcoxon p | 与配对 t 判断一致 |",
        "|---|---|---:|---:|:---:|",
    ]
    for result in flagged:
        same = (result.wilcoxon_p < ALPHA) == (result.p_raw < ALPHA)
        lines.append(
            f"| {result.metric_label} | {result.model} | "
            f"{fmt_p_short(result.shapiro_p)} | {fmt_p_short(result.wilcoxon_p)} | "
            f"{'是' if same else '否'} |"
        )
    agree = all((r.wilcoxon_p < ALPHA) == (r.p_raw < ALPHA) for r in flagged)
    lines += [
        "",
        f"共 {len(flagged)}/16 组差值偏离正态；这些组上 Wilcoxon 与配对 t 的显著性判断"
        f"{'全部一致' if agree else '存在不一致'}（α = .05，均为原始 p）。",
        "",
    ]
    return lines


def render_markdown(results: list[Result], df: pd.DataFrame) -> str:
    today = date.today().isoformat()
    by_metric = {m["key"]: m for m in METRICS}

    sig_counts = []
    for metric in METRICS:
        subset = [r for r in results if r.metric == metric["key"]]
        n_sig = sum(1 for r in subset if r.p_holm < ALPHA)
        sig_counts.append((metric, subset, n_sig))

    lines = [
        "# 四指标配对 t 检验、Levene 方差齐性与 Holm 校正",
        "",
        f"**生成日期**：{today}（由脚本自动生成，请勿手改）  ",
        "**脚本**：`analysis/paired_tests.py`  ",
        "**输入**：`analysis/per-text-table.csv`（150 行 = 30 prompts × 5 组）  ",
        "**输出**：`analysis/tests-paired.csv`（长表 16 行）、本文件",
        "",
        "## 方法",
        "",
        "- **配对键**：`prompt_id`（0–29）。同一 prompt 下取该模型文本与 Human 文本为 1 对，"
        "差值 $d_i = \\text{AI}_i - \\text{Human}_i$，正值为 AI 更高。四个模型各 30 对，$df = 29$。",
        "- **配对 t 检验**：$t = \\bar{d} / (s_d / \\sqrt{n})$，双侧 p；"
        "**Cohen's d** 用配对口径 $d = \\bar{d} / s_d$，$s_d$ 为差值样本标准差（ddof = 1），"
        "不做 Hedges 小样本校正。",
        "- **方差齐性**：Levene 检验，比较该模型 30 篇与 Human 30 篇；"
        "主口径 `center = \"median\"`（Brown–Forsythe），同时给 `center = \"mean\"` 作对照。"
        "任一版本 p < .05 即视为不齐，并按保守口径补充非参数检验（只由主口径触发也能满足要求）。",
        "- **非参数对照**：配对用 Wilcoxon signed-rank（双侧；scipy 默认零差值处理与 `method=\"auto\"`，n = 30 时为正态近似），"
        "组间用 Mann–Whitney U（双侧）。这些 p 为**原始值**，未纳入 Holm 校正。",
        "- **多重比较**：4 指标 × 4 模型 = 16 组原始 p 一起做 Holm 逐步校正，`p_holm` 已单调化，与 α = .05 比较。",
        "- **口径**：只报描述统计与检验结果，不做因果推断；显著性不被解释为「AI 与人类存在本质差异」。",
        "",
        "## 结论速览",
        "",
        "| 指标 | 30 对/模型 | Holm 后显著的模型数 | 显著模型 | 差值方向 |",
        "|---|---:|:---:|---|---|",
    ]
    for metric, subset, n_sig in sig_counts:
        sig_models = [r.model for r in subset if r.p_holm < ALPHA]
        diffs = [r.mean_diff for r in subset]
        if all(v > 0 for v in diffs):
            direction = "四组均为正"
        elif all(v < 0 for v in diffs):
            direction = "四组均为负"
        else:
            direction = "方向不一致"
        lines.append(
            f"| {metric['label']} | {N_PAIRS} | {n_sig}/4 | "
            f"{join_models(sig_models) if sig_models else '—'} | {direction} |"
        )

    lines += [
        "",
        "## 主表：配对 t 检验与 Holm 校正",
        "",
        *render_main_table(results),
        "",
        "> `p（原始）`为双侧配对 t 检验；`p（Holm）`为 16 组一起校正后的值。"
        "均值差与 d 的符号一致：正 = AI 高于 Human。",
        "",
        "## 方差齐性（Levene）",
        "",
        *render_levene_table(results),
        "",
        "> BF = Brown–Forsythe（中位数中心，主口径）；均值版为对照。"
        "`判定`中的「仅均值版」表示中位数版 p ≥ .05、均值版 p < .05。",
        "",
        "## 非参数对照（方差齐性不满足的格子）",
        "",
        *render_nonparametric_table(results),
        "",
        "## 附加诊断：配对差值的正态性",
        "",
        *render_normality_section(results),
        "## 分指标结论",
        "",
    ]

    for metric in METRICS:
        subset = [r for r in results if r.metric == metric["key"]]
        lines += [
            f"### {metric['label']}",
            "",
            render_metric_paragraph(metric, subset),
            "",
        ]

    min_row = min(results, key=lambda r: r.p_raw)
    lines += [
        "## 复算核对",
        "",
        "下面两组用纯 Python 逐项重算（不用 pandas/numpy 的均值、标准差与 t 检验），"
        "并与主表逐位比对；脚本每次运行都会执行同样检查，不一致即报错退出。",
        "",
        *render_manual_check(df, results, "MATTR", "Claude"),
        *render_manual_check(df, results, "mean_paragraph_length", "GPT"),
        "**Holm 校正核对**",
        "",
        f"16 组中 {min_row.metric_label} × {min_row.model} 的原始 p 最小"
        f"（{fmt_p_sci(min_row.p_raw)}），Holm 第一步乘以 16："
        f"16 × {fmt_p_sci(min_row.p_raw)} = {fmt_p_sci(min(1.0, 16 * min_row.p_raw))}，"
        f"与表中 `p_holm = {fmt_p_sci(min_row.p_holm)}` 一致；"
        "其余组按排序依次乘以 15、14……并做单调化。",
        "",
        "## 口径与限制",
        "",
        "1. **Levene 检验的是组间方差齐性**，不是配对 t 检验的正态性假设；"
        "本表按老师要求报告它，并用它决定是否补非参数对照，两者在解释上分开看。",
        "2. 非参数 p 值未做多重比较校正；Mann–Whitney U 忽略配对关系，只作组间参照，"
        "配对设计下 Wilcoxon 更贴合。",
        "3. 段长的均值差对少数超长 Human 段落敏感：中位差与均值差可能不同号（见下），"
        "因此段长只作描述，不据此下结论。",
        "4. MATTR（窗口 100）与 MTLD 的 token 口径不同，两者只比方向、不比绝对水平。",
        "5. 本表不改变 `per-text-table.csv`，也不改清洗与指标计算；"
        "所有数值可由 `python3 analysis/paired_tests.py` 重跑复现。",
        "",
        "## 段长中位差（仅作稳健性参照）",
        "",
        "| 模型 | 均值差 | 中位差 | 差值 SD |",
        "|---|---:|---:|---:|",
    ]
    for result in [r for r in results if r.metric == "mean_paragraph_length"]:
        lines.append(
            f"| {result.model} | {fmt_num(result.mean_diff, 2, sign=True)} | "
            f"{fmt_num(result.median_diff, 2, sign=True)} | {fmt_num(result.sd_diff, 2)} |"
        )

    lines += [
        "",
        "---",
        "",
        f"*数据：`analysis/per-text-table.csv`（150 篇，30 prompts × 5 组）；"
        f"脚本：`analysis/paired_tests.py`；生成日期：{today}。*",
        "",
    ]
    return "\n".join(lines)


# ── 输出 ──────────────────────────────────────────────────────────────────

def write_csv(results: list[Result]) -> None:
    rows = []
    for r in results:
        rows.append(
            {
                "metric": r.metric,
                "model": r.model,
                "n_pairs": r.n_pairs,
                "mean_diff": fmt_num(r.mean_diff, 6),
                "t": fmt_num(r.t, 6),
                "df": r.df,
                "p_raw": fmt_p_csv(r.p_raw),
                "p_holm": fmt_p_csv(r.p_holm),
                "cohens_d": fmt_num(r.cohens_d, 6),
                "levene_stat": fmt_num(r.levene_bf_stat, 6),
                "levene_p": fmt_p_csv(r.levene_bf_p),
                "note": build_note(r),
            }
        )
    columns = [
        "metric",
        "model",
        "n_pairs",
        "mean_diff",
        "t",
        "df",
        "p_raw",
        "p_holm",
        "cohens_d",
        "levene_stat",
        "levene_p",
        "note",
    ]
    pd.DataFrame(rows, columns=columns).to_csv(OUTPUT_CSV, index=False)


def main() -> None:
    df = load_pairs(INPUT_CSV)
    results = compute_results(df)
    write_csv(results)
    OUTPUT_MD.write_text(render_markdown(results, df), encoding="utf-8")

    print(f"输入：{INPUT_CSV}（{len(df)} 行，{df['prompt_id'].nunique()} prompts）")
    print(f"输出：{OUTPUT_CSV}（{len(results)} 组）")
    print(f"输出：{OUTPUT_MD}")
    print("配对校验：每模型 30 对，每 prompt 五组齐全，无 NaN")
    holm_sig = [r for r in results if r.p_holm < ALPHA]
    print(f"Holm 后显著：{len(holm_sig)}/16")
    for r in results:
        print(
            f"  {r.metric:22s} {r.model:9s} diff={fmt_num(r.mean_diff, 4, sign=True):>10s} "
            f"t={fmt_num(r.t, 2):>7s} p={fmt_p_short(r.p_raw):>6s} "
            f"p_holm={fmt_p_short(r.p_holm):>6s} d={fmt_num(r.cohens_d, 2, sign=True):>6s} "
            f"BFp={fmt_p_short(r.levene_bf_p):>6s} meanp={fmt_p_short(r.levene_mean_p):>6s}"
        )


if __name__ == "__main__":
    main()
