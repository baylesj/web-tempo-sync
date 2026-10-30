#!/usr/bin/env python3
"""Render this repo's Markdown docs (explainer, objections, questionnaire) as pages next to the built spec.

Run by .github/workflows/pages.yml (needs the `markdown` package):
    render-md.py <source dir> <output dir> <site name> <demos URL> <file.md>...
The site name is unused; it's kept so the arguments match unraid-config's scripts/spec-render-md.py, which
this is a copy of, restyled from the bayl.es home-server look to the project's own.
Links between the docs (foo.md, index.bs) are rewritten to the published pages (foo.html, ./).

Each page gets a navbar across the docs, links on its headings, a contents list when it's long,
and its code highlighted here, server-side, in the same house colours and token kinds as the
tempo demo's js/highlight.js (js, webidl, sh), so a page looks the same standalone and inside
the demo's read tabs, which lift its <article>.
"""

import html
import re
import sys
from pathlib import Path

import markdown

STYLE = "https://cdn.jsdelivr.net/gh/baylesj/bayl.es-style@v1.12.2"

# Navbar order and labels; docs not listed come after, labelled by file name.
DOC_ORDER = ["explainer", "OBJECTIONS", "security-privacy-questionnaire", "slides"]
DOC_LABEL = {"OBJECTIONS": "objections", "security-privacy-questionnaire": "privacy"}
# A contents list once a page has this many sections.
TOC_MIN_SECTIONS = 5

PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link rel="icon" type="image/svg+xml" href="{style}/icons/home.svg" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400..700;1,400&family=Atkinson+Hyperlegible+Mono:wght@400..600&display=swap" />
    <script src="{style}/js/theme.js"></script>
    <link rel="stylesheet" href="base.css" />
    <style>
      /* The project's look, as on the demos: base.css (a W3C/GitHub look in Atkinson Hyperlegible, copied from
         web-tempo-sync-demo's css/base.css), and a line naming what this is above the title. */
      .top a.mark {{ color: var(--ink); text-decoration: none; }}
      .kicker {{ display: block; color: var(--soft); font: 600 13px var(--sans); letter-spacing: 0.04em;
                 text-transform: uppercase; }}
      /* Three words, so on a phone it shrinks a little and the theme toggle stays beside it. */
      @media (width <= 480px) {{ .top {{ flex-wrap: nowrap; gap: 12px; }} .top .mark {{ font-size: clamp(26px, 8vw, 32px); }} }}

      /* Navbar: the spec and its docs, the current one underlined, and the way back to the demos. */
      .docnav {{ display: flex; flex-wrap: wrap; gap: 0 2px; margin: 0 0 28px; border-bottom: 1px solid var(--line); }}
      .docnav a {{ padding: 8px 9px 9px; border-bottom: 2px solid transparent; color: var(--soft);
                   font: 500 14px var(--sans); text-decoration: none; }}
      .docnav a:hover {{ color: var(--ink); }}
      .docnav a[aria-current] {{ border-bottom-color: var(--sig-fill); color: var(--ink); }}
      .docnav .home {{ margin-left: auto; }}

      article {{ max-width: 46rem; }}
      article p, article ul, article ol, article table, article pre, article blockquote {{ margin: 0 0 14px; }}
      article h1 {{ font-size: 32px; line-height: 1.2; margin: 0 0 18px; }}
      article h2 {{ font-size: 22px; margin: 38px 0 10px; }}
      article h3 {{ font-size: 18px; margin: 28px 0 8px; }}
      article h4 {{ font-size: 16px; margin: 22px 0 6px; }}
      article li + li {{ margin-top: 4px; }}
      article li > ul, article li > ol {{ margin: 4px 0 0; }}
      article blockquote {{ padding-left: 14px; border-left: 3px solid var(--line); color: var(--soft); }}
      article hr {{ margin: 28px 0; border: 0; border-top: 1px solid var(--line); }}
      article img {{ display: block; max-width: 100%; border: 1px solid var(--line); border-radius: 8px; }}
      article :not(pre) > code {{ padding: 1px 5px; border-radius: 4px; background: var(--field);
                                  border: 1px solid var(--line); font-size: 0.85em; }}

      /* Heading links: a # that shows on hover, for linking to a section. */
      article .anchor {{ margin-left: 8px; color: var(--comment); text-decoration: none; opacity: 0;
                         transition: opacity 0.15s; }}
      article :is(h2, h3, h4):hover .anchor, article .anchor:focus-visible {{ opacity: 1; }}

      /* Contents, for the long pages. */
      article nav.toc {{ margin: 0 0 24px; padding: 12px 16px; border: 1px solid var(--line); border-radius: 8px; }}
      article nav.toc b {{ display: block; margin: 0 0 6px; color: var(--soft); font: 600 12px var(--sans);
                           letter-spacing: 0.06em; text-transform: uppercase; }}
      article nav.toc ul {{ margin: 0; padding-left: 18px; }}
      article nav.toc li + li {{ margin-top: 2px; }}

      article table {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
      article th, article td {{ padding: 6px 10px; border-bottom: 1px solid var(--line); text-align: left;
                                vertical-align: top; }}
      article th {{ color: var(--soft); font-weight: 600; }}
      article .table-wrap {{ overflow-x: auto; }}

      /* Code blocks, as on the demo: highlighted in the house palette, with a copy button. */
      article pre.code-snippet {{ position: relative; padding: 14px 16px; border: 1px solid var(--line);
                                  border-radius: 8px; background: var(--field); overflow-x: auto;
                                  font: 14px/1.6 var(--mono); color: var(--ink); tab-size: 2; }}
      article pre code {{ font-size: inherit; }}
      .tok-keyword {{ color: var(--purple); }}
      .tok-string {{ color: var(--green); }}
      .tok-number {{ color: var(--orange); }}
      .tok-function {{ color: var(--teal); }}
      .tok-type {{ color: var(--amber-text); }}
      .tok-property {{ color: var(--ink); }}
      .tok-comment {{ color: var(--comment); font-style: italic; }}
      .tok-punct {{ color: var(--soft); }}
      .copy-btn {{ position: absolute; top: 8px; right: 8px; min-height: 0; padding: 2px 10px; font: 12px var(--mono);
                   opacity: 0; transition: opacity 0.15s; }}
      pre:hover .copy-btn, .copy-btn:focus-visible {{ opacity: 1; }}
      @media (hover: none) {{ .copy-btn {{ opacity: 1; }} }}
    </style>
  </head>
  <body>
    <main>
      <header class="top">
        <div>
          <span class="kicker">Draft proposal for the W3C Audio Community Group</span>
          <a class="mark" href="{landing}">web tempo sync</a>
        </div>
        <button class="theme-toggle" type="button"></button>
      </header>
      <nav class="docnav" aria-label="Documents">
{nav}
      </nav>
      <article>
{body}
      </article>
      <footer>
        <span><a href="{landing}">demos</a> · <a href="./">spec</a> · <a href="https://github.com/baylesj/web-tempo-sync">source</a></span>
        <span><a href="https://style.bayl.es">bayl.es-style</a></span>
      </footer>
    </main>
    <script>
      // Copy buttons on code blocks (added here, so pages that lift the article add their own).
      if (navigator.clipboard) {{
        for (const pre of document.querySelectorAll("article pre.code-snippet")) {{
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "quiet copy-btn";
          btn.textContent = "copy";
          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText(pre.querySelector("code").textContent);
              btn.textContent = "copied";
            }} catch {{
              btn.textContent = "couldn't copy";
            }}
            setTimeout(() => (btn.textContent = "copy"), 1500);
          }});
          pre.append(btn);
        }}
      }}
    </script>
  </body>
</html>
"""

# --- Highlighting: a port of the demo's js/highlight.js, token for token. ---

KEYWORDS = {
    "js": {
        "async",
        "await",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "default",
        "do",
        "else",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "function",
        "if",
        "import",
        "in",
        "instanceof",
        "let",
        "new",
        "null",
        "of",
        "return",
        "static",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "typeof",
        "undefined",
        "var",
        "void",
        "while",
        "yield",
    },
    "webidl": {
        "attribute",
        "boolean",
        "callback",
        "const",
        "dictionary",
        "double",
        "enum",
        "false",
        "getter",
        "inherit",
        "interface",
        "long",
        "mixin",
        "null",
        "optional",
        "partial",
        "readonly",
        "required",
        "sequence",
        "setter",
        "short",
        "static",
        "stringifier",
        "true",
        "typedef",
        "undefined",
        "unsigned",
        "void",
    },
    "sh": set(),
}
LANGS = {
    "js": "js",
    "javascript": "js",
    "ts": "js",
    "typescript": "js",
    "json": "js",
    "webidl": "webidl",
    "idl": "webidl",
    "sh": "sh",
    "bash": "sh",
    "shell": "sh",
    "console": "sh",
    "zsh": "sh",
}

REST = (
    r"(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\b\d[\d_]*(?:\.\d+)?\b)|([A-Za-z_$][\w$]*)"
    r"|(--?[\w-]+(?:=[^\s\\]+)?)|([\s\S])"
)
COMMENT = {"sh": r"#[^\n]*", "js": r"//[^\n]*|/\*[\s\S]*?\*/"}


def tokenize(source, lang):
    keywords = KEYWORDS.get(lang, KEYWORDS["js"])
    token = re.compile(f"({COMMENT['sh'] if lang == 'sh' else COMMENT['js']})|{REST}")
    out, pos, line_start = [], 0, True
    while pos < len(source):
        # Shell: the command at the start of a line is one token, path and all.
        if lang == "sh" and line_start:
            cmd = re.match(r"[^\s\\#\"'-][^\s]*", source[pos:])
            if cmd:
                out.append((cmd.group(0), "function"))
                pos += len(cmd.group(0))
                line_start = False
                continue
        m = token.match(source, pos)
        if not m:
            break
        text, comment, string, number, word, flag = m.group(0), *m.groups()[:5]
        kind = None
        if comment is not None:
            kind = "comment"
        elif string is not None:
            kind = "string"
        elif number is not None:
            kind = "number"
        elif word is not None and lang == "sh":
            kind = None  # shell arguments are plain
        elif word is not None:
            nxt = re.match(r"\s*(.)", source[m.end() :])
            if word in keywords:
                kind = "keyword"
            elif nxt and nxt.group(1) == "(":
                kind = "function"
            elif word[0].isupper():
                kind = "type"
            elif pos > 0 and source[pos - 1] == ".":
                kind = "property"
        elif flag is not None and lang == "sh":
            kind = "keyword"
        elif re.fullmatch(r"[{}()\[\];,.<>=+*/&|!?:-]", text):
            kind = "punct"
        out.append((text, kind))
        if text == "\n":
            line_start = True
        elif not text.isspace() and text != "\\":
            line_start = False
        pos = m.end()
    return out


def highlight_block(match):
    lang = LANGS.get((match.group(1) or "").lower())
    source = html.unescape(match.group(2))
    if not lang:
        return f'<pre class="code-snippet"><code>{html.escape(source, quote=False)}</code></pre>'
    spans = "".join(
        f'<span class="tok-{kind}">{html.escape(text, quote=False)}</span>' if kind else html.escape(text, quote=False)
        for text, kind in tokenize(source, lang)
    )
    return f'<pre class="code-snippet"><code data-lang="{lang}">{spans}</code></pre>'


def highlight(body):
    return re.sub(r'<pre><code(?: class="language-([\w+-]+)")?>(.*?)</code></pre>', highlight_block, body, flags=re.S)


# --- Pages ---


def nav_html(docs, current, landing):
    items = [("./", "spec")] + [(f"{stem}.html", DOC_LABEL.get(stem, stem.lower())) for stem in docs]
    links = [
        f'        <a href="{href}"{' aria-current="page"' if href == f"{current}.html" else ""}>{label}</a>'
        for href, label in items
    ]
    links.append(f'        <a class="home" href="{landing}">demos ↗</a>')
    return "\n".join(links)


LIST_ITEM = re.compile(r"^ {0,3}(?:[*+-]|\d+[.)])\s")


def loosen_lists(text):
    """Start a list that follows a paragraph without a blank line, as GitHub does.

    Python-Markdown only starts a list after a blank line, so "This feature exposes:" followed
    directly by "* ..." lines rendered as one paragraph with literal asterisks.
    """
    out, prev, fence = [], "", False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and LIST_ITEM.match(line) and prev.strip() and not LIST_ITEM.match(prev) and prev[:1] not in " \t":
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def render(text):
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists", "toc", "footnotes", "attr_list", "def_list"],
        extension_configs={
            "toc": {
                "permalink": "#",
                "permalink_class": "anchor",
                "permalink_title": "Link to this section",
                "toc_depth": "2",
            },
        },
    )
    body = md.convert(loosen_lists(text))
    body = highlight(body)
    body = re.sub(r"<table>(.*?)</table>", r'<div class="table-wrap"><table>\1</table></div>', body, flags=re.S)
    sections = len(re.findall(r"^##\s", text, re.M))
    if sections >= TOC_MIN_SECTIONS and md.toc_tokens:
        entries = "".join(
            f'<li><a href="#{t["id"]}">{t["name"]}</a></li>'
            for top in md.toc_tokens
            for t in (top.get("children") or [top])
            if t["level"] == 2
        )
        toc = f'<nav class="toc" aria-label="Contents"><b>Contents</b><ul>{entries}</ul></nav>'
        # After the title and its opening paragraphs: before the first section heading.
        body = re.sub(r"(<h2[ >])", toc + r"\1", body, count=1)
    return body


def main(src, out, site, landing, *files):
    src, out = Path(src), Path(out)
    stems = [Path(f).stem for f in files if (src / f).exists()]
    docs = sorted(stems, key=lambda s: (DOC_ORDER.index(s) if s in DOC_ORDER else len(DOC_ORDER), s.lower()))
    for stem in docs:
        path = src / f"{stem}.md"
        text = path.read_text()
        title = next((m.group(1).strip() for m in re.finditer(r"^#\s+(.+)$", text, re.M)), stem)
        # Links to the other docs point at their published pages.
        text = re.sub(
            r"\]\((?:\./)?([\w.-]+)\.md(#[^)]*)?\)", lambda m: f"]({m.group(1)}.html{m.group(2) or ''})", text
        )
        text = re.sub(r"\]\((?:\./)?index\.bs(#[^)]*)?\)", lambda m: f"](./{m.group(1) or ''})", text)
        page = PAGE.format(
            title=html.escape(title),
            style=STYLE,
            site=site,
            landing=landing,
            nav=nav_html(docs, stem, landing),
            body=render(text),
        )
        (out / f"{stem}.html").write_text(page)
        print(f"rendered {stem}.md -> {stem}.html")


if __name__ == "__main__":
    if len(sys.argv) < 6:
        sys.exit(__doc__)
    main(*sys.argv[1:])
