"""
metrics.py — 8 个 stylistic metrics extraction
用于 Ray Summer Research 2026：量化 AI 生成文本 vs 人类写作的结构差异

输入：sample_v1.json
输出：metrics_results.json（每个 sample 的 8 个指标 + H1 sanity check）

Metrics (locked in docs/metric-specification.md):
  1. word_length       - 平均 char/word
  2. sentence_length   - 平均 words/sentence
  3. sentence_length_var - 句长方差  ⭐ H1
  4. TTR               - unique/total tokens
  5. MTLD              - 词汇多样性 (moving-window)
  6. conj_freq         - 连接词频率
  7. paragraph_length  - 平均 words/paragraph
  8. paragraph_length_var - 段落长方差
"""

import json
import re
import statistics
from pathlib import Path

import spacy

nlp = spacy.load("en_core_web_sm")

# MTLD 常量
MTLD_WINDOW = 100  # forward + reverse moving window

# 连接词（CC 关系 + 显式连词）
CONJ_PATTERNS = [
    "however", "therefore", "moreover", "furthermore", "nevertheless",
    "although", "though", "because", "since", "unless", "whereas",
    "while", "but", "and", "or", "yet", "so", "then", "thus", "hence",
]


def split_sentences(text: str) -> list[str]:
    """用 spaCy 分句。"""
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def split_paragraphs(text: str) -> list[str]:
    """按双换行分段落（spaCy 不直接做）。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) <= 1:
        # fallback: 单换行当段落边界（<newline> 形式来自 Huang 数据）
        paras = [p.strip() for p in text.split("<newline>") if p.strip()]
    return paras


def tokenize_words(text: str) -> list[str]:
    """简单分词（spaCy）。"""
    doc = nlp(text.lower())
    return [t.text for t in doc if t.is_alpha]


def metric_word_length(words: list[str]) -> float:
    """平均 char/word。"""
    if not words:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def metric_sentence_length(sentences: list[str]) -> tuple[float, float]:
    """(平均 words/sentence, 句长方差)。"""
    lens = [len(tokenize_words(s)) for s in sentences if s.strip()]
    if not lens:
        return 0.0, 0.0
    return statistics.mean(lens), statistics.pvariance(lens)


def metric_ttr(words: list[str]) -> float:
    """Type-Token Ratio。"""
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def metric_mtld(words: list[str]) -> float:
    """Measure of Textual Lexical Diversity (forward)。"""
    if len(words) < MTLD_WINDOW:
        return 0.0

    def ttr_at(seq):
        n_types = len(set(seq))
        return n_types / len(seq) if seq else 1.0

    factor_count = 0
    total_factors = 0.0
    for i in range(0, len(words) - MTLD_WINDOW + 1):
        window = words[i:i + MTLD_WINDOW]
        ttr = ttr_at(window)
        if ttr < 0.72:  # standard threshold
            factor_count += 1
            total_factors += 1 - (ttr / 0.72)
        else:
            total_factors += 1.0
    return total_factors if factor_count > 0 else MTLD_WINDOW


def metric_conj_freq(words: list[str]) -> float:
    """连接词占总词数比例。"""
    if not words:
        return 0.0
    text_lower = " ".join(words)
    count = sum(text_lower.count(c) for c in CONJ_PATTERNS)
    return count / len(words)


def metric_paragraph_length(paragraphs: list[str]) -> tuple[float, float]:
    """(平均 words/paragraph, 段落长方差)。"""
    lens = [len(tokenize_words(p)) for p in paragraphs if p.strip()]
    if not lens:
        return 0.0, 0.0
    return statistics.mean(lens), statistics.pvariance(lens)


def compute_all_metrics(text: str) -> dict:
    """对一个 story 算全部 8 个指标。"""
    words = tokenize_words(text)
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    sent_avg, sent_var = metric_sentence_length(sentences)
    para_avg, para_var = metric_paragraph_length(paragraphs)

    return {
        "word_length": metric_word_length(words),
        "sentence_length": sent_avg,
        "sentence_length_var": sent_var,
        "ttr": metric_ttr(words),
        "mtld": metric_mtld(words),
        "conj_freq": metric_conj_freq(words),
        "paragraph_length": para_avg,
        "paragraph_length_var": para_var,
        # debug info
        "_n_words": len(words),
        "_n_sentences": len(sentences),
        "_n_paragraphs": len(paragraphs),
    }


def main():
    sample_path = Path(__file__).parent.parent / "data" / "processed" / "sample_v1.json"
    with open(sample_path) as f:
        sample = json.load(f)

    # All condition fields in sample_v1.json (story fields)
    CONDITION_FIELDS = [
        ("human", "Human"),
        ("gpt35", "GPT-3.5"),
        ("MiMo-V2.5-Pro", "MiMo-V2.5-Pro"),
        ("DeepSeek-V4-Flash", "DeepSeek-V4-Flash"),
        ("MiniMax-M3", "MiniMax-M3"),
        ("Muse-Spark-1.2-Contributor", "Muse-Spark-1.2-Contributor"),
        ("GPT-5.6-Luna", "GPT-5.6-Luna"),
        ("Claude-Sonnet-5-High", "Claude-Sonnet-5-High"),
        ("Gemini-3.6-Flash", "Gemini-3.6-Flash"),
        ("Kimi-K3", "Kimi-K3"),
    ]

    results = []
    for s in sample["samples"]:
        entry = {"prompt_id": s["prompt_id"]}
        for field_key, label in CONDITION_FIELDS:
            story_field = f"{field_key}_story"
            story = s.get(story_field)
            if story is None or len(story.strip()) < 100:
                # Skip empty/short stories (still record presence so downstream knows)
                entry[field_key] = None
                continue
            metrics = compute_all_metrics(story)
            entry[field_key] = metrics
        results.append(entry)

    output_path = sample_path.parent / "metrics_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Wrote {len(results)} samples to {output_path}")

    # H1 sanity check: print per-condition sentence length variance for human vs each AI
    print("\n=== Sanity Check: Sentence Length Variance ===")
    for field_key, label in CONDITION_FIELDS:
        vals = [
            r[field_key]["sentence_length_var"]
            for r in results
            if r.get(field_key) and r[field_key].get("_n_sentences", 0) > 1
        ]
        if vals:
            print(f"  {label:30s} n={len(vals):2d}  mean={statistics.mean(vals):.2f}  median={statistics.median(vals):.2f}")


if __name__ == "__main__":
    main()