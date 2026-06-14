#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка рабочих листов курса «1С:Элемент» из Markdown в PDF (формат A4).

Обрабатывает файлы rabochiy-list.md и domashnyaya-rabota.md в папках уроков.
Блоки кода двух видов:
  - справочные (памятка, примеры) — рисуются как светлая плашка с подсветкой;
  - скелеты с пустыми строками — превращаются в поле для записи кода
    (пунктирные линии, куда ученик вписывает решение).

Использование:
    python3 tools/build_worksheets.py                 # все листы
    python3 tools/build_worksheets.py путь/к/файлу.md  # один файл
"""

import sys
import re
import glob
import os

import markdown
from weasyprint import HTML

from build_pdf import esc, highlight_eos, replace_emoji

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, "worksheet.css")

FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


def is_fillin(code: str) -> bool:
    """Скелет для записи: есть пустые строки внутри кода."""
    lines = code.strip("\n").split("\n")
    return any(not l.strip() for l in lines)


def fillin_html(code: str) -> str:
    lines = code.strip("\n").split("\n")
    rows, blanks = [], 0
    for l in lines:
        if l.strip():
            rows.append(f'<div class="cl">{esc(l)}</div>')
        else:
            rows.append('<div class="wl"></div>')
            blanks += 1
    # добавим простор для записи, если пустых строк мало
    rows += ['<div class="wl"></div>'] * max(0, 4 - blanks)
    return '<div class="fillin">' + "".join(rows) + "</div>"


def ref_html(code: str) -> str:
    return f'<div class="ref"><pre><code>{highlight_eos(code.strip(chr(10)))}</code></pre></div>'


def code_block(lang: str, code: str) -> str:
    return fillin_html(code) if is_fillin(code) else ref_html(code)


def render(md_path: str):
    raw = replace_emoji(open(md_path, encoding="utf-8").read())

    blocks = []
    def stash(m):
        blocks.append(code_block(m.group(1), m.group(2)))
        return f"\n\n@@CODE{len(blocks)-1}@@\n\n"
    body = FENCE_RE.sub(stash, raw)

    md = markdown.Markdown(extensions=["fenced_code", "tables", "sane_lists"])
    htmlbody = md.convert(body)

    for i, b in enumerate(blocks):
        htmlbody = htmlbody.replace(f"<p>@@CODE{i}@@</p>", b).replace(f"@@CODE{i}@@", b)

    # покрасим звёздочки сложности и галочки
    htmlbody = htmlbody.replace("★", '<span class="star">★</span>')
    htmlbody = htmlbody.replace("✓", '<span style="color:#16a37b;font-weight:800">✓</span>')
    htmlbody = htmlbody.replace("✗", '<span style="color:#e5484d;font-weight:800">✗</span>')

    doc = ("<!doctype html><html lang='ru'><head><meta charset='utf-8'></head>"
           "<body>" + htmlbody + "</body></html>")
    out_path = os.path.splitext(md_path)[0] + ".pdf"
    HTML(string=doc, base_url=HERE).write_pdf(out_path, stylesheets=[THEME])
    print(f"  ✓ {out_path}")
    return out_path


def main(argv):
    if argv:
        targets = argv
    else:
        base = os.path.dirname(HERE)
        targets = sorted(
            glob.glob(os.path.join(base, "uroki", "*", "rabochiy-list.md")) +
            glob.glob(os.path.join(base, "uroki", "*", "domashnyaya-rabota.md")))
    if not targets:
        print("Не найдено ни одного рабочего листа.")
        return 1
    print(f"Собираю рабочие листы в PDF ({len(targets)} шт.):")
    for t in targets:
        render(t)
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
