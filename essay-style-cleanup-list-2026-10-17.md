# essay 化清单：清理「过程痕迹」（2026-10-17）

起因：Ray 指出 §3.4「附加发现：词长（候选 H6）」与「（见 metric-specification.md，2026-08-05）」两种写法都不像 essay，像工作报告。老师口径：避免把探索过程写进论文。以下为全文扫描结果与改法建议。

## 一、必改（编辑痕迹／内部信息外露）

1. **§3.4 标题**：「Additional Finding: Word Length (Candidate H6)」/「附加发现：词长（候选 H6）」→ 建议改「Word Length: A Difference Not Explained by Length」/「词长：一项未被长度解释的差异」。
2. **§3.4 末句**：「This finding is post-hoc (see metric-specification.md, 2026-08-05) and is reported as an 'Additional Finding' rather than as a pre-registered hypothesis (H6 candidate); it requires independent confirmation at N=90.」→ 改：「该模式不在预先设定的假设之列，此处作为探索性发现报告；在独立数据（N=90）上复现之前，不应当作稳定结论。」
3. **§5 局限第七条**：「（见 metric-specification.md, 2026-08-05）」删掉，只留「并非预先设定的假设」。
4. **参考文献区那行斜体注**：「*All 12 references verified ... (2026-08-29; Covington and McFall added 2026-10-17 ...) Verification log: `analysis/citation_verification.md`.*」整行删除（移入仓库笔记）。
5. **中文版编辑指令残留**（§5）：「早先版本中“模型层面异质性”的表述应全文改为“流程层面异质性”：……」→ 改写为正文句：「因此条件间差异应理解为流程层面的异质性，而非模型层面的差异：可能反映渠道、温度、思考模式、系统提示或采样策略，当前设计无法区分。」
6. **正文内指向内部文件的句子**：`results_v1.json`（2 处）、`analysis/metrics_extended_stats.json`（1 处）、「supplementary materials」等 → 正文改为「逐篇检查」「随附材料」，完整文件清单只保留在「代码与数据可用性」一节。

## 二、建议清（版本对照／修订叙述）

7. **「修订框架（revised framework）」字样全文 15 处（中文 14 处）**：含 3.2 节标题与 2.4 节开头。essay 只呈现一套方法，建议删除括注与「under the revised framework」短语。
8. **「This replaces the earlier paired Wilcoxon signed-rank framework: the paired design ... is superseded, and its results are not mixed with those reported below.」** → 删；如需交代设计选择，可写一句中性的「本文把每个条件的文本作为一组与人类基线比较」。
9. **「The length-control analysis was re-run under the revised framework: ... (An earlier paired analysis had reported 0/9 for both metrics; that result does not replicate under the revised framework.)」** → 删括号里的版本对照，只留当前结果。
10. **MTLD 段落的版本史**：「早期计算中范围为 121.7-452.6」「34.0% 重要性是在旧实现上计算的」→ 只保留当前实现与当前数字，旧实现不再入正文。

## 三、你定（内容去留）

11. **词长这条发现的身份**：保留改写（推荐）／移进讨论区／整段删除。
12. 若保留：是否在 §3.4 首句补一句「先由分类器特征重要性引起注意」的来路说明。（透明但略带过程；不写也合规。）

## 四、改法样例（词长节首句）

- 原文：Word length (chars/word) emerged as a candidate metric when inspecting feature importance from the overall classifier (where it ranked 7th of 8 features) and the GPT-3.5 per-condition classifier (where it was the top feature with importance 0.278).
- 建议：Word length (characters per word) is not among the pre-specified hypotheses and is reported here as an exploratory finding. It is also the metric whose difference length control does not eliminate: group comparisons are significant in 3 of 9 conditions before, and 5 of 9 after, residualizing on word count (AI > human).

（英文改完后中文同步；改完重生成 PDF，并给 Ray 看 diff。）
