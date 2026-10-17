// 图表说明-图文版.typ — 组会图表包逐图说明（图文版）
// 编译：typst compile "图表说明-图文版.typ" "图表说明-图文版.pdf"
#set document(title: "组会图表包 · 逐图说明（图文版）", author: "Ray")

#set page(
  paper: "a4",
  margin: (x: 18mm, top: 18mm, bottom: 16mm),
  footer: context [
    #set text(size: 7.5pt, fill: luma(150), font: ("MiSans", "Noto Sans CJK SC"))
    #grid(columns: (1fr, auto), align: (left, right),
      [何睿 · 组会图表包（第二轮）], [#counter(page).display()])
  ],
)

#set text(
  font: ("Noto Serif CJK SC", "Noto Serif SC"),
  size: 10.5pt,
  lang: "zh",
  features: ("kern",),
)
#set par(justify: true, leading: 1.15em)

#show heading.where(level: 1): it => {
  set text(font: "MiSans", size: 16pt, weight: "bold")
  align(center)[#block(width: 100%, inset: 0pt)[#it.body]]
  v(0.6em)
}

#show heading.where(level: 2): it => {
  set text(font: "MiSans", size: 12.5pt, weight: "bold")
  block(below: 2mm, breakable: false)[#it]
  v(-1mm)
  line(length: 100%, stroke: 0.45pt + luma(190))
  v(1.5mm)
}

#let fileline(name) = block(above: 0pt, below: 1.2mm)[
  #text(size: 8.5pt, fill: luma(125), font: ("DejaVu Sans Mono", "Noto Sans CJK SC"))[#name]
]
#let field(l, b) = block(above: 0pt, below: 2.4mm)[*#l*#b]

= 组会图表包 · 逐图说明（图文版）

#align(center)[
  #text(size: 10pt, fill: luma(100))[第二轮 ｜ 2026-10-17 ｜ 何睿]
  #v(1.5mm)
  #text(size: 9.5pt, fill: luma(100))[数据：30 个写作题目 ×（人类 + 9 个 AI 模型），英文短篇小说]
]

#v(4mm)

*口径（先说一次）*

- 统计：每指标 × 每模型做独立样本 Welch t 检验（双尾、未校正）；「AI 内部一致性」＝组内方差比 `var(AI)/var(Human)` 加 Levene 方差齐性检验。N=30/组，属筛选性描述。
- 通用读法（所有单指标两联图）：左格＝分布（黑色＝人类；蓝灰＝9 个 AI 模型；小提琴＝密度形状，箱线＝中位数与四分位）；右格＝方差比棒图（对数轴；蓝色且比值小于 1 ＝AI 组内更「齐」；柱顶数字＝比值，星号＝该模型 p 值小于 .05）。
- 每张图给五样：类型 / 含义 / 作用 / 怎么读 / 一句话看点。

#v(2mm)

*目录*：01–05 新增指标（词、句、段）｜06–13 既有 8 指标（本轮补图）｜14–15 总览两张。

#pagebreak()

== 图 01 ｜ 实词率 Lexical Density
#fileline("new_lexical_density.png")
#image("new_lexical_density.png", width: 100%)
#v(2.5mm)
#field("类型：", "小提琴图＋箱线图（左）｜对数棒图（右）。")
#field("含义：", "实词（名词/动词/形容词/副词/专名）占全部词的比例；越高＝内容词越密、虚词（冠词、介词、连词）越少。")
#field("作用：", "检验「AI 用词是更实还是更空」，同时看 AI 彼此之间像不像。")
#field("怎么读：", "左格看中位数位置是否与人类拉开；右格看每个模型的比值离 1 多远。")
#field("看点：", "均值上人机差别不大（中位 d = −0.13），但 AI 组内方差比中位仅 0.31、9/9 模型更齐（Levene 9/9 显著）：AI 的用词密度不是更高，而是彼此更像。")
#pagebreak()

== 图 02 ｜ 词长标准差 Word Length SD
#fileline("new_word_length_sd.png")
#image("new_word_length_sd.png", width: 100%)
#v(2.5mm)
#field("类型：", "同上两联图。")
#field("含义：", "每篇内部词长的离散程度（词长参差度）。")
#field("作用：", "看 AI 用词长度是否更单一（词汇形态复杂度的一环）。")
#field("怎么读：", "同通用读法。")
#field("看点：", "6/9 更齐（中位方差比 0.85）；均值 AI 略高（d +0.31）。方向较杂、属弱信号，汇报时放轻。")
#pagebreak()

== 图 03 ｜ 长词率 Long Word Ratio（≥7 字符）
#fileline("new_long_word_ratio.png")
#image("new_long_word_ratio.png", width: 100%)
#v(2.5mm)
#field("类型：", "同上两联图。")
#field("含义：", "长度 ≥7 字母的词的比例：用词分量的粗指标。")
#field("作用：", "看 AI 是否更依赖长词/复杂词，以及组内一致性。")
#field("怎么读：", "同通用读法。")
#field("看点：", "9/9 更齐（0.50）且均值略低（d −0.30）：AI 长词用得更少、也更均匀，像「用词更保险」。")
#pagebreak()

== 图 04 ｜ 句长变异系数 Sentence Length CV
#fileline("new_sentence_length_cv.png")
#image("new_sentence_length_cv.png", width: 100%)
#v(2.5mm)
#field("类型：", "同上两联图。")
#field("含义：", "句长 SD 除以均值：剔除绝对长度后的「句长起伏」。")
#field("作用：", "检验 AI 句子长短是否更均匀（与此前句长方差的发现互相印证）。")
#field("怎么读：", "同通用读法。")
#field("看点：", "7/9 更齐（0.75）；与「AI 句长更齐」的既有结论一致，且 CV 版对长短不一的文本更稳。")
#pagebreak()

== 图 05 ｜ 每段句数 Sentences per Paragraph
#fileline("new_sentences_per_paragraph.png")
#image("new_sentences_per_paragraph.png", width: 100%)
#v(2.5mm)
#field("类型：", "同上两联图。")
#field("含义：", "段落平均句数：段落粒度与组织结构指标。")
#field("作用：", "看 AI 的段落切分是否更规律。")
#field("怎么读：", "同通用读法；注意右格比值极端。")
#field("看点：", "9/9 更齐（方差比中位 0.006），注意：人类文本来自 Reddit、空行少，这个指标一半在反映排版格式，解读留余量（讲的时候说一句「格式敏感」）。")
#pagebreak()

== 图 06 ｜ 平均词长 Word Length（既有）
#fileline("old_word_length.png")
#image("old_word_length.png", width: 100%)
#v(2.5mm)
#field("含义：", "字符/词。")
#field("看点：", "8/9 组内更齐（0.57）；均值 AI 略高（d +0.39）。")
#pagebreak()

== 图 07 ｜ 平均句长 Sentence Length（既有）
#fileline("old_sentence_length.png")
#image("old_sentence_length.png", width: 100%)
#v(2.5mm)
#field("含义：", "词/句。")
#field("看点：", "均值 7/9 显著、AI 更长（d +0.57）；方差比 0.90，一致性差别最弱的之一。")
#pagebreak()

== 图 08 ｜ 句长方差 Sentence Length Variance（既有）
#fileline("old_sentence_length_var.png")
#image("old_sentence_length_var.png", width: 100%)
#v(2.5mm)
#field("含义：", "篇内句长方差。")
#field("看点：", "6/9 更齐（0.28）；均值 AI 偏高（d +0.41）。")
#pagebreak()

== 图 09 ｜ TTR（既有）
#fileline("old_ttr.png")
#image("old_ttr.png", width: 100%)
#v(2.5mm)
#field("含义：", "类符与形符之比（受文本长度影响，报告已正面处理）。")
#field("看点：", "9/9 更齐（0.22）；均值 AI 略低（d −0.42）。")
#pagebreak()

== 图 10 ｜ MTLD（既有）
#fileline("old_mtld.png")
#image("old_mtld.png", width: 100%)
#v(2.5mm)
#field("含义：", "词汇多样性（移动窗口）。")
#field("看点：", "唯一反例：AI 组内方差更大（中位比值 2.40、仅 1/9 更齐），均值远高于人类（d +2.03）。按既有口径标「存疑，等扩样本复核」，单列讲。")
#pagebreak()

== 图 11 ｜ 连接词频率 Conjunction Frequency（既有）
#fileline("old_conj_freq.png")
#image("old_conj_freq.png", width: 100%)
#v(2.5mm)
#field("含义：", "连接词占比。")
#field("看点：", "9/9 更齐（0.56）；均值 AI 更高（d +0.66）。")
#pagebreak()

== 图 12 ｜ 平均段长 Paragraph Length（既有）
#fileline("old_paragraph_length.png")
#image("old_paragraph_length.png", width: 100%)
#v(2.5mm)
#field("含义：", "词/段。")
#field("看点：", "8/9 更齐（0.03，最极端之一）；均值差异弱（d −0.24）。注意：同图 05，受切分影响。")
#pagebreak()

== 图 13 ｜ 段长方差 Paragraph Length Variance（既有）
#fileline("old_paragraph_length_var.png")
#image("old_paragraph_length_var.png", width: 100%)
#v(2.5mm)
#field("含义：", "篇内段长方差。")
#field("看点：", "9/9 更齐（0.08）；均值弱（d −0.16）。")
#pagebreak()

== 图 14 ｜ 方差比热图 Overview · Variance Ratio
#fileline("overview_variance_ratio.png")
#image("overview_variance_ratio.png", width: 100%)
#v(2.5mm)
#field("类型：", "热图（14 指标 × 9 模型）。")
#field("含义：", "每格＝该指标 × 该模型的组内方差比；越蓝（越小）＝AI 越「齐」；格内数字＝比值。")
#field("作用：", "一页看「哪些层面 AI 最同质」：词汇层与段落层最深（低至 0.03–0.31），MTLD 那一行是红的。")
#field("怎么读：", "先扫蓝色块集中在哪几行，再找红格（反例）。")
#pagebreak()

== 图 15 ｜ 效应量点阵图 Overview · Effect Sizes
#fileline("overview_effect_sizes.png")
#image("overview_effect_sizes.png", width: 100%)
#v(2.5mm)
#field("类型：", "点阵图（dot plot）。")
#field("含义：", "每格＝Cohen's d（AI 减 人类）；红点＝|d| ≥ 0.8（强效应）。")
#field("作用：", "看「差异有多大」：最红的是 MATTR（+1.66）与 MTLD（+2.03）；多数格在中小效应区。")
#field("怎么读：", "横排看模型一致性、纵排看指标；点离 0 越远差异越大。")
#pagebreak()

== 附 ｜ 汇报顺序建议（口头用）

- 先放图 14，一句话：词汇与段落层面，AI 比人类更「齐」（9 个模型 9 个方向一致）。
- 再挑 1–2 个新指标细讲（推荐 01 实词率、03 长词率：结论干净）。
- 主动交代图 10（MTLD）这个反例：单列、存疑、等扩样本。
- 收尾用图 15：差异强度整体不大，红点集中在两个多样性指标上，方向与长度混淆问题一致。
- 口径声明（一句）：双尾未校正、N=30，属筛选性结果，等 N=90 复核。
