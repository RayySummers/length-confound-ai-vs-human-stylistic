# -*- coding: utf-8 -*-
"""从当前 report_en.typ（房式版：正文 Newsreader 12pt + 标题/粗体 Sentient）生成对照变体并编译：

  1. sentient        —— 正文也换成 Sentient（整本 Sentient）
  2. newsreader-14   —— 正文换 Newsreader 14pt 光学档（字号仍 12pt），用于光学尺寸对照

如需行距对照，改 build 产出的 base 里 `leading: 0.7em` 后再跑本脚本即可。
输入：report_en.typ（由 build_reports.py 生成，须先跑最新 md）
输出：report_en_<variant>.typ + length-confound-report-<variant>.pdf
"""
import io
import subprocess

SRC = 'report_en.typ'
base = io.open(SRC, encoding='utf-8').read()


def compile_variant(name, body_font):
    s = base.replace('font: "Newsreader 12pt"', f'font: "{body_font}"')
    assert s != base, '未找到正文字体设置，report_en.typ 可能已变'
    out_typ = f'report_en_{name}.typ'
    out_pdf = f'length-confound-report-{name}.pdf'
    io.open(out_typ, 'w', encoding='utf-8').write(s)
    r = subprocess.run(['typst', 'compile', out_typ, out_pdf], capture_output=True, text=True)
    print(out_typ, '->', out_pdf, '| rc =', r.returncode)
    if r.stderr:
        print(r.stderr[:400])


compile_variant('sentient', 'Sentient')
compile_variant('newsreader-14pt', 'Newsreader 14pt')
