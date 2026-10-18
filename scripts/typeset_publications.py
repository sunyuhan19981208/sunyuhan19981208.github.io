"""Turn the two paper imports into publication-quality, static blog HTML.

Authoring only: Python (bs4, Pillow) and mathjax-full@3.2.2 in
.tools/math-authoring. Hugo and the reader's browser need no math runtime.
Run after importing/editing either paper's source.html. Idempotent.
"""
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from PIL import Image
from copy import deepcopy
import json, re, subprocess, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ['livethinking', 'harness-aware-training', 'livethinking-cn']

# Mathematical content is unchanged; only line breaks and alignment are authored.
TEX_LAYOUTS = {
    ('harness-aware-training', 'S3.E4'): r'''\begin{aligned}
\hat{A}_{i}^{g}&=\sum_{d\in\mathcal{D}_{g}}\hat{A}_{i}^{(d)}-\lambda\hat{A}^{(\mathrm{CoT},g)}_{i},\\[5pt]
\hat{A}_{i}^{g,\star}&=\frac{\hat{A}_{i}^{g}-\mu^{g}}{\sigma^{g}}.
\end{aligned}''',
    ('harness-aware-training', 'S3.E5'): r'''\begin{aligned}
\mathcal{L}&=-\frac{1}{|\mathcal{G}|G}\sum_g\sum_i\min\!\Bigl(\rho_i(\theta)\,\hat{A}^{g,\star}_i,\\
&\hspace{3em}\mathrm{clip}(\rho_i(\theta),1{\pm}\varepsilon)\,\hat{A}^{g,\star}_i\Bigr),\\[8pt]
\rho_i(\theta)&=\left(\frac{\pi_\theta(y_i\mid x)}{\pi_{\theta_{\mathrm{old}}}(y_i\mid x)}\right)^{\!\frac{1}{|y_i|}},\\[6pt]
&=\exp\!\left(\frac{1}{|y_i|}\sum_{t=1}^{|y_i|}\log\frac{\pi_\theta(y_{i,t}\mid x,y_{i,<t})}{\pi_{\theta_{\mathrm{old}}}(y_{i,t}\mid x,y_{i,<t})}\right).
\end{aligned}''',
    ('livethinking', 'S4.EGx3'): r'''\begin{aligned}
\mathcal{L}^{\mathrm{GRPO}}(\theta)&=\frac{1}{K}\sum_{j=1}^{K}\Bigg[\min\Bigg(\frac{\pi_\theta(a_j|s_j)}{\pi_{\theta_{\mathrm{old}}}(a_j|s_j)}A_j,\\[5pt]
&\quad\mathrm{clip}\!\left(\frac{\pi_\theta(a_j|s_j)}{\pi_{\theta_{\mathrm{old}}}(a_j|s_j)},1-\eta,1+\eta\right)A_j\Bigg)\\[5pt]
&\quad-\beta D_{\text{KL}}\!\left(\pi_{\theta_{\mathrm{old}}}\|\pi_\theta\right)\Bigg].
\end{aligned}''',
}

def set_classes(tag, *values):
    tag['class'] = list(dict.fromkeys(tag.get('class', []) + list(values)))

def remove_styles(parent):
    for node in parent.find_all(True):
        node.attrs.pop('style', None)

def size_image(img, page):
    path = page / img['src']
    if path.suffix == '.svg':
        root = ET.parse(path).getroot()
        box = root.attrib.get('viewBox', '').split()
        if len(box) == 4: width, height = float(box[2]), float(box[3])
        else:
            width = float(re.match(r'[\d.]+', root.attrib['width'])[0])
            height = float(re.match(r'[\d.]+', root.attrib['height'])[0])
    else:
        width, height = Image.open(path).size
    img['width'], img['height'] = str(round(width)), str(round(height))
    return width, height

def preserve_anchors(soup, old, target):
    existing = {node.get('id') for node in target.find_all(id=True)} | {target.get('id')}
    for node in old.find_all(id=True):
        if node['id'] not in existing:
            anchor = soup.new_tag('span', id=node['id'])
            anchor['class'] = ['equation-anchor']
            anchor['aria-hidden'] = 'true'
            target.append(anchor)
            existing.add(node['id'])

def align_rows(rows):
    if len(rows) == 1 and len(rows[0]) == 1:
        return rows[0][0]
    chunks=[]
    for row in rows:
        if len(row) == 1: chunks.append('&'+row[0])
        else: chunks.append(row[0]+'&'+''.join(row[1:]))
    return '\\begin{aligned}\n'+'\\\\[6pt]\n'.join(chunks)+'\n\\end{aligned}'

def prepare(slug, jobs):
    page = ROOT/'content/posts'/slug
    source = page/'source.html'
    if not source.exists():source.write_bytes((page/'body.html').read_bytes())
    soup=BeautifulSoup(source.read_text(encoding='utf-8'),'html.parser')
    body=soup.select_one('article')
    set_classes(body,'publication-body')
    for heading in body.select('p.ltx_title_subsection'):
        heading.name='h3'
    original_math_count=len(body.select('math'))
    original_ids={node['id'] for node in body.find_all(id=True)}
    counter=0
    def math_placeholder(tex,display,identifier=None,spoken=None):
        nonlocal counter
        counter+=1
        key=f'{slug}:{counter:04d}'
        tag=soup.new_tag('div' if display else 'span')
        tag['class']=['math-display' if display else 'math-inline']
        tag['data-typeset-key']=key
        tag['data-tex']=tex
        tag['role']='math'
        tag['aria-label']=spoken or tex
        if identifier:tag['id']=identifier
        jobs.append({'key':key,'tex':tex,'display':display})
        return tag

    # Rebuild three small diagrams authored as absolute-positioned foreignObject SVG.
    # Move their actual content into responsive HTML instead of inheriting PDF geometry.
    for diagram in list(body.select('svg.ltx_picture')):
        paragraphs=diagram.select('.ltx_p')
        if not paragraphs:continue
        panel=soup.new_tag('aside',id=diagram.get('id'))
        panel['class']=['concept-panel']
        label=soup.new_tag('div');label['class']=['concept-label']
        label.string=paragraphs[0].get_text(' ',strip=True)
        panel.append(label)
        if 'trajectory' in label.text.lower():
            code=soup.new_tag('pre');inner=soup.new_tag('code')
            text=paragraphs[-1].get_text('',strip=False).strip()
            text=re.sub(r'\s+(?=(?:input\.danmaku|context\.current_link_id|call\[|result\[|reply\s*=))','\n',text)
            inner.string=text;code.append(inner);panel.append(code)
        else:
            content=soup.new_tag('div');content['class']=['concept-content']
            if 'Loop' in label.text:content['class'].append('concept-flow')
            for paragraph in paragraphs[1:]:
                for node in list(paragraph.contents):content.append(node.extract())
            remove_styles(content);panel.append(content)
        preserve_anchors(soup,diagram,panel)
        diagram.replace_with(panel)

    # Replace PDF-style equation tables with real equation blocks; preserve every anchor.
    equation_blocks=0
    for table in list(body.select('table.ltx_eqn_table')):
        table_id=table.get('id','')
        rows=[];numbers=[]
        for row in table.select('tr'):
            cells=row.find_all('td',recursive=False)
            equations=[''.join(m.get('alttext','') for m in cell.select('math')) for cell in cells if cell.select('math')]
            number=' '.join(cell.get_text(' ',strip=True) for cell in cells if 'ltx_eqn_eqno' in cell.get('class',[])).strip()
            if equations:rows.append(equations);numbers.append(number)
        container=soup.new_tag('div',id=table_id)
        container['class']=['equation-group']
        groups=[([row],number) for row,number in zip(rows,numbers)] if sum(bool(n) for n in numbers)>1 else [(rows,next((n for n in numbers if n),''))]
        for group_rows,number in groups:
            block=soup.new_tag('div');block['class']=['equation-block']
            formula=math_placeholder(TEX_LAYOUTS.get((slug.removesuffix('-cn'),table_id),align_rows(group_rows)),True)
            scroll=soup.new_tag('div');scroll['class']=['equation-formula'];scroll['tabindex']='0'
            scroll['aria-label']='Mathematical expression';scroll.append(formula);block.append(scroll)
            if number:
                tag=soup.new_tag('span');tag['class']=['equation-number'];tag.string=number;block.append(tag)
            container.append(block);equation_blocks+=1
        preserve_anchors(soup,table,container)
        table.replace_with(container)

    # Every remaining formula is inline (including the original captions and tables).
    for math in list(body.select('math')):
        placeholder=math_placeholder(math['alttext'],math.get('display')=='block',math.get('id'),math.get_text(' ',strip=True))
        math.replace_with(placeholder)

    for img in body.select('img'):
        size_image(img,page)

    figures=body.select('figure.ltx_figure')
    for figure in figures:
        set_classes(figure,'publication-figure')
        caption=figure.find('figcaption',recursive=False)
        caption_label=caption.select_one('.ltx_tag_figure') if caption else None
        number=caption_label.get_text(' ',strip=True).rstrip('.: ') if caption_label else 'Figure'
        if caption_label:caption_label.decompose()
        if caption:
            set_classes(caption,'publication-caption')
            for img in caption.select('img'):
                set_classes(img,'figure-key-icon')
                img['alt']='AI response indicator'
        header=soup.new_tag('div');header['class']=['figure-heading']
        label=soup.new_tag('span');label['class']=['figure-label'];label.string=number
        button=soup.new_tag('button',type='button');button['class']=['figure-expand']
        button['aria-label']=f'放大查看：{number}' if slug.endswith('-cn') else f'Enlarge {number}'
        button.string='查看大图 ↗' if slug.endswith('-cn') else 'View figure ↗'
        header.append(label);header.append(button)
        media=soup.new_tag('div');media['class']=['figure-media']
        for node in list(figure.contents):
            if node is not caption:media.append(node.extract())
        primary=media.select_one('img')
        if primary:
            ratio=float(primary['width'])/float(primary['height'])
            if ratio<0.85:set_classes(figure,'figure-portrait')
            else:set_classes(figure,'figure-landscape')
            if ratio>2:set_classes(figure,'figure-wide')
            caption_text=caption.get_text(' ',strip=True) if caption else number
            primary['alt']=caption_text.split('. ')[0][:220]
            primary['loading']='lazy';primary['decoding']='async'
        figure.insert(0,media);figure.insert(0,header)

    tables=body.select('figure.ltx_table')
    for figure in tables:
        set_classes(figure,'publication-table')
        caption=figure.find('figcaption')
        if caption:set_classes(caption,'table-caption')
        for table in figure.select('table'):
            table['class']=list(dict.fromkeys(table.get('class',[])+['publication-data']))
            for cell in table.select('td,th'):
                text=cell.get_text(' ',strip=True)
                if re.fullmatch(r'[+−\-–]?\s*\d[\d\s.,%/×+−\-–]*',text):set_classes(cell,'numeric-cell')

    # The blog omits HAT's publisher logos; retain the source anchor for links.
    if slug == 'harness-aware-training':
        logos = body.select_one('.ltx_para#p2')
        if logos and logos.select('img') and not logos.get_text(strip=True):
            logos.clear()
            logos['hidden'] = ''
        team_line = body.select_one('.ltx_para#p3')
        if team_line and team_line.get_text(' ', strip=True) == 'TaoLive AIGC LLM Team':
            team_source = deepcopy(team_line)
            team_line.clear()
            preserve_anchors(soup, team_source, team_line)
            team_line['hidden'] = ''

    # Other affiliation marks are never treated as content figures.
    for para in body.select('.ltx_para'):
        if not para.find_parent('figure') and para.select('img') and not para.get_text(strip=True):
            set_classes(para,'publication-affiliations')
    for para in body.select('.ltx_para'):
        if para.get_text(' ',strip=True).lstrip('*∗ ').strip()=='Equal contribution':
            set_classes(para,'contribution-note')

    missing=original_ids-{node['id'] for node in body.find_all(id=True)}
    if missing:raise ValueError(f'{slug}: lost source anchors {missing}')
    return soup,{'slug':slug,'source_math':original_math_count,'typeset_units':counter,'equation_blocks':equation_blocks,'figures':len(figures),'tables':len(tables),'responsive_diagrams':len(body.select('.concept-panel'))}

def main():
    jobs=[];documents=[];reports=[]
    for slug in SLUGS:
        soup,report=prepare(slug,jobs);documents.append((slug,soup));reports.append(report)
    inputs=ROOT/'.tools/math-input.json';outputs=ROOT/'.tools/math-output.json'
    inputs.write_text(json.dumps(jobs,ensure_ascii=False),encoding='utf-8')
    subprocess.run(['node',str(ROOT/'scripts/render_math.cjs'),str(inputs),str(outputs)],check=True)
    rendered=json.loads(outputs.read_text(encoding='utf-8'))
    for slug,soup in documents:
        for placeholder in soup.select('[data-typeset-key]'):
            markup=BeautifulSoup(rendered[placeholder['data-typeset-key']],'html.parser')
            # Preserve SVG's XML attribute casing through the HTML parser.
            for svg in markup.select('svg'):
                if svg.has_attr('viewbox'):svg['viewBox']=svg.attrs.pop('viewbox')
                svg['aria-hidden']='true';svg['focusable']='false'
            placeholder.attrs.pop('data-typeset-key')
            for node in list(markup.contents):placeholder.append(node.extract())
            semantic=soup.new_tag('span')
            semantic['class']=['math-source-text'];semantic['aria-hidden']='true'
            semantic.string=placeholder['aria-label']
            placeholder.append(semantic)
        (ROOT/'content/posts'/slug/'body.html').write_text(str(soup),encoding='utf-8')
    audit=ROOT/'.preview/publication-audit.json';audit.parent.mkdir(exist_ok=True)
    audit.write_text(json.dumps(reports,indent=2),encoding='utf-8')
    print(json.dumps(reports,indent=2))
    if (ROOT/'editorial/posts').exists():
        from build_editorial import main as build_editorial
        build_editorial()

if __name__=='__main__':main()
