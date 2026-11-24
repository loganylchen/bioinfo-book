"""Typeset one comparison page from the published chapter, outside the book and EPUB."""
import html
import re
import shutil
import subprocess
from pathlib import Path
from string import Template


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SITE = ROOT / '_book'
SLUG = 'spatial-segmentation'
SOURCE = ROOT / f'chapters/atlas/{SLUG}.qmd'
ORIGINAL = f'../../chapters/atlas/{SLUG}.html'
OUT = SITE / 'preview' / SLUG
IMAGE = re.compile(r'!\[([^\]]+)\]\((assets/[\w./-]+)\)')
CAPTION = re.compile(r'^(?:图示|[图表补][^｜\n]{0,14})｜')


def nav(compiled):
    groups = []
    current = None
    for anchor in re.finditer(r'<a\b([^>]*\bsidebar-item-text\b[^>]*)>\s*<span class="menu-text">(.*?)</a>', compiled, re.S):
        attributes, inner = anchor.groups()
        text = html.unescape(re.sub('<[^>]+>', '', inner)).strip()
        if 'data-bs-target=' in attributes:
            groups.append((text, []))
            continue
        link = re.search(r'href="(\.\./\.\./chapters/[^"<>]+\.html)"', attributes)
        if not link or not groups:
            continue
        number, title = text.split(maxsplit=1)
        groups[-1][1].append((number, title, link[1]))
        if link[1] == ORIGINAL:
            current = (groups[-1][0], number, title)
    if not current:
        raise ValueError('Chapter missing from book navigation')
    pieces = []
    for part, items in groups:
        links = ''.join(f'<a href="{url if url != ORIGINAL else "#start"}"'+(' aria-current="page"' if url == ORIGINAL else '')+f'><small>{number.zfill(2)}</small><span>{html.escape(title)}</span></a>' for number, title, url in items)
        pieces.append('<details'+(' open' if part == current[0] else '')+f'><summary>{html.escape(part)}</summary><div>{links}</div></details>')
    return current, ''.join(pieces)


def markdown(blocks):
    return subprocess.run(['quarto','pandoc','-f','markdown+autolink_bare_uris','-t','html5','--wrap=none'],input='\n\n'.join(blocks),text=True,capture_output=True,check=True).stdout


def typeset(blocks):
    output = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        image = IMAGE.fullmatch(block)
        if image:
            label, src = image.groups()
            src = '../../chapters/atlas/'+src
            label = html.escape(label)
            caption = ''
            if index+1 < len(blocks) and CAPTION.match(blocks[index+1]):
                index += 1
                caption = markdown([blocks[index]]).strip()
            output.append(f'<figure class="plate"><a href="{src}" aria-label="查看原图：{label}"><img src="{src}" alt="{label}" loading="lazy"></a><figcaption><strong>{label}</strong>{caption}</figcaption></figure>')
        else:
            output.append(block)
        index += 1
    return output


def build():
    if not SOURCE.exists():
        if OUT.exists():
            shutil.rmtree(OUT)
        return
    compiled = (SITE / 'chapters' / 'atlas' / f'{SLUG}.html').read_text()
    (part, number, title), book_nav = nav(compiled)
    source = re.split(r'\n\s*\n',SOURCE.read_text().strip())
    first_section = next(index for index, block in enumerate(source) if block.startswith('## '))
    records = source[1:first_section]
    opener = source[first_section+1]
    if opener.startswith(('#', '!', ':::')):
        raise ValueError('Opening is not a paragraph; check the reading proof against the chapter')
    body, toc = [], []
    previous = ''
    for block in [source[first_section], *source[first_section+2:]]:
        if block.startswith('## '):
            heading = re.sub(r'^##\s+(?:\d+[.．、]\s*)?', '', block)
            seq = len(toc)+1
            toc.append(f'<a href="#section-{seq}"><small>{seq:02}</small>{html.escape(heading)}</a>')
            body.append(f'<h2 id="section-{seq}"><small>{seq:02}</small>{html.escape(heading)}</h2>')
            previous = heading
        elif block != '### '+previous:
            body.append(block)
    proof = Template((HERE/'page.html.in').read_text()).substitute(
        part=html.escape(part), number=number, title=html.escape(title), book_nav=book_nav,
        original=ORIGINAL, lead=markdown([opener]), article=markdown(typeset(body)),
        toc=''.join(toc), records=markdown(typeset(records)),
    )
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'index.html').write_text(proof)
    for name in ['reading.css','boundaries.svg']:
        shutil.copyfile(HERE/name, OUT/name)


if __name__ == '__main__':
    build()
