#!/usr/bin/env python3
"""corpus v2 generator — RAW model calls through Magpie.

Rules baked in (do not change):
  * One user message per request. NO system prompt, NO tools, NO agent/harness.
  * Same prompt text for the human story and the model call (paired design).
  * Fixed sampling parameters for every model; nothing model-specific except the id.

Writes one JSONL row per (arm, prompt, model) with the full request/response metadata.
Idempotent: re-running skips rows already present.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ENDPOINT = os.environ.get("MAGPIE_URL", "http://127.0.0.1:3425/v1/chat/completions")
API_KEY = os.environ.get("MAGPIE_KEY", "sk-placeholder")  # gateway accepts a placeholder
USER_AGENT = "ray-length-confound/2.0 (corpus-v2)"
# 唯一的框架句：所有模型、所有题目共用，逐字固定。人类写手在 Reddit 上看到的也是
# 「题目 + 写故事」这个语境，这里用一个最小指令复现，不引入任何长度或风格要求。
PROMPT_TEMPLATE = "Write a story based on the following prompt.\n\n{prompt}"
TEMPERATURE = 1.0
MAX_TOKENS = 4096
RETRIES = 3

MODELS = {
    "gpt6":     "commandcode-2/gpt-6-luna",
    "ds41":     "commandcode-2/deepseek/deepseek-v4.1-flash",
    "sonnet55": "commandcode-2/claude-sonnet-5-5",
    "kimi31":   "opencode-go-2/kimi-k3.1-pro",
}


def call(model_id, prompt):
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(prompt=prompt)}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = json.load(r)
    return raw, int((time.time() - t0) * 1000)


def key_of(row):
    return f"{row['arm']}:{row['src_p']}:{row['model_key']}"


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(key_of(json.loads(line)))
                except Exception:
                    continue
    return done


def run_one(job, out_path, lock):
    arm, item, model_key, model_id = job
    for attempt in range(1, RETRIES + 1):
        try:
            raw, ms = call(model_id, item["prompt"])
            choice = (raw.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            text = msg.get("content") or ""
            row = {
                "arm": arm,
                "src_p": item["src_p"],
                "src_s": item.get("src_s"),
                "model_key": model_key,
                "model_id": model_id,
                "prompt_sha1": hashlib.sha1(item["prompt"].encode()).hexdigest()[:12],
                "template": PROMPT_TEMPLATE,
                "prompt": item["prompt"],
                "human_words": item.get("human_words"),
                "content": text,
                "content_words": len(text.split()),
                "finish_reason": choice.get("finish_reason"),
                "response_id": raw.get("id"),
                "usage": raw.get("usage"),
                "ms": ms,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "user_agent": USER_AGENT,
                "attempt": attempt,
            }
            if not text.strip():
                raise RuntimeError("empty content")
            with lock:
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return key_of(row), None
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            if attempt == RETRIES:
                return None, f"{arm}:{item['src_p']}:{model_key} -> {err}"
            time.sleep(2 ** attempt)
    return None, "unreachable"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default="prompts_v2.json")
    ap.add_argument("--outdir", default="raw")
    ap.add_argument("--models", default="gpt6,ds41,sonnet55,kimi31")
    ap.add_argument("--arm", default="pool")
    ap.add_argument("--limit", type=int, default=0, help="max prompts per arm (pilot)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    data = json.load(open(args.prompts, encoding="utf-8"))
    os.makedirs(args.outdir, exist_ok=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]


    items = data.get("items") or []
    if args.limit:
        items = items[: args.limit]
    jobs = [(args.arm, item, mk, MODELS[mk]) for item in items for mk in models]

    import threading
    lock = threading.Lock()
    total_ok = total_skip = 0
    failures = []
    by_model = {m: {"ok": 0, "skip": 0} for m in models}
    for mk in models:
        out_path = os.path.join(args.outdir, f"corpus_v2_{mk}.jsonl")
        done = load_done(out_path)
        pending = [j for j in jobs if j[2] == mk and f"{j[0]}:{j[1]['src_p']}:{mk}" not in done]
        total_skip += len(jobs) and 0
        print(f"[{mk}] {MODELS[mk]} — pending {len(pending)}", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(run_one, j, out_path, lock) for j in pending]
            for fu in as_completed(futs):
                k, err = fu.result()
                if err:
                    failures.append(err)
                else:
                    total_ok += 1
                    by_model[mk]["ok"] += 1

    print(json.dumps({"ok": total_ok, "failures": len(failures), "by_model": by_model,
                      "failure_samples": failures[:5]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
