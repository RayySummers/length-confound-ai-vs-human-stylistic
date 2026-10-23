#!/usr/bin/env python3
"""wordcount_distribution.py — 组会材料②：五组文本的词数分布图。

输入：analysis/per-text-table.csv（每篇文本一行；Human + Claude/GPT/DeepSeek/Kimi）
输出：
  analysis/figures/wordcount-distribution.png  (300 dpi)
  analysis/figures/wordcount-distribution.pdf  (vector)
  analysis/figures/wordcount-distribution-stats.json  (图中所有数字，便于核对/复用)

图注写在 analysis/figures/README.md。文字只描述分布，不作因果解释。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fig_style import GROUP_COLORS, GROUP_ORDER, MODEL_TO_GROUP, apply_style

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba

BASE = Path(__file__).resolve().parent.parent
TABLE = BASE / "analysis" / "per-text-table.csv"
OUT_DIR = BASE / "analysis" / "figures"
OUT_PNG = OUT_DIR / "wordcount-distribution.png"
OUT_PDF = OUT_DIR / "wordcount-distribution.pdf"
OUT_STATS = OUT_DIR / "wordcount-distribution-stats.json"

SHORT_TO_MODEL = {
    "Human": "Human",
    "Claude": "Claude-Sonnet-5-High",
    "GPT": "GPT-5.6-Luna",
    "DeepSeek": "DeepSeek-V4-Flash",
    "Kimi": "Kimi-K3",
}


def load_values() -> dict[str, np.ndarray]:
    values: dict[str, list[float]] = {g: [] for g in GROUP_ORDER}
    unknown: set[str] = set()
    with TABLE.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            model = row["model"].strip()
            group = MODEL_TO_GROUP.get(model)
            if group is None:
                unknown.add(model)
                continue
            raw = row["word_count"].strip()
            if raw:
                values[group].append(float(raw))
    if unknown:
        raise ValueError(f"表里出现了五组之外的模型：{sorted(unknown)}")
    missing = [g for g, v in values.items() if not v]
    if missing:
        raise ValueError(f"这些组没有数据：{missing}")
    return {g: np.sort(np.asarray(v, dtype=float)) for g, v in values.items()}


def describe(values: dict[str, np.ndarray]) -> tuple[dict, dict]:
    groups: list[dict] = []
    for group in GROUP_ORDER:
        v = values[group]
        q1, median, q3 = (float(x) for x in np.percentile(v, [25, 50, 75]))
        groups.append({
            "group": group,
            "model": SHORT_TO_MODEL[group],
            "n": int(v.size),
            "min": float(v.min()),
            "q1": q1,
            "median": median,
            "q3": q3,
            "max": float(v.max()),
            "iqr": q3 - q1,
            "mean": float(v.mean()),
            "sd": float(v.std(ddof=1)),
            "values": [float(x) for x in v],
        })

    human = next(g for g in groups if g["group"] == "Human")
    q1, q3 = human["q1"], human["q3"]
    overlap: dict[str, dict] = {}
    for g in groups[1:]:
        v = np.asarray(g["values"])
        inside = int(np.sum((v >= q1) & (v <= q3)))
        overlap[g["group"]] = {
            "count": inside,
            "n": g["n"],
            "pct": 100.0 * inside / g["n"],
        }
    pooled_n = sum(g["n"] for g in groups[1:])
    pooled_in = sum(o["count"] for o in overlap.values())

    reverse: dict[str, dict] = {}
    hvals = np.asarray(human["values"])
    for g in groups[1:]:
        inside = int(np.sum((hvals >= g["q1"]) & (hvals <= g["q3"])))
        reverse[g["group"]] = {"count": inside, "n": human["n"],
                               "pct": 100.0 * inside / human["n"]}

    stats = {
        "metric": "word_count",
        "definition": "alphabetic tokens (spaCy en_core_web_sm, token.is_alpha)",
        "source": str(TABLE.relative_to(BASE)),
        "mattr_note": "word_count 来自 per-text-table.csv；MATTR 口径见表内 README",
        "groups": groups,
        "human_iqr": [q1, q3],
        "overlap_ai_in_human_iqr": overlap,
        "overlap_all_ai": {
            "count": pooled_in,
            "n": pooled_n,
            "pct": 100.0 * pooled_in / pooled_n,
        },
        "reverse_overlap_human_in_ai_iqr": reverse,
        "figure": {
            "png": str(OUT_PNG.relative_to(BASE)),
            "pdf": str(OUT_PDF.relative_to(BASE)),
        },
    }
    return stats, overlap


def render(values: dict[str, np.ndarray], stats: dict) -> None:
    apply_style()
    groups = stats["groups"]
    human = groups[0]
    q1, median, q3 = human["q1"], human["median"], human["q3"]

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    fig.subplots_adjust(left=0.105, right=0.875, top=0.795, bottom=0.185)
    positions = np.arange(1, len(GROUP_ORDER) + 1)
    colors = [GROUP_COLORS[g] for g in GROUP_ORDER]

    # Human IQR 带（贯穿全图），让「谁落在里面」一眼可见
    ax.axhspan(q1, q3, facecolor="#ececec", zorder=0)
    for edge in (q1, q3):
        ax.axhline(edge, color="#bdbdbd", lw=0.8, ls=(0, (3, 3)), zorder=0.6)
    ax.axvline(1.5, color="#d2d2d2", lw=0.8, ls=(0, (1, 2)), zorder=0.5)

    # 散点（单篇文本）
    rng = np.random.default_rng(20261023)
    for pos, group, color in zip(positions, GROUP_ORDER, colors):
        v = values[group]
        jitter = rng.uniform(-0.155, 0.155, size=v.size)
        ax.scatter(pos + jitter, v, s=13, color=color, alpha=0.62,
                   linewidths=0, zorder=3)

    # 箱线图
    boxes = ax.boxplot(
        [values[g] for g in GROUP_ORDER],
        positions=positions,
        widths=0.30,
        patch_artist=True,
        showfliers=False,
        whis=1.5,
        medianprops={"color": "#1a1a1a", "lw": 1.5, "zorder": 5},
        whiskerprops={"lw": 1.0},
        capprops={"lw": 1.0},
        boxprops={"lw": 1.1},
        zorder=4,
    )
    for patch, color in zip(boxes["boxes"], colors):
        patch.set_facecolor(to_rgba(color, 0.20))
        patch.set_edgecolor(color)
    for artist in ("whiskers", "caps"):
        for line, color in zip(boxes[artist], np.repeat(colors, 2)):
            line.set_color(color)

    # 各 AI 组落在 Human IQR 内的篇数
    y_counts = 1150
    y_header = 1215
    ai_positions = positions[1:]
    ax.text(float(np.mean(ai_positions)), y_header,
            f"AI texts inside the Human IQR ({q1:.0f}–{q3:.0f} words)",
            ha="center", va="center", fontsize=7.6, color="#666666")
    for pos, group in zip(ai_positions, GROUP_ORDER[1:]):
        o = stats["overlap_ai_in_human_iqr"][group]
        ax.text(pos, y_counts, f"{o['count']}/{o['n']}", ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="#2b2b2b")

    # 右侧 IQR 带标签
    ax.text(1.022, (q1 + q3) / 2, f"Human IQR {q1:.0f}–{q3:.0f}",
            transform=ax.get_yaxis_transform(), rotation=90,
            ha="center", va="center", fontsize=7.2, color="#6f6f6f",
            clip_on=False)

    ax.set_xlim(0.45, 5.55)
    ax.set_ylim(0, 1260)
    ax.set_yticks(np.arange(0, 1201, 200))
    ax.set_ylabel("Word count (alphabetic tokens)")
    ax.set_xticks(positions, [
        f"{g}\nn = {len(values[g])}" for g in GROUP_ORDER
    ])
    ax.tick_params(axis="x", length=0, pad=7)
    ax.grid(axis="y", color="#e6e6e6", lw=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#9a9a9a")

    fig.text(0.105, 0.952, "Word count across the five groups",
             fontsize=12.5, fontweight="bold", color="#1a1a1a", va="top")
    fig.text(0.105, 0.906,
             "Same 30-prompt set per group · one dot = one text · box = IQR with median · "
             "whiskers = 1.5×IQR",
             fontsize=8, color="#666666", va="top")
    fig.text(0.105, 0.060,
             "GPT = GPT-5.6-Luna · Claude = Claude-Sonnet-5-High · "
             "DeepSeek = DeepSeek-V4-Flash · Kimi = Kimi-K3",
             fontsize=6.8, color="#6f6f6f", va="top")
    fig.text(0.105, 0.032,
             "Word count = alphabetic tokens (spaCy en_core_web_sm). "
             "Kimi n = 29: prompt 26 has no Kimi text.",
             fontsize=6.8, color="#6f6f6f", va="top")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=300, facecolor="white")
    fig.savefig(OUT_PDF, facecolor="white",
                metadata={"Title": "Word count across the five groups",
                          "Subject": "Per-text word count distributions, Human vs four AI models",
                          "Creator": "analysis/wordcount_distribution.py"})
    plt.close(fig)


def main() -> None:
    values = load_values()
    stats, overlap = describe(values)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render(values, stats)
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'group':8s} {'n':>3s} {'min':>5s} {'Q1':>7s} {'median':>7s} {'Q3':>7s} "
          f"{'max':>5s} {'IQR':>6s}  in Human IQR")
    for g in stats["groups"]:
        extra = ""
        if g["group"] != "Human":
            o = overlap[g["group"]]
            extra = f"{o['count']}/{o['n']} ({o['pct']:.1f}%)"
        print(f"{g['group']:8s} {g['n']:3d} {g['min']:5.0f} {g['q1']:7.2f} "
              f"{g['median']:7.1f} {g['q3']:7.2f} {g['max']:5.0f} {g['iqr']:6.1f}  {extra}")
    pooled = stats["overlap_all_ai"]
    print(f"\nHuman IQR = {stats['human_iqr'][0]:.0f}–{stats['human_iqr'][1]:.0f} words")
    print(f"pooled AI inside Human IQR: {pooled['count']}/{pooled['n']} ({pooled['pct']:.1f}%)")
    print(f"wrote {OUT_PNG.relative_to(BASE)}")
    print(f"wrote {OUT_PDF.relative_to(BASE)}")
    print(f"wrote {OUT_STATS.relative_to(BASE)}")


if __name__ == "__main__":
    main()
