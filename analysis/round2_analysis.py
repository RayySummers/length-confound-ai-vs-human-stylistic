#!/usr/bin/env python3
"""round2_analysis.py — 组会 #2 图表包：指标 × 双维度（人机对比 + AI 内部一致性）

口径沿用 9/21 定稿（group_homogeneity_analysis.py）：
  - 每指标 × 每模型：独立样本 Welch t 检验（双尾，未校正）+ Cohen's d
  - AI 内部一致性：组内方差比 var(AI)/var(Human) + Levene 方差齐性检验
数据:
  - 新 5 指标: analysis/metrics_extended_results.json（metrics_extended.py 产出）
  - 旧 9 指标: data/processed/results_v1.json per_sample_metrics（分布）
              + analysis/group_homogeneity_results.json rows（统计已算好）
输出:
  - analysis/metrics_extended_stats.json
  - analysis/figures_round2/*.png（每指标 2 面板图 + 2 张总览，200dpi）
  - analysis/figures_round2/figures_round2.pdf（矢量版）
"""
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats

import matplotlib.font_manager as fm


def _setup_fonts():
    """图内字体：Inter（WSL 直读 Windows 字体目录；退化 Arial/Liberation）。"""
    import os
    cands = [
        "/mnt/c/Windows/Fonts/Inter-Regular.otf",
        "/mnt/c/Windows/Fonts/Inter-Italic.otf",
        "/mnt/c/Windows/Fonts/Inter-Bold.otf",
        "/mnt/c/Windows/Fonts/Inter-BoldItalic.otf",
        "/mnt/c/Windows/Fonts/Inter-Medium.otf",
        "/mnt/c/Windows/Fonts/Inter-SemiBold.otf",
        "/mnt/c/Windows/Fonts/arial.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf",
        "/mnt/c/Windows/Fonts/ariali.ttf",
        "/mnt/c/Windows/Fonts/arialbi.ttf",
    ]
    for p in cands:
        if os.path.exists(p):
            fm.fontManager.addfont(p)
    for fam in ("Inter", "Arial"):
        try:
            resolved = fm.findfont(fm.FontProperties(family=fam), fallback_to_default=False)
            plt.rcParams["font.family"] = fam
            print("figure font:", resolved)
            return
        except Exception:
            continue
    plt.rcParams["font.family"] = ["Liberation Sans", "DejaVu Sans"]
    print("figure font: fallback", plt.rcParams["font.family"])


_setup_fonts()

BASE = Path(__file__).resolve().parent.parent
FIGDIR = BASE / "analysis" / "figures_round2"

NEW_METRICS = {
    "lexical_density": "Lexical Density (content/total)",
    "word_length_sd": "Word Length SD",
    "long_word_ratio": "Long Word Ratio (>=7 chars)",
    "sentence_length_cv": "Sentence Length CV (sd/mean)",
    "sentences_per_paragraph": "Sentences per Paragraph",
}
OLD_METRICS = {
    "mattr_w100": "MATTR (window 100)",
    "word_length": "Word Length",
    "sentence_length": "Sentence Length",
    "sentence_length_var": "Sentence Length Variance",
    "ttr": "TTR",
    "mtld": "MTLD",
    "conj_freq": "Conjunction Frequency",
    "paragraph_length": "Paragraph Length",
    "paragraph_length_var": "Paragraph Length Variance",
}
# (raw key in data, display label; label must match group_homogeneity rows' condition)
MODELS = [
    ("gpt35", "GPT-3.5", "GPT-3.5"),
    ("MiMo-V2.5-Pro", "MiMo-V2.5-Pro", "MiMo-V2.5-Pro"),
    ("DeepSeek-V4-Flash", "DeepSeek-V4-Flash", "DeepSeek-V4-Flash"),
    ("MiniMax-M3", "MiniMax-M3", "MiniMax-M3"),
    ("Muse-Spark-1.2-Contributor", "Muse-Spark-1.2", "Muse-Spark-1.2"),
    ("GPT-5.6-Luna", "GPT-5.6-Luna", "GPT-5.6-Luna"),
    ("Claude-Sonnet-5-High", "Claude-Sonnet-5-High", "Claude-Sonnet-5-High"),
    ("Gemini-3.6-Flash", "Gemini-3.6-Flash", "Gemini-3.6-Flash"),
    ("Kimi-K3", "Kimi-K3", "Kimi-K3"),
]


def load(p):
    return json.loads(Path(p).read_text())


def compute_stats_for_new():
    rows = load(BASE / "analysis" / "metrics_extended_results.json")
    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], {})[r["prompt_id"]] = r["metrics"]
    human = by_cond["human"]
    all_rows, summary = [], {}
    for metric in NEW_METRICS:
        m_rows = []
        for cond, label, _gh in MODELS:
            ids = sorted(set(by_cond[cond]) & set(human))
            a = np.array([by_cond[cond][i][metric] for i in ids])
            h = np.array([human[i][metric] for i in ids])
            t, p_t = stats.ttest_ind(a, h, equal_var=False)
            _, p_u = stats.mannwhitneyu(a, h, alternative="two-sided")
            _, p_lev = stats.levene(a, h, center="median")
            pooled = math.sqrt(((a.size - 1) * a.var(ddof=1) + (h.size - 1) * h.var(ddof=1))
                               / max(1, a.size + h.size - 2))
            d = (a.mean() - h.mean()) / pooled if pooled else 0.0
            vr = a.var(ddof=1) / h.var(ddof=1) if h.var(ddof=1) else float("nan")
            m_rows.append({
                "metric": metric, "label": label, "condition": label,
                "n_ai": int(a.size), "n_human": int(h.size),
                "ai_mean": float(a.mean()), "human_mean": float(h.mean()),
                "ai_var": float(a.var(ddof=1)), "human_var": float(h.var(ddof=1)),
                "var_ratio": float(vr), "ttest_t": float(t), "ttest_p": float(p_t),
                "ranksum_p": float(p_u), "cohens_d": float(d), "levene_p": float(p_lev),
                "ttest_sig": bool(p_t < 0.05), "levene_sig": bool(p_lev < 0.05),
            })
        all_rows.extend(m_rows)
        summary[metric] = {
            "label": NEW_METRICS[metric],
            "n_models_sig_vs_human": sum(1 for r in m_rows if r["ttest_sig"]),
            "n_models_ai_var_smaller": sum(1 for r in m_rows if r["var_ratio"] < 1),
            "n_levene_sig": sum(1 for r in m_rows if r["levene_sig"]),
            "median_var_ratio": float(np.median([r["var_ratio"] for r in m_rows])),
            "median_cohens_d": float(np.median([r["cohens_d"] for r in m_rows])),
        }
    return {"summary": summary, "rows": all_rows}


def collect_distributions():
    """两个数据源：新指标 rows；旧指标 results_v1 per_sample_metrics。"""
    new_rows = load(BASE / "analysis" / "metrics_extended_results.json")
    old = load(BASE / "data" / "processed" / "results_v1.json")["per_sample_metrics"]
    return new_rows, old


def val_map(rows, condition_of, metrics_of):
    d = {}
    for r in rows:
        c = condition_of(r)
        d.setdefault(c, {})[r["prompt_id"]] = metrics_of(r)
    return d


def two_panel_figure(metric_label, series, stat_rows, outpath, stat_key="var_ratio", pdf=None):
    """series: list of (name, np.array) with human first."""
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.1))
    ax = axes[0]
    data = [s[1] for s in series]
    names = [s[0] for s in series]
    bp = ax.violinplot(data, showextrema=False, widths=0.9)
    for i, b in enumerate(bp["bodies"]):
        b.set_facecolor("#333333" if i == 0 else "#7f9dc0")
        b.set_alpha(0.9 if i == 0 else 0.55)
    ax.boxplot(data, widths=0.18, positions=np.arange(1, len(data) + 1),
               showfliers=False, medianprops=dict(color="k", lw=1.1))
    ax.set_xticks(np.arange(1, len(names) + 1), names, rotation=45, ha="right", fontsize=7)
    ax.set_title(f"{metric_label}\nHuman vs 9 AI models (distributions)", fontsize=9)
    ax.set_ylabel("value", fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    xs = np.arange(len(stat_rows))
    ratios = [r[stat_key] for r in stat_rows]
    colors = ["#4477aa" if x < 1 else "#cc6677" for x in ratios]
    ax.bar(xs, ratios, color=colors, alpha=0.85)
    for i, r in enumerate(stat_rows):
        mark = "*" if (r.get("levene_sig") or r.get("ttest_sig")) else ""
        ax.text(xs[i], ratios[i] * 1.06, f"{ratios[i]:.2f}{mark}", ha="center",
                va="bottom", fontsize=6)
    ax.axhline(1.0, color="k", lw=1)
    ax.set_xticks(xs, [r["label"] for r in stat_rows], rotation=45, ha="right", fontsize=7)
    ax.set_yscale("log")
    ax.set_title("Within-group variance ratio (AI / Human)\n< 1 = AI texts more uniform "
                 "(* p<.05 t or Levene)", fontsize=9)
    ax.set_ylabel("var ratio (log)", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    if pdf is not None:
        pdf.savefig(fig)
    plt.close(fig)


def main():
    FIGDIR.mkdir(exist_ok=True)
    pdf = PdfPages(FIGDIR / "figures_round2.pdf")
    print("[1/4] stats for extended metrics ...")
    ext_stats = compute_stats_for_new()
    (BASE / "analysis" / "metrics_extended_stats.json").write_text(
        json.dumps(ext_stats, ensure_ascii=False, indent=1))
    gh = load(BASE / "analysis" / "group_homogeneity_results.json")
    gh_rows = gh["rows"]

    new_rows, old_rows = collect_distributions()
    new_map = val_map(new_rows, lambda r: r["condition"], lambda r: r["metrics"])
    old_map = val_map(old_rows, lambda r: r["condition"], lambda r: r["metrics"])

    print("[2/4] per-metric figures (new 5 + old 8; mattr_w100 chart pending per-sample data) ...")
    human = new_map["human"]
    for metric, label in NEW_METRICS.items():
        series = [("Human", np.array([human[p][metric] for p in sorted(human)]))]
        for cond, disp, _ in MODELS:
            ids = sorted(set(new_map[cond]) & set(human))
            series.append((disp, np.array([new_map[cond][i][metric] for i in ids])))
        st_rows = [r for r in ext_stats["rows"] if r["metric"] == metric]
        two_panel_figure(label, series, st_rows, FIGDIR / f"new_{metric}.png", pdf=pdf)

    if old_map:
        old_human = old_map.get("human", {})
        for metric, label in OLD_METRICS.items():
            if metric.startswith("mattr"):
                continue  # 无 per-sample 数据，暂缺（见 README 备注）
            if not old_human or metric not in next(iter(old_human.values())):
                continue
            series = [("Human", np.array([old_human[p][metric] for p in sorted(old_human)]))]
            for cond, disp, _ in MODELS:
                ids = sorted(set(old_map.get(cond, {})) & set(old_human))
                series.append((disp, np.array([old_map[cond][i][metric] for i in ids])))
            st_rows = []
            for cond_raw, disp, gh_label in MODELS:
                hit = [r for r in gh_rows if r["metric"] == metric and r["condition"] == gh_label]
                if hit:
                    st_rows.append({**hit[0], "label": disp})
            two_panel_figure(f"{label} (existing)", series, st_rows,
                             FIGDIR / f"old_{metric}.png", pdf=pdf)

    print("[3/4] overview figures ...")
    row_labels = [OLD_METRICS[m] for m in OLD_METRICS] + [NEW_METRICS[m] for m in NEW_METRICS]
    vr_mat = []
    for metric in OLD_METRICS:
        vals = []
        for _, _, gh_label in MODELS:
            hit = [r for r in gh_rows if r["metric"] == metric and r["condition"] == gh_label]
            vals.append(hit[0]["var_ratio"] if hit else np.nan)
        vr_mat.append(vals)
    for metric in NEW_METRICS:
        vr_mat.append([r["var_ratio"] for r in ext_stats["rows"] if r["metric"] == metric])
    vr = np.array(vr_mat, dtype=float)

    fig, ax = plt.subplots(figsize=(10.8, 6.4))
    im = ax.imshow(np.log10(vr), cmap="RdBu_r", vmin=-2, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(MODELS)), [m[1] for m in MODELS], rotation=45,
                  ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(row_labels)), row_labels, fontsize=7)
    for i in range(vr.shape[0]):
        for j in range(vr.shape[1]):
            v = vr[i, j]
            if math.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6,
                        color="w" if abs(math.log10(v)) > 0.85 else "k")
    ax.set_title("Within-group variance ratio (AI / Human) — all 14 metrics x 9 models\n"
                 "blue = AI more uniform than human", fontsize=9)
    fig.colorbar(im, ax=ax, label="log10 ratio")
    fig.tight_layout()
    fig.savefig(FIGDIR / "overview_variance_ratio.png", dpi=200)
    pdf.savefig(fig)
    plt.close(fig)

    d_mat = []
    for metric in OLD_METRICS:
        vals = []
        for _, _, gh_label in MODELS:
            hit = [r for r in gh_rows if r["metric"] == metric and r["condition"] == gh_label]
            vals.append(hit[0]["cohens_d"] if hit else np.nan)
        d_mat.append(vals)
    for metric in NEW_METRICS:
        d_mat.append([r["cohens_d"] for r in ext_stats["rows"] if r["metric"] == metric])
    dm = np.array(d_mat, dtype=float)
    fig, ax = plt.subplots(figsize=(10.8, 6.4))
    for i in range(dm.shape[0]):
        for j in range(dm.shape[1]):
            v = dm[i, j]
            if not math.isfinite(v):
                continue
            ax.scatter(j, i, s=54, c="#cc6677" if abs(v) >= 0.8 else "#4477aa",
                       edgecolors="k", linewidths=0.3)
            ax.annotate(f"{v:+.2f}", (j, i), textcoords="offset points", xytext=(0, 6),
                        ha="center", fontsize=5.5)
    ax.set_yticks(np.arange(len(row_labels)), row_labels, fontsize=7)
    ax.set_xticks(np.arange(len(MODELS)), [m[1] for m in MODELS], rotation=45,
                  ha="right", fontsize=7)
    ax.set_title("Effect size Cohen's d (AI vs Human) per metric x model\n"
                 "(two-tailed Welch t, uncorrected; |d|>=0.8 red)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGDIR / "overview_effect_sizes.png", dpi=200)
    pdf.savefig(fig)
    plt.close(fig)

    print("[4/4] finalize vector PDF ...")
    pdf.close()
    print("PDF:", FIGDIR / "figures_round2.pdf")

    print("\n== summary (new metrics) ==")
    for metric, s in ext_stats["summary"].items():
        print(f"{metric:26s} sig={s['n_models_sig_vs_human']}/9 "
              f"var<1={s['n_models_ai_var_smaller']}/9 "
              f"levene_sig={s['n_levene_sig']}/9 "
              f"med_vr={s['median_var_ratio']:.3f} med_d={s['median_cohens_d']:+.2f}")
    print("\nfigures in:", FIGDIR)


if __name__ == "__main__":
    main()
