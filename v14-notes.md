# proposal_v14 — 改动清单（2026-10-17，Hari 起草）

> 位置：`length-confound-archive/proposal_v14.md` / `proposal_v14_zh.md`（由 v13 复制修改；v13 原样保留在 `proposal_v13.md` / `_zh.md`，未删）
> 上一版：v13（10/12 组会汇报版）；本清单记录 10/17 一天内、v13 之后的全部改动
> 对外的 PDF 名字不带版本号：`length-confound-report.pdf` / `length-confound-report-zh.pdf`（由 `build_reports.py` 从 v14 生成）

## 本次改了什么

1. **增补指标**（按老师 10/12 意见）：新增五个探索性指标（实词率、词长标准差、长词率、句长变异系数、每段句数），写作新 §3.5；沿用 §2.4 的双维度口径（Welch t 双尾未校正＋组内方差比与 Levene）。
2. **图进正文**：§3.2 两总览（图 1 方差比热图、图 2 效应量点阵）；图 3–7 配新 §3.5；附录 B 收 8 个锁定指标的逐指标两联图（图 8–15）。全文 15 图、矢量合集 PDF 另有 `figures_round2.pdf`。
3. **MATTR 出处补引**：新增「MATTR 实现说明」（Covington & McFall 2010；窗口全件固定 100 词元）＋参考文献第 12 条；核验记录见 `analysis/citation_verification.md`。
4. **§2「相关工作」折叠**（按老师「文献不全章罗列、应 inline」的意见）：删整章 10 段，内容改写进引言两段（P1 人机文体比较、P2 测量与长度）；章号前移 3→2、4→3、5→4、6→5（含子节），交叉引用约 30 处同步。
5. **数字一致性**：全文「8 metrics / 8 个指标」清零，统一为「八个锁定指标＋五项增补」「九个核心指标（含 MATTR）」。
6. **风格清理（同日早些时候，含在 v13 与 v14 之间的改动）**：advisor / 导师字样 10 处清零；粗体 142/144 处收到各 4 处。

## 状态与待办

- 渲染：英文 30 页、中文 34 页，各 15 图；`build_reports.py` 无报错。
- 12 条参考文献全部仍被正文引用（含折叠后核验）。
- 待办：N=90 复现（future work）；Covington & McFall 原文 PDF 到手后按需细读窗口讨论；教师发送时点由 Ray 定（今天或明天均可）。
- 相关记录：`advisor-requirements-2026-10-12-checklist.md`（十条对照）、`review-diff-2026-10-17-sect2-inline.md`（折叠全文 diff）、`review-intro-fold-2026-10-17.md`（引言前后对比）。

## 追加清理（batch 2，2026-10-17 晚）

- **版本字眼清零**：英文 revised 18 处、中文「修订」20 处全部处理（标题、方法、结果、讨论、结论、局限）；中文版「早先版本中…应全文改为…」编辑指令句改写为正文。
- **§3.5 标题**去「（探索性）」，披露句改为「补充性质、非预设假设」。
- **结论**：三条 bullet 改为两段散文；破折号中英各清零（原各 10 处）。
- **「无法确认条目」**：引导句改为「尚无法确认的具体条目：」；条目内版本叙述改写。
- **正文内部文件引用清零**（results_v1.json、metric-specification.md、metrics_extended_stats.json），统一指向「数据与代码可用性」；参考文献区核验说明行整行删除。
- **MTLD 小节标题**改中性的「MTLD Dominance and Text Length」/「MTLD 的主导地位与文本长度」（原括注导致标题断行）。
- 重建：英文 29 页、中文 33 页，各 15 图。
- 备份：`proposal_v14.md.bak-batch2-pre` / `_zh` 同；审阅 diff：`review-diff-2026-10-17-batch2.md`。
- 待定：词长节去留（保留改写／移讨论／删）、MTLD 小节是否压缩成一段。
- **MTLD 小节压缩**：独立小节并入「词汇多样性作为分类器的主导特征」，内容压为一段；重建后英文 28 页、中文 32 页。见 `review-diff-2026-10-17-mtld-compress.md`。
- **§3.4 词长改写**（方案：保留改写）：标题改为「Word Length: A Difference Not Explained by Length」／「词长：一项未被长度解释的差异」；删除「候选 H6」与发现过程的叙述；披露句保留一行。
- **表 1b 拆表**：宽矩阵（11 列）改为表 1b（词/句层四项）＋表 1c（词汇与段落层四项），条件为行；正文引用改为「表 1a 至 1c」；数值未变。
- **标题断行修复**：pandoc 改为 --wrap=none；英文标题完整回到标题样式（两行居中）。build_reports.py 已更新。
- **括号列举改造**：EN 17 处、ZH 15 处，示例清单改为 namely/such as/例如/分别为/即；参数与统计括号未动。见 `review-diff-2026-10-17-paren.md`。
- **解释性括号→从句（第一批）**：EN 20 处 / ZH 16 处（which/where/since/即/例如 等改写）；引用、统计数值、表图数值注释保留。见 `review-diff-2026-10-17-clauses.md`。
- **图注瘦身**：图 1/2 说明移入 §3.2 正文；图 3–7 布局说明移入 §3.5；附录 B 引导句改散文并补单位。见 `review-diff-2026-10-17-captions.md`。
- **中文双右引号修复**：3 处直引号（最难／最易、离群、较老一代）改弯引号，核验 0 残留。
- **Sentient 变体**：`report_en_sentient.typ` → `length-confound-report-sentient.pdf`；`report_zh_sentient.typ` → `length-confound-report-zh-sentient.pdf`（正文 Sentient 优先、CJK 回落 Noto）。
- **摘要去粗体**：中英摘要各 4 处加粗（关键词、1.6×、与仅长度基线持平、初步结论）全部改为不加粗；核验残留 0。
- **混合字体变体**：`report_en_sentient-newsreader.typ` → `length-confound-report-sentient-newsreader.pdf`（正文 Newsreader 14pt；标题、子标题、粗体用 Sentient）。
- **Newsreader 12pt 光学匹配变体**：用变量字体（opsz 6–18）在 opsz=12、wght 400/700 生成四个静态实例（Newsreader 12pt 家族），正文 12pt、标题/粗体 Sentient → `length-confound-report-mix12.pdf`（34 页；11pt 版为 29 页）。
- **变体生成脚本**：新增 `make_variants.py`（从当前 report_en.typ 统一生成 sentient / sentient-newsreader / mix12 三份变体并编译），修复先前变体使用过期源、摘要残留旧粗体的问题。
- **行距定稿**：Ray 选定现状档（leading 0.7em，12pt 下行距 16.4pt ≈ Word 1.2 倍 / 字号 1.37 倍）；mix12 保持不变。对照实验档（lead83 / lead100）仅留仓库内，不入对外包。
- **房式切换（EN+ZH）**：EN 正文 Newsreader 12pt、标题/粗体 Sentient、行距 0.7em；ZH 正文汉字思源宋体 12pt＋拉丁 Newsreader、标题与粗体优先 Sentient（汉字回落 MiSans／思源宋体）。`build_reports.py` 已内置房式（style_en/style_zh），重建即生效；`make_variants.py` 改为生成 sentient 与 newsreader-14pt 两个对照变体。旧 Times 11pt 版备份：`length-confound-report.times11.bak.pdf`、`length-confound-report-zh.bak.pdf`。
- 重建结果：EN 34 页、ZH 31 页。
