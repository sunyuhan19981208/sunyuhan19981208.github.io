"""Dependency-free static-site checks, also run by GitHub Actions."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json, sys, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'public'
class Page(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.images=[]; self.h1=0; self.ids=[]; self.canonicals=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='h1':self.h1+=1
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='img' and attrs.get('src'):self.images.append(attrs['src'])
        if tag=='link' and attrs.get('rel')=='canonical':self.canonicals.append(attrs['href'])

errors=[]
entries=json.loads((PUBLIC/'index.json').read_text(encoding='utf-8'))
works=json.loads((ROOT/'data/works.json').read_text(encoding='utf-8'))
expected_slugs=[slug for work in works for slug in work['versions']]
if len(set(expected_slugs))!=len(expected_slugs):errors.append('Duplicate editions in works.json')
if len({work['id'] for work in works})!=len(works):errors.append('Duplicate work IDs')
if len(entries)!=len(expected_slugs):errors.append(f'Expected {len(expected_slugs)} language editions, got {len(entries)}')
for work in works:
    editions=[entry for entry in entries if entry.get('workId')==work['id']]
    if len(editions)!=2 or {entry.get('language') for entry in editions}!={'zh-CN','en'}:
        errors.append(f'{work["id"]}: expected one Chinese and one English edition')
# Discover the base path used by project Pages (for example /blog/).
root_page=Page();root_page.feed((PUBLIC/'index.html').read_text(encoding='utf-8'))
prefix=''
if root_page.canonicals:prefix=urlsplit(root_page.canonicals[0]).path.rstrip('/')
pages=list(PUBLIC.rglob('*.html'))
cache={}
def parse(path):
    key=path.resolve()
    if key not in cache:
        parsed=Page();parsed.feed(key.read_text(encoding='utf-8'));cache[key]=parsed
    return cache[key]
for file in pages:
    page=parse(file)
    if file.name=='body.html':continue # A source resource, not a standalone page.
    if page.h1!=1:errors.append(f'{file.relative_to(PUBLIC)}: expected one h1, got {page.h1}')
    for value in page.links+page.images:
        link=urlsplit(value)
        if link.scheme or link.netloc:continue
        if not link.path:
            if link.fragment and unquote(link.fragment) not in page.ids:errors.append(f'{file.relative_to(PUBLIC)}: missing fragment {value}')
            continue
        path=unquote(link.path)
        if path.startswith('/'):
            if prefix and (path==prefix or path.startswith(prefix+'/')):path=path[len(prefix):]
            target=PUBLIC/path.lstrip('/')
        else:target=file.parent/path
        if target.is_dir():target=target/'index.html'
        if not target.exists():errors.append(f'{file.relative_to(PUBLIC)}: missing {value}')
        elif link.fragment and target.suffix=='.html' and unquote(link.fragment) not in parse(target).ids:errors.append(f'{file.relative_to(PUBLIC)}: missing fragment {value}')
for entry in entries:
    if len(entry['content'])<700:errors.append(f'Missing blog body: {entry["title"]}')
ET.parse(PUBLIC/'index.xml')
ET.parse(PUBLIC/'sitemap.xml')
rss=ET.parse(PUBLIC/'index.xml')
if len(rss.findall('./channel/item'))!=len(works):errors.append(f'RSS should contain {len(works)} works rather than duplicate editions')
# Language switching must be reciprocal, and every version needs its original citation.
for work in works:
    for slug in work['versions']:
        path=PUBLIC/'posts'/slug/'index.html'
        if not path.exists():errors.append(f'Missing edition: {slug}');continue
        other=next(value for value in work['versions'] if value!=slug)
        parsed=parse(path)
        if not any(urlsplit(link).path.rstrip('/').endswith('/posts/'+other) for link in parsed.links):errors.append(f'{slug}: missing language switch')
        if 'cite' not in parsed.ids:errors.append(f'{slug}: missing original citation')
if errors:
    print('\n'.join(errors[:50]));print(f'{len(errors)} errors');sys.exit(1)
print(f'PASS: {len(works)} bilingual works, {len(entries)} full-text editions; {len(pages)} HTML files; language switches; local images and links; RSS and sitemap.')
