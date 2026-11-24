"""Apply the shared reading edition after Quarto has resolved links, figures and math."""
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile

from lxml import etree, html


SITE = Path(__file__).resolve().parents[1] / '_book'
CAPTION = re.compile(r'^(?:编者示意｜|(?:图示|示意图|导读示意|概念示意|封面|上半部导读)[｜：为]|(?:图|表|补图|补表)\s*[\d一二三四五六七八九]+(?:局部.?|[a-zA-Z–-]+)?[｜：]|Ren 图\s*\d+：|AI\s*辅助.{0,12}(?:示意|图像))')
PREFIX = re.compile(r'^\s*(?:(?:[0-9]{1,2}(?:\.(?=\s)|[．、｜])|\d{1,2}(?:\.\d{1,2})+\s+|[一二三四五六七八九十]+、)\s*)+')


def text(node):
    return ''.join(node.itertext()).strip()


def element(parent, tag, content=None, **attrs):
    namespace = etree.QName(parent).namespace
    node = etree.SubElement(parent, f'{{{namespace}}}{tag}' if namespace else tag, attrs)
    node.text = content
    return node


def local(node):
    return etree.QName(node).localname if isinstance(node.tag,str) else ''


def descendants(node, tag):
    return node.xpath(f'.//*[local-name()="{tag}"]')


def has(node, cls):
    return cls in node.get('class','').split()


def copy_link(parent, href, label, **attrs):
    return element(parent,'a',label,href=href,**attrs)


def figures(article, web):
    for figure in descendants(article,'figure'):
        images = descendants(figure,'img')
        if not images:
            continue
        caption = next(iter(descendants(figure,'figcaption')),None)
        wrapper = figure.getparent() if has(figure.getparent(),'quarto-figure') else figure
        following = wrapper.getnext()
        if following is not None and local(following)=='p' and CAPTION.match(text(following)):
            if caption is None:
                caption = element(figure,'figcaption')
            caption.append(following)
        if web:
            for image in images:
                if not image.get('alt') and caption is not None:
                    image.set('alt',(caption.text or '').strip())
                if local(image.getparent())!='a':
                    previous = image.getparent()
                    link = copy_link(previous,image.get('src'),None,**{'aria-label':'查看原图：'+(image.get('alt') or '图版')})
                    previous.replace(image,link)
                    link.append(image)


def editorial(article, web):
    figures(article,web)
    notes = next((child for child in article if has(child,'book-source')),None)
    sections = [child for child in article if local(child)=='section' and has(child,'level2')]
    if notes is None or not sections:
        return
    first = sections[0]
    beginning = list(article)[article.index(notes):article.index(first)]
    credit = element(article,'p',**{'class':'credit'})
    credit.text = '原论文 · '
    if '细胞分割榜单，为什么会换冠军' in text(article) or any('boundaries.svg' in image.get('src','') for image in descendants(first,'img')):
        credit.text = '原论文：Martínez-de-Morentin、Khan 等 · Nature Methods · '
    doi = next(iter(descendants(notes,'a')),None)
    if doi is not None:
        credit.append(deepcopy(doi))
    article.insert(article.index(first),credit)
    first_paragraph = next((node for node in descendants(first,'p') if local(node.getparent())=='section' and len(text(node))>18 and not CAPTION.match(text(node)) and not descendants(node,'img')),None)
    if first_paragraph is not None:
        following = first_paragraph.getnext()
        lead = element(article,'div',**{'class':'lead'})
        first.addprevious(lead)
        lead.append(first_paragraph)
        if following is not None and any('boundaries.svg' in image.get('src','') for image in descendants(following,'img')):
            following.set('class',following.get('class','')+' opening')
            first.addprevious(following)
        elif following is not None and any('同一组 RNA，两种细胞边界' in image.get('alt','') for image in descendants(following,'img')):
            first.addprevious(following)
    source = element(article,'section',id='reading-sources',**{'class':'sources'})
    element(source,'h2','来源与核验记录')
    container = source
    if web:
        container = element(source,'details')
        element(container,'summary','展开原文出处、核验范围与归档图版')
    for node in beginning:
        container.append(node)


def headings(article):
    seq = 0
    for heading in article.xpath('.//*[local-name()="h2" or local-name()="h3" or local-name()="h4" or local-name()="h5"]'):
        counter = next((child for child in heading if has(child,'header-section-number')),None)
        if counter is not None:
            suffix = counter.tail or ''
            heading.remove(counter)
            heading.text = (heading.text or '')+suffix
        if heading.text:
            heading.text = PREFIX.sub('',heading.text)
        if local(heading)=='h2' and counter is not None:
            seq += 1
            label = element(heading,'small',f'{seq:02}',**{'class':'reader-heading-number'})
            label.tail, heading.text = heading.text, None
            heading.insert(0,label)
        parent = heading.getparent()
        if local(heading)=='h3' and local(parent.getparent())=='section':
            upper = next((child for child in parent.getparent() if local(child)=='h2'),None)
            if upper is not None and text(upper).removeprefix(f'{seq:02}').strip()==text(heading):
                heading.set('class',heading.get('class','')+' unlisted-heading')


def book_navigation(sidebar):
    nav = html.Element('nav', {'class':'book-nav','aria-label':'全书目录'})
    current_part = ''
    for group in sidebar.xpath('.//li[contains(@class,"sidebar-item-section")]'):
        title = text(group.xpath('./div/a[1]')[0]); items = group.xpath('./ul/li/div/a[@href]')
        current = any(has(item,'active') for item in items)
        details = element(nav,'details',**({'open':'open'} if current else {}))
        if current:
            current_part = title
        element(details,'summary',title)
        links = element(details,'div')
        for item in items:
            number = item.find('.//span[@class="chapter-number"]')
            label = item.find('.//span[@class="chapter-title"]')
            link = copy_link(links,item.get('href'),None,**({'aria-current':'page'} if has(item,'active') else {}))
            if number is not None:
                element(link,'small',text(number).zfill(2))
            element(link,'span',text(label if label is not None else item))
    return nav,current_part


def web_page(path):
    tree = html.document_fromstring(path.read_bytes(),parser=html.HTMLParser(encoding='utf-8'))
    body = tree.find('body')
    if body is None or has(body,'reader'):
        return
    mains = body.xpath('.//main[@id="quarto-document-content"]')
    if not mains:
        return
    main = mains[0]; sidebar = tree.get_element_by_id('quarto-sidebar')
    nav,part = book_navigation(sidebar)
    root = os.path.relpath(SITE,path.parent)+'/'
    scripts = body.xpath('.//script[not(ancestor::main)]')
    titleblock = main.find('header'); title = titleblock.find('.//h1')
    number = title.find('span[@class="chapter-number"]')
    chapter_no = text(number) if number is not None else ''
    if number is not None:
        title.remove(number)
    page_nav = body.xpath('.//nav[contains(@class,"page-navigation")]')
    for child in list(body):
        body.remove(child)
    body.set('class','reader quarto-light'); body.set('id','start')
    opts = tree.get_element_by_id('quarto-search-options'); config = json.loads(opts.text); config['type']='overlay'; opts.text=json.dumps(config,ensure_ascii=False)
    for script in tree.xpath('//head/script[contains(@src,"quarto-nav/")]'):
        script.getparent().remove(script)
    element(body,'div',id='quarto-search-results'); copy_link(body,'#quarto-document-content','跳到正文',**{'class':'skip'})
    mast = element(element(body,'header',**{'class':'mast'}),'div',**{'class':'wrap'})
    brand = copy_link(mast,root+'index.html',None,**{'class':'brand'}); element(brand,'img',src=root+'mark.svg',alt='',width='26',height='26').tail='生物信息学手记'
    element(mast,'span','FIELDNOTES',**{'class':'proof-label'})
    actions = element(mast,'div',**{'class':'mast-actions'}); element(actions,'div',id='quarto-search',hidden='hidden'); element(actions,'button','搜索',type='button',onclick='window.quartoOpenSearch()'); copy_link(actions,root+'bioinfo-book.epub','下载 EPUB')
    spread = element(body,'div',**{'class':'wrap spread'}); rail = element(element(spread,'div',role='complementary',**{'class':'rail'}),'div',**{'class':'rail-inner'})
    element(rail,'div','全书目录',**{'class':'overline'}); rail.append(nav); copy_link(rail,root+'rights.html','图版与授权',**{'class':'home'})
    spread.append(main); main.set('class','reader-main'); main.set('tabindex','-1')
    article = html.Element('article'); titleblock.addnext(article)
    for node in list(main)[main.index(article)+1:]:
        article.append(node)
    editorial(article,True); headings(article)
    for table in list(article.iter('table')):
        if local(table.getparent()) in ('div','section','article') and not has(table.getparent(),'table-responsive'):
            scroll = html.Element('div',{'class':'table-scroll'}); table.addprevious(scroll); scroll.append(table)
    tools = html.Element('div',{'class':'tools'}); main.insert(0,tools)
    element(tools,'span',(f'第 {chapter_no} 章　/　'+part if chapter_no else 'BIOINFORMATICS　/　FIELDNOTES'),**{'class':'folio'})
    menu = element(tools,'details',**{'class':'menu'}); summary=element(menu,'summary'); element(summary,'span','本章',**{'class':'desktop'}).tail='目录'
    pop = element(menu,'div',**{'class':'reader-menu'}); element(pop,'div','本章目录',**{'class':'overline'}); toc = element(pop,'nav',**{'class':'sections','aria-label':'本章目录'})
    for pos,section in enumerate(article.xpath('.//section[@id][h2]'),1):
        heading = section.find('h2'); counter = heading.find('small'); label = text(heading)
        if counter is not None:
            label = label.removeprefix(text(counter)).strip()
        copy_link(toc,'#'+section.get('id'),label)
        if path.stem=='spatial-segmentation' and has(section,'level2'):
            section.insert(0,html.Element('span',id=f'section-{pos}'))
    if not len(toc):
        copy_link(toc,'#start','章首')
    mobile = element(pop,'div',**{'class':'mobile'}); element(mobile,'div','全书目录',**{'class':'overline'}); mobile.append(deepcopy(nav))
    titleblock.clear(); titleblock.set('id','title-block-header'); titleblock.append(title)
    if path==SITE/'index.html':
        element(titleblock,'p','Yuelong Chen',**{'class':'credit'})
        shortcuts = html.Element('nav',{'class':'home-links','aria-label':'按篇阅读'})
        for group in nav:
            first = group.find('.//a')
            if first is not None:
                copy_link(shortcuts,first.get('href'),text(group.find('summary'))+' →')
        intro = article.xpath('.//*[contains(concat(" ",@class," ")," field-cover ")]')
        if intro:
            intro[0].addnext(shortcuts)
    foot = element(main,'footer')
    if page_nav:
        foot.append(page_nav[0])
    for script in scripts:
        body.append(script)
    element(body,'script').text="const readerMenu=document.querySelector('.menu');document.addEventListener('click',e=>{if(!readerMenu.contains(e.target)||e.target.closest('.menu a'))readerMenu.open=false});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&readerMenu.open){readerMenu.open=false;readerMenu.querySelector('summary').focus()}});"
    path.write_bytes(html.tostring(tree,encoding='utf-8',doctype='<!DOCTYPE html>'))


def epub(path):
    with ZipFile(path) as old, NamedTemporaryFile(dir=path.parent,delete=False) as pending:
        with ZipFile(pending,'w') as new:
            for file in old.infolist():
                data = old.read(file)
                if file.filename.startswith('EPUB/text/') and file.filename.endswith('.xhtml'):
                    page = etree.fromstring(data)
                    for article in page.xpath('//*[local-name()="section" and contains(concat(" ",@class," ")," level1 ")]'):
                        if article.get('data-reading-edition'):
                            continue
                        editorial(article,False); headings(article); article.set('data-reading-edition','1')
                    data = etree.tostring(page,encoding='utf-8',xml_declaration=True,doctype='<!DOCTYPE html>')
                new.writestr(file,data)
    os.replace(pending.name,path)


if __name__=='__main__':
    for page in [SITE/'index.html',SITE/'rights.html',*sorted((SITE/'chapters').rglob('*.html'))]:
        if page.exists():
            web_page(page)
    if (SITE/'bioinfo-book.epub').exists():
        epub(SITE/'bioinfo-book.epub')
    legacy = SITE/'preview/spatial-segmentation/index.html'; legacy.parent.mkdir(parents=True,exist_ok=True)
    target = '../../chapters/atlas/spatial-segmentation.html' if (SITE/'chapters/atlas/spatial-segmentation.html').exists() else '../../index.html'
    legacy.write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={target}"><title>前往正式版</title><a href="{target}">进入正式版</a><script>location.replace("{target}"+location.hash)</script></html>')
