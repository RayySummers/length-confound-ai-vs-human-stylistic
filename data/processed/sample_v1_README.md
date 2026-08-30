# sample_v1 — 30 prompts × 1 story/prompt (min version)

**生成日期**：2026-08-28
**生成者**：Hari（Ray 授权）
**对应 Multica issue**：RAY-300（前置）→ RAY-301（sanity check）

---

## 数据来源

| 项 | 值 |
|---|---|
| 源 | HuggingFace `vkpriya/GPT-WritingPrompts` |
| License | **MIT** ✅ |
| 论文 | Huang et al. 2024, EMNLP Workshop on Narrative Understanding |
| 底层数据 | Fan et al. 2018 (ACL) — Reddit WritingPrompts |

**License 详情**：HF dataset metadata 明确标注 `license:mit`，允许商用 / 修改 / 分发 / 再发布派生。唯一要求：保留版权声明 + MIT 文本。

---

## 抽样策略

```
random.seed(42)
shuffle(prompts)
take first 30
for each prompt:
  human_story = first story in human_wp_stories.json with len > 100 chars
  gpt35_story = first story in gpt_wp_stories.json with len > 50 chars
```

**为什么用 seed=42**：可复现。下次任何人重跑会得到完全一样的 30 个 sample。

**为什么过滤长度**：human 数据集里有少量超短 story（之前看过有 1 字符的），过滤掉避免脏数据。

---

## 文件结构

```json
{
  "metadata": {
    "version": "v1",
    "sample_size": 30,
    "random_seed": 42,
    "source": "HuggingFace vkpriya/GPT-WritingPrompts (MIT)",
    "license": "MIT",
    "models_to_fill_in": [
      "MiMo-V2.5-Pro",
      "DeepSeek-V4-Flash",
      "GPT-5.6_Sol",
      "GPT-5.6_Luna",
      "MiniMax_M3"
    ]
  },
  "samples": [
    {
      "prompt_id": 0,
      "prompt": "...",
      "human_story": "...",
      "gpt35_story": "...",
      "MiMo-V2.5-Pro_story": null,
      "DeepSeek-V4-Flash_story": null,
      "GPT-5.6_Sol_story": null,
      "GPT-5.6_Luna_story": null,
      "MiniMax_M3_story": null
    }
  ]
}
```

---

## 数据质量

| 字段 | Min | Max | Avg |
|---|---|---|---|
| human_story | 651 chars | 6,114 chars | 2,592 chars |
| gpt35_story | 2,822 chars | 3,875 chars | 3,279 chars |

**观察**：GPT 故事长度方差小（~1KB），Human 故事长度方差大（~5KB） —— 这跟 H1 假设方向一致（AI 方差 < Human）。

---

## 怎么 reproduce

```python
import json, random
random.seed(42)
# 重跑完整抽取逻辑见 /home/hunde/.hermes-hari/memories/projects/summer-research-2026/decisions.md
```

---

## 怎么扩展到 N=90（full version）

把脚本里的 `SAMPLE_SIZE = 30` 改成 `90`，其余不变。

**注意**：full version 时建议分 3 批（每批 30），用 seed=42 + 43 + 44，方便 sanity check（任何一批出问题只用重跑那一批）。

---

## 下一步

1. **今天**：跑 H1 sanity check（句长方差）验证管线 → 见 `analysis/metrics.py` + RAY-301
2. **明后天**：Ray 自己跑 5 个现代模型填入 `*_story` 字段 → 见 RAY-302
3. **之后**：扩到 N=90（full version）