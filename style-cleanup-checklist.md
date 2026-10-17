# 报告风格清理清单（2026-10-17）

> 依据 10/12 组会意见：「不罗列文献、去『导师裁定/advised』字样、收粗体」。
> 本轮已执行前两项中的机械部分并重建双语 PDF；文献列举给方案、暂未动正文。

## 一、advisor / 导师 字样：已清零（10 处 = 英文 5 + 中文 5）

| # | 文件 · 位置 | 原文（节选） | 改后 |
|---|---|---|---|
| 1 | EN · 摘要 | Following advisor guidance (2026-09-21), we compare each… | We compare each… |
| 2 | EN · §3.4 | **Hypothesis testing…** Following advisor guidance (2026-09-21), condition-level… | …Condition-level… |
| 3 | EN · §3.4 | …is applied** (advisor ruling, 2026-09-21) | …is applied** |
| 4 | EN · §3.4 | per the advisor ruling, no cross-window comparison… | no cross-window comparison… |
| 5 | EN · Limitations | …no multiplicity correction, per advisor guidance, 2026-09-21; §3.4) | …no multiplicity correction; §3.4) |
| 6–10 | ZH · 同 5 处 | 依照导师指导（2026-09-21）、依据导师指导意见、导师裁定、按导师裁定、按导师指导… | 全部删除署源，只保留方法本身（如「不做多重比较校正；§3.4」） |

核验：`pdftotext` 对两份新 PDF 检索 `advisor` / `导师` 均为 0 命中。

## 二、粗体：142 / 144 处 → 各 4 处

- 保留的 4 处：`Keywords:`（关键词标签）+ 摘要里的三条结论级短语（1.6× longer / 与仅用长度的基线基本持平 / 发现为初步、功效不足）。
- 其余全部去粗：正文的 run-in 标签（Human baseline. / Tools. / Headline takeaway. 等）与**附录表格字段**（Provider / Model / Date / Temperature 等）一并转普通字重。
- 备份：`proposal_v13.md.bak-20261017-1351-pre-cleanup`、`proposal_v13_zh.md.bak-…`（同名规则）。
- 说人话：如果觉得某几处标签该保留加粗，告诉我位置，我按清单回加（加粗策略可调，不重写正文）。

## 三、文献列举：两个方案，待你选（未动正文）

现状：§2 Related Work 有 5 段，逐篇介绍（Huang et al. 2024；Chakrabarty et al. 2024a/b；…）。

- **方案 A（推荐，改动小）**：把逐篇介绍压成 2–3 句「按问题归类」的综述，只留与本文直接相关的三处（Fan 2018 语料；Huang 2024 基线；Chakrabarty 2024a 创作辅助）。
- **方案 B（更彻底）**：正文只留一句总括＋三篇核心引用，其余移入脚注或参考文献表。
- 说明：这属于措辞与叙事，涉及你的口吻，所以本轮没有代笔。

## 四、「越新模型方差越小」：数据不支持，稿中未出现

- 核对：MATTR（窗 100）组内方差，GPT-3.5 为 0.000557，与最小的 Gemini-3.6-Flash（0.000556）基本并列，**不是**「越新越小」，也无单调关系（最大为 MiniMax-M3 0.001308）。
- 稿子里没有这句话；建议口头也别这么说，若被问就按实测答：「未见随模型更新而方差的单调变化」。

## 五、C&M 文献：仍未到手

- Covington & McFall (2010) 是 MATTR 的奠基文献，老师 9/21 说回去帮找，目前只有 Kubat & Milicka (2013) 在库。
- 备用：可从校图书馆/期刊库获取；需要我找公开版就说一声。

## 六、产物

| 文件 | 页数 | 说明 |
|---|---|---|
| `length-confound-report.pdf` | 24 | 英文版（清洁后，重建于 2026-10-17 13:51） |
| `length-confound-report-zh.pdf` | 29 | 中文版（同上） |
| `proposal_v13.md` / `proposal_v13_zh.md` | — | 源文件（已清 advisor、粗体收敛） |

流程：`build_reports.py`（pandoc → typst）重建两份 PDF，rc=0。

## 七、图插入（2026-10-17 14:30）

- **§4.2**：两张总览（图 1 方差比热图、图 2 效应量点阵），正文前置一句引导。
- **新增 §4.5「增补指标（探索性）」**：五个新指标的定义、双维度口径说明与结果摘要；配图 3–7（实词率、词长标准差、长词率、句长 CV、每段句数）。
- **附录 B**：八个锁定指标的两联图（图 8–15）；MATTR 无逐篇记录，仅见于图 1–2。
- 结果：英文 30 页、中文 34 页；每份内嵌 15 张图；`build_reports.py` 重建无报错。
- 待定：摘要仍写「8 个指标」，如需可加一句增补指标说明（未动）。

## 八、数字一致性更新（2026-10-17 14:4x）

- 摘要：8 个指标 → 八个锁定指标＋五项增补（并补 MATTR 的九核心表述）；§3.2 增加「增补指标不计入锁定集」；图 1 图注改写为「九个核心指标＋五项增补」；代码与数据节补 metrics_extended/round2_analysis/figures_round2。
- 重建后核验：全文「8 metrics／8 个指标」残留 0；英文 30 页、中文 34 页，各 15 图。

## 九、升版 v14（2026-10-17 14:53）

- 当前内容另存 `proposal_v14.md` / `proposal_v14_zh.md`；v13 从备份复原留档（两名并存）。
- `build_reports.py` 改读 v14；重建英文 30 页、中文 34 页，各 15 图，无报错。
- v14 与 v13 的差异＝§2 折叠＋章号前移＋交叉引用同步（另有同日增补指标、图、MATTR 引用等已含在内）。
