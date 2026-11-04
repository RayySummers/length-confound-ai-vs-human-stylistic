# corpus_v2 — 长度匹配语料生成（工作指南）

本目录只做一件事：**用原始 API 调用，为 150 个题目各生成 4 个模型的文本**，供后续长度匹配分析使用。

---

## 0. 先读这三条硬规则

1. **样本只能由脚本产生。** 任何 agent／助手都不许自己写、改写、润色、补写sample。脚本返回什么就存什么，哪怕看起来像没写完。
2. **不许给请求加任何东西。** 不加 system prompt、不加工具、不加"请写得更像人类"之类的提示。脚本里的 `PROMPT_TEMPLATE` 是唯一框架句，一个字都不许改。
3. **不许改模型、参数、题目。** 模型 id、temperature、max_tokens、`prompts_v2.json` 全部固定。发现问题就停下来写报告，不要"顺手修正"。

这三条是这项研究成立的前提：这批数据要能说"模型看到的只有题目本身"。

---

## 1. 环境

- 仓库：`RayySummers/length-confound-ai-vs-human-stylistic`，分支 **`corpus-v2`**（不是 main）。
- 运行位置：本机 WSL。网关是 Magpie，地址 `http://127.0.0.1:3425/v1/chat/completions`，**本机回环，不需要 key**（脚本里用占位 key）。
- 依赖：Python 3 标准库即可，不需要 pip 安装。
- 输出目录：`corpus_v2/raw/`。

```bash
git clone -b corpus-v2 https://github.com/RayySummers/length-confound-ai-vs-human-stylistic.git
cd length-confound-ai-vs-human-stylistic
python3 corpus_v2/generate.py --models gpt6 --limit 2 --workers 2   # 冒烟测试
```

冒烟测试应当返回 `"ok": 2`，`corpus_v2/raw/corpus_v2_gpt6.jsonl` 里两行，每行 `content_words` 明显大于 200。通过后再跑全量。

---

## 2. 全量怎么跑（分模型、分批，可断点续跑）

一次跑满 600 条会超时，**按模型分开跑，每个模型分两批**。脚本是幂等的：同样的命令再跑一次会自动跳过已完成的条目，所以中断了直接重跑同一条命令即可，不会重复写。

```bash
# 每个模型 150 条，分 3 批 × 50 条
for M in gpt6 ds41 sonnet55 kimi31; do
  for L in 50 50 50; do
    python3 corpus_v2/generate.py --models "$M" --limit 150 --workers 4
  done
done
```

> `--limit 150` 每次都会从第一条开始扫，但已完成的会被跳过，所以重复执行是安全的；实际每轮只跑剩下的。**不要用 `--limit` 去"只跑前 50 条"**——它按题目顺序截断，不是按批次。

跑完一个模型就 `git add corpus_v2/raw && git commit`，不要攒到最后。

---

## 3. 交付物

1. `corpus_v2/raw/corpus_v2_{gpt6,ds41,sonnet55,kimi31}.jsonl`，**合计 600 行**（150 题 × 4 模型）。
2. `corpus_v2/RUN_LOG.md`：每个模型的完成条数、失败条数与错误原文、起止时间、累计耗时。
3. 一个 PR（分支 `corpus-v2` → `main`），**不要自己 merge**。

每行的字段（脚本已写好，不要改结构）：`arm / src_p / src_s / model_key / model_id / prompt / human_words / content / content_words / finish_reason / response_id / usage / ms / ts / temperature / max_tokens / user_agent / template`。

---

## 4. 验收标准（Hari 复核，达不到就退回）

- 每个模型文件恰好 **150 行**，四个文件合计 600 行，`src_p` 无重复。
- 全部 600 行满足：`finish_reason == "stop"`、`content_words >= 200`、`content` 非空且不是报错文本。
- `template` 字段全部等于 `Write a story based on the following prompt.\n\n{prompt}`。
- `usage` 里 `completion_tokens` 全部存在且大于 0。
- 抽样 5 行回读：内容必须是完整故事（有情节、有结尾），不是"我无法"、不是解释题意、不是元评论。
- `RUN_LOG.md` 里的条数与 JSONL 实际行数一致。

---

## 5. 出问题怎么办

- **某模型整批失败**（例如 `MODEL_NOT_IN_PLAN`、`Model is unavailable`）：不要换模型顶替，也不要改题目，停下来把完整报错写进 `RUN_LOG.md` 并在 issue 里 @ 何睿。
- **偶发超时／5xx**：脚本已带 3 次重试；重试仍失败的条目会出现在最后输出的 `failure_samples` 里，重跑一次同样命令即可补上。
- **内容明显不像故事**（例如模型只回了一句话）：不要手改，原样保留并在 issue 里贴出该行 `src_p` 与 `model_key`，由 Hari 判断是否需要调整框架句。

---

## 6. 这批数据用来干什么（背景，供写报告时参考）

人类故事来自 WritingPrompts 母语料（MIT），按词数分六层各抽 25 题（450–1500 词）。生成完成后，会按 `|模型词数 − 人类词数| / 人类词数 ≤ 10%` 逐模型挑出匹配对；挑中的子样本用来检验"四指标的 AI/人类差异是否只是长度造成的"。

所以：**不要为了凑匹配去挑选或重写输出**，匹配是 Hari 在生成完成之后按上面的规则算的，生成阶段只管如实跑完。
