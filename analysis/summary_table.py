#!/usr/bin/env python3
"""summary_table.py — 组会材料③：五指标汇总表 + 4 张关键分布图。

  2026-10-28（RAY-598）在 MATTR / 句长 CV / 段长之外加入 MTLD：
  MTLD 阈值取 lexical_diversity 默认 0.72，token 与 word_count 同一套
  （见 analysis/build_per_text_table.py），本脚本只读 CSV 不做重算。

输入：analysis/per-text-table.csv（每篇文本一行；Human + Claude/GPT/DeepSeek/Kimi）
输出：
  analysis/summary-table.csv              长表：指标 × 组，N / 均值 / 标准差 / AI-Human 方差比
  analysis/summary-table.md               可直接贴 PPT 的 Markdown 表格 + 每指标一行判断
  analysis/figures/mattr-distribution.{png,pdf}
  analysis/figures/sentence-length-cv-distribution.{png,pdf}
  analysis/figures/paragraph-length-distribution.{png,pdf}
  analysis/figures/summary-metrics-stats.json   图中所有数字，便于核对

口径：
  - 标准差一律样本标准差（ddof = 1）；方差比 = var(组) / var(Human)，同为 ddof = 1。
  - MATTR 窗口固定 100（沿 analysis/mattr_group_ttest.py）。
  - 句长 = 每句字母词数；句长 CV = 篇内句长 pstdev / mean（见任务①）。
  - 段长 = 每段字母词数。
  - 只做描述统计：不跑检验、不做分类器。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba

from fig_style import GROUP_COLORS, GROUP_ORDER, MODEL_TO_GROUP, apply_style

BASE = Path(__file__).resolve().parent.parent
TABLE = BASE / "analysis" / "per-text-table.csv"
OUT_DIR = BASE / "analysis" / "figures"
OUT_CSV = BASE / "analysis" / "summary-table.csv"
OUT_MD = BASE / "analysis" / "summary-table.md"
OUT_STATS = OUT_DIR / "summary-metrics-stats.json"

SHORT_TO_MODEL = {
    "Human": "Human",
    "Claude": "Claude-Sonnet-5-High",
    "GPT": "GPT-5.6-Luna",
    "DeepSeek": "DeepSeek-V4-Flash",
    "Kimi": "Kimi-K3",
}

# 标题里的指标个数用中文数字（指标数 = METRICS 行数 + word_count）
CN_NUM = {3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八"}

# 任务①的表 2026-10-24 起把 model 列改成了短名（Claude/GPT/...），旧版本是全名。
# 两种写法都接受，组名统一交给 fig_style 的映射。
MODEL_ALIASES = {
    "Human": "Human", "human": "Human",
    "Claude": "Claude", "Claude-Sonnet-5-High": "Claude",
    "GPT": "GPT", "GPT-5.6-Luna": "GPT",
    "DeepSeek": "DeepSeek", "DeepSeek-V4-Flash": "DeepSeek",
    "Kimi": "Kimi", "Kimi-K3": "Kimi",
}


def to_group(model: str) -> str | None:
    return MODEL_ALIASES.get(model) or MODEL_TO_GROUP.get(model)

# (csv 列名, 中文展示名, 英文图题, 图文件名, 坐标轴标签, 小数位, 是否对数轴)
METRICS = [
    ("MATTR", "MATTR", "MATTR", "mattr-distribution",
     "MATTR (moving-average TTR, window = 100)", 3, False),
    ("mtld", "MTLD", "MTLD", "mtld-distribution",
     "MTLD (factor threshold 0.72, word_count tokens)", 1, False),
    ("sentence_length_CV", "句长 CV", "Sentence-length CV",
     "sentence-length-cv-distribution",
     "Sentence-length CV (within text: SD / mean)", 3, False),
    ("mean_paragraph_length", "平均段长", "Mean paragraph length",
     "paragraph-length-distribution",
     "Mean paragraph length (words per paragraph, log scale)", 1, True),
]

# 均值方向与变异之外，允许写到什么程度（与任务说明「MATTR 之外不下强结论」一致）
INTERPRETATION = {
    "MATTR": "本表各项指标里唯一可以下明确结论的一项：AI 文本词汇多样性更高，且组内更齐。",
    "mtld": "与 MATTR 互证：均值方向一致（AI 四组全部高于 Human），词汇多样性差异不是"
            "单一指标的产物；但组内离散并非 AI 组一致更小（MATTR 的方差比为 0.22–0.29，全部小于 1），"
            "「AI 更齐」不能从 MATTR 直接搬到 MTLD。只作描述，不下推断结论。",
    "sentence_length_CV": "这一项不支持「AI 句子更规整」的直觉：两组高于人类、两组与人类持平；"
                          "只作描述，不下结论。",
    "mean_paragraph_length": "只作描述：人类文本里个别篇目整篇只有 1 段（最长 541 词），"
                             "Human 的 SD 主要由此撑大，方差比低至 0.01 不能读成「AI 段落更整齐」；"
                             "结论须先过段落切分核查。",
}

# 均值差小于该百分比视为「与 Human 基本持平」，避免把 0.0% 写成方向
FLAT_PCT = 1.0


def load_values() -> tuple[dict[str, dict[str, np.ndarray]], dict[str, list[int]]]:
    raw: dict[str, dict[str, list[float]]] = {
        g: {m[0]: [] for m in METRICS} for g in GROUP_ORDER
    }
    prompts: dict[str, list[int]] = {g: [] for g in GROUP_ORDER}
    unknown: set[str] = set()
    with TABLE.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            group = to_group(row["model"].strip())
            if group is None:
                unknown.add(row["model"].strip())
                continue
            for key, *_ in METRICS:
                cell = row[key].strip()
                if cell:
                    raw[group][key].append(float(cell))
            prompts[group].append(int(row["prompt_id"]))
    if unknown:
        raise ValueError(f"表里出现了五组之外的模型：{sorted(unknown)}")
    for g, per_metric in raw.items():
        if not per_metric["MATTR"]:
            raise ValueError(f"{g} 没有数据")
    values = {g: {k: np.sort(np.asarray(v, dtype=float)) for k, v in per.items()}
              for g, per in raw.items()}
    return values, prompts


def describe(values, prompts) -> list[dict]:
    rows: list[dict] = []
    for key, label, _en, _stem, _axis, nd, _log in METRICS:
        human = values["Human"][key]
        human_var = float(human.var(ddof=1))
        human_mean = float(human.mean())
        for group in GROUP_ORDER:
            v = values[group][key]
            var = float(v.var(ddof=1))
            rows.append({
                "metric": key,
                "metric_label": label,
                "group": group,
                "model": SHORT_TO_MODEL[group],
                "n": int(v.size),
                "mean": float(v.mean()),
                "sd": float(v.std(ddof=1)),
                "var_ratio_vs_human": 1.0 if group == "Human" else var / human_var,
                "mean_diff_pct_vs_human": 0.0 if group == "Human"
                else 100.0 * (float(v.mean()) - human_mean) / human_mean,
                "decimals": nd,
            })
    return rows


def judgment(rows: list[dict], key: str) -> str:
    """把「均值是否有明显差异 / 变异是否更小」写成一行，数字全部来自本表。"""
    block = [r for r in rows if r["metric"] == key and r["group"] != "Human"]
    above = [r for r in block if r["mean_diff_pct_vs_human"] > FLAT_PCT]
    below = [r for r in block if r["mean_diff_pct_vs_human"] < -FLAT_PCT]
    flat = [r for r in block if abs(r["mean_diff_pct_vs_human"]) <= FLAT_PCT]
    pcts = [r["mean_diff_pct_vs_human"] for r in block]
    ratios = [r["var_ratio_vs_human"] for r in block]
    smaller = [r for r in block if r["var_ratio_vs_human"] < 1.0]
    total = len(block)
    span = f"{min(pcts):+.1f}% ~ {max(pcts):+.1f}%"

    if len(above) == total:
        mean_part = f"均值 {total}/{total} 组高于 Human（{span}）"
    elif len(below) == total:
        mean_part = f"均值 {total}/{total} 组低于 Human（{span}）"
    else:
        bits = []
        if above:
            bits.append("、".join(r["group"] for r in above) + " 高于 Human")
        if below:
            bits.append("、".join(r["group"] for r in below) + " 低于 Human")
        if flat:
            names = "、".join(r["group"] for r in flat)
            vals = " / ".join(fmt_pct(r["mean_diff_pct_vs_human"]) for r in flat)
            bits.append(f"{names} 与 Human 基本持平（{vals}）")
        mean_part = f"均值方向不一致（{'；'.join(bits)}；跨组范围 {span}）"

    if len(smaller) == total:
        var_part = f"变异 {total}/{total} 组小于 Human（方差比 {min(ratios):.2f}–{max(ratios):.2f}，ddof=1）"
    elif not smaller:
        var_part = f"变异 0/{total} 组小于 Human（方差比 {min(ratios):.2f}–{max(ratios):.2f}）"
    else:
        var_part = (f"变异 {len(smaller)}/{total} 组小于 Human（方差比 "
                    f"{min(ratios):.2f}–{max(ratios):.2f}）")
    return f"- **{mean_part}**；{var_part}。{INTERPRETATION[key]}"


def fmt(x: float, nd: int) -> str:
    return f"{x:.{nd}f}"


def fmt_pct(x: float) -> str:
    """带符号百分比；四舍五入后为 0.0 时写 0.0%，不写成 -0.0%。"""
    return "0.0%" if abs(x) < 0.05 else f"{x:+.1f}%"


def write_outputs(rows: list[dict], prompts: dict[str, list[int]]) -> str:
    # ---------- CSV ----------
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "metric_label", "group", "model", "n", "mean", "sd",
                    "var_ratio_vs_human", "mean_diff_pct_vs_human", "sd_ddof"])
        for r in rows:
            w.writerow([
                r["metric"], r["metric_label"], r["group"], r["model"], r["n"],
                f"{r['mean']:.6f}", f"{r['sd']:.6f}",
                f"{r['var_ratio_vs_human']:.4f}", f"{r['mean_diff_pct_vs_human']:.2f}",
                1,
            ])

    # ---------- Markdown ----------
    n_total = sum(len(prompts[g]) for g in GROUP_ORDER)
    lines: list[str] = []
    lines.append(f"# {CN_NUM.get(len(METRICS) + 1, len(METRICS) + 1)}指标初步汇总（Human × 四模型）")
    lines.append("")
    short_groups = [f"{g} {len(prompts[g])} 篇" for g in GROUP_ORDER if len(prompts[g]) != 30]
    source_note = ("5 组 × 30 prompts 齐全" if not short_groups
                   else "5 组 × 30 prompts − " + "、".join(short_groups))
    lines.append(f"数据源：`analysis/per-text-table.csv`（{n_total} 篇 = {source_note}）。"
                 "只做描述统计，未跑检验、未做分类器。")
    lines.append("")
    lines.append("> **GPT 组用的是哪一份数据**：`GPT-5.6-Luna`（任务① `per-text-table.csv` 的 "
                 "`GPT-5.6-Luna_story` 字段），不是 GPT-3.5。RAY-591 的语料核查截至本表生成时"
                 "仍未有结论，故沿用任务①的口径；若核查结论改为另一份 GPT 数据，"
                 "改 `MODEL_ALIASES` 后重跑 `python3 analysis/summary_table.py` 即可。")
    lines.append("")
    lines.append("> 标准差一律为**样本标准差（ddof = 1）**；"
                 "方差比 = var(组) / var(Human)，同样按 ddof = 1 计算。"
                 "Human 行按定义方差比 = 1.00。")
    lines.append("")

    # 速览：均值 ± SD
    lines.append("## 速览：均值 ± 标准差")
    lines.append("")
    head = "| 组 | N | " + " | ".join(m[1] for m in METRICS) + " |"
    lines.append(head)
    lines.append("|---" * (len(METRICS) + 2) + "|")
    for group in GROUP_ORDER:
        cells = []
        for key, _label, _en, _stem, _axis, nd, _log in METRICS:
            r = next(x for x in rows if x["metric"] == key and x["group"] == group)
            cells.append(f"{fmt(r['mean'], nd)} ± {fmt(r['sd'], nd)}")
        n = next(x["n"] for x in rows if x["metric"] == METRICS[0][0] and x["group"] == group)
        lines.append(f"| {group} | {n} | " + " | ".join(cells) + " |")
    lines.append("")

    # 分指标明细 + 判断
    lines.append("## 分指标明细（含 RQ2 方差比）")
    for key, label, _en, stem, _axis, nd, _log in METRICS:
        lines.append("")
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| 组 | N | 均值 | 标准差 | AI/Human 方差比 | 均值差 vs Human |")
        lines.append("|---|---|---|---|---|---|")
        for r in (x for x in rows if x["metric"] == key):
            ratio = "1.00（参照）" if r["group"] == "Human" else f"{r['var_ratio_vs_human']:.2f}"
            diff = "—" if r["group"] == "Human" else fmt_pct(r["mean_diff_pct_vs_human"])
            lines.append(f"| {r['group']} | {r['n']} | {fmt(r['mean'], nd)} | "
                         f"{fmt(r['sd'], nd)} | {ratio} | {diff} |")
        lines.append("")
        lines.append(judgment(rows, key))
        lines.append("")
        lines.append(f"图：`analysis/figures/{stem}.png`（300 dpi，矢量版同名 `.pdf`）")
    lines.append("")

    lines.append("## 图注")
    lines.append("")
    for key, label, _en, stem, axis, _nd, log_scale in METRICS:
        n_note = "；".join(f"{g} n = {len(prompts[g])}" for g in GROUP_ORDER)
        lines.append(f"- **{label}**（`{stem}.png`）：{axis}。"
                     f"一篇文章一个点（横向抖动避免重叠），箱体为四分位距、中线为中位数、"
                     f"须为 1.5×IQR；灰色带为 Human 的 25–75 分位区间。{n_note}。")
    lines.append("")
    lines.append("## 备注")
    lines.append("")
    lines.append("- 组名口径：GPT = GPT-5.6-Luna，Claude = Claude-Sonnet-5-High，"
                 "DeepSeek = DeepSeek-V4-Flash，Kimi = Kimi-K3（与任务①一致，不含 gpt35 等其它条件）。")
    if short_groups:
        lines.append("- 篇数不齐的组：" + "、".join(short_groups)
                     + "（原因见 `analysis/per-text-table-missing.csv`），N 与任务①的表一致。")
    else:
        lines.append("- 五组各 30 篇（Kimi prompt 26 于 2026-10-24 补齐后，30×5 网格已满）。")
    lines.append("- MATTR 窗口固定 100（`metric-specification.md` 未规定窗口，沿用 "
                 "`analysis/mattr_group_ttest.py` 与报告 §3.4 的口径）。")
    lines.append("- 段长对比前请先看段落切分核查结果（RAY-591 / `docs/2026-10-23-语料核查.md`）。")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def render(values, prompts, rows, key, en_label, stem, axis_label, nd,
           log_scale=False) -> None:
    apply_style()
    positions = np.arange(1, len(GROUP_ORDER) + 1)
    colors = [GROUP_COLORS[g] for g in GROUP_ORDER]
    human_q1, human_q3 = (float(x) for x in np.percentile(values["Human"][key], [25, 75]))

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    fig.subplots_adjust(left=0.115, right=0.965, top=0.790, bottom=0.225)

    # Human IQR 带：RQ2「AI 是否比人更齐」一眼可见
    ax.axhspan(human_q1, human_q3, facecolor="#ececec", zorder=0)
    for edge in (human_q1, human_q3):
        ax.axhline(edge, color="#bdbdbd", lw=0.8, ls=(0, (3, 3)), zorder=0.6)
    ax.axvline(1.5, color="#d2d2d2", lw=0.8, ls=(0, (1, 2)), zorder=0.5)

    rng = np.random.default_rng(20261023)
    for pos, group, color in zip(positions, GROUP_ORDER, colors):
        v = values[group][key]
        ax.scatter(pos + rng.uniform(-0.155, 0.155, size=v.size), v,
                   s=13, color=color, alpha=0.62, linewidths=0, zorder=3)

    boxes = ax.boxplot(
        [values[g][key] for g in GROUP_ORDER],
        positions=positions, widths=0.30, patch_artist=True, showfliers=False, whis=1.5,
        medianprops={"color": "#1a1a1a", "lw": 1.5, "zorder": 5},
        whiskerprops={"lw": 1.0}, capprops={"lw": 1.0}, boxprops={"lw": 1.1}, zorder=4,
    )
    for patch, color in zip(boxes["boxes"], colors):
        patch.set_facecolor(to_rgba(color, 0.20))
        patch.set_edgecolor(color)
    for artist in ("whiskers", "caps"):
        for line, color in zip(boxes[artist], np.repeat(colors, 2)):
            line.set_color(color)

    # 每组方差比（RQ2 的数字）写在组名下方，避免压住数据点
    lo, hi = float(np.min([values[g][key].min() for g in GROUP_ORDER])), \
        float(np.max([values[g][key].max() for g in GROUP_ORDER]))
    if log_scale:
        ax.set_yscale("log")
        ax.set_ylim(lo * 0.80, hi * 1.25)
        ax.set_yticks([1, 2, 5, 10, 20, 50, 100, 200, 500])
        ax.set_yticklabels(["1", "2", "5", "10", "20", "50", "100", "200", "500"])
        ax.yaxis.set_minor_locator(plt.NullLocator())
    else:
        span = hi - lo
        ax.set_ylim(lo - 0.05 * span, hi + 0.10 * span)
    ratios = {x["group"]: x["var_ratio_vs_human"] for x in rows if x["metric"] == key}

    ax.set_xlim(0.45, len(GROUP_ORDER) + 0.55)
    ax.set_ylabel(axis_label)
    ax.set_xticks(positions, [
        f"{g}\nn = {len(values[g][key])}\n" + (f"×{ratios[g]:.2f}" if g != "Human" else "ref.")
        for g in GROUP_ORDER
    ])
    ax.tick_params(axis="x", length=0, pad=6)
    ax.grid(axis="y", color="#e6e6e6", lw=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#9a9a9a")

    human = next(x for x in rows if x["metric"] == key and x["group"] == "Human")
    fig.text(0.115, 0.952, f"{en_label} across the five groups",
             fontsize=12.5, fontweight="bold", color="#1a1a1a", va="top")
    fig.text(0.115, 0.906,
             f"Human mean {fmt(human['mean'], nd)} (SD {fmt(human['sd'], nd)}) · "
             "one dot = one text · box = IQR with median · whiskers = 1.5×IQR · "
             "grey band = Human IQR",
             fontsize=7.8, color="#666666", va="top")
    fig.text(0.115, 0.878,
             "× = variance ratio vs Human (< 1 = AI texts more uniform); "
             "ref. = reference group"
             + ("; y axis on a log scale (Human spread 2–541 words)" if log_scale else ""),
             fontsize=7.8, color="#666666", va="top")
    fig.text(0.115, 0.062,
             "GPT = GPT-5.6-Luna · Claude = Claude-Sonnet-5-High · "
             "DeepSeek = DeepSeek-V4-Flash · Kimi = Kimi-K3",
             fontsize=6.8, color="#6f6f6f", va="top")
    uneven = [f"{g} n = {len(values[g][key])}" for g in GROUP_ORDER if len(values[g][key]) != 30]
    fig.text(0.115, 0.034,
             (", ".join(uneven) if uneven else "All five groups n = 30")
             + ". Sample SD, ddof = 1.",
             fontsize=6.8, color="#6f6f6f", va="top")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png, pdf = OUT_DIR / f"{stem}.png", OUT_DIR / f"{stem}.pdf"
    fig.savefig(png, dpi=300, facecolor="white")
    fig.savefig(pdf, facecolor="white", metadata={
        "Title": f"{en_label} across the five groups",
        "Subject": "Human vs four AI models, per-text distribution",
        "Creator": "analysis/summary_table.py",
    })
    plt.close(fig)


def main() -> None:
    values, prompts = load_values()
    rows = describe(values, prompts)
    write_outputs(rows, prompts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_STATS.write_text(json.dumps({
        "source": str(TABLE.relative_to(BASE)),
        "sd": "sample SD (ddof=1)",
        "variance_ratio": "var(group, ddof=1) / var(Human, ddof=1)",
        "groups": [{"group": g, "model": SHORT_TO_MODEL[g], "n": len(prompts[g]),
                    "prompt_ids": sorted(prompts[g])} for g in GROUP_ORDER],
        "metrics": [{
            "metric": m[0], "label": m[1],
            "figure": f"analysis/figures/{m[3]}.png",
            "groups": [r for r in rows if r["metric"] == m[0]],
        } for m in METRICS],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    for key, label, _en, stem, _axis, nd, _log in METRICS:
        print(f"\n## {label}")
        for r in (x for x in rows if x["metric"] == key):
            print(f"  {r['group']:9s} n={r['n']:3d} mean={r['mean']:.{nd}f} "
                  f"sd={r['sd']:.{nd}f} var_ratio={r['var_ratio_vs_human']:.3f}")
        print("  " + judgment(rows, key))
        render(values, prompts, rows, key, _en, stem, _axis, nd, _log)
        print(f"  wrote analysis/figures/{stem}.png/.pdf")
    print(f"\nwrote {OUT_CSV.relative_to(BASE)}")
    print(f"wrote {OUT_MD.relative_to(BASE)}")
    print(f"wrote {OUT_STATS.relative_to(BASE)}")


if __name__ == "__main__":
    main()
