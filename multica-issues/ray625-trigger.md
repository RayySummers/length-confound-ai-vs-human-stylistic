OCG 的 5 小时额度已在 12:05 重置（opencode-go-2 5h 0%）。可以重跑了。

**开始前先 git pull 到最新**（5800f7e 起支持流式、路径改为脚本相对，不再依赖 cwd；当前 corpus-v2 分支最新是 58a4fa6，含 argparse 缩进修复）。

**这次必须开流式**。病因已复现并写进 commit 1063156：非流式长请求会被上游在 250–340 秒掐断（502 / EOF），跟模型参数和 timeout 设置无关——客户端超时提到 900s 也救不了，因为是上游断的。

命令照抄：

```
CORPUS_STREAM=1 python3 corpus_v2/generate.py --models kimi31 --workers 3
```

- worker 数保持 3，别往上加（长请求并发高更容易被掐）
- 现状：corpus_v2/raw/corpus_v2_kimi31.jsonl 还没有有效样本，目标 150 条
- 先冒烟确认流式通路：`CORPUS_STREAM=1 python3 corpus_v2/generate.py --models kimi31 --limit 2 --workers 2`，应返回 ok=2
- 每完成一批就 `git add corpus_v2/raw && git commit` 推 corpus-v2 分支，并在 RUN_LOG.md 记起止时间、完成条数、失败条数与报错原文

硬规则不变：只让脚本产出样本，不改 PROMPT_TEMPLATE、不改模型参数、不手写；整批报错就停下来写报告，不要换参数顶替。
