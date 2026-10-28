#!/usr/bin/env python3
"""fig_style.py — 组会图包共用样式（配色 / 字体 / 坐标轴）。

后续同类图请 `from fig_style import GROUP_ORDER, GROUP_COLORS, apply_style`，
不要各自另起一套颜色：Human 固定中性 #333333，四个 AI 组沿用既有蓝色 #7f9dc0
的同色系四阶（既区分模型，又保持「AI＝蓝」的语义）。
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# 任务指定的五组顺序（Human 永远在最左）
GROUP_ORDER = ["Human", "Claude", "GPT", "DeepSeek", "Kimi"]

# 语料 condition（模型全名）→ 图上的组名
MODEL_TO_GROUP = {
    "Human": "Human",
    "Claude-Sonnet-5-High": "Claude",
    "GPT-5.6-Luna": "GPT",
    "DeepSeek-V4-Flash": "DeepSeek",
    "Kimi-K3": "Kimi",
}

# Human 中性色 + AI 蓝色系四阶（基准 #7f9dc0 为既有 AI 取色）
GROUP_COLORS = {
    "Human": "#333333",
    "Claude": "#2c5a86",
    "GPT": "#4f7ba6",
    "DeepSeek": "#7f9dc0",
    "Kimi": "#a3b9cf",
}


def _resolve_font() -> str:
    """优先 Arial（与既有图一致），退化到 Liberation Sans / DejaVu Sans。"""
    for family in ("Arial", "Liberation Sans", "DejaVu Sans"):
        try:
            fm.findfont(fm.FontProperties(family=family), fallback_to_default=False)
            return family
        except Exception:
            continue
    return "DejaVu Sans"


def apply_style() -> str:
    """套用统一的 rcParams，返回实际使用的字体名。"""
    font = _resolve_font()
    plt.rcParams.update({
        "font.family": font,
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 8.5,
        "axes.edgecolor": "#8a8a8a",
        "axes.linewidth": 0.8,
        "axes.labelcolor": "#222222",
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })
    return font
