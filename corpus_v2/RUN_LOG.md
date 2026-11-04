# corpus_v2 生成日志 — sonnet55（Claude-Sonnet-5.5）

模型：`commandcode-2/claude-sonnet-5-5`（`model_key = sonnet55`）
参数：`temperature=1.0`、`max_tokens=4096`、单条 user message、`PROMPT_TEMPLATE` 原样未改
网关：`http://127.0.0.1:3425/v1/chat/completions`（Magpie 本机回环，占位 key）
执行：`cd corpus_v2 && python3 generate.py --models sonnet55 --limit N --workers 4`（脚本未作任何修改；`--prompts`/`--outdir` 默认值相对于 `corpus_v2/`，因此在 `corpus_v2/` 内执行）

## 进度（截至 2026-11-05 01:15 +0800 / 2026-11-04 17:15 UTC）

| 项目 | 数值 |
| --- | --- |
| 目标条数 | 150 |
| 已写入 `raw/corpus_v2_sonnet55.jsonl` | **46** |
| 其中 `finish_reason == "stop"` | 40 |
| 其中 `finish_reason == "length"`（触顶 4096） | **6**（见下「异常 2」） |
| 重试后仍失败（未写入） | 4 |
| 待生成 | 104 |

- 冒烟：`--limit 2 --workers 2` → `ok=2`（38 s）
- 第 1 批：`--limit 25 --workers 4` → `ok=23`（4 min 05 s），累计 25 行
- 第 2 批：`--limit 50 --workers 4` → `ok=21, failures=4`（3 min 48 s），累计 46 行
- 单条中位耗时约 40–55 s（含 4 并发排队），46 行累计墙钟约 8 min 50 s（01:02:24 → 01:11:12 +0800）

## 异常 1：上游 5 小时配额耗尽（阻塞，未解决）

第 2 批末尾 4 条在 3 次重试后仍失败，报错为 `HTTP Error 429`。用相同 payload 单发复现，网关原文（逐字）：

```
HTTP 429
{"error":{"code":null,"message":"Command Code 2: You've reached your 5-hour usage limit for your plan. Your limit resets at 2026-11-04T20:32:39.676Z. Please wait for the window to reset or upgrade your plan to continue. (out of its allowance: not asked again before Nov 10 16:21 UTC+8)","param":null,"type":"rate_limit_error"}}
```

- 失败条目（`failure_samples`）：`pool:53107`、`pool:44243`、`pool:7148`（HTTP 400，复现时为 429，同一配额问题），以及 `pool:58411`（HTTP 429）。
- 复现时间：2026-11-05 01:13 +0800，三条 `src_p` 均返回上述 429。
- 影响：**剩余 104 条无法继续**，直到 `2026-11-04T20:32:39Z`（= 2026-11-05 04:32 +0800）配额窗口重置。
- 处理：未换模型、未改参数、未改题目。已排定配额重置后的自动续跑；重跑同一命令即可补齐（脚本幂等，已完成的 46 行不会重复写）。

## 异常 2：6 条触顶 `max_tokens=4096`，被截断（需 Hari 判断）

`finish_reason == "length"`，`usage.completion_tokens == 4096`，正文在句中断掉：

| src_p | content_words | completion_tokens | ms |
| --- | --- | --- | --- |
| 23766 | 1083 | 4096 | 55319 |
| 13291 | 1454 | 4096 | 39753 |
| 22365 | 1118 | 4096 | 45473 |
| 86342 | 1664 | 4096 | 44045 |
| 14798 | 1682 | 4096 | 45599 |
| 74067 | 1042 | 4096 | 53048 |

按硬规则 3，**未改** `max_tokens`，这些行原样保留在 JSONL 里。但它们不满足验收条件「每行 `finish_reason == "stop"`」，需要 Hari 决定：是接受截断行、还是在授权后提高 `max_tokens` 重跑这 6 条（会改变采样参数，必须由人决定）。当前 46 行中占比 13%，全量 150 条预计还有约 20 条同类情况。

## 其余验收项自查（46 行）

- `src_p` 无重复：46/46 唯一
- `content` 非空、无报错文本：是
- `template` 全部等于 `Write a story based on the following prompt.\n\n{prompt}`：是
- `usage.completion_tokens` 全部存在且 > 0：是
- `content_words` 范围 759–1682，远高于 200
- 抽样回读：完整故事（有情节、有结尾），无「我无法」/解释题意/元评论
