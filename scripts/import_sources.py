"""Import the author's six original publications. Cached inputs live in .tools/.

Run with Python 3 and: pip install beautifulsoup4 requests markdownify
Source HTML is never shipped; only the article body and downloaded figures are kept.
"""
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from markdownify import MarkdownConverter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, timedelta
import hashlib, json, re, requests

ROOT = Path(__file__).resolve().parents[1]
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'}
POSTS = [
 dict(slug='llm-barrage-interaction', file='extra-2.html', url='https://mp.weixin.qq.com/s/93Nk6lpRpTqUaD-U8OAeEQ', title='淘宝直播数字人：LLM弹幕互动技术', shortTitle='LLM 弹幕互动', language='zh-CN', kind='技术实践', tags=['LLM','RAG','Digital Avatar'], description='从多轮意图识别、实体解析到商品检索与回复生成，构建数字人直播的实时互动链路。', lead='让每一条弹幕，都成为一次有上下文的对话。', flow=['观众弹幕','多轮意图识别','实体解析与检索','回复与口播'], highlights=[['理解上下文','结合当前讲品、历史对话与观众弹幕，识别多轮对话中的真实意图。'],['连接商品知识','按意图解析商品、属性和链接号，为回复提供对应的检索信息。'],['走向自然互动','区分文本与口播通道，在模型训练中兼顾事实、语境与表达方式。']]),
 dict(slug='llm-distillation-and-reasoning-compression', file='distillation-original.html', url='https://mp.weixin.qq.com/s/pnn6jyudY7iv426hyO-WIw', title='淘宝直播数字人LLM推理优化：模型蒸馏与路径压缩实践', shortTitle='模型蒸馏与路径压缩', language='zh-CN', kind='技术实践', tags=['LLM','Distillation','Efficient Reasoning'], description='围绕数字人互动中的推理延迟，探索模型蒸馏、轻量化与推理路径压缩的质量和效率权衡。', lead='把推理能力带进直播间，也把等待时间降下来。', flow=['教师推理轨迹','领域能力蒸馏','推理路径压缩','低延迟互动'], highlights=[['先迁移能力','通过领域推理数据训练学生模型，评估模型规模与业务能力的关系。'],['再压缩路径','围绕冗长推理探索不同优化方法，使回复速度适应实时场景。'],['同时关注质量','结合正确性与帮助性评价，分析推理效率和回答质量的取舍。']]),
 dict(slug='livethinking', file='source-6.html', url='https://arxiv.org/abs/2510.07685', title='LiveThinking: Enabling Real-Time Efficient Reasoning for AI-Powered Livestreaming via Reinforcement Learning', shortTitle='LiveThinking', language='en', kind='Research paper', date='2025-10-09', tags=['Reinforcement Learning','Distillation','Efficient Reasoning'], description='A two-stage framework that combines reasoning distillation and reinforcement learning for real-time digital-avatar interactions.', lead='Reason well. Respond in real time.', flow=['Teacher trajectories','RFT distillation','GRPO compression','Live interaction'], authors='Yuhan Sun · Zhiwei Huang · Wanqing Cui · Shaopan Xiong · Yazhi Guo · Meiguang Jin · Junfeng Ma', pdf='https://arxiv.org/pdf/2510.07685', arxiv='2510.07685', version='v1', highlights=[['Transfer the capability','Rejection Sampling Fine-Tuning transfers e-commerce reasoning from a large teacher into a compact MoE student.'],['Shorten the reasoning','GRPO jointly rewards correctness, helpfulness and concise reasoning instead of optimizing length alone.'],['Validate in production','Offline evaluation and a Taobao Live deployment connect reasoning efficiency with real viewer interactions.']]),
 dict(slug='agenticrl', file='agenticrl-original.html', url='https://mp.weixin.qq.com/s/7A3QbSMM6gxG9d1LpYDIPQ', title='淘宝直播数字人 AgenticRL 实践：从 RLVR 到 MultiAgent RL', shortTitle='从 RLVR 到 MultiAgent RL', language='zh-CN', kind='技术实践', tags=['Reinforcement Learning','Agents','Multi-Agent'], description='从静态 Workflow 升级到 Agentic 架构，探索工具调用与回复模型的多智能体协同强化学习。', lead='从固定的工作流，走向会规划、会调用工具的数字人。', flow=['动态上下文','Agent 工具调用','多智能体协同训练','自然且可靠的回复'], highlights=[['架构升级','以按需工具调用与全局上下文感知，替代固定的意图识别和检索链路。'],['可靠且低延迟','结合 AgentTuning 与 RLVR，改善模型的响应延迟和事实可靠性。'],['分工后协同优化','将工具调用与最终回复解耦，为不同能力设计奖励并进行协同训练。']]),
 dict(slug='harness-aware-training', file='source-7.html', url='https://arxiv.org/pdf/2608.15763', title='Training Agents to Evolve with Their Harness: TaoLive Digital Avatar Agent Technical Report', shortTitle='Harness-Aware Training', language='en', kind='Technical report', date='2026-08-16', updated='2026-10-04', tags=['Agents','Harness','Reinforcement Learning'], description='Harness-Aware Training teaches compact agents to adapt as Skills, Hooks, prompts and tools evolve.', lead='An evolving harness needs a model that can evolve with it.', flow=['Harness-state augmentation','HSA-SFT','General OPD','HSA-RL'], authors='TaoLive AIGC LLM Team', pdf='https://arxiv.org/pdf/2608.15763', arxiv='2608.15763', version='v5', companion='harness-aware-training-cn', highlights=[['Make change trainable','Harness-State Augmentation exposes the policy to task-preserving changes in Skills, tools, prompts and Hooks.'],['Train in three stages','HSA-SFT, General On-Policy Distillation and HSA-RL combine task learning, generalization recovery and interactive learning.'],['Evaluate adaptation','The report examines task quality, harness variants, general instruction following and deployment performance.']]),
 dict(slug='harness-aware-training-cn', file='extra-1.html', url='https://mp.weixin.qq.com/s/ajL2P5PY1HcQnJt_RFalnw', title='淘宝直播数字人互动 Harness-Aware Training 实践：让 Agent Model 随 Harness 一起进化', shortTitle='让 Agent 随 Harness 一起进化', language='zh-CN', kind='技术报告 · 中文解读', tags=['Agents','Harness','Reinforcement Learning'], description='将变化的 Harness 显式纳入训练分布，让低延迟模型适应 Skills、Hooks、工具和提示词的持续迭代。', lead='业务规则持续变化，模型也需要读懂变化后的运行环境。', flow=['Harness 状态增强','HSA-SFT','通用 OPD','HSA-RL'], companion='harness-aware-training', highlights=[['将变化纳入训练','通过 Harness 状态增强，避免模型只记住某一版 Skill 名称、工具 Schema 或提示词格式。'],['三阶段训练','监督微调学习任务，通用 OPD 恢复泛化能力，强化学习学习变化环境中的交互。'],['打通落地链路','从 Harness 设计、评测与自进化，到低延迟部署和线上验证，覆盖完整实践过程。']]),
]

class ArticleMarkdown(MarkdownConverter):
    def convert_img(self,el,text,parent_tags):
        # Chapter badges embedded in headings are decoration, not figure labels.
        if el.find_parent(re.compile('^h[1-6]$')):
            return ''
        if 'inline-equation' in el.get('class',[]):
            return str(el)
        return super().convert_img(el,text,parent_tags)

def apply_editorial_edits(slug, content):
    """Keep the author's browser-reviewed edits when importing again."""
    # Omit repeated publisher/team promotion from every Chinese article. Stop at
    # the next peer/parent heading so later technical appendices remain intact.
    team_heading=re.compile(r'^(#{1,6})[ \t]+(?:团队介绍|关于团队|团队简介)[ \t]*$',re.M)
    while match:=team_heading.search(content):
        next_heading=re.search(r'^#{1,'+str(len(match[1]))+r'}[ \t]+',content[match.end():],re.M)
        end=match.end()+next_heading.start() if next_heading else len(content)
        content=content[:match.start()]+content[end:]
    # The publisher's cross-channel recommendations are unrelated to the post.
    recommendations=re.search(r'^[^\n]*¤[^\n]*拓展阅读[^\n]*¤[^\n]*$',content,re.M)
    if recommendations:content=content[:recommendations.start()]
    content=content.rstrip()
    if slug != 'harness-aware-training-cn':
        return content
    # Remove the duplicated publisher summary and the abstract's cover/link panel.
    intro='直播电商中的数字人Agent，'
    if intro in content:
        content=content[content.index(intro):]
    # The technical conclusion remains; the publisher's team promotion is omitted.
    content=re.split(r'^#{1,6}[ \t]+团队介绍[ \t]*$',content,maxsplit=1,flags=re.M)[0]
    content=re.sub(r'!\[[^\]]*\]\(images/figure-1c65e5127094\.png\)', '', content)
    # Earlier imports flattened chapter badge alt text into these section titles.
    content=re.sub(r'^(#{1,6})[ \t]+(?:原文图[ \t]+\d+[ \t]*)+',r'\1 ',content,flags=re.M)
    content=re.sub(r'^[ \t]*#{1,6}[ \t]*$','',content,flags=re.M)
    content=re.sub(r'^\|[ \t]*\n\|[ \t]*\|[ \t]*$','',content,flags=re.M)
    # Use the actual caption (or nearby section) for accessibility, not scrape order.
    lines=content.splitlines()
    heading='Harness-Aware Training 方法图解'
    for i,line in enumerate(lines):
        if line.startswith('#'):
            heading=line.lstrip('#').strip()
        image=re.fullmatch(r'!\[原文图 \d+\]\((images/[^)]+)\)',line)
        if image:
            following=next((v.strip() for v in lines[i+1:] if v.strip()),'')
            label=following if re.match(r'^图\s*\d+',following) else heading+'配图'
            lines[i]=f'![{label}]({image[1]})'
    return re.sub(r'\n{3,}','\n\n','\n'.join(lines)).strip()

def import_post(meta):
    cached = ROOT/'.tools'/meta['file']
    if not cached.exists():
        original = Path('D:/Code/CV/sources')/meta['file']
        if original.exists():
            cached.write_bytes(original.read_bytes())
        else:
            url = f"https://arxiv.org/html/{meta['arxiv']}{meta['version']}" if 'arxiv' in meta else meta['url']+'?scene=21'
            r=requests.get(url,headers=UA,timeout=45); r.raise_for_status(); cached.write_bytes(r.content)
    raw=cached.read_text(encoding='utf-8')
    soup=BeautifulSoup(raw,'html.parser')
    body=soup.select_one('article.ltx_document' if 'arxiv' in meta else '#js_content')
    if body is None: raise ValueError(f"Original article unavailable: {meta['url']}")
    # arXiv emits some vector figures as objects; import them as ordinary local images.
    for vector in body.select('object[type="image/svg+xml"][data]'):
        figure=soup.new_tag('img',src=vector['data'])
        for attr in ['id','width','height']:
            if vector.has_attr(attr):figure[attr]=vector[attr]
        caption=vector.find_parent('figure')
        if caption and caption.find('figcaption'):
            figure['alt']=caption.find('figcaption').get_text(' ',strip=True)
        vector.replace_with(figure)
    page=ROOT/'content'/'posts'/meta['slug']; page.mkdir(parents=True,exist_ok=True)
    if 'date' not in meta:
        match=re.search(r'var create_time\s*=\s*[\"\x27](\d+)',raw)
        if not match: raise ValueError('Missing original publication date')
        meta['date']=datetime.fromtimestamp(int(match[1]),timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    if 'authors' not in meta:
        meta['authors']='淘宝直播 AIGC 团队'
    # Drop scripts, hidden duplicate editor wrappers, tracking and subscription footers.
    for e in list(body.select('script, style, iframe, mp-style-type, .js_darkmode__bg__0, .ltx_title_document, .ltx_authors, .ltx_dates, .ltx_pubnotes, .ltx_note_mark, .ltx_note_outer')):
        e.decompose()
    for e in list(body.find_all(style=True)):
        if e.parent is not None and 'display:none' in re.sub(r'\s','',e.get('style','')): e.decompose()
    for pre in body.select('pre.code-snippet__js'):
        code_lines=pre.find_all('code',recursive=False)
        if code_lines:
            code='\n'.join(line.get_text() for line in code_lines)
            pre.clear(); pre.append(NavigableString(code))
    for e in list(body.find_all(re.compile('^h[1-6]$'))):
        if e.parent is None: continue
        if e.find(re.compile('^h[1-6]$')): e.unwrap(); continue
        text=e.get_text(' ',strip=True).replace('▐','').strip()
        if not text and not e.find('img'): e.decompose(); continue
        if text and len(text)>180: e.name='p'
        elif text.startswith('图') and len(text)<120: e.name='figcaption'
        elif e.name=='h1': e.name='h2'
        elif len(text)>80: e.name='p'
    # WeChat has decorative numbered chapter titles implemented as spans.
    if 'arxiv' not in meta:
        for e in list(body.select('span[style]')):
            if e.parent is None: continue
            text=e.get_text(' ',strip=True)
            if 2<len(text)<85 and re.search(r'font-size:\s*(?:24|25|26|28)px',e.get('style','')) and not e.find('span') and not e.find_parent(re.compile('^h[1-6]$')):
                e.name='h2'
    jobs=[]
    for i,img in enumerate(body.select('img'),1):
        src=img.get('data-src') or img.get('src','')
        if not src or src.startswith('data:'): img.decompose(); continue
        # Remove account logos and numbered orange chapter badges; real figures stay.
        ratio=float(img.get('data-ratio') or 0)
        data_width=float(img.get('data-w') or 0)
        if 'arxiv' not in meta and ((0.29<ratio<0.37 and 220<data_width<450) or (img.get('data-type')=='gif' and data_width==636)):
            img.decompose(); continue
        style=img.get('style','')
        w=re.search(r'(?:^|;)\s*width:\s*([0-9.]+)px',style)
        h=re.search(r'(?:^|;)\s*height:\s*([0-9.]+)px',style)
        inline_equation=w and h and float(h[1])<=45 and float(w[1])<700
        url=urljoin(f"https://arxiv.org/html/{meta.get('arxiv','')}{meta.get('version','')}",src) if 'arxiv' in meta else src
        name=f"figure-{hashlib.sha256(url.encode()).hexdigest()[:12]}"
        suffix=Path(urlparse(url).path).suffix.lower()
        if suffix not in ['.jpg','.png','.svg','.webp','.gif','.jpeg']:
            fmt=re.search(r'wx_fmt=(\w+)',url)
            suffix='.'+(fmt[1] if fmt and fmt[1] in ['png','jpeg','jpg','gif','webp'] else 'png')
        dest=page/'images'/(name+suffix); dest.parent.mkdir(exist_ok=True)
        jobs.append((url,dest))
        dimensions={key:img[key] for key in ['width','height'] if img.has_attr(key)}
        img.attrs={'src':'images/'+dest.name,'alt':img.get('alt') or (f'Original figure {i}' if meta['language']=='en' else f'原文图 {i}'),'loading':'lazy','decoding':'async',**dimensions}
        if inline_equation:
            img['class']='inline-equation'
            img['width']=w[1];img['height']=h[1]
    # Preserve native MathML and original anchors; remove publisher-specific typography.
    for e in list(body.select('annotation, annotation-xml')): e.decompose()
    for e in body.find_all(True):
        if e.name in ['math','svg','semantics','mrow','mi','mo','mn','msub','msup','mfrac','mtext','mtable','mtr','mtd','mover','munder','munderover','msqrt','mstyle','msubsup','mspace','mpadded','mphantom','menclose','mfenced','mmultiscripts','mprescripts','none'] or e.find_parent(['math','svg']):
            for attr in list(e.attrs):
                if attr.lower().startswith('on'): del e.attrs[attr]
            continue
        e.attrs={k:v for k,v in e.attrs.items() if k in ['id','href','src','alt','colspan','rowspan','loading','decoding','class','width','height']}
        if e.name=='a':
            href=e.get('href','')
            if href.startswith('javascript:'): e.attrs.pop('href',None)
            elif href and not href.startswith(('#','http','mailto:')): e['href']=urljoin(f"https://arxiv.org/html/{meta.get('arxiv','')}{meta.get('version','')}",href)
    # Keep research HTML for exact equations, cross references and complex tables.
    # Chinese text becomes Markdown, so future edits do not need an HTML editor.
    if 'arxiv' in meta:
        content='{{< source-content >}}'
        (page/'source.html').write_text(str(body),encoding='utf-8')
        (page/'body.html').write_text(str(body),encoding='utf-8')
    else:
        content=ArticleMarkdown(heading_style='ATX',bullets='-').convert(str(body))
        content=re.sub(r'^\s*#{1,6}\s*$', '', content,flags=re.M)
        content=re.sub(r'^(#{2,6})\s*(?:\*\*)?▐(?:\*\*)?\s*',r'\1 ',content,flags=re.M)
        # Restore chapter headings drawn using publisher-specific styled spans.
        chapters=['引言','业务背景介绍','互动架构总览','多轮意图识别模块','实体解析模块','互动LLM模型','互动LLM生成模块','总结&规划','团队介绍','TLDR','数字人互动任务定义','蒸馏DeepSeek-R1实验','推理路径压缩实验','推理路径压缩','泛化性实验','总结','附录A','附录B','背景介绍','Agentic架构升级','Agentic RL实践','Multi-Agent RL多智能体协同强化学习','Workflow架构升级到Agentic架构','Workflow 架构升级到 Agentic 架构']
        for chapter in chapters:
            content=re.sub(r'^'+re.escape(chapter)+r'\s*$', '## '+chapter,content,flags=re.M)
        lines=[]
        for line in content.splitlines():
            if line.startswith('#'):line=line.replace('**','')
            if '▐' in line and len(line)<160 and not line.startswith('|'):
                line='### '+re.sub(r'^[\s#-]*','',line.replace('**','').replace('▐','')).strip()
            lines.append(line)
        content='\n'.join(lines)
        # The account's unrelated reading recommendations are not part of the article.
        content=re.split(r'¤\s*拓展阅读\s*¤',content)[0]
        content=re.sub(r'\n{3,}','\n\n',content).strip()
        content=apply_editorial_edits(meta['slug'],content)
    text=body.get_text(' ',strip=True)
    meta['readingMinutes']=max(1,round((len(re.findall(r'[\u4e00-\u9fff]',text))/450)+(len(re.findall(r'\b[a-zA-Z]+\b',text))/220)))
    front={k:v for k,v in meta.items() if k!='file'}
    front['source']=front.pop('url')
    front['publicationType']=front.pop('kind')
    # Preserve the bilingual work identity when refreshing original publications.
    works_file=ROOT/'data/works.json'
    if works_file.exists():
        for work in json.loads(works_file.read_text(encoding='utf-8')):
            if meta['slug'] in work['versions']:
                front.update(workId=work['id'],counterpart=next(v for v in work['versions'] if v!=meta['slug']),secondaryVersion=meta['slug']!=work['primary'],sourceTitle=front['title'])
                front.pop('companion',None)
    (page/'index.md').write_text(json.dumps(front,ensure_ascii=False,indent=2)+'\n\n'+content+'\n',encoding='utf-8')
    print(meta['slug'],meta['date'],len(text),'characters',len(jobs),'images',flush=True)
    return jobs,{'slug':meta['slug'],'url':meta['url'],'version':meta.get('version'),'retrieved':'2026-10-18','sha256':hashlib.sha256(raw.encode()).hexdigest()}

def download(job):
    url,dest=job
    if dest.exists() and dest.stat().st_size>0: return None
    for attempt in range(3):
        try:
            r=requests.get(url,headers=UA,timeout=45); r.raise_for_status()
            if 'image' not in r.headers.get('content-type',''): raise ValueError('Not an image')
            dest.write_bytes(r.content); return None
        except Exception as e:
            error=str(e)
    return {'url':url,'file':str(dest.relative_to(ROOT)),'error':error}

if __name__=='__main__':
    jobs=[]; manifest=[]
    for meta in POSTS:
        assets,source=import_post(meta); jobs.extend(assets); manifest.append(source)
    with ThreadPoolExecutor(max_workers=8) as pool: failures=[x for x in pool.map(download,jobs) if x]
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data'/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'.tools'/'asset-failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Imported',len(POSTS),'posts;',len(jobs),'figures;',len(failures),'download failures',flush=True)
