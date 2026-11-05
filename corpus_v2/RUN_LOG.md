# corpus_v2 生成日志 — sonnet55（Claude-Sonnet-5.5）

模型：`commandcode/claude-sonnet-5-5`（渠道 CCG1；`model_key = sonnet55`）
参数：`temperature=1.0`、`max_tokens=8000`（2026-11-05 由 4096 上调，原因见下「CCG2 时代已归档」）、单条 user message、`PROMPT_TEMPLATE` 原样未改
网关：`http://127.0.0.1:3425/v1/chat/completions`（Magpie 本机回环，占位 key）
执行：`cd corpus_v2 && python3 generate.py --models sonnet55 --limit N --workers 4`（脚本未作任何修改；`--prompts`/`--outdir` 默认值相对 `corpus_v2/`，故在 `corpus_v2/` 内执行）
起止：2026-11-05 04:42 → 07:16 +0800（UTC 2026-11-04 20:42 → 23:16），跨两个额度窗口，实际生成墙钟约 26 min

## 进度（截至 2026-11-05 07:16 +0800 / 2026-11-04 23:16 UTC）

| 项目 | 数值 |
| --- | --- |
| 目标条数 | 150 |
| 已写入 `raw/corpus_v2_sonnet55.jsonl` | **122** |
| 其中 `finish_reason == "stop"` | 122 |
| 其中 `finish_reason == "length"` | 0 |
| 重试后仍失败（未写入） | 28（全部因上游 5 小时额度 429，见「异常」） |
| 待生成 | 28 |

- 冒烟：`--limit 2 --workers 2` → `ok=2`（2 min 55 s，含冷启动与 2 次重试）
- 第 1 批：`--limit 16 --workers 4` → `ok=14`（2 min 19 s），累计 16 行
- 第 2 批：`--limit 56 --workers 4` → `ok=40`（5 min 57 s），累计 56 行
- 第 3 批：`--limit 96 --workers 4` → `ok=0, failures=40`（61 s，全部 429），文件仍 56 行
- 第 4 批（额度重置后）：`--limit 100 --workers 4` → `ok=44`（6 min 36 s），累计 100 行
- 第 5 批：`--limit 150 --workers 4` → `ok=22, failures=28`（3 min 53 s，后半段 429），累计 122 行

## 异常：CCG1 的 5 小时额度把 150 条切成三个窗口（阻塞，按 reset 时间续跑）

**第一次打满**（第 3 批，2026-11-05 05:00 +0800）。逐字原文：

```
HTTP 429
{"error":{"code":null,"message":"Command Code: You've reached your 5-hour usage limit for your plan. Your limit resets at 2026-11-04T22:58:43.926Z. Please wait for the window to reset or upgrade your plan to continue. (out of its allowance: not asked again before 06:58 UTC+8)","param":null,"type":"rate_limit_error"}}
```

**第二次打满**（第 5 批，2026-11-05 07:16 +0800）。逐字原文：

```
HTTP 429
{"error":{"code":null,"message":"Command Code: You've reached your 5-hour usage limit for your plan. Your limit resets at 2026-11-05T04:05:58.197Z. Please wait for the window to reset or upgrade your plan to continue. (out of its allowance: not asked again before 12:05 UTC+8)","param":null,"type":"rate_limit_error"}}
```

- 一个窗口大约只够 60 余条（每条约 3.3k completion tokens）。
- 影响：剩余 **28 条**需等 `2026-11-05T04:05:58Z`（= 12:05 +0800）窗口重置后继续。
- 处理：未换模型顶替、未改参数、未改题目；已排定重置后的自动续跑，同一命令重跑即可补齐（脚本幂等，已有 122 行不会重复写）。

## CCG2 时代已归档（历史记录）

2026-11-05 01:00–01:15 +0800 曾在 `commandcode-2`（CCG2）渠道上跑过 46 条（`max_tokens=4096`，其中 6 条触顶被截断：`src_p` 23766 / 13291 / 22365 / 86342 / 14798 / 74067）。随后 CCG2 先报 5 小时额度 429，重置后又报 `Command Code 2: You have insufficient credits to make this request.`（HTTP 400，逐字），账户额度耗尽。

渠道切到 CCG1、`max_tokens` 上调到 8000 后，这 46 条整体归档到 `raw/archive/corpus_v2_sonnet55.ccg2-46rows.jsonl`，本文件从头重新生成，故不再计入 150 条。

## 验收自查（122 行）

- `src_p` 无重复：122/122 唯一
- `finish_reason == "stop"`：122/122
- `content_words` 范围 602–2221，全部 ≥ 200
- `template` 全部等于 `Write a story based on the following prompt.\n\n{prompt}`
- `usage.completion_tokens` 全部存在且 > 0
- `content` 非空、无报错文本；抽样回读为完整故事

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

> ⚠️ 本节判断已被下文「第二次尝试：客户端超时提到 900 s 之后」推翻：超时提到 900 s 后请求仍然在
> 上游 247–338 s 被 EOF 断开，真正的病因是非流式长请求被上游断连。原文保留作为时间线记录。

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
## 第二次尝试：客户端超时提到 900 s 之后（2026-11-05 08:14 → 08:40 +0800）

脚本已更新到 `414b328`（`urlopen(timeout=900)`，`max_tokens=8000` 不变），
`opencode-go-2` 的 5 小时窗口开局读数 **1%**（08:14，额度确实已重置）。
执行：`cd corpus_v2 && python3 generate.py --models kimi31 --limit 2 --workers 2`。

结果仍然是 **0 条**，但失败原因和上一节不同 —— **上一节「阻塞 2：300 s 客户端超时」的判断已被推翻**，
问题在上游，不在客户端：

```
[kimi31] opencode-go-2/kimi-k3.1-pro — pending 2
{
  "ok": 0,
  "failures": 2,
  "failure_samples": [
    "pool:48384:kimi31 -> HTTPError: HTTP Error 502: Bad Gateway",
    "pool:9191:kimi31 -> HTTPError: HTTP Error 502: Bad Gateway"
  ]
}
```

`magpie usage` 里本次 6 条记录（时间 +0800）：

| 时间 | 状态 | 耗时 | 输出 token | 错误原文 |
| --- | --- | --- | --- | --- |
| 08:14:51 | 502 | 247353 ms | 0 | `Post "https://opencode.ai/zen/go/v1/chat/completions": EOF` |
| 08:14:51 | 502 | 305515 ms | 0 | 同上 |
| 08:19:00 | 502 | 334675 ms | 0 | 同上 |
| 08:19:58 | 502 | 247357 ms | 0 | 同上 |
| 08:24:10 | 502 | 337893 ms | 0 | 同上（`max_tokens=3000` 的诊断请求） |
| 08:24:39 | 502 | 283809 ms | 0 | 同上（重试） |

两个请求各重试 3 次，全部在 **247–338 s** 被上游断开，`0` 输出 token。

### 诊断 1：不是 token 上限，也不是客户端超时

用同一题目（`src_p=48384`）、同一 `PROMPT_TEMPLATE`、同参数，只把 `max_tokens` 降到 **3000** 单发：

```
HTTPError 502 after 302s: {"error":{"message":"OpenCode Go 2: Post \"https://opencode.ai/zen/go/v1/chat/completions\": EOF","type":"api_error"}}
```

`max_tokens` 降到 3000 依然在 302 s 被断开 → 上限不是 token 数；客户端超时已经是 900 s，也不是客户端。

### 诊断 2：加 `stream: true` 同一条请求 290 s 正常跑完（决定性证据）

同一题目、同一模型、同参数，仅额外带 `"stream": true`：

```
STREAM OK 290s chunks=6550 finish=stop words=1170
usage={"prompt_tokens":123,"completion_tokens":6562,
       "completion_tokens_details":{"reasoning_tokens":4872},
       "opencode":{"list_cost":0.065866,...}}
```

`finish_reason == "stop"`、1170 词、6562 completion token（其中 4872 是 reasoning）。

**结论**：OpenCode Go 的上游对**非流式**长请求在约 250–340 s 断连（EOF）；改流式后同样的请求可以
正常完成。这不是脚本参数的问题，是 `call()` 用非流式请求这一实现方式的问题。

### 需要的改动（一行级，但属硬规则 3 的禁区，未动）

`corpus_v2/generate.py` 的 `call()` 里：payload 加 `"stream": True`，按 SSE 逐块拼
`choices[0].delta.content`，`finish_reason` 取最后一块，`usage` 取带 usage 的那一块（实测网关会返回）。
`PROMPT_TEMPLATE`、`model`、`temperature`、`max_tokens`、题目、`user_agent` 全部不变，写出的行结构与现在一致。

### 额度侧备注

- 08:14 → 08:40，`opencode-go-2` 的 5 小时窗口从 1% 涨到 86%、7 天从 49% 涨到 83%。
- 但同一时段 `magpie usage` 里 `opencode-go-2` 的 99 条请求中，只有 **8 条**是本任务（`ray-length-confound`），
  其余 91 条是 `dsh` / `hermes` 走 `group/main` 路由组打进来的 —— **这个 Go 额度是和本机 agent 自己的
  流量共享的**，所以 kimi 跑到一半被 429 掐断是常态，不是异常。
- 5 小时窗口重置：`2026-11-05T04:05:24Z` = **12:05:24 +0800**。

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

---

# corpus_v2 生成日志 — ds41（DeepSeek-V4.1-Flash）

模型：`commandcode/deepseek/deepseek-v4.1-flash`（`model_key = ds41`，CCG1 渠道）
参数：`temperature=1.0`、`max_tokens=8000`、单条 user message、`PROMPT_TEMPLATE` 原样未改
网关：`http://127.0.0.1:3425/v1/chat/completions`（Magpie 本机回环，占位 key）
执行：`cd corpus_v2 && python3 generate.py --models ds41 --limit N --workers 4`（脚本未改；`--prompts`/`--outdir` 默认值相对于 `corpus_v2/`）

## 结果

| 项目 | 数值 |
| --- | --- |
| 写入 `raw/corpus_v2_ds41.jsonl` | **150**（`src_p` 150 个，无重复） |
| `finish_reason == "stop"` | 143 |
| `finish_reason == "length"`（触顶 8000） | **7**（见下「异常」） |
| 重试后仍失败（未写入） | 0（唯一一次 `empty content` 已补跑成功） |
| 起止时间 | 2026-11-05 **02:05:13 → 02:36:29** +0800（约 **31 min**） |
| 单条耗时中位 | 38.6 s（4 并发） |
| 正文词数合计 | 158,222（单条 42–2048 词） |

配额：开工前 `magpie quota` → `commandcode` 5h 窗口 0%、balance $70.00；收工 5h 6%、balance $69.23。

## 批次

| 批次 | 命令 | 结果 | 累计 | 墙钟 |
| --- | --- | --- | --- | --- |
| 冒烟 | `--models ds41 --limit 2 --workers 2` | `ok=2` | 2 | 1 m 10 s |
| 1 | `--models ds41 --limit 50 --workers 4` | `ok=47, failures=1` | 49 | 9 m 36 s |
| 补跑 | `--models ds41 --limit 50 --workers 2` | `ok=1`（补 `pool:74067`） | 50 | 1 m 20 s |
| 2 | `--models ds41 --limit 100 --workers 4` | `ok=50, failures=0` | 100 | 9 m 07 s |
| 3 | `--models ds41 --limit 150 --workers 4` | `ok=50, failures=0` | 150 | 9 m 49 s |

每批跑完即 commit（`ce18487` 归档 + `14c64ed` 第 1 批、`ddecd19` 第 2 批、第 3 批见本提交）。

## 渠道变更与 CCG2 旧样本

本轮最初按旧脚本（`commandcode-2`、`max_tokens=4096`）跑了 27 条（批 1 的 `ok=25` 加冒烟 2 条），
其中 3 条 `length` 截断、2 条不足 200 词；同一批量里另有 23 条失败，报错为
`RuntimeError: empty content` 与 `HTTP Error 429: Too Many Requests`（CHANNEL `commandcode-2`
5 小时窗口打满）。渠道切到 CCG1 后，这 27 条（`model_id=commandcode-2/...`、`max_tokens=4096`）
已整体移入 `raw/archive/corpus_v2_ds41.ccg2-27rows.jsonl`，与 sonnet55 的处理方式一致，
`raw/corpus_v2_ds41.jsonl` 的 150 行全部是 CCG1 + 8000 的单一配置。

## 异常：8 条不满足验收（需 Hari 判断）

7 条 `finish_reason == "length"`，`usage.completion_tokens == 8000`，其中
`reasoning_tokens` 占 6248–7949 —— 这个模型在 CCG1 上是推理模型，思考 token 计入
`max_tokens`，长思考把正文挤掉；另有 1 条正常 `stop` 但正文只有 72 词。按硬规则 3
**未改** `max_tokens`、未手改任何样本，原样保留：

| src_p | content_words | finish_reason | completion_tokens | reasoning_tokens | ms |
| --- | --- | --- | --- | --- | --- |
| 23766 | 42 | length | 8000 | 7949 | 65802 |
| 12205 | 72 | stop | 349 | 240 | 3571 |
| 74956 | 109 | length | 8000 | 7863 | 58737 |
| 24142 | 207 | length | 8000 | 7737 | 82076 |
| 34385 | 313 | length | 8000 | 7595 | 63360 |
| 44243 | 314 | length | 8000 | 7593 | 80404 |
| 74067 | 413 | length | 8000 | 7466 | 63713 |
| 53107 | 1341 | length | 8000 | 6248 | 70311 |

这 8 条不满足验收「每行 `finish_reason == "stop"`、`content_words >= 200`」。可选处置
（都要人拍板，我不自行决定）：接受；或授权提高 `max_tokens` / 关思考；或授权删除这 8 行后
用同参数重抽。重抽会让样本按长度被筛过，属于方法学决定。

## 其余验收项自查（150 行）

- `src_p` 无重复：150/150 唯一
- `template` 全部等于 `Write a story based on the following prompt.\n\n{prompt}`：是
- `usage.completion_tokens` 全部存在且 > 0：是
- `model_id` / `max_tokens`：150/150 均为 `commandcode/deepseek/deepseek-v4.1-flash` / 8000
- 抽样回读 5 行（3103 / 12416 / 18728 / 40000 / 44933）：均为完整故事（有情节、有结尾），
  无「我无法」、无解释题意、无元评论

---
