#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка презентаций курса «Программирование на 1С:Элемент» из Markdown в PDF.

Берёт файлы prezentaciya.md (формат Marp: слайды разделены строкой ---),
превращает каждый слайд в красивую страницу и собирает PDF через WeasyPrint —
без браузера.

Использование:
    python3 tools/build_pdf.py                       # собрать все уроки
    python3 tools/build_pdf.py uroki/urok-01-.../prezentaciya.md   # один файл

PDF кладётся рядом с исходным .md (файл prezentaciya.pdf).
"""

import sys
import re
import glob
import os

import markdown
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, "theme.css")
BRAND = "1С:Элемент · курс с нуля"

# Цветные эмодзи в PDF (WeasyPrint) рендерятся плохо. Заменяем их на
# чёткие символьные глифы из DejaVu Sans перед версткой.
EMOJI_MAP = {
    "⭐": "★",
    "✅": "✓",
    "❌": "✗",
    "🎉": "★",
    "✨": "★",
    "🔧": "•",
    "📝": "•",
    "🚀": "★",
}


def replace_emoji(text: str) -> str:
    for k, v in EMOJI_MAP.items():
        text = text.replace(k, v)
    return text


def colorize_marks(html: str) -> str:
    """Покрасить галочку/крестик в зелёный/красный."""
    html = html.replace(
        "✓", '<span style="color:#27ae60;font-weight:800">✓</span>')
    html = html.replace(
        "✗", '<span style="color:#e74c3c;font-weight:800">✗</span>')
    return html


def strip_front_matter(text: str):
    """Убрать YAML-преамбулу Marp (--- ... ---) в начале файла."""
    if text.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        if m:
            return text[m.end():]
    return text


def split_slides(text: str):
    """Разбить на слайды по строкам, состоящим только из ---."""
    parts = re.split(r"^\s*---\s*$", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def classify(html: str, index: int, total: int) -> str:
    """Подобрать css-класс слайду: титул / итог / обычный контент."""
    if index == 0:
        return "title"
    low = html.lower()
    if "что мы узнали" in low or "что мы сделали" in low:
        return "summary"
    return "content"


def render(md_path: str):
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    body = strip_front_matter(raw)
    slides = split_slides(body)

    md = markdown.Markdown(extensions=["fenced_code", "tables", "sane_lists"])

    sections = []
    total = len(slides)
    for i, slide_md in enumerate(slides):
        md.reset()
        inner = md.convert(replace_emoji(slide_md))
        inner = colorize_marks(inner)
        cls = classify(inner, i, total)
        sections.append(
            f'<section class="slide {cls}">'
            f'{inner}'
            f'<div class="brand">{BRAND}</div>'
            f'<div class="pageno">{i + 1} / {total}</div>'
            f'</section>'
        )

    html_doc = (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'></head>"
        "<body>" + "".join(sections) + "</body></html>"
    )

    out_path = os.path.splitext(md_path)[0] + ".pdf"
    HTML(string=html_doc, base_url=HERE).write_pdf(out_path, stylesheets=[THEME])
    print(f"  ✓ {out_path}  ({total} слайдов)")
    return out_path


def main(argv):
    if argv:
        targets = argv
    else:
        targets = sorted(glob.glob(os.path.join(
            os.path.dirname(HERE), "uroki", "*", "prezentaciya.md")))

    if not targets:
        print("Не найдено ни одной презентации.")
        return 1

    print(f"Собираю презентации в PDF ({len(targets)} шт.):")
    for t in targets:
        render(t)
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
