CCG1 的 5 小时额度已在 12:05 重置（commandcode · GOAT 5h 0%）。请继续把剩下 2 条补完。

**开始前先 git pull 到最新**（5800f7e 起支持流式、路径改为脚本相对，不再依赖 cwd；当前 corpus-v2 分支最新是 58a4fa6，含 argparse 缩进修复）。

- 现状：corpus_v2/raw/corpus_v2_gpt6.jsonl 148 行
- 缺 2 条，src_p：**12195、62541**
- 命令照旧：`cd <仓库根> && python3 corpus_v2/generate.py --models gpt6 --workers 2`（脚本幂等，已完成的会自动跳过）
- 跑完 `git add corpus_v2/raw && git commit` 推 corpus-v2 分支，并在 RUN_LOG.md 记完成条数

硬规则不变：只让脚本产出样本，不改 PROMPT_TEMPLATE、不改模型参数、不手写。
