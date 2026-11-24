"""Check the self-contained Pages artifact and ebook before deployment."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile
from lxml import etree, html

site = Path('_book').resolve()
errors = []


class Links(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.page = page

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag not in {'a','img','script','link','source'}:
            return
        url = urlsplit(attrs.get('src') or attrs.get('href') or '')
        if url.scheme or url.netloc or not url.path:
            return
        target = unquote(url.path)
        path = ((site/target.removeprefix('/bioinfo-book/')) if target.startswith('/bioinfo-book/') else (self.page.parent/target)).resolve()
        if not path.is_relative_to(site) or not path.exists():
            errors.append((self.page.relative_to(site),url.path))


for required in ['index.html','rights.html','search.json','bioinfo-book.epub']:
    if not (site/required).is_file():
        raise SystemExit('Missing '+required)
for page in sorted(site.rglob('*.html')):
    Links(page).feed(page.read_text(encoding='utf-8'))
chapters = [site / source.with_suffix('.html') for source in Path('chapters').rglob('*.qmd')]
for page in [site/'index.html', site/'rights.html', *chapters]:
    tree = html.parse(page)
    if not tree.xpath('//body[@class="reader quarto-light"]//main/article') or not tree.xpath('//*[@id="quarto-search-options"]'):
        raise SystemExit(f'Missing reading layout or search in {page}')
    if page in chapters and len(tree.xpath('//div[@class="rail"]//a[@aria-current="page"]'))!=1:
        raise SystemExit(f'Missing current chapter in {page}')
if errors:
    raise SystemExit(f'Unresolved site links: {errors[:8]}')
with ZipFile(site/'bioinfo-book.epub') as ebook:
    if ebook.read('mimetype')!=b'application/epub+zip' or ebook.testzip():
        raise SystemExit('Invalid EPUB archive')
    xhtml = [etree.fromstring(ebook.read(name)) for name in ebook.namelist() if name.startswith('EPUB/text/') and name.endswith('.xhtml')]
    if sum(len(doc.xpath('//*[@data-reading-edition]')) for doc in xhtml)<len(chapters):
        raise SystemExit('Missing reading edition in EPUB chapters')
print('Checked site links, images, search and EPUB archive.')
