"""Authoring command: publish four complete translations and five version pairs."""
from pathlib import Path
from copy import deepcopy
from bs4 import BeautifulSoup
import json,re,hashlib
from translation_segments import write_markdown,write_paper,markdown_segments,paper_segments
ROOT=Path(__file__).resolve().parents[1]
PAIRS=[('llm-barrage-interaction','llm-barrage-interaction-en'),('llm-distillation-and-reasoning-compression','llm-distillation-and-reasoning-compression-en'),('livethinking','livethinking-cn'),('agenticrl','agenticrl-en'),('harness-aware-training','harness-aware-training-cn')]
METADATA={
'llm-barrage-interaction':dict(title='Taobao Live Digital Avatars: LLM-Powered Viewer Interaction',shortTitle='LLM-Powered Viewer Interaction',description='Multi-turn intent recognition, entity parsing, retrieval, and response generation for real-time digital-avatar conversations.',lead='Make every viewer comment part of a conversation.',highlights=[['Understand the context','Identify intent from the current product, dialogue history, and viewer comment.'],['Connect product knowledge','Extract product names, attributes, and link numbers to retrieve the right facts.'],['Respond naturally','Train text and spoken responses with their distinct presentation requirements.']]),
'llm-distillation-and-reasoning-compression':dict(title='Taobao Live Digital Avatars: Model Distillation and Reasoning-Path Compression',shortTitle='Distillation & Reasoning Compression',description='Distilling DeepSeek-R1 and balancing response quality with low latency through quality–length Dual-Preference DPO.',lead='Bring reasoning into the livestream, and bring the waiting time down.',highlights=[['Transfer reasoning','Compare three distillation strategies, model sizes, and quantization choices.'],['Compress the path','Align length and quality preferences to shorten reasoning without losing response quality.'],['Preserve generalization','Use fresh production traffic and larger preference datasets to test and improve robustness.']]),
'agenticrl':dict(title='Taobao Live Digital Avatars: From RLVR to Multi-Agent Reinforcement Learning',shortTitle='From RLVR to Multi-Agent RL',description='Migrating from a static workflow to agents and jointly training tool-calling and response models with separate rewards.',lead='From a fixed workflow to an avatar that plans and uses tools.',highlights=[['Upgrade the architecture','Replace rigid intent routing with contextual, on-demand tool use.'],['Be fast and reliable','Combine AgentTuning and RLVR to reduce latency and improve factual responses.'],['Optimize together','Separate tool use and response generation, then jointly train their distinct skills.']]),
'livethinking':dict(title='LiveThinking：通过强化学习实现 AI 直播的实时高效推理',shortTitle='LiveThinking',description='结合拒绝采样蒸馏与 GRPO 强化学习，在实时数字人互动中兼顾推理效率、回复正确性和帮助性。',lead='让推理更高效，让互动更及时。',highlights=[['迁移推理能力','通过拒绝采样微调，将大教师的电商推理能力迁移至轻量 MoE 学生。'],['压缩推理路径','联合长度、正确性和帮助性奖励，减少冗长思考并保持回复质量。'],['验证真实效果','结合工业数据、公开多跳问答及淘宝直播部署，评估质量、成本和用户互动。']])
}

def read(slug):
 text=(ROOT/'content/posts'/slug/'index.md').read_text(encoding='utf-8');meta,end=json.JSONDecoder().raw_decode(text)
 return meta,text[end:].strip()
def save(slug,meta,body):
 page=ROOT/'content/posts'/slug;page.mkdir(parents=True,exist_ok=True)
 (page/'index.md').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n\n'+body.strip()+'\n',encoding='utf-8')

def main():
 records=[];works=[]
 for primary,secondary in PAIRS:
  meta,body=read(primary)
  meta.update(workId=primary,counterpart=secondary,secondaryVersion=False,sourceTitle=meta.get('sourceTitle',meta['title']))
  meta.pop('companion',None);save(primary,meta,body)
  if primary in METADATA:
   english=meta['language']!='en';language='en' if english else 'zh-CN'
   mapping=json.loads((ROOT/'scripts/translations'/f'{primary}.{"en" if english else "zh"}.json').read_text(encoding='utf-8'))
   translated=deepcopy(meta);translated.update(METADATA[primary]);translated.update(slug=secondary,language=language,counterpart=primary,secondaryVersion=True,isTranslation=True,sourceLanguage=meta['language'])
   translated['authors']='Taobao Live AIGC Team' if english else meta['authors']
   translated['publicationType']='Technical practice' if english else '研究论文'
   translated.pop('flow',None)
   page=ROOT/'content/posts'/secondary;page.mkdir(parents=True,exist_ok=True)
   if primary=='livethinking':
    source=write_paper(primary,mapping)
    (page/'source.html').write_text(source,encoding='utf-8')
    translated_body='{{< source-content >}}'
    plain=BeautifulSoup(source,'html.parser').get_text(' ',strip=True)
   else:
    translated_body=write_markdown(primary,secondary,mapping);plain=translated_body
   translated['readingMinutes']=max(1,round(len(re.findall(r'[\u4e00-\u9fff]',plain))/450+len(re.findall(r'\b[a-zA-Z]+\b',plain))/220))
   save(secondary,translated,translated_body)
   source_file=ROOT/'content/posts'/primary/('source.html' if primary=='livethinking' else 'index.md')
   records.append(dict(source=primary,translation=secondary,language=language,sourceSha256=hashlib.sha256(source_file.read_bytes()).hexdigest(),translatedBlocks=len(mapping),date='2026-10-19'))
  else:
   translated,translated_body=read(secondary)
   translated.update(workId=primary,counterpart=primary,secondaryVersion=True,sourceTitle=translated.get('sourceTitle',translated['title']))
   translated.pop('companion',None);save(secondary,translated,translated_body)
  works.append(dict(id=primary,primary=primary,versions=[primary,secondary]))
 (ROOT/'data/works.json').write_text(json.dumps(works,indent=2),encoding='utf-8')
 (ROOT/'data/translations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Prepared 5 works, 10 language versions, and 4 full translations.')

if __name__=='__main__':main()
