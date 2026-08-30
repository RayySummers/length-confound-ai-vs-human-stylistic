#!/usr/bin/env python3
"""
generate_modern_models.py — Generate ~500-word stories from modern LLMs
for each of 30 prompts in sample_v1.json. v2 — uses actual token plan endpoints
discovered from Ray's info file.

Designed for Ray to run locally with his own API keys.
The agent NEVER calls any LLM API — keys belong to Ray.

Usage:
    # Dry run (no API calls, prints what it would do)
    python analysis/generate_modern_models.py --dry-run

    # Run one model at a time
    python analysis/generate_modern_models.py --model MiMo-V2.5-Pro
    python analysis/generate_modern_models.py --model DeepSeek-V4-Flash-0731
    python analysis/generate_modern_models.py --model MiniMax-M3
    python analysis/generate_modern_models.py --model Muse-Spark-1.2-Contributor

    # Run specific prompts only (partial re-run)
    python analysis/generate_modern_models.py --model DeepSeek-V4-Flash-0731 --prompts 0,5,10

    # Run all models sequentially
    python analysis/generate_modern_models.py

Environment variables (NEVER hardcode, NEVER log):

MINIMAX:
    MINIMAX_API_KEY         — Anthropic-format key for MiniMax M3
    MINIMAX_BASE_URL        — https://api.minimaxi.com/anthropic (Anthropic-compatible)

COMMAND CODE GOAT (OpenAI-compatible endpoint, hosts multiple providers):
    CMD_GOAT_API_KEY        — OpenAI-format key for Command Code Goat provider
    CMD_GOAT_BASE_URL       — https://api.commandcode.ai/provider/v1 (OpenAI chat completions)

OPENCODE GO (OpenAI-compatible endpoint, hosts multiple providers):
    OPENCODE_API_KEY        — OpenAI-format key for OpenCode Go
    OPENCODE_BASE_URL       — https://opencode.ai/v1 (Ray to confirm — web was blocked)

Per-model env overrides (optional):
    <MODEL>_MODEL            — override the default model identifier

ARENA MODELS (Claude*, GPT*, Gemini*) — NOT in this script.
Ray pastes Arena outputs manually into sample_v1.json fields.
Use analysis/paste_arena_outputs.py helper (if needed) — Ray to write.

License: MIT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Prompt template — adapted from Huang et al. 2024 §3.1
# "Generate a ~500-word story in response to the prompt. Maintain the same
# narrative point of view as the human writer (to be inferred from prompt
# context)."  (arXiv:2406.16767v2, EMNLP Workshop on Narrative Understanding)
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = (
    "Generate a story of at least 500 words (and at most 800 words) in response to the following prompt. "
    "Maintain the same narrative point of view as the human writer "
    "(to be inferred from prompt context). Write a complete story with a clear beginning, middle, and end.\n\n"
    "Prompt: {prompt}"
)

# ---------------------------------------------------------------------------
# Model configuration
#
# Each entry maps to:
#   - token_plan: which of Ray's three subscriptions
#   - sdk: "anthropic" or "openai"
#   - api_key_env / base_url_env: which env vars hold credentials
#   - model_default: default model identifier (for OpenCode Go, prefix may vary)
#   - sample_field: which field in sample_v1.json to fill
#   - temperature_default: per-model recommended temperature
#   - max_tokens_default: per-model max output tokens
# ---------------------------------------------------------------------------
MODELS: dict[str, dict] = {
    "MiniMax-M3": {
        "token_plan": "MiniMax CN (Anthropic)",
        "sdk": "anthropic",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url_env": "MINIMAX_BASE_URL",
        "base_url_default": "https://api.minimaxi.com/anthropic",
        "model_env": "MINIMAX_MODEL",
        "model_default": "MiniMax-M3",
        "sample_field": "MiniMax_M3_story",
        "temperature_default": 1.0,  # per docs: "recommended value 1.0"
        "max_tokens_default": 1500,
    },
    "DeepSeek-V4-Flash-0731": {
        "token_plan": "Command Code Goat",
        "sdk": "openai",
        "api_key_env": "CMD_GOAT_API_KEY",
        "base_url_env": "CMD_GOAT_BASE_URL",
        "base_url_default": "https://api.commandcode.ai/provider/v1",
        "model_env": "DEEPSEEK_MODEL",
        "model_default": "deepseek/deepseek-v4-flash",
        "sample_field": "DeepSeek-V4-Flash_story",
        "temperature_default": 0.7,
        "max_tokens_default": 2500,  # bumped — DeepSeek smoke test output was 271 words
    },
    "MiMo-V2.5-Pro": {
        "token_plan": "Command Code Goat",
        "sdk": "openai",
        "api_key_env": "CMD_GOAT_API_KEY",  # SAME as DeepSeek — same token plan
        "base_url_env": "CMD_GOAT_BASE_URL",
        "base_url_default": "https://api.commandcode.ai/provider/v1",
        "model_env": "MIMO_MODEL",
        "model_default": "XiaomiMiMo/MiMo-V2.5-Pro",  # exact prefix TBD — Ray verify
        "sample_field": "MiMo-V2.5-Pro_story",
        "temperature_default": 0.7,
        "max_tokens_default": 1500,
    },
    "Muse-Spark-1.2-Contributor": {
        "token_plan": "OpenCode Go (preferred) OR Command Code Goat (fallback)",
        "sdk": "openai",
        "api_key_env": "OPENCODE_GO_API_KEY",
        "base_url_env": "OPENCODE_GO_BASE_URL",
        "base_url_default": "https://opencode.ai/zen/go/v1",  # verified via /v1/models (2026-08-28)
        "model_env": "OPENCODE_MODEL",
        "model_default": "muse-spark-1.2-contributor",  # verified in OpenCode Go /v1/models list
        "sample_field": "Muse-Spark-1.2-Contributor_story",
        "temperature_default": 0.7,
        "max_tokens_default": 1500,
        # NOTE: OpenCode Go may return RegionError for users in CN.
        # Workaround: set env vars to point to Command Code Goat instead:
        #   export OPENCODE_GO_API_KEY=$CMD_GOAT_API_KEY
        #   export OPENCODE_GO_BASE_URL=https://api.commandcode.ai/provider/v1
        #   export OPENCODE_MODEL=meta/muse-spark-1.2-contributor
    },
    "Claude-Sonnet-5-High": {
        "token_plan": "Faro API (Ray 充值的 20 元中转, model=claude-sonnet-5)",
        "sdk": "anthropic",
        "api_key_env": "FARO_API_KEY",
        "base_url_env": "FARO_BASE_URL",
        "base_url_default": "https://faroapi.com",
        "model_env": "FARO_MODEL",
        "model_default": "claude-sonnet-5",
        "sample_field": "Claude-Sonnet-5-High_story",
        "temperature_default": 1.0,  # Claude default
        "max_tokens_default": 1500,
        # API format: anthropic /v1/messages (verified 2026-08-29)
        # thinking "adaptive" supported (smoke test prompt 3 = werewolf, 644 words OK)
    },
    "Kimi-K3": {
        "token_plan": "OpenCode Go (preferred) OR Command Code Goat (fallback — see Kimi-K3 env var note)",
        "sdk": "openai",
        "api_key_env": "OPENCODE_GO_API_KEY",
        "base_url_env": "OPENCODE_GO_BASE_URL",
        "base_url_default": "https://opencode.ai/zen/go/v1",  # verified via /v1/models (2026-08-28)
        "model_env": "OPENCODE_MODEL",
        "model_default": "kimi-k3",  # OpenCode Go verified
        "sample_field": "Kimi-K3_story",
        "temperature_default": 0.7,
        "max_tokens_default": 1500,
        # NOTE: OpenCode Go may hit 5-hour usage limit. Workaround via Command Code Goat:
        #   export OPENCODE_GO_API_KEY=$CMD_GOAT_API_KEY
        #   export OPENCODE_GO_BASE_URL=https://api.commandcode.ai/provider/v1
        #   export OPENCODE_MODEL=moonshotai/Kimi-K3
    },
}

# Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds; exponential: 2, 4, 8 ...

# Paths (relative to project root)
SAMPLE_PATH = Path("data/processed/sample_v1.json")
OUTPUT_DIR = Path("data/processed/modern_model_outputs")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve(model_name: str) -> dict:
    """Resolve env vars → concrete credentials + parameters."""
    cfg = MODELS[model_name]
    api_key = os.environ.get(cfg["api_key_env"], "")
    base_url = os.environ.get(cfg["base_url_env"], cfg["base_url_default"])
    model = os.environ.get(cfg["model_env"], cfg["model_default"])
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "temperature": cfg["temperature_default"],
        "max_tokens": cfg["max_tokens_default"],
        "sample_field": cfg["sample_field"],
        "sdk": cfg["sdk"],
    }


def _call_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> Optional[str]:
    """Call an OpenAI-compatible chat completions endpoint with retries."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        print("ERROR: `openai` package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    if not api_key:
        return None
    if not base_url:
        return None

    # HTTP timeout — OpenAI/Anthropic SDK default is infinite, can hang on bad network
    HTTP_TIMEOUT = 120  # seconds per request — thinking models need more time

    # Higher default for thinking models — thinking tokens count toward max_tokens.
    # 8000 leaves room for ~500-word story (~700 tokens) + 7000 thinking tokens.
    DEFAULT_MAX_TOKENS_THINKING = 8000

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=HTTP_TIMEOUT)

    # Per-model reasoning/thinking config. Some models (DeepSeek-V4-Flash, etc.) need
    # explicit thinking mode enabled or they get stuck at 0 chars with finish_reason=length.
    REASONING_CONFIG = {
        "deepseek-v4-flash": {"reasoning_effort": "high", "thinking": "enabled", "max_tokens": DEFAULT_MAX_TOKENS_THINKING},
        "deepseek-v4-pro":   {"reasoning_effort": "high", "thinking": "enabled", "max_tokens": DEFAULT_MAX_TOKENS_THINKING},
        "mimo-v2.5-pro":     {"reasoning_effort": "high", "max_tokens": DEFAULT_MAX_TOKENS_THINKING},
        "kimi-k3":           {"reasoning_effort": "high", "max_tokens": 16000},  # CCG fallback — hard prompts need more budget
        "muse-spark-1.2-contributor": {"reasoning_effort": "high", "max_tokens": 16000},  # OpenCode Go — hard prompts need more thinking budget
    }

    def _thinking_kwargs(model: str) -> dict:
        # Match by substring on model id (e.g. "deepseek/deepseek-v4-flash" → "deepseek-v4-flash")
        for k, v in REASONING_CONFIG.items():
            if k in model:
                return v
        return {}

    MIN_WORD_COUNT = 300  # if output is shorter, retry once with higher max_tokens

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout": HTTP_TIMEOUT,
            }
            # Apply per-model thinking config (overrides max_tokens if specified)
            tcfg = _thinking_kwargs(model)
            if tcfg:
                extra = {}
                if "thinking" in tcfg:
                    extra["thinking"] = {"type": tcfg["thinking"]}
                if "reasoning_effort" in tcfg:
                    extra["reasoning_effort"] = tcfg["reasoning_effort"]
                kwargs["extra_body"] = extra
                if "max_tokens" in tcfg:
                    kwargs["max_tokens"] = tcfg["max_tokens"]
                    max_tokens = tcfg["max_tokens"]  # update for retry logic
                print(f"  [thinking: {tcfg}]")

            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            if text and len(text.strip()) > 50:
                word_count = len(text.split())
                # If too short, retry once with higher max_tokens (no extra backoff)
                if word_count < MIN_WORD_COUNT and max_tokens < 4000:
                    print(f"  Short output ({word_count} words, finish={finish_reason}), bumping max_tokens to 4000...")
                    max_tokens = 4000
                    continue
                return text.strip()
            # 0 chars or near-empty — log and give up immediately (don't retry on length-truncated)
            print(f"  WARNING: model returned {len(text or '')} chars (finish_reason={finish_reason}). Skipping.")
            return None
        except Exception as exc:
            wait = RETRY_BACKOFF_BASE ** attempt
            print(f"  ERROR (attempt {attempt}/{MAX_RETRIES}, type={type(exc).__name__}): {str(exc)[:200]}")
            if attempt < MAX_RETRIES:
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  FAILED after {MAX_RETRIES} attempts.")
                return None
    return None


def _call_anthropic(
    api_key: str,
    base_url: str,
    model: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> Optional[str]:
    """Call an Anthropic-compatible endpoint with retries (MiniMax M3 via Anthropic SDK)."""
    try:
        import anthropic  # type: ignore
    except ImportError:
        print("ERROR: `anthropic` package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    if not api_key:
        return None
    if not base_url:
        return None

    # HTTP timeout — Anthropic SDK default is 60s, but explicit is safer
    HTTP_TIMEOUT = 120  # seconds per request — thinking models need more time

    # anthropic.Anthropic reads ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL from env,
    # but we pass explicitly so multiple keys don't conflict.
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url, timeout=HTTP_TIMEOUT)

    MIN_WORD_COUNT = 300  # if output is shorter, retry once with higher max_tokens

    # Per-model reasoning/thinking config for Anthropic SDK
    # Anthropic M3 with adaptive thinking can use 16000+ tokens just for reasoning
    # on hard prompts (e.g. werewolf), leaving little room for the ~500-word story.
    # Bump to 32000 to give thinking + final answer enough budget.
    DEFAULT_MAX_TOKENS_THINKING_ANTHROPIC = 32000
    REASONING_CONFIG_ANTHROPIC = {
        "MiniMax-M3": {"thinking": {"type": "adaptive"}, "max_tokens": DEFAULT_MAX_TOKENS_THINKING_ANTHROPIC},
        "claude-sonnet-5": {"thinking": {"type": "adaptive"}, "max_tokens": DEFAULT_MAX_TOKENS_THINKING_ANTHROPIC},  # Faro API
    }

    def _thinking_kwargs_anthropic(model: str) -> dict:
        for k, v in REASONING_CONFIG_ANTHROPIC.items():
            if k.lower() in model.lower():
                return v
        return {}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
                ],
                "timeout": HTTP_TIMEOUT,
            }
            tcfg = _thinking_kwargs_anthropic(model)
            if tcfg:
                # Update max_tokens if specified (thinking counts toward it)
                if "max_tokens" in tcfg:
                    kwargs["max_tokens"] = tcfg["max_tokens"]
                    max_tokens = tcfg["max_tokens"]
                if "thinking" in tcfg:
                    kwargs["thinking"] = tcfg["thinking"]
                print(f"  [thinking: {tcfg}]")

            message = client.messages.create(**kwargs)
            # Anthropic response.content is a list of content blocks (text/thinking/tool_use)
            # Extract text blocks only.
            text_parts = []
            for block in message.content:
                if hasattr(block, "type") and block.type == "text":
                    text_parts.append(block.text)
                # Skip thinking/tool_use blocks (they don't add to the story)
            text = "".join(text_parts).strip()
            finish_reason = getattr(message, "stop_reason", "?")
            if text and len(text) > 50:
                word_count = len(text.split())
                if word_count < MIN_WORD_COUNT and max_tokens < 4000:
                    print(f"  Short output ({word_count} words, finish={finish_reason}), bumping max_tokens to 4000...")
                    max_tokens = 4000
                    continue
                return text
            print(f"  WARNING: model returned {len(text)} chars (finish_reason={finish_reason}). Skipping.")
            return None
        except Exception as exc:
            wait = RETRY_BACKOFF_BASE ** attempt
            print(f"  ERROR (attempt {attempt}/{MAX_RETRIES}, type={type(exc).__name__}): {str(exc)[:200]}")
            if attempt < MAX_RETRIES:
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  FAILED after {MAX_RETRIES} attempts.")
                return None
    return None


def generate_story(model_name: str, prompt: str) -> Optional[str]:
    """Generate a story for one prompt using one model. Routes by SDK type."""
    cfg = MODELS[model_name]
    resolved = _resolve(model_name)

    if not resolved["api_key"]:
        print(f"  SKIP: {cfg['api_key_env']} not set")
        return None
    if not resolved["base_url"]:
        print(f"  SKIP: {cfg['base_url_env']} not set")
        return None

    user_prompt = PROMPT_TEMPLATE.format(prompt=prompt)

    if cfg["sdk"] == "anthropic":
        return _call_anthropic(
            api_key=resolved["api_key"],
            base_url=resolved["base_url"],
            model=resolved["model"],
            user_prompt=user_prompt,
            temperature=resolved["temperature"],
            max_tokens=resolved["max_tokens"],
        )
    else:  # openai
        return _call_openai_compatible(
            api_key=resolved["api_key"],
            base_url=resolved["base_url"],
            model=resolved["model"],
            user_prompt=user_prompt,
            temperature=resolved["temperature"],
            max_tokens=resolved["max_tokens"],
        )


def load_samples(project_root: Path) -> dict:
    path = project_root / SAMPLE_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_samples(project_root: Path, data: dict) -> None:
    path = project_root / SAMPLE_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Updated {path}")


def save_individual_output(
    project_root: Path,
    model_name: str,
    prompt_id: int,
    prompt: str,
    story: str,
) -> Path:
    out_dir = project_root / OUTPUT_DIR / model_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{prompt_id}.json"
    record = {
            "prompt_id": prompt_id,
            "prompt": prompt,
            "model": model_name,
            "token_plan": MODELS[model_name]["token_plan"],
            "sdk": MODELS[model_name]["sdk"],
            "story": story,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return out_file


def output_exists(project_root: Path, model_name: str, prompt_id: int, data=None, sample_field: str = None) -> bool:
    """A prompt is considered "already done" only if BOTH:
    1. The individual file exists at out_dir/{N}.json
    2. The sample_v1.json sample[N][sample_field] is non-empty (>= 100 chars)
    Otherwise we'll re-generate to ensure consistency between disk and sample_v1.json.
    """
    out_file = project_root / OUTPUT_DIR / model_name / f"{prompt_id}.json"
    if not out_file.exists():
        return False
    if data is not None and sample_field is not None:
        sample = next((s for s in data["samples"] if s["prompt_id"] == prompt_id), None)
        if not sample or not sample.get(sample_field) or len(sample[sample_field]) < 100:
            return False  # file exists but sample_v1.json is missing — re-generate
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ~500-word stories from modern LLMs for sample_v1.json prompts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        help="Run only this model (omit to run all 4 sequentially).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without calling any API.",
    )
    parser.add_argument(
        "--prompts",
        type=str,
        help="Comma-separated prompt IDs to process (e.g. '0,5,10'). Default: all 30.",
    )
    args = parser.parse_args()

    # Resolve project root (one level up from analysis/)
    project_root = Path(__file__).resolve().parent.parent
    data = load_samples(project_root)
    samples = data["samples"]

    # Filter prompts
    if args.prompts:
        selected_ids = set(int(x.strip()) for x in args.prompts.split(","))
        samples = [s for s in samples if s["prompt_id"] in selected_ids]
        print(f"Filtered to {len(samples)} prompt(s): {sorted(selected_ids)}")

    # Determine models
    model_names = [args.model] if args.model else list(MODELS.keys())

    print(f"Models: {model_names}")
    print(f"Prompts: {len(samples)}")
    print(f"Dry run: {args.dry_run}")
    print()

    if args.dry_run:
        # ---- DRY RUN ----
        for mn in model_names:
            cfg = MODELS[mn]
            resolved = _resolve(mn)
            has_key = bool(resolved["api_key"])
            has_url = bool(resolved["base_url"])
            print(f"[DRY RUN] {mn} ({cfg['token_plan']}, {cfg['sdk'].upper()} SDK)")
            print(f"  API key env:  {cfg['api_key_env']} = {'SET' if has_key else 'NOT SET'}")
            print(f"  Base URL env: {cfg['base_url_env']} = {'SET: '+resolved['base_url'] if has_url else 'NOT SET — Ray must fill in'}")
            print(f"  Model name:   {resolved['model']}")
            print(f"  Sample field: {cfg['sample_field']}")
            print(f"  Temperature:  {cfg['temperature_default']}")
            print(f"  Max tokens:   {cfg['max_tokens_default']}")
            for s in samples:
                pid = s["prompt_id"]
                exists = output_exists(project_root, mn, pid, data=data, sample_field=cfg["sample_field"])
                status = "EXISTS (skip)" if exists else "WOULD GENERATE"
                print(f"  prompt {pid:2d}: {status}")
            print()
        print("Dry run complete. No API calls made, no files written.")
        return

    # ---- LIVE RUN ----
    total_generated = 0
    total_skipped = 0
    total_failed = 0

    for mn in model_names:
        cfg = MODELS[mn]
        resolved = _resolve(mn)
        if not resolved["api_key"] or not resolved["base_url"]:
            print(f"⚠ {mn}: missing env vars — skipping entire model.")
            print(f"  Need: {cfg['api_key_env']} and {cfg['base_url_env']}")
            total_failed += len(samples)
            continue

        print(f"═══ {mn} ({cfg['token_plan']}, {cfg['sdk'].upper()} SDK) ═══")
        for s in samples:
            pid = s["prompt_id"]
            prompt = s["prompt"]

            # Skip if individual output already exists AND sample_v1.json has the story
            if output_exists(project_root, mn, pid, data=data, sample_field=cfg["sample_field"]):
                print(f"  prompt {pid:2d}: already exists — skip")
                total_skipped += 1
                continue

            print(f"  prompt {pid:2d}: generating...", end=" ", flush=True)
            story = generate_story(mn, prompt)

            if story:
                # Save individual output file
                out_file = save_individual_output(project_root, mn, pid, prompt, story)
                print(f"✓ ({len(story)} chars) → {out_file.name}")

                # Update the corresponding field in sample_v1.json
                field = cfg["sample_field"]
                for sample in data["samples"]:
                    if sample["prompt_id"] == pid:
                        sample[field] = story
                        break

                total_generated += 1

                # Persist after each successful generation (crash-safe)
                save_samples(project_root, data)
            else:
                print("FAILED")
                total_failed += 1

        print()

    # Final summary
    print("═" * 50)
    print(f"Generated: {total_generated}")
    print(f"Skipped (existing): {total_skipped}")
    print(f"Failed: {total_failed}")
    print("═" * 50)

    if total_generated > 0:
        print(f"\n✓ sample_v1.json updated with {total_generated} new story/stories.")
        print("  Downstream metric pipeline (analysis/metrics.py) can now re-run.")
        print()
        print("NOTE: Arena models (Claude*, GPT*, Gemini*) are NOT in this script.")
        print("      Ray to paste Arena outputs manually into sample_v1.json — see README.")


if __name__ == "__main__":
    main()