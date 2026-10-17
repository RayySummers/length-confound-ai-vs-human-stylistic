// proposal_v12_header.typ — Typst header for the Summer Research 2026 v12 proposal
// Margins: 2.5cm all sides (matching RAY-437)
// Ligatures enabled (8/31 v13 polish)

#set document(
  title: "Length as a Primary Confound in AI-vs-Human Stylistic Comparisons: A Conservative Preliminary Report",
  author: "Ray",
)

#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
  number-align: right,
)

// Enable ligatures: standard (liga) + discretionary (dlig) + historical (hlig)
#set text(
  font: "Times New Roman",
  size: 11pt,
  lang: "en",
  features: ("liga", "dlig", "hlig", "kern"),
)

// Line spacing: ~Word 1.2x (measured pitch ~15.3pt at 11pt)
#set par(leading: 0.7em)

// Title - make it larger and bold, allow line breaks at semantic points
#show heading.where(level: 1): it => {
  set text(size: 16pt, weight: "bold")
  // Use full-width block (100%) with center alignment
  // This keeps the title as one logical block; long titles wrap naturally
  // and ALL wrapped lines remain centered (not just the first).
  align(center)[#block(width: 100%, inset: 0pt)[#it.body]]
  v(1em)
}

// Section headings
#show heading.where(level: 2): it => {
  set text(size: 13pt, weight: "bold")
  it
  v(0.5em)
}

#show heading.where(level: 3): it => {
  set text(size: 11pt, weight: "bold")
  it
  v(0.3em)
}

// Table styling
#show table: it => {
  set text(size: 9pt)
  it
}

// Caption styling
#show figure.caption: it => {
  set text(size: 9pt, style: "italic")
  it
}

