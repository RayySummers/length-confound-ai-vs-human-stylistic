// proposal_v13_zh_header.typ — 中文参考版 Typst 头
// 正文：Noto Serif CJK SC 12pt；标题：MiSans；行距 1.6 倍（≈19.2pt 实测标定 0.87em）
#set document(
  title: "AI 与人类文体比较中的主要混淆因素：长度（中文参考版）",
  author: "Ray",
)

#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
  number-align: right,
)

#set text(
  font: ("Noto Serif CJK SC", "Noto Serif SC"),
  size: 12pt,
  lang: "zh",
  features: ("kern",),
)

// 行距：目标 ≈19.2pt（12pt × 1.6）；实测 pitch = 8.75 + 12L → L = 0.87em
#set par(leading: 0.87em)

// 标题（一级）：MiSans 加粗、居中
#show heading.where(level: 1): it => {
  set text(font: "MiSans", size: 18pt, weight: "bold")
  align(center)[#block(width: 100%, inset: 0pt)[#it.body]]
  v(1em)
}

// 二级标题
#show heading.where(level: 2): it => {
  set text(font: "MiSans", size: 14pt, weight: "bold")
  it
  v(0.5em)
}

// 三级标题
#show heading.where(level: 3): it => {
  set text(font: "MiSans", size: 12.5pt, weight: "bold")
  it
  v(0.3em)
}

// 表格
#show table: it => {
  set text(size: 10pt)
  it
}

// 说明文字
#show figure.caption: it => {
  set text(size: 10pt)
  it
}
