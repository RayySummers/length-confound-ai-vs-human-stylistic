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

---

# corpus_v2 生成日志 — kimi31（Kimi-K3.1-Pro）

模型：`opencode-go-2/kimi-k3.1-pro`（`model_key = kimi31`，渠道 `opencode-go-2`，README 2026-11-05 起的规定）
参数：`temperature=1.0`、`max_tokens=8000`、单条 user message、`PROMPT_TEMPLATE` 原样未改
网关：`http://127.0.0.1:3425/v1/chat/completions`（Magpie 本机回环，占位 key）
执行：`cd corpus_v2 && python3 generate.py --models kimi31 --limit 2 --workers 2`（脚本未作任何修改）
起止：2026-11-05 02:04 → 02:17 +0800（UTC 2026-11-04 18:04 → 18:17），墙钟约 13 min

## 结果：冒烟未通过，0 条写入（`raw/corpus_v2_kimi31.jsonl` 未生成）

脚本输出（逐字）：

```
[kimi31] opencode-go-2/kimi-k3.1-pro — pending 2
{
  "ok": 0,
  "failures": 2,
  "by_model": {
    "kimi31": {
      "ok": 0,
      "skip": 0
    }
  },
  "failure_samples": [
    "pool:9191:kimi31 -> HTTPError: HTTP Error 429: Too Many Requests",
    "pool:48384:kimi31 -> HTTPError: HTTP Error 429: Too Many Requests"
  ]
}
```

## 阻塞 1：`opencode-go-2` 的 5 小时 Go 额度已 100% 耗尽

02:18:22 +0800 用与脚本完全相同的 payload（`max_tokens=8000`、`temperature=1.0`、同一 `PROMPT_TEMPLATE`）
单发复现，网关原文（逐字，含响应头）：

```
HTTP/1.1 429 Too Many Requests
Retry-After: 3527
X-Magpie-Model: opencode-go-2/kimi-k3.1-pro
X-Magpie-Provider: opencode-go-2

{"error":{"code":null,"message":"OpenCode Go 2: Go usage limit exceeded (out of its allowance: not asked again before 03:17 UTC+8)","param":null,"type":"rate_limit_error"}}
```

`magpie quota --json`（02:18:34 +0800 读数）：

| 窗口 | 已用 | 重置 |
| --- | --- | --- |
| 5 hours | **100%** | `2026-11-04T21:33:52Z` = 2026-11-05 **05:33:52 +0800** |
| 7 days | 48% | `2026-11-09T00:00:00Z` |
| Month | 40% | `2026-11-25T08:03:07Z` |

同一时段读数变化：02:05 为 60% → 02:10 为 65% → 02:18 为 **100%**。也就是说，下面这 4 次
**客户端已超时、返回 0 token** 的请求仍然把窗口打满了（上游在 300 s 内一直在生成，额度按上游实际
生成的 token 扣）。

## 阻塞 2：单条故事在脚本的 300 s 客户端超时内没有跑完

`magpie usage` 里对应本次运行的 4 条记录（时间 +0800，模型 `opencode-go-2/kimi-k3.1-pro`）：

| 时间 | 状态 | 耗时 | 输出 token | 错误原文 |
| --- | --- | --- | --- | --- |
| 02:05:21 | 499 | 300100 ms | 0 | `the agent canceled the request`（= 脚本 `urlopen(timeout=300)` 到点） |
| 02:05:21 | 499 | 300101 ms | 0 | 同上 |
| 02:10:23 | 499 | 300093 ms | 0 | 同上 |
| 02:10:23 | 502 | 285542 ms | 0 | `Post "https://opencode.ai/zen/go/v1/chat/completions": EOF` |

对照组：同一时刻 `max_tokens=16` 的小请求 02:05:13 返回 `200`、16 token，说明**模型 id 与渠道正常**，
卡住的是「一条 8000 token 上限的完整故事」这一量级的请求。

历史参照：今日 00:47 +0800 有两条同模型请求成功（输出 531 / 1162 token，耗时 19 s / 99 s，含
489 / 1013 reasoning token），吞吐约 12 token/s。按此估算，一条 2000 token 正文 + 1000+ reasoning
token 的故事需要 250 s 以上，与 300 s 的客户端超时几乎重合；8000 token 上限一旦被用满必然超时。

## 未做的动作（硬规则）

- 没有换模型顶替（没有试 `kimi-k3`、`commandcode/kimi-*` 等其他 id 出数据）。
- 没有改 `max_tokens` / `temperature` / `PROMPT_TEMPLATE` / 题目。
- 没有改脚本里的 `timeout=300`、没有改 `RETRIES`。
- 因此 `raw/` 下没有留下任何 kimi31 行 —— 本次 0 条，不是「跑了一部分」。

## 需要 Hari 决定（两条都需要动脚本，属硬规则 3 的禁区）

1. `max_tokens=8000` 对 kimi 这个推理模型是否维持？推理 token 与正文共享 8000，且推理开销让单条
   请求逼近/超过 300 s。
2. 是否授权把 `call()` 里的 `urllib` 超时从 300 s 提高到 600–900 s（`RETRIES` 不变）？不改这一项，
   kimi31 很可能永远跑不出 `finish_reason == "stop"` 的行。

额度侧：5 小时窗口 05:33:52 +0800 重置；在拿到上面两条决定之前不自动重试，避免再次把窗口烧在
注定超时的请求上。
# corpus_v2 生成日志 — gpt6（GPT-6-Luna）

模型：`commandcode/gpt-6-luna`（`model_key = gpt6`，CCG1 渠道）
参数：`temperature=1.0`、`max_tokens=8000`、单条 user message、`PROMPT_TEMPLATE` 原样未改
网关：`http://127.0.0.1:3425/v1/chat/completions`（Magpie 本机回环，占位 key）
执行：`cd corpus_v2 && python3 generate.py --models gpt6 --limit N --workers 4`（脚本未作任何修改；`--prompts`/`--outdir` 默认值相对于 `corpus_v2/`，因此在 `corpus_v2/` 内执行）

## 进度（2026-11-04 18:05Z / 2026-11-05 02:06 +0800 → 02:20 +0800）

| 项目 | 数值 |
| --- | --- |
| 目标条数 | 150 |
| 已写入 `raw/corpus_v2_gpt6.jsonl` | **150** |
| `finish_reason == "stop"` | **150** |
| 重试后仍失败（未写入） | 0 |
| 待生成 | 0 |

- 跑前 `magpie quota`：`commandcode` 余额 $70.00（5h 0%、Weekly 0%）；`commandcode-2` 已 100%、余额 $0.00，不再使用。
- 冒烟：`--limit 2 --workers 2` → `ok=2`（34 s），两行均为 `stop`、645/932 词。
- 第 1 批：`--limit 25` → `ok=23`（2 min 14 s）；`--limit 50` → `ok=25`（2 min 09 s）。累计 50，全部 `stop` → commit `c150455`
- 第 2 批：`--limit 75` → `ok=25`（2 min 16 s）；`--limit 100` → `ok=25`（2 min 01 s）。累计 100 → commit `15bb642`
- 第 3 批：`--limit 125` → `ok=25`（2 min 14 s）；`--limit 150` → `ok=25`（2 min 18 s）。累计 150 → 本文件所在 commit
- 150 行累计墙钟约 14 min（02:06:01 → 02:19:57 +0800），单条 `ms` 中位 16.8 s、最长 52.6 s；4 并发。
- `usage.completion_tokens` 合计 234,368；推理 token 每条都存在（中位 385、最大 3,948），是模型默认行为，脚本未传任何 reasoning 参数。

## CCG2 时代的 72 条已归档

`commandcode-2` 渠道在 2026-11-04 17:15Z 前后打满（`Command Code 2: You have insufficient credits…`，另有 429 配额报错），当时已产出 72 条。该批用的是旧 `max_tokens=4096`、旧渠道，含 3 条 `finish_reason=length`（82394 / 23766 / 53107）和 3 条 `finish_reason=content-filter`（81633 / 59002 / 60101，`completion_tokens=0`），另有 1 条仅 171 词（85858）。
按 `raw/archive/corpus_v2_sonnet55.ccg2-46rows.jsonl` 的同一处理方式，整批移到 `raw/archive/corpus_v2_gpt6.ccg2-72rows.jsonl`，用 CCG1 + `max_tokens=8000` 重新生成整套 150 条，保证同一文件内渠道与参数一致。归档文件原样保留、未改一行。

## 两条未达 `content_words >= 200`（原样保留，待 Hari 判断）

| src_p | content_words | completion_tokens | 情况 |
| --- | --- | --- | --- |
| 12195 | 190 | 772 | 开头有一句「I can’t retell all seven films… But I can offer an original…」的免责句，随后是一首完整的 Seuss 风格韵文故事 |
| 62541 | 90 | 210 | 完整短篇（跳水的瞬间），有起承转合，但只有 90 词 |

按硬规则 1/3 未改写、未重跑，行原样留在 JSONL 里。

## 其余验收项自查（150 行）

- 行数 150、`src_p` 无重复：150/150 唯一
- `finish_reason == "stop"`：150/150
- `content` 非空、无报错文本、无以「I cannot / As an AI」开头的元评论：是（12195 见上表）
- `template` 全部等于 `Write a story based on the following prompt.\n\n{prompt}`：是
- `usage.completion_tokens` 全部存在且 > 0：是
- `content_words`：中位 661，范围 90–1528
- `model_id` 全部为 `commandcode/gpt-6-luna`，`max_tokens` 全部为 8000
