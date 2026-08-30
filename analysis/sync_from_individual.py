#!/usr/bin/env python3
"""
sync_from_individual.py — Sync any out-of-sync stories from individual files to sample_v1.json
Run this after background generation processes finish, to ensure no stories were lost
between individual file writes and sample_v1.json updates.
"""
import json
from pathlib import Path

BASE = Path("/mnt/e/Creative/Projects/summer-research-2026/data/processed")
SAMPLE = BASE / "sample_v1.json"

CONDITIONS = [
    ("human_story", "Human"),
    ("gpt35_story", "GPT-3.5"),
    ("MiMo-V2.5-Pro_story", "MiMo-V2.5-Pro"),
    ("DeepSeek-V4-Flash_story", "DeepSeek-V4-Flash"),
    ("MiniMax_M3_story", "MiniMax-M3"),
    ("Muse-Spark-1.2-Contributor_story", "Muse-Spark-1.2-Contributor"),
    ("Kimi-K3_story", "Kimi-K3"),
    ("Gemini-3.6-Flash_story", "Gemini-3.6-Flash (Arena)"),  # not in modern_model_outputs — Arena paste
    ("GPT-5.6-Luna_story", "GPT-5.6-Luna (Arena)"),
    ("Claude-Sonnet-5-High_story", "Claude-Sonnet-5-High (Arena)"),
]

with open(SAMPLE) as f:
    data = json.load(f)

restored = 0
for field, model_dir in CONDITIONS:
    # Skip Arena fields (they don't have individual files in modern_model_outputs)
    if "Arena" in model_dir:
        continue
    out_dir = BASE / "modern_model_outputs" / model_dir
    if not out_dir.exists():
        continue
    for s in data["samples"]:
        pid = s["prompt_id"]
        if s.get(field) is None or len(s.get(field) or "") < 100:
            individual = out_dir / f"{pid}.json"
            if individual.exists():
                with open(individual) as f:
                    rec = json.load(f)
                if rec.get("story") and len(rec["story"]) >= 100:
                    s[field] = rec["story"]
                    restored += 1
                    print(f"  Restored {field} for prompt {pid} ({len(rec['story'])} chars)")

if restored:
    with open(SAMPLE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Total restored: {restored}")
else:
    print("✓ Already in sync (no restoration needed)")

# Final report
print("\n=== Final fill rate by condition ===")
for field, _ in CONDITIONS:
    n = sum(1 for s in data["samples"] if s.get(field) and len(s.get(field) or "") >= 100)
    bar = "█" * (n // 2) + "░" * (15 - n // 2)
    print(f"  {field:35s} {n:2d}/30  [{bar}]  {100*n/30:.0f}%")