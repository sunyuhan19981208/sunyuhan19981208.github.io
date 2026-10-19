"""Build the edited bilingual blog editions; retain full publication sources."""
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from copy import deepcopy
import json,re,math,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
PATTERN=re.compile(r'<!-- (image|figure):([^: ]+):([^|]+?)\s*\|\s*(.*?) -->')

def main():
    entries={}
    for source in sorted((ROOT/'editorial/posts').glob('*.md')):
        slug=source.stem;raw=source.read_text(encoding='utf-8');meta,end=json.JSONDecoder().raw_decode(raw)
        text=raw[end:].strip();english=slug.endswith('-en') or slug in ['livethinking','harness-aware-training']
        count=0
        def illustration(match):
            nonlocal count
            count+=1;kind,origin,key,caption=match.groups();key=key.strip()
            origin_page=ROOT/'content/posts'/origin
            if kind=='figure':
                original=BeautifulSoup((origin_page/'body.html').read_text(encoding='utf-8'),'html.parser').find(id=key)
                assert original and 'publication-figure' in original.get('class',[]),(slug,key)
                figure=deepcopy(original)
                figure.find('figcaption').string=caption
                for img in figure.select('img[src]'):
                    if img['src'].startswith('images/'):img['src']=f'../{origin}/'+img['src']
                    img['alt']=caption
            else:
                path=origin_page/key;assert path.exists(),path
                width,height=Image.open(path).size
                soup=BeautifulSoup('<figure class="publication-figure"><div class="figure-heading"><span class="figure-label"></span><button type="button" class="figure-expand"></button></div><div class="figure-media"><img loading="lazy" decoding="async"></div><figcaption class="publication-caption"></figcaption></figure>','html.parser')
                figure=soup.figure;figure['id']=f'blog-figure-{count}'
                figure['class'].append('figure-landscape' if width>700 else 'figure-natural')
                image=figure.img;image['src']=f'../{origin}/{key}';image['width']=str(width);image['height']=str(height);image['alt']=caption
                figure.figcaption.string=caption
            number=f'Figure {count}' if english else f'图 {count}'
            figure.select_one('.figure-label').string=number
            button=figure.select_one('.figure-expand');button.string='View figure ↗' if english else '查看大图 ↗';button['aria-label']=f'Enlarge {number}' if english else f'放大查看：{number}'
            return str(figure)
        rendered=PATTERN.sub(illustration,text)
        assert '<!-- image:' not in rendered and '<!-- figure:' not in rendered
        page=ROOT/'content/posts'/slug;assert (page/'index.md').exists(),slug
        (page/'blog.md').write_text(rendered+'\n',encoding='utf-8')
        visible=BeautifulSoup(PATTERN.sub('',text),'html.parser')
        for formula in visible.select('svg, script, style'):
            formula.decompose()
        plain=visible.get_text(' ',strip=True)
        meta['minutes']=max(3,math.ceil(len(re.findall(r'[\u4e00-\u9fff]',plain))/450+len(re.findall(r'\b[a-zA-Z]+\b',plain))/220))
        meta['figures']=count;entries[slug]=meta
    assert len(entries)==10,'Expected ten edited language editions'
    (ROOT/'data/editorial.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared 10 edited blog editions; full sources remain unchanged.')

if __name__=='__main__':main()
