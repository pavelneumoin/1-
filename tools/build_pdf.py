#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка презентаций курса «Программирование на 1С:Элемент» из Markdown в PDF.

Слайды разделены строкой `---` (как в Marp). Поддерживаются директивы в начале
слайда:
    <!-- class: quiz -->     тип слайда (quiz/tip/warn/fun/section/...)
    <!-- kicker: ВЫВОД -->   текст метки-рубрики сверху

Блоки кода размечаются языком в ограждении:
    ```eos   — код на 1С:Элемент (с подсветкой синтаксиса), рисуется как редактор
    ```out   — вывод программы, рисуется как терминал
    ```txt   — обычная моноширинная вставка

Рендер в PDF через WeasyPrint — без браузера.

Использование:
    python3 tools/build_pdf.py                 # собрать все уроки
    python3 tools/build_pdf.py путь/к/файлу.md # один файл
"""

import sys
import re
import glob
import os
import html

import markdown
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, "theme.css")
BRAND = "1С:Элемент · курс с нуля"

# Цветные эмодзи в PDF рендерятся плохо — заменяем чёткими символами.
EMOJI_MAP = {
    "⭐": "★", "✅": "✓", "❌": "✗", "🎉": "★", "✨": "★",
    "🔧": "•", "📝": "•", "🚀": "★", "🎯": "●", "💡": "★",
    "⚡": "★", "🔥": "★", "🎮": "●", "🍕": "●", "🐱": "●",
    "👀": "●", "🏆": "★", "🤔": "?", "👉": "→", "➡": "→",
}

# Ключевые слова и встроенные имена 1С:Элемент для подсветки.
KEYWORDS = ("пер|знч|метод|возврат|если|иначеесли|иначе|тогда|пока|"
            "для|каждого|из|по|цикл|и|или|не|истина|ложь|"
            "Истина|Ложь|попытка|исключение|прервать|продолжить")
TYPES = "Строка|Число|Булево|Массив|Соответствие|Множество"
BUILTINS = ("Консоль|Записать|СчитатьСтроку|СчитатьЧисло|Скрипт|"
            "Цел|Добавить|Количество|Сообщить")

TOKEN_RE = re.compile(
    r"(?P<comment>//[^\n]*)"
    r"|(?P<string>\"[^\"]*\")"
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<kw>\b(?:" + KEYWORDS + r")\b)"
    r"|(?P<type>\b(?:" + TYPES + r")\b)"
    r"|(?P<builtin>\b(?:" + BUILTINS + r")\b)"
)


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def replace_emoji(text: str) -> str:
    for k, v in EMOJI_MAP.items():
        text = text.replace(k, v)
    return text


def highlight_eos(code: str) -> str:
    """Подсветка синтаксиса 1С:Элемент: возвращает HTML с span-токенами."""
    out, pos = [], 0
    for m in TOKEN_RE.finditer(code):
        if m.start() > pos:
            out.append(esc(code[pos:m.start()]))
        kind, text = m.lastgroup, m.group()
        if kind == "string":
            inner = esc(text)
            inner = re.sub(r"\$\w+",
                           lambda x: f'<span class="t-var">{x.group()}</span>',
                           inner)
            out.append(f'<span class="t-str">{inner}</span>')
        else:
            out.append(f'<span class="t-{kind}">{esc(text)}</span>')
        pos = m.end()
    out.append(esc(code[pos:]))
    return "".join(out)


def code_figure(lang: str, code: str) -> str:
    """Сгенерировать HTML для блока кода/вывода.

    ```eos — редактор с подсветкой синтаксиса;
    ```out — терминал;
    остальное (в т. ч. без языка) — нейтральная тёмная плашка.
    """
    code = code.strip("\n")
    if lang == "out":
        return (f'<figure class="term"><figcaption class="term-bar">'
                f'Консоль</figcaption><pre><code>{esc(code)}</code></pre></figure>')
    if lang == "eos":
        return (f'<figure class="editor"><figcaption class="editor-bar">'
                f'<span class="dot r"></span><span class="dot y"></span>'
                f'<span class="dot g"></span><span class="fname">скрипт.1с</span>'
                f'</figcaption><pre><code>{highlight_eos(code)}</code></pre></figure>')
    # по умолчанию — простая тёмная плашка без хрома и подсветки
    return (f'<figure class="editor plain"><pre><code>{esc(code)}'
            f'</code></pre></figure>')


FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
DIRECTIVE_RE = re.compile(r"<!--\s*(class|kicker)\s*:\s*(.*?)\s*-->")


def render_slide_html(md, slide_md):
    """Вернуть (css_class, kicker, html) для одного слайда."""
    cls, kicker = "content", None
    for m in DIRECTIVE_RE.finditer(slide_md):
        if m.group(1) == "class":
            cls = m.group(2).strip()
        else:
            kicker = m.group(2).strip()
    slide_md = DIRECTIVE_RE.sub("", slide_md).strip()

    # вынуть блоки кода, заменить плейсхолдерами
    blocks = []
    def stash(m):
        blocks.append(code_figure(m.group(1), m.group(2)))
        return f"\n\n@@CODE{len(blocks)-1}@@\n\n"
    body = FENCE_RE.sub(stash, replace_emoji(slide_md))

    md.reset()
    inner = md.convert(body)
    inner = inner.replace("✓", '<span style="color:#16a37b;font-weight:800">✓</span>')
    inner = inner.replace("✗", '<span style="color:#ff5f56;font-weight:800">✗</span>')

    for i, b in enumerate(blocks):
        inner = inner.replace(f"<p>@@CODE{i}@@</p>", b).replace(f"@@CODE{i}@@", b)

    return cls, kicker, inner


def auto_class(cls, inner, index):
    if index == 0 and cls == "content":
        return "title"
    if cls == "content":
        low = inner.lower()
        if "что мы узнали" in low or "что мы сделали" in low:
            return "summary"
    return cls


def render(md_path: str):
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    body = strip_front_matter(raw)
    slides = split_slides(body)

    md = markdown.Markdown(extensions=["fenced_code", "tables", "sane_lists"])
    total = len(slides)
    sections = []
    for i, slide_md in enumerate(slides):
        cls, kicker, inner = render_slide_html(md, slide_md)
        cls = auto_class(cls, inner, i)
        kick = f'<div class="kicker">{esc(kicker)}</div>' if kicker else ""
        sections.append(
            f'<section class="slide {cls}">{kick}{inner}'
            f'<div class="foot"><span class="brand">{BRAND}</span>'
            f'<span class="pageno">{i + 1} / {total}</span></div></section>'
        )

    doc = ("<!doctype html><html lang='ru'><head><meta charset='utf-8'></head>"
           "<body>" + "".join(sections) + "</body></html>")
    out_path = os.path.splitext(md_path)[0] + ".pdf"
    HTML(string=doc, base_url=HERE).write_pdf(out_path, stylesheets=[THEME])
    print(f"  ✓ {out_path}  ({total} слайдов)")
    return out_path


def strip_front_matter(text: str):
    if text.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        if m:
            return text[m.end():]
    return text


def split_slides(text: str):
    parts = re.split(r"^\s*---\s*$", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def main(argv):
    targets = argv or sorted(glob.glob(os.path.join(
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
