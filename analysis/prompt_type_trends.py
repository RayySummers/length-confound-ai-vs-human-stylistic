#!/usr/bin/env python3
"""prompt_type_trends.py — RAY-602 第二步：任务类型趋势。

读 `analysis/per-text-table.csv`（每篇一行，150 行）与 `analysis/prompt-types.csv`
（RAY-602 第一步的四类分类），产出：

  1. `analysis/by-type.csv`：4 指标 × 4 模型 × 4 类型，同 prompt 的 AI−Human
     配对差值均值，并给出每格 n、两侧均值/标准差、差值中位数与标准差的描述统计。
  2. `analysis/figures/pair-{mattr,mtld,mean-sentence-length,mean-paragraph-length}.png`：
     4 张逐 prompt 散点图，横轴 Human、纵轴 AI，四模型四色 + 四种点形，虚线 y = x。
  3. `analysis/by-type.md`：上面两张产物的文字版，含口径、每类 n、图注与限制。

只做描述统计：不做显著性检验、不建模、不写因果结论。分类若改动，重跑本脚本即可；
本脚本不写 `per-text-table.csv`，也不碰清洗与指标计算。

用法：
    python3 analysis/prompt_type_trends.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fig_style import GROUP_COLORS, apply_style

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
FIGDIR = ANALYSIS / "figures"
PER_TEXT = ANALYSIS / "per-text-table.csv"
PROMPT_TYPES = ANALYSIS / "prompt-types.csv"
OUT_CSV = ANALYSIS / "by-type.csv"
OUT_MD = ANALYSIS / "by-type.md"

MODELS = ["Claude", "GPT", "DeepSeek", "Kimi"]
TYPE_ORDER = ["奇幻/超自然", "科幻/推想", "现实/社会", "极简提示/形式约束"]
# (列名, 文件名 slug, 英文轴标签, 英文短名, 小数位, 是否 log 轴)
METRICS = [
    ("MATTR", "mattr", "MATTR (window 100)", "MATTR", 3, False),
    ("mtld", "mtld", "MTLD", "MTLD", 1, False),
    ("mean_sentence_length", "mean-sentence-length",
     "Mean sentence length (words/sentence)", "Mean sentence length", 2, False),
    # 段长跨 5.5–541 词（近两个数量级），线性轴会把 120 个点挤在左下角；
    # 仅这一张用 log–log，轴标签已注明。
    ("mean_paragraph_length", "mean-paragraph-length",
     "Mean paragraph length (words/paragraph)", "Mean paragraph length", 1, True),
]

# 四模型四色沿用 fig_style 的 AI 蓝色系；点形再区分一次，避免同色系难辨。
MARKERS = {"Claude": "o", "GPT": "s", "DeepSeek": "^", "Kimi": "D"}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    per_text = pd.read_csv(PER_TEXT)
    prompt_types = pd.read_csv(PROMPT_TYPES)

    if len(per_text) != 150:
        sys.exit(f"per-text-table.csv 应为 150 行，实际 {len(per_text)} 行")
    counts = per_text.groupby("model").size().to_dict()
    if counts != {m: 30 for m in ["Human", *MODELS]}:
        sys.exit(f"每组应为 30 篇，实际 {counts}")

    if sorted(prompt_types["prompt_id"].tolist()) != list(range(30)):
        sys.exit("prompt-types.csv 的 prompt_id 应为 0–29 各一条")
    if prompt_types["type"].isna().any() or prompt_types["reason"].isna().any():
        sys.exit("prompt-types.csv 存在空的 type/reason")
    unknown = set(prompt_types["type"]) - set(TYPE_ORDER)
    if unknown:
        sys.exit(f"prompt-types.csv 出现未知类型：{sorted(unknown)}")

    for metric, *_ in METRICS:
        if per_text[metric].isna().any():
            sys.exit(f"{metric} 存在缺失值，先查 per-text-table.csv")
    if per_text["missing_fields"].notna().any():
        sys.exit("per-text-table.csv 的 missing_fields 非空，先补齐再跑")

    # 每类至少 5 条（第一步验收），这里再兜一次底。
    type_n = prompt_types["type"].value_counts()
    too_small = {t: int(type_n.get(t, 0)) for t in TYPE_ORDER if int(type_n.get(t, 0)) < 5}
    if too_small:
        sys.exit(f"以下类型不足 5 条：{too_small}")
    return per_text, prompt_types


def paired_frames(per_text: pd.DataFrame, metric: str) -> dict[str, pd.DataFrame]:
    """返回 {model: DataFrame(index=prompt_id, columns=[human, ai])}。"""
    human = per_text[per_text["model"] == "Human"].set_index("prompt_id")
    frames = {}
    for model in MODELS:
        ai = per_text[per_text["model"] == model].set_index("prompt_id")
        joined = pd.concat(
            [human[metric].rename("human"), ai[metric].rename("ai")], axis=1
        ).dropna()
        if len(joined) != 30:
            sys.exit(f"{metric} × {model} 配对后应 30 对，实际 {len(joined)}")
        frames[model] = joined
    return frames


def build_by_type(per_text: pd.DataFrame, prompt_types: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric, *_ in METRICS:
        frames = paired_frames(per_text, metric)
        for model in MODELS:
            joined = frames[model]
            for type_name in TYPE_ORDER:
                ids = prompt_types.loc[prompt_types["type"] == type_name, "prompt_id"]
                sub = joined.loc[joined.index.isin(ids)]
                n = len(sub)
                diff = sub["ai"] - sub["human"]
                rows.append({
                    "metric": metric,
                    "type": type_name,
                    "model": model,
                    "n_pairs": n,
                    "human_mean": sub["human"].mean(),
                    "human_sd": sub["human"].std(ddof=1) if n > 1 else np.nan,
                    "ai_mean": sub["ai"].mean(),
                    "ai_sd": sub["ai"].std(ddof=1) if n > 1 else np.nan,
                    "mean_diff": diff.mean(),
                    "median_diff": diff.median(),
                    "sd_diff": diff.std(ddof=1) if n > 1 else np.nan,
                    "flag": "n<5" if n < 5 else "",
                })
    return pd.DataFrame(rows)


def plot_scatter(per_text: pd.DataFrame) -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    apply_style()
    for metric, slug, label, short, _decimals, log_scale in METRICS:
        frames = paired_frames(per_text, metric)
        values = np.concatenate([f.to_numpy().ravel() for f in frames.values()])
        lo, hi = float(values.min()), float(values.max())
        if log_scale:
            lim = (lo / 1.12, hi * 1.12)
        else:
            pad = (hi - lo) * 0.04 if hi > lo else max(abs(hi), 1.0) * 0.04
            lim = (lo - pad, hi + pad)

        fig, ax = plt.subplots(figsize=(6.7, 5.7))
        if log_scale:
            ax.set_xscale("log")
            ax.set_yscale("log")
        ax.plot(list(lim), list(lim), ls="--", lw=0.9, color="#8a8a8a", zorder=1,
                label="y = x")
        for model in MODELS:
            joined = frames[model]
            ax.scatter(joined["human"], joined["ai"], s=34, marker=MARKERS[model],
                       color=GROUP_COLORS[model], edgecolors="white", linewidths=0.45,
                       alpha=0.9, zorder=2, label=model)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        if log_scale:
            ax.set_box_aspect(1)
        else:
            ax.set_aspect("equal", adjustable="box")
        scale_note = " (log scale)" if log_scale else ""
        ax.set_xlabel(f"Human — {label}{scale_note}")
        ax.set_ylabel(f"AI — {label}{scale_note}")
        ax.set_title(f"{short}: AI vs Human, one point per prompt\n"
                     f"(30 prompts × 4 models; dashed line: y = x)", fontsize=10.5)
        ax.grid(True, color="#e6e6e6", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        # 图例放到坐标区右侧，避免压住上左/下左的点（句长图就有一个点落在上左）。
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0,
                  frameon=True, framealpha=0.95, edgecolor="#cccccc",
                  fontsize=8.5, handletextpad=0.5, borderpad=0.5)
        fig.tight_layout()
        out = FIGDIR / f"pair-{slug}.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"figure: {out.relative_to(ROOT)}")


def fmt(value: float, decimals: int) -> str:
    return f"{value:+.{decimals}f}"


def write_markdown(by_type: pd.DataFrame, prompt_types: pd.DataFrame) -> None:
    type_n = prompt_types["type"].value_counts().to_dict()
    lines = [
        "# 任务类型趋势：按类聚合与逐 prompt 散点（RAY-602 第二步）",
        "",
        "数据：`analysis/per-text-table.csv`（150 篇 = 30 prompts × 5 组）＋ "
        "`analysis/prompt-types.csv`（第一步四类，已由作者确认）。",
        "脚本：`analysis/prompt_type_trends.py`；重跑会同时覆盖本文件、`by-type.csv` 与四张图。",
        "",
        "## 口径",
        "",
        "- **配对差值** = 同一 `prompt_id` 的 AI 值 − Human 值；先逐题作差，再在类型内取均值。"
        "正数表示该类 AI 高于 Human，负数表示低于。",
        "- 四指标：`MATTR`（窗口 100）、`mtld`、`mean_sentence_length`（字母词/句）、"
        "`mean_paragraph_length`（字母词/段），全部直接取自 `per-text-table.csv`，未重算、未改口径。",
        "- 每格 n = 该类型下的配对数（四模型均完整 30 对，故 n 即该类 prompt 数）。"
        "某格 n < 5 时在 CSV 的 `flag` 列标 `n<5`，此处不解读。",
        "- **只报描述统计**：不做显著性检验、不建模、不作因果推断；n 只有 5–10，差值均值仅描述这份语料。",
        "",
        "## 每类条数",
        "",
        "| 类型 | n |",
        "|---|---:|",
    ]
    for type_name in TYPE_ORDER:
        lines.append(f"| {type_name} | {type_n.get(type_name, 0)} |")
    lines.append(f"| **合计** | **{sum(type_n.values())}** |")
    lines.append("")

    for metric, _slug, label, _short, decimals, _log in METRICS:
        sub = by_type[by_type["metric"] == metric]
        human_mean = (sub.drop_duplicates("type").set_index("type")["human_mean"])
        lines.append(f"## {label}：AI − Human 配对差值均值")
        lines.append("")
        header = "| 类型 (n) | Human 均值 | " + " | ".join(f"{m} 差值" for m in MODELS) + " |"
        lines.append(header)
        lines.append("|---:|---:|" + "---:|" * len(MODELS))
        for type_name in TYPE_ORDER:
            n = int(sub[(sub["type"] == type_name)]["n_pairs"].iloc[0])
            cells = []
            for model in MODELS:
                row = sub[(sub["type"] == type_name) & (sub["model"] == model)].iloc[0]
                cell = fmt(row["mean_diff"], decimals)
                if n < 5:
                    cell += " (n<5)"
                cells.append(cell)
            lines.append(
                f"| {type_name} ({n}) | {human_mean[type_name]:.{decimals}f} | "
                + " | ".join(cells) + " |"
            )
        lines.append("")

    lines += [
        "## 逐 prompt 散点图",
        "",
        "横轴 Human、纵轴 AI，每个点是一个 prompt，四模型四色＋四种点形；虚线为 y = x，"
        "点在线上方表示该题 AI 值高于 Human，下方表示低于。",
        "",
    ]
    for metric, slug, label, _short, _decimals, log_scale in METRICS:
        scale = "，log–log 轴" if log_scale else ""
        lines.append(f"- `analysis/figures/pair-{slug}.png` — {label}，30 prompts × 4 models，"
                     f"300 dpi{scale}。")
    lines += [
        "",
        "## 限制",
        "",
        "- 每类只有 5–10 个 prompt，格内 n 很小；差值均值对个别极端文本敏感（尤其段长），"
        "只作趋势描述，不构成总体估计。",
        "- 类型是按 prompt 写法人工判定的四类，不是随机分组；分类口径见 `prompt-types.csv` 的 `reason` 列。",
        "- 图与表都不回答「AI 是否受任务类型影响更大」，只呈现这份语料上的配对差值。",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"table:  {OUT_MD.relative_to(ROOT)}")


def main() -> None:
    per_text, prompt_types = load_data()
    by_type = build_by_type(per_text, prompt_types)
    by_type.to_csv(OUT_CSV, index=False, float_format="%.6f")
    print(f"table:  {OUT_CSV.relative_to(ROOT)}  ({len(by_type)} 行)")
    write_markdown(by_type, prompt_types)
    plot_scatter(per_text)

    print("\n== 每类 AI − Human 差值均值（描述统计，不作检验） ==")
    for metric, _slug, _label, _short, decimals, _log in METRICS:
        sub = by_type[by_type["metric"] == metric]
        print(f"\n{metric}")
        for type_name in TYPE_ORDER:
            cells = []
            for model in MODELS:
                row = sub[(sub["type"] == type_name) & (sub["model"] == model)].iloc[0]
                cells.append(f"{row['model']}={row['mean_diff']:+.{decimals}f}")
            print(f"  {type_name:12s} n={int(sub[sub['type'] == type_name]['n_pairs'].iloc[0]):2d}  "
                  + "  ".join(cells))


if __name__ == "__main__":
    main()
