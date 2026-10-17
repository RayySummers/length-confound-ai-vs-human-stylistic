# proposal_v13 — 改动清单与开放项（2026-10-03 晚，Hari 起草）

> 位置：`length-confound-archive/proposal_v13.md`（由 `proposal_v12.md` 复制修改；v12 原样保留，未删）
> 数字来源：`analysis/mattr_group_ttest_results.json`、`analysis/group_homogeneity_results.json`（均为 2026-09-21 按老师口径跑的）
> 老师口径出处：`memories/academic/meetings/2026-09-21-王雅琴组会.md`

## 本次改了什么（按 9/21 老师四条意见）

1. **§3.4 统计口径整段改写** — 独立样本 Welch t 检验（模型组 30 篇 vs 人类组 30 篇；双尾）；不做多重比较校正；每个对比同时报 p + Cohen's d；稳健性：t 与秩和检验 81 个对比里 72 个一致（89%）；MATTR 固定窗口 100（跨窗口比较降级为稳健性注记）。旧配对框架（Wilcoxon + Holm）标注为被取代、结果不混用。
2. **§4.2 整块替换** — 新表 2a（9 指标 × 4 个判据计数）＋ 表 2b（MATTR 逐模型：M/SD/ΔM/t/p/d/方差比）＋ 三条读法；旧的配对检验表与"14 显著/12 Holm"总结移出正文（v12/git 里可查）。
3. **同质性一节（老师第 5 条意见）** — 并入 §4.2（表 2a + 读法 1/2/3）与 §6 新段：MATTR/TTR/连词/段长方差 = 9/9 模型 AI 组内方差更小（中位比 0.08–0.56）；MTLD 是唯一反例（2.40）。
4. **TTR / MATTR / MTLD 方向矛盾** — §5 新小节（长度混淆：TTR 与长度 r≈−0.45，MATTR/MTLD 弱 ≈+0.22/+0.12；TTR 方向被长度带反属预期）。
5. **MTLD 异常单独说明** — §5 同小节第二段（方差更大 + 均值差最大；机制留 N=90）。
6. 摘要：方法句换新口径 + 加同质性发现句 + 残差结论标"初步"；§4.3/§6 管线行补 v13 脚本名。

## 开放项 [V13-OPEN]

- **长度残差化重跑**：v12 的配对版残差分析（H3/H4 各 0/9）需按新组间框架重跑；文中已标"初步"。
- **§4.4 词长节 + 表 5**：仍用旧 one-tailed Wilcoxon 数字（表 2a 里已有组间框架下的词长结果）——下一轮统一。
- **§5 遗留小节**（H4/H1/H2、分类器注意事项）与 **§6 三刻板印象 bullet / Limitations**：局部仍提 Holm/单尾；§5 顶部已放注记，待统稿。
- **摘要/§6 最终一致性**：等残差重跑后做最后一轮。
- N=90 复现仍为 future work（未变）。

## 未做（等 Ray 定）

- PDF 渲染（等审后跑 Typst/Chrome 管线）
- git 提交/推送（本地仓库，未提交；公开仓库未动）

## 渲染记录（2026-10-03）

- 英文 PDF：`proposal_v13.pdf`（Typst 0.14.2；24 页；行距 1.2 倍 ≈15.3pt @11pt TNR；管线：pandoc md→typ + v13_header.typ（含 set par(leading: 0.7em)）+ typst compile；`#horizontalrule` 已移除、`#blockquote` 换 `#quote(block: true)`）。
- 排版源文件：`proposal_v13_header.typ`、`proposal_v13_combined.typ`（仓库与 E 盘各一份）。
- 待办：中文参考版（1.6 倍 ≈19.2pt，明天开始翻译+排版）。

## 中文参考版（2026-10-03 晚完成）

- `proposal_v13_zh.md` + `proposal_v13_zh.pdf`（29 页；正文 Noto Serif CJK SC 12pt；标题 MiSans；行距实测 19.2pt = 12×1.6；参考文献与 BibTeX 保留英文原样）。
- 翻译方式：分 7 块并行翻译后合并（标题摘要/方法/结果12/结果34/讨论/结论/附录A）；术语按统一表。
- 补记：英文版 §1、§3.1、§3.3 的 4 处旧框架残留（paired framework / Wilcoxon signed-rank 描述）已修正，英文 PDF 已重渲（15.3pt ≈ Word 1.2 倍）。§5/§6 深层遗留段落仍待下一轮统稿。

## 打磨三项完成（2026-10-03 晚）

1. **残差化重跑（修订框架）**：`analysis/residualization_v13.py` + `residualization_v13_results.json`。结果：TTR 4/9 显著（幸存方向全部反转为 AI > 人类）；连词频率 5/9；词长 5/9（ANCOVA 稳健性：TTR 4/9、连词 2/9、词长 3/9）。旧 v12「0/9」不复制。§4.2/摘要/§5/§6 均已更新。
2. **旧框架段落统一**：§1、§4.3、§4.4（整节重写 + 新表 5）、§5（H4/H1/H1-H2 局限/词汇多样性/MTLD 小节）、§6（开头/刻板印象块/局限/披露/要点）、Future Work、摘要——全部改为修订框架口径；Holm/配对/单尾残留已清零（仅保留 supersession 说明）。
3. **摘要终稿一致性**：摘要与正文一致；[V13-OPEN] 标记全部清除。
4. **重渲**：英文 PDF 25 页（1.2×）；中文 PDF 29 页（1.6×）。两版同步。

## 仍开放（非本次范围）
- 老师两篇论文（MATTR 奠基 + 捷克）未到；术语确认小项（Maxine/MDG/预存/红军）留 10/12 当场问。
- N=90 复现（future work，已写在文中）。

## 对外版去版本号 + 一键重渲（2026-10-12）

- Ray 定：**正文不得出现内部版本号**（v12/v13 及 v7/v8 评审回合引用）——最后只有一个成品，版本信息只留后台。
- 已剔除（中英同步）：`v12/v13` 全部字样、「回应 Kimi v7 / GLM v8」类引用、「30v30→30 vs 30」；脚本引用改为无版本名 `analysis/residualization.py`（副本）。
- 顺手修复：Limitations 标题此前被粘在上一段句尾（`artifacts.## Limitations`），现已成独立标题。
- 新增 `build_reports.py`（一键：pandoc → 拼 header → 三处后处理 → typst compile）；后处理＝①删 `#horizontalrule` 行 ②`#blockquote[`→`#quote(block: true)[` ③行首「/ 」合并（否则被当术语列表要冒号）。
- 新产物（对外名）：`length-confound-report.pdf`（EN，24 页）、`length-confound-report-zh.pdf`（ZH，29 页）。旧 `proposal_v13.*` 全套保留（后台）。
- 保留说明：`sample_v1.json`/`results_v1.json`（数据资产名）与 API 路径 `/v1` 未动。

---

> 后续版本：**v14（2026-10-17）**，见 `v14-notes.md`。v13 文件保留在 `proposal_v13.md` / `proposal_v13_zh.md`。
