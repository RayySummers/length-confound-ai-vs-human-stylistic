# -*- coding: utf-8 -*-
"""一键重建 EN/ZH 报告 PDF（pandoc → typst），并套用房式：

房式（2026-10-17 定）：
  EN —— 正文 Newsreader 12pt；标题/子标题/粗体 Sentient；行距 0.7em（≈1.37 倍）
  ZH —— 正文汉字思源宋体、拉丁与数字 Newsreader 12pt；标题/粗体优先 Sentient，汉字回落 MiSans / 思源宋体

已知后处理：
   1) 删除 pandoc 产出的 #horizontalrule 行（typst 不识别）
   2) #blockquote[ → #quote(block: true)[
   3) 行首的 "/ "（被 typst 误判为术语列表）合并回上一行
来源 md：proposal_v14.md / proposal_v14_zh.md（后台名，含内部版本号，不对外）
产物：length-confound-report.pdf / length-confound-report-zh.pdf（对外名，无版本号）
"""
import io
import re
import subprocess

jobs = [
    ('proposal_v14.md',    'report_en.typ', 'proposal_v13_combined.typ', 'length-confound-report.pdf'),
    ('proposal_v14_zh.md', 'report_zh.typ', 'zh_combined.typ',           'length-confound-report-zh.pdf'),
]


def style_en(c):
    c = c.replace('font: "Times New Roman"', 'font: "Newsreader 12pt"')
    c = c.replace('\n  size: 11pt,\n', '\n  size: 12pt,\n')          # 正文字号 11 → 12
    c = c.replace('set text(size: 16pt, weight: "bold")', 'set text(font: "Sentient", size: 17pt, weight: "bold")')
    c = c.replace('set text(size: 13pt, weight: "bold")', 'set text(font: "Sentient", size: 14pt, weight: "bold")')
    c = c.replace('set text(size: 11pt, weight: "bold")', 'set text(font: "Sentient", size: 12pt, weight: "bold")')
    if '#show strong' not in c:
        c = c.replace('#set par(leading: 0.7em)',
                      '#set par(leading: 0.7em)\n\n// 粗体统一 Sentient\n#show strong: set text(font: "Sentient")')
    return c


def style_zh(c):
    c = c.replace('font: ("Noto Serif CJK SC", "Noto Serif SC"),',
                  'font: ("Newsreader 12pt", "Noto Serif CJK SC", "Noto Serif SC"),')
    for size in ('18pt', '14pt', '12.5pt'):
        c = c.replace(f'set text(font: "MiSans", size: {size}, weight: "bold")',
                      f'set text(font: ("Sentient", "MiSans"), size: {size}, weight: "bold")')
    if '#show strong' not in c:
        c = c.replace('#set par(leading: 0.87em)',
                      '#set par(leading: 0.87em)\n\n// 粗体：拉丁走 Sentient，汉字回落思源宋体\n'
                      '#show strong: set text(font: ("Sentient", "Noto Serif CJK SC"))')
    return c


for src, out_typ, old_typ, out_pdf in jobs:
    old = io.open(old_typ, encoding='utf-8').read().split('\n')
    i = next(k for k, l in enumerate(old) if l.startswith('= '))
    prefix = '\n'.join(old[:i])
    # --wrap=none：禁止 pandoc 硬折行（typst 的标题只认单行，长标题被折断会掉出标题样式）
    body = subprocess.run(['pandoc', src, '--wrap=none', '-t', 'typst'], capture_output=True, text=True).stdout
    c = prefix + '\n' + body
    c = '\n'.join(l for l in c.split('\n') if l.strip() != '#horizontalrule')
    c = c.replace('#blockquote[', '#quote(block: true)[')
    c = re.sub(r'\n/ ', ' / ', c)          # 行首 "/ " 合并（含多级）
    while re.search(r'\n/ ', c):           # 防御性：再跑一遍
        c = re.sub(r'\n/ ', ' / ', c)
    c = style_en(c) if out_typ == 'report_en.typ' else style_zh(c)
    io.open(out_typ, 'w', encoding='utf-8').write(c)
    r = subprocess.run(['typst', 'compile', out_typ, out_pdf], capture_output=True, text=True)
    print(out_typ, '->', out_pdf, '| rc =', r.returncode)
    if r.stderr:
        print(r.stderr[:600])
