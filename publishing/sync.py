"""Export selected Markdown and its referenced images; never mirror the source tree."""
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
STATS = Path('Statistics')
PAPERS = Path('References/公众号解读')
PRIVATE = re.compile(r'仅供私人|仅限私人|私人审读归档|仅供内部|不得公开|禁止公开|private[-_ ](?:only|study|reading)', re.I)
UNSAFE = re.compile(r'(?i)(?:\b(?:Daily|Projects)/|(?:/home/|/Users/|/mnt/|/Volumes/)|file://|obsidian://|<\s*(?:script|iframe|object|embed)\b|\{\{<|^```\{|BEGIN [A-Z ]*PRIVATE KEY)', re.M)
WIKI = re.compile(r'(!?)\[\[([^\]\n]+)\]\]')
IMAGE = re.compile(r'!\[([^\]\n]*)\]\(([^)\n]+)\)')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def load(path):
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def read_note(path):
    text = path.read_text(encoding='utf-8-sig')
    if text.startswith('---\n'):
        header, marker, text = text[4:].partition('\n---\n')
        if not marker:
            raise ValueError('Invalid note header')
        return yaml.safe_load(header) or {}, text.lstrip()
    return {}, text


def under(path, root):
    return path.resolve().is_relative_to(root.resolve())


def section_for(meta):
    if meta.get('book_part'):
        return meta['book_part']
    labels = ' '.join(str(meta.get(field, '')) for field in ('tags', 'title')).lower()
    for name, terms in [('reads', ('long-read','nanopore','转录本','读段','异构体')), ('atlas', ('spatial','single-cell','空间','单细胞')), ('genetics', ('qtl','gwas','人群遗传','疾病图谱'))]:
        if any(term in labels for term in terms):
            return name
    return None


def catalog(vault, sections):
    reviewed = {}
    for part, entries in load(ROOT/'publishing/selection.yml').items():
        for source, slug in entries:
            relative = Path(source) if source.startswith('Statistics/') else PAPERS/(source+'.md')
            reviewed[relative] = (part, slug)
    candidates = set()
    for area in [STATS, PAPERS]:
        root = vault/area
        if not root.is_dir() or not under(root, vault) or root.is_symlink():
            raise ValueError('Source checkout is incomplete')
        candidates.update(path.relative_to(vault) for path in root.rglob('*.md') if 'assets' not in path.relative_to(root).parts and path.stem not in {'index','README'})
    entries, slugs = [], set()
    for relative in [*reviewed, *sorted(candidates - reviewed.keys())]:
        if relative not in candidates:
            continue
        path = vault/relative
        if path.resolve() != path.absolute():
            raise ValueError('Symlink is not a publication source')
        if relative not in reviewed and not re.search(r'(?m)^book_publish:\s*true\s*$', path.read_text(encoding='utf-8-sig').split('\n---\n', 1)[0]):
            continue
        meta, body = read_note(path)
        if meta.get('book_publish') is False or meta.get('draft') is True or PRIVATE.search(str(meta.get('status',''))+'\n'+body):
            continue
        if relative in reviewed:
            part, slug = reviewed[relative]
        else:
            if meta.get('book_publish') is not True:
                continue
            part = 'methods' if relative.is_relative_to(STATS) else section_for(meta)
            slug = meta.get('book_slug') or path.stem
            if part not in sections or not SLUG.fullmatch(str(slug)):
                continue
        if part not in sections or not SLUG.fullmatch(slug) or slug in slugs:
            raise ValueError('Invalid or duplicate publication identifier')
        if UNSAFE.search(body):
            raise ValueError('Publication guard stopped a note; inspect the source privately')
        slugs.add(slug)
        entries.append((part, slug, path, meta, body))
    return entries


def export(vault, destination):
    sections = load(ROOT/'publishing/sections.yml')
    attachments = load(ROOT/'publishing/attachments.yml')
    entries = catalog(vault, sections)
    links = {path.stem: Path('chapters')/part/(slug+'.qmd') for part,slug,path,*_ in entries}
    config = load(ROOT/'publishing/base.yml')
    chapters = ['index.qmd']
    count = 0
    for part, part_title in sections.items():
        pages = []
        for entry_part, slug, path, meta, body in entries:
            if part != entry_part:
                continue
            target = links[path.stem]
            out = destination/target
            out.parent.mkdir(parents=True, exist_ok=True)
            figures = {}
            examples = {}
            approval = attachments.get(path.relative_to(vault).as_posix(), {})
            directory = approval.get('directory', path.stem)
            if Path(directory).name != directory or directory in {'', '.', '..'}:
                raise ValueError(f'Invalid attachment directory in {slug}')
            expected = path.parent/'assets'/directory

            def attachment(raw, allowed):
                raw = unquote(raw.strip().strip('<>'))
                source = path.parent/raw
                if Path(raw).is_absolute() or '..' in Path(raw).parts or source.resolve() != source.absolute() or not under(source,expected) or not source.is_file() or source.suffix.lower() not in allowed:
                    raise ValueError(f'Unapproved attachment reference in {slug}')
                name = source.relative_to(expected)
                if source.suffix.lower() in {'.svg','.py'} and hashlib.sha256(source.read_bytes()).hexdigest() != approval.get('files',{}).get(name.as_posix()):
                    raise ValueError(f'Attachment requires review in {slug}')
                rel = Path('assets')/slug/name
                dest = out.parent/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,dest)
                return rel

            def image(match):
                label, raw = match.groups()
                rel = attachment(raw,{'.png','.jpg','.jpeg','.webp','.svg'})
                figures[rel] = True
                return f'![{label}]({rel.as_posix()})'

            def example(match):
                label, raw = match.groups()
                rel = attachment(raw,{'.py'})
                anchor = slug+'-example-'+hashlib.sha256(rel.as_posix().encode()).hexdigest()[:8]
                examples[rel] = anchor
                return f'[{label}](#{anchor})'

            def wiki(match):
                embedded, value = match.groups()
                source, sep, alias = value.partition('|')
                note, _, anchor = source.partition('#')
                if embedded or note not in links:
                    raise ValueError(f'Unapproved internal reference in {slug}')
                ref = os.path.relpath(links[note], target.parent)
                return f'[{alias if sep else note}]({ref}'+(f'#{anchor}' if anchor else '')+')'

            body = WIKI.sub(wiki, IMAGE.sub(image,body))
            body = re.sub(r'(?<!!)\[([^\]\n]+)\]\((assets/[^()\n]+\.py)\)',example,body)
            def note_link(match):
                name, anchor = unquote(match[1]), match[2] or ''
                if name not in links:
                    raise ValueError(f'Unapproved linked note in {slug}')
                return ']('+os.path.relpath(links[name],target.parent)+anchor+')'

            body = re.sub(r'\]\(([^:/()#]+)\.md(#[^()]*)?\)',note_link,body)
            if '![' in re.sub(IMAGE, '', body) or re.search(r'<(?:img|a)\s[^>]*(?:href|src)\s*=',body,re.I):
                raise ValueError(f'Unresolved embed in {slug}')
            if re.search(r'\]\((?!(?:https?://|mailto:|#|[\w./-]+\.qmd(?:#|\))))',IMAGE.sub('',body)):
                raise ValueError(f'Unapproved local link in {slug}')
            heading = re.search(r'^# (.+)$', body, re.M)
            title = str(meta.get('title') or (heading[1] if heading else path.stem))
            if heading:
                body = body[:heading.start()]+body[heading.end():]
            if slug=='meta-template':
                title = '项目运行记录模板'
            if slug=='delong':
                title = 'DeLong 检验：比较相关 ROC 曲线的 AUC'
            if slug=='spatial-segmentation':
                body = re.sub(r'(?m)^(做空间转录组时[^\n]+)$', r'\1\n\n![同一组 RNA，两种细胞边界](../../boundaries.svg)\n\n编者示意｜两幅图里的点没有动。只把分界线向右移，十字标记的 RNA 就换了归属。非实验数据。', body, count=1)
            intro = ''
            if path.is_relative_to(vault/PAPERS):
                doi = str(meta.get('doi',''))
                if not re.fullmatch(r'10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+',doi):
                    raise ValueError(f'Missing or invalid DOI in {slug}')
                intro = f'::: {{.book-source}}\n论文：[DOI {doi}](https://doi.org/{doi})。原有图注和许可说明见正文；未明确许可的图版标记为**授权待确认**。\n:::\n\n'
            for rel, anchor in examples.items():
                program = (out.parent/rel).read_text(encoding='utf-8').rstrip()
                source_url = config['book']['repo-url']+'/blob/main/'+(target.parent/rel).as_posix()
                body += f'\n\n## 配套 Python 示例 {{#{anchor}}}\n\n[查看或下载 `{rel.name}`]({source_url})\n\n```python\n{program}\n```\n'
            out.write_text(f'# {title}\n\n'+intro+body.strip()+'\n',encoding='utf-8')
            pages.append(target.as_posix())
            count += len(figures)
        if pages:
            chapters.append({'part':part_title,'chapters':pages})
    config['book']['chapters'] = [*chapters,'rights.qmd']
    (destination/'_quarto.yml').write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
    print(f'Publication: {len(entries)} chapters; {count} referenced images.')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(dir=ROOT) as scratch:
        stage = Path(scratch)
        export(Path(sys.argv[1]).resolve(),stage)
        shutil.rmtree(ROOT/'chapters',ignore_errors=True)
        if (stage/'chapters').exists():
            shutil.move(stage/'chapters',ROOT/'chapters')
        (stage/'_quarto.yml').replace(ROOT/'_quarto.yml')
