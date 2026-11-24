"""Check the self-contained Pages artifact and ebook before deployment."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile

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
if errors:
    raise SystemExit(f'Unresolved site links: {errors[:8]}')
with ZipFile(site/'bioinfo-book.epub') as ebook:
    if ebook.read('mimetype')!=b'application/epub+zip' or ebook.testzip():
        raise SystemExit('Invalid EPUB archive')
print('Checked site links, images, search and EPUB archive.')
