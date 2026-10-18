"""Prepare and validate complete translations without changing code or math."""
from pathlib import Path
from bs4 import BeautifulSoup
from copy import deepcopy
import re,json,html,hashlib
ROOT=Path(__file__).resolve().parents[1]

def markdown_segments(slug):
    text=(ROOT/'content/posts'/slug/'index.md').read_text(encoding='utf-8')
    _,end=json.JSONDecoder().raw_decode(text)
    blocks=re.split(r'\n\s*\n',text[end:].strip())
    segments=[];fenced=False
    for i,block in enumerate(blocks):
        if '```' in block:
            if block.count('```')%2:fenced=not fenced
            continue
        if fenced or re.fullmatch(r'!\[[^\]]*\]\([^)]+\)',block):continue
        protected=[]
        def protect(m):
            protected.append(m[0]);return f'[[{len(protected)-1}]]'
        value=re.sub(r'<img\b[^>]*>|!\[[^\]]*\]\([^)]+\)',protect,block)
        if not re.search(r'[\u3400-\u9fff]',value):continue
        segments.append(dict(id=str(i),text=value,protected=protected))
    return blocks,segments

def paper_segments(slug):
    soup=BeautifulSoup((ROOT/'content/posts'/slug/'source.html').read_text(encoding='utf-8'),'html.parser')
    segments=[]
    for node in [*soup.select('p.ltx_p,h2,h3,h4,h5,h6,figcaption,td,th'),*soup.select('p.ltx_title_subsection,.ltx_keywords')]:
        if node.find_parent('math') or node.find_parent(class_='ltx_bibliography'):continue
        if node.name in ['td','th'] and node.select('p.ltx_p'):continue
        if node.name=='p' and node.find_parent(['td','th','figcaption']):
            if node.find_parent('figcaption'):continue
        if node.find_parent('table',class_='ltx_eqn_table'):continue
        if not re.search(r'[a-zA-Z]{3}',node.get_text()):continue
        identifier=node.get('id') or 'block-'+str(len(segments))
        clone=deepcopy(node);protected=[]
        for atom in list(clone.select('math,a,img,code,.ltx_tag')):
            if atom.parent is None or atom.find_parent(['math','a','code']):continue
            if 'ltx_tag' in atom.get('class',[]):
                for text in list(atom.find_all(string=True)):
                    text.replace_with(str(text).replace('Appendix','附录').replace('Figure','图').replace('Table','表'))
            protected.append(str(atom));atom.replace_with(f'[[{len(protected)-1}]]')
        value=clone.get_text(' ',strip=True);value=re.sub(r'\s+',' ',value)
        node['data-translation-id']=identifier
        segments.append(dict(id=identifier,text=value,protected=protected))
    return soup,segments

def write_markdown(source,target,mapping):
    blocks,segments=markdown_segments(source)
    assert set(mapping)=={s['id'] for s in segments}, f'{source}: incomplete translation coverage'
    for segment in segments:
        value=mapping[segment['id']]
        for i,original in enumerate(segment['protected']):
            assert value.count(f'[[{i}]]')==1,(source,segment['id'],i)
            value=value.replace(f'[[{i}]]',original)
        blocks[int(segment['id'])]=value
    body='\n\n'.join(blocks)+'\n'
    # Share the original figures, formulas and code examples between versions.
    body=body.replace('images/',f'../{source}/images/')
    body=re.sub(r'!\[原文图 (\d+)\]',r'![Original figure \1]',body)
    body=body.replace('alt="原文图 ','alt="Original figure ')
    return body

def write_paper(source,mapping):
    soup,segments=paper_segments(source)
    assert set(mapping)=={s['id'] for s in segments}, 'Incomplete paper translation coverage'
    for segment in segments:
        node=soup.find(attrs={'data-translation-id':segment['id']})
        ids=[child['id'] for child in node.select('[id]')]
        value=html.escape(mapping[segment['id']])
        for i,original in enumerate(segment['protected']):
            assert value.count(f'[[{i}]]')==1,(segment['id'],i)
            value=value.replace(f'[[{i}]]',original)
        node.clear()
        node.extend(BeautifulSoup(value,'html.parser').contents)
        existing={child['id'] for child in node.select('[id]')}
        for identifier in ids:
            if identifier not in existing:
                anchor=soup.new_tag('span',id=identifier);anchor['hidden']='';node.append(anchor)
        del node['data-translation-id']
    for image in soup.select('img[src]'):
        image['src']=image['src'].replace('images/',f'../{source}/images/')
    for heading in soup.select('.ltx_bibliography .ltx_title_bibliography'):
        heading.string='参考文献'
    return str(soup)

if __name__=='__main__':
    for slug in ['agenticrl','llm-barrage-interaction','llm-distillation-and-reasoning-compression','livethinking']:
        _,segments=paper_segments(slug) if slug=='livethinking' else markdown_segments(slug)
        destination=ROOT/'.preview'/f'{slug}-segments.json'
        destination.write_text(json.dumps(segments,ensure_ascii=False,indent=2),encoding='utf-8')
        print(slug,len(segments),sum(len(s['text']) for s in segments))
