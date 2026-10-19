观众先问“能推荐个马桶吗”，接着只发一句“智能马桶”。单看第二句话，像是在要求讲解；放回对话里，它仍然是一次商品咨询。

直播互动里，这类省略比完整问题更常见。模型需要知道观众之前说了什么、主播正在讲什么，以及哪些商品还在售。


## 文本回复与口播回复 {#先分清文本回复和口播回复}
直播互动有两种回复方式：文字直接显示在弹幕区；口播则经过 TTS 和口型驱动，由数字人说出来。两者处理的是同一类观众问题，对上下文和事实的要求接近，但资源开销、等待时间和表达方式差别很大。口播主要用于资源更充足的旗舰版本，其他版本更多使用文字回复。无论采用哪一种，都要先判断观众在问什么，再决定查哪些信息、怎样回答。我们按这个顺序组织了意图识别、检索和生成链路。

## 弹幕处理流程 {#一条弹幕会经过哪些环节}
<figure class="publication-figure figure-landscape" id="blog-figure-1"><div class="figure-heading"><span class="figure-label">图 1</span><button aria-label="放大查看：图 1" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="弹幕互动工作流：意图与实体先确定检索范围，再进入回复生成。" decoding="async" height="515" loading="lazy" src="../llm-barrage-interaction/images/figure-92603a48521c.png" width="1080"/></div><figcaption class="publication-caption">弹幕互动工作流：意图与实体先确定检索范围，再进入回复生成。</figcaption></figure>

一条弹幕经过以下模块：

- 预置 FAQ：先用嵌入向量召回商家配置的问答，再用重排模型筛选。命中后直接采用对应的意图和答案，跳过后面的意图分类。商家写好的回答因此能优先使用，也减少了生成时改写原意的问题。
- 意图识别模块：未命中预置库时，结合弹幕、历史对话和直播间状态判断意图，再进入对应的处理分支。
- 实体解析模块：根据历史对话和已识别的意图，提取商品名称、属性或链接号。
- 检索模块：

- 如果意图为链接号商品问答/讲解则使用链接号检索需要的商品信息；
- 如果意图为无主语商品问答则直接使用当前讲品信息作为检索结果；
- 如果意图为商品问答/讲解则使用当前弹幕作为query在向量库中查询最匹配商品作为检索结果。

- 生成模块：把检索信息、观众弹幕和历史对话填入对应的 Prompt 模板，交给 LLM 生成回复。模板分为闲聊、商品问答和优惠问答三种。
- 讲解顺序调整：如果意图为商品讲解或者链接号讲解，将不会使用 LLM 生成回复，而是调整讲解顺序，使用固定话术进行回复。

## 多轮意图识别
### 多轮上下文 {#让下一句能接上上一句}

我们从 2024 年 12 月开始重点补多轮互动。观众经常省略主语，接着上一句问“那这个呢”，只看当前弹幕很难判断。回复需要接住前面的对话，不能每一轮都重新开始。

- 先设计多轮对话架构，再积累数据，逐步改善互动效果。
- 原来的意图模型只看当前弹幕，已经积累了大量单轮数据。改造时既要利用这些数据，也要让模型支持新增的多轮能力。

我们把直播间商品、历史对话和当前弹幕一起作为输入，再用直接输出意图标签的 LLM 替换 BERT 分类器。分类任务没变，输入补上了判断省略语句所需的上下文。这批多轮数据上的准确率为 80%，DeepSeek-R1 为 71%；用同一份单轮与多轮混合数据训练的 BERT 为 69%。这组比较反映的是模型对业务标签边界的掌握程度，适用于当前场景的选型，不能据此判断其他任务上的能力。

### 多轮互动架构

<figure class="publication-figure figure-landscape" id="blog-figure-2"><div class="figure-heading"><span class="figure-label">图 2</span><button aria-label="放大查看：图 2" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="多轮互动中的上下文流转。" decoding="async" height="628" loading="lazy" src="../llm-barrage-interaction/images/figure-385eb43e3f0f.png" width="722"/></div><figcaption class="publication-caption">多轮互动中的上下文流转。</figcaption></figure>

- 在每轮对话开始前，绿色框中内容会被输入到意图识别模型中进行意图识别。
- 确认意图后，会根据意图决定检索方式以及系统指令。
- 检索到对应信息后，将虚线框中的内容交给互动生成 LLM，生成新一轮主播回复。

### 意图分类

<figure class="publication-figure figure-landscape" id="blog-figure-3"><div class="figure-heading"><span class="figure-label">图 3</span><button aria-label="放大查看：图 3" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="业务意图及其对应的处理分支。" decoding="async" height="372" loading="lazy" src="../llm-barrage-interaction/images/figure-ffd9170fc0ec.png" width="1080"/></div><figcaption class="publication-caption">业务意图及其对应的处理分支。</figcaption></figure>

- 意图类型经历过两次变更：

- 2024年7月：新增商品推荐意图、直播间优惠问题意图
- 2025年1月：将商品推荐意图、商品查询意图合并入商品问答意图

### 对话样例 {#放到真实对话里看}

| 观众弹幕 | 历史对话 | 意图识别结果 | 数字人回复 |
| --- | --- | --- | --- |
| 智能马桶 | user: 能不能推荐马桶  assistant: 主播建议可以先看看17号链接。这款智能马桶功能齐全，包括停电冲水、自动调节座温水温、脚感冲水等，非常适合小户型使用，性价比很高。 | 商品问答 | 17号链接的九牧智能马桶有停电冲水、自动调节水温、脚感冲水等功能，券后价2199，现在入手很划算哦。 |
| 蓝牙连哪一个呢 | user: 请问领夹麦要连蓝牙吗  assistant: 我们这款领夹麦是蓝牙连接的，方便又实用哦。 | 商品问答 | 宝宝可以看一下6号链接的金运蓝牙耳机，是无线蓝牙连接的哦，或者11号链接的入耳式款，都是蓝牙连接的哈。 |
| 好的 | user: 怎么抽奖？  assistant: 抽奖的问题比较专业，建议宝宝去问下客服哈，他们应该更清楚具体的规则呢。 | 闲聊 | 好的，祝你抽奖顺利！ |

### 基于 LLM 的意图识别 {#为什么换成带上下文的-llm}

<figure class="publication-figure figure-landscape" id="blog-figure-4"><div class="figure-heading"><span class="figure-label">图 4</span><button aria-label="放大查看：图 4" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="意图识别从单轮分类迁移到带直播间上下文的 LLM。" decoding="async" height="523" loading="lazy" src="../llm-barrage-interaction/images/figure-c8b91623c77e.png" width="1080"/></div><figcaption class="publication-caption">意图识别从单轮分类迁移到带直播间上下文的 LLM。</figcaption></figure>

- 单轮意图识别模型使用观众弹幕作为意图识别模型的输入，使用 BERT 进行序列分类，输出意图label\_id。
- 多轮意图识别使用直播间讲品、历史对话和观众弹幕作为意图识别模型的输入，使用 LLM 进行分类，直接输出意图label。

#### 训练数据构建

1. 使用单轮意图模型和DeepSeek-V3在清洗后的20k量级数据上分别进行预测，仅保留预测结果不一致的数据。（预测一致的数据靠原有的单轮数据就可以补充其分类能力）
2. 再次清洗，筛去不合规弹幕数据，比如偷跑弹幕数据（实际弹幕是在和真人对话但是是开的数字人直播）、刷屏数据，这一步人工筛选。
3. 送标，交由标注人员进行标注。
4. 算法RD逐条检查标注结果，人工筛掉那些人为难以分辨、理解的数据，最后保留3000+条多轮意图识别数据。

#### 评测与边界案例 {#指标和几个边界案例}

| method | description | accuracy |
| --- | --- | --- |
| deepseek-V3 | prompt engineering | 0.66 |
| deepseek-R1 | prompt engineering | 0.71 |
| Qwen2.5 7B仅在多轮数据sft | 仅在3000条多轮数据微调，无cot，直接出答案 | 0.77 |
| Qwen2.5 7B在多轮&单轮数据上sft，直接出结果 | 在3000条多轮数据+16000条单轮数据上微调，无cot，直接出答案 | 0.80 |
| BERT在多轮&单轮数据上finetune | 在3000条多轮数据+16000条单轮数据上微调，与Qwen在数据上完全对齐 | 0.69 |

- 相比于单轮意图难判断很多，每条数据可能需要半分钟到一分钟来确定真实意图是什么
- 目前的输入源[当前直播间讲品信息， 与观众的历史对话， 观众当前弹幕]完全足以判断观众的真实意图
- 多轮对话的标签边界比单轮模糊。同一个问题可能补出链接号，也可能提取出商品关键词；历史里讨论的商品还可能刚好切成当前讲品。这几种路由有时都能查到足够的事实，分类错了一类，最终仍可能答对。因此，意图准确率和最终回复效果需要分别评测。

上下文如何改变意图判断

| 当前弹幕 | 当前讲品 | 历史对话 | 单轮意图 | 多轮意图 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 智能马桶 |  | user: 能不能推荐马桶  assistant: 主播建议可以先看看17号链接。这款智能马桶功能齐全，包括停电冲水、自动调节座温水温、脚感冲水等，非常适合小户型使用，性价比很高。 | 商品讲解 | 商品问答 | 如果仅看一轮意图，观众直接说了一个商品，那么就会给观众讲智能马桶，结合多轮数据后识别到用户是希望推荐智能马桶 |
| 擦头发 |  | user: 哪款适合擦头发  assistant: 主播建议可以先看看2号链接。这款干发毛巾采用纯棉材质，吸水性好，设计多样，非常适合日常使用。 | 拒答 | 商品问答 | 只看"擦头发"不知所云，结合上下文后识别到用户是要擦头发的商品 |
| 主播你好，这款进位器需要充电吗？ | gps定位器车载车辆防丢防盗追跟定仪器订位汽车跟踪追踪录音神器 | user: 主播你好，要充电吗assistant: 这个问题蛮专业的，我不太清楚，可以去问下客服哈，他们应该了解。 | 商品问答 | 无主语商品问答 | 只看弹幕，可能被分类到"商品问答"意图，去宝贝口袋检索商品，但是结合当前讲品来看，基本确定问的就是正在讲的商品 |

多轮对比DeepSeek-R1结果分析

- DeepSeek-R1会在长尾边界问题上给出错误的意图分类结果，无法单纯通过调prompt来解决分布广泛的长尾边界问题。
- 但依赖数据驱动的 SFT 模型可以解决这类广泛的长尾边界问题，并且可以在后续的优化中通过大量标注的线上数据进一步提升性能。

### CoT 对分类效果的影响 {#加入-cot也可能适得其反}

- 我们尝试用 R1 根据已有意图标签补出 CoT，再用这些带推理过程的数据训练 LLM，观察能否迁移 R1 的 reasoning 能力。

| method | description | accuracy |
| --- | --- | --- |
| Qwen2.5 7B仅在多轮数据sft | 仅在3000条多轮数据微调，无cot，直接出答案 | 0.77 |
| Qwen2.5 7B仅在多轮cot数据sft | 仅在3000条多轮cot数据微调，带cot，reasoning后出答案 | 0.68 |

- 这组实验加入生成的 CoT 后，准确率反而下降。较长的推理监督可能削弱了标签学习，但这个解释和结果都只针对当前任务。
- 在开放标签空间下使用R1标注会有良好的效果，但是如果在本身就有真实标签的情况下使用R1进行reasoning的标注反而会不及预期

## 实体解析
实体解析接着处理历史对话和识别出的意图，提取商品名称、商品属性或链接号。

核心挑战：需处理历史依赖、数字干扰、商品泛化等复杂场景。

- 输入：用户当前弹幕+历史对话记录+识别的多轮意图
- 输出：结构化提取以下三类实体：

- 商品实体（特仑苏纯牛奶）
- 商品属性（2匹/39码/iPhone15）
- 链接号（107号/39号）

<figure class="publication-figure figure-landscape" id="blog-figure-5"><div class="figure-heading"><span class="figure-label">图 5</span><button aria-label="放大查看：图 5" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="实体解析输入与结构化输出。" decoding="async" height="508" loading="lazy" src="../llm-barrage-interaction/images/figure-fa5ffaedbb15.png" width="1080"/></div><figcaption class="publication-caption">实体解析输入与结构化输出。</figcaption></figure>

### 训练数据

实体解析使用意图识别的那批对话，保留商品问答、商品讲解和链接号相关样本。DeepSeek-R1 在这组解析测试中表现最好，我们用它生成结果，再人工检查，整理出 2100 条高质量多轮样本。检查时尤其留意历史中出现的商品是否与当前问题有关，避免把已经换掉的话题带进来。

| 数据维度 | 说明 |
| --- | --- |
| 基础数据 | 保留原始数据中的商品问答（840条）、商品讲解（210条）、链接号相关（770条） |
| 数据增强 | 采用对抗样本生成策略新增1000条，覆盖发音/拼写/方言等干扰场景 |
| 质量保障 | - 多阶段DeepSeek-R1推理生成  - 人工校验 |

### 数据增强

数值歧义

链接号会受到对话中数值信息的干扰，导致解析结果错误，需要提升模型对数字的敏感度。以下是三类干扰类型：

| 干扰类型 | 典型案例 | 错误分析 |
| --- | --- | --- |
| 产品功率数值 | 2匹空调 → 提取2 | 数值型参数与链接号混淆 |
| 尺码/尺寸数值 | 39码运动鞋 → 提取39 | 未建立「参数-链接号」层级关系 |
| 版本迭代数字 | iPhone15 → 提取15 | 商品名称中的数字被误判为链接号 |

我们让 DeepSeek-R1 先生成干扰类型，再按类型生成对话样本，以增加数据的多样性。

<figure class="publication-figure figure-natural" id="blog-figure-6"><div class="figure-heading"><span class="figure-label">图 6</span><button aria-label="放大查看：图 6" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="用数值歧义样本区分商品参数与链接号。" decoding="async" height="292" loading="lazy" src="../llm-barrage-interaction/images/figure-16373a291666.png" width="494"/></div><figcaption class="publication-caption">用数值歧义样本区分商品参数与链接号。</figcaption></figure>

商品泛化

如果对话历史中出现具体商品，模型会错误提取为具体商品，而用户问的是泛化商品。例如：

用户问：哪个牛奶有活动 -> 模型错误提取：特仑苏纯牛奶

我们生成泛化类型商品，主要包含以下三种：

| 泛化类型 | 商品 | 类型 |
| --- | --- | --- |
| 商品泛化 | 佳沛奇异果 | 水果 |
| 品牌泛化 | 特仑苏纯牛奶 | 牛奶 |
| 规格泛化 | 农夫山泉5L装 | 大瓶装水 |

我们先人工标注一批商品，用DeepSeek-R1扩展商品池后再结合商品类目生成对话样本。

<figure class="publication-figure figure-natural" id="blog-figure-7"><div class="figure-heading"><span class="figure-label">图 7</span><button aria-label="放大查看：图 7" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="商品泛化样本覆盖品牌、品类和规格层级。" decoding="async" height="482" loading="lazy" src="../llm-barrage-interaction/images/figure-4e025b93aef7.png" width="498"/></div><figcaption class="publication-caption">商品泛化样本覆盖品牌、品类和规格层级。</figcaption></figure>

历史噪声

历史商品与当前弹幕冲突时，模型容易仍然提取历史中明确出现的商品。我们为此生成对抗数据，覆盖以下问题类型：

| 问题类型 | 生成策略 | 示例 |
| --- | --- | --- |
| 发音简写 | 保留首字母+数字 | i12 → iPhone12 |
| 拼写错误 | 相邻键位替换/漏字母 | iQO10 → iQOO10 |
| 系列混淆 | 跨代系混合 | 小米13 → 小米14 |
| 方言谐音 | 拼音变形 | 爱酷11 → iQOO11 |

我们使用DeepSeek-R1先生成存在不同问题类型的商品对，再根据商品对生成对话样本。

<figure class="publication-figure figure-natural" id="blog-figure-8"><div class="figure-heading"><span class="figure-label">图 8</span><button aria-label="放大查看：图 8" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="历史噪声与商品名称扰动的数据构建。" decoding="async" height="292" loading="lazy" src="../llm-barrage-interaction/images/figure-ff72febd7e73.png" width="494"/></div><figcaption class="publication-caption">历史噪声与商品名称扰动的数据构建。</figcaption></figure>

### 评测与错误分析 {#实体解析怎么评错在哪里}

训练方法：我们使用7B的底座模型进行 LoRA 微调

评测指标：计算预测item和实际item字符串2-gram的Jaccard相似度，正确阈值设置为0.7，最终指标使用accuracy。

<figure class="publication-figure figure-landscape" id="blog-figure-9"><div class="figure-heading"><span class="figure-label">图 9</span><button aria-label="放大查看：图 9" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="实体解析使用字符串 2-gram Jaccard 相似度评估。" decoding="async" height="264" loading="lazy" src="../llm-barrage-interaction/images/figure-45a61484792f.png" width="1080"/></div><figcaption class="publication-caption">实体解析使用字符串 2-gram Jaccard 相似度评估。</figcaption></figure>

- <img alt="2-gram 集合记号" class="inline-equation" decoding="async" height="23" loading="lazy" src="../llm-barrage-interaction/images/figure-9cc4c1a4bc85.png" width="47"/>表示字符串 S 的 2-gram 集合

| model | acc |
| --- | --- |
| gpt4-fewshot-cot | 0.77 |
| deepseek-r1 | 0.87 |
| ours | 0.92 |

| 当前弹幕 | 历史对话 | 多轮意图 | 商品解析结果 |
| --- | --- | --- | --- |
| 保暖款 | "观众弹幕: 鞋",  "主播回复: 涛涛小铺吖宝宝，154号宝贝可以先看看商详页，这个商品我会在晚些的直播时间段里专门来讲解噢。好，那主播先把107号宝贝讲完哈" | 商品问答 | 保暖款鞋 |
| 是不是长得差不多啊 | "观众弹幕: 12跟13比哪个性价比高","主播回复: iQOO 12和iQOO 13的性价比需要综合考虑价格和性能。iQOO 12原价3999元，券后价3118.3元，iQOO 13原价3999元，券后价3928.3元。iQOO 12的性价比更高，建议宝宝可以优先考虑iQOO 12。","观众弹幕: 12跟13哪个性能更好","主播回复: iQOO 13的CPU是骁龙8至尊版，而iQOO 12的CPU是第三代骁龙8，从性能上来说，iQOO 13更胜一筹。","观众弹幕: 拍照哪个好","主播回复: 主播建议可以先看看39号链接。这款手机主摄像素高达5000万，前置摄像头1600万像素，超广角像素也是5000万，非常适合喜欢拍照的小伙伴。" | 商品问答 | iQOO 12,  iQOO 13 |
| 一号连接跟七号有什么差别吗 | 观众弹幕: 7号可以录音吗？主播回复: 7号链接的高端定位器有录音功能哦，具体细节可以问下客服哈，他们更清楚呢观众弹幕：七号连接，要连接WIFI吗？主播回复：7号链接的高端定位器有WIFI版本哦，具体怎么操作可以问下客服哈，他们更清楚呢 | 链接号商品问答 | 1,7 |
| 区别 | 观众弹幕：30和27号的优惠主播回复：咱们下单前记得点击直播间右下角的宝贝口袋，看到有店铺优惠券的哈，进店查看宝贝后即可领取。 | 链接号商品问答 | 30,27 |

## 商品信息检索

<figure class="publication-figure figure-landscape" id="blog-figure-10"><div class="figure-heading"><span class="figure-label">图 10</span><button aria-label="放大查看：图 10" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="商品库实时同步，以及语义召回与词频排序。" decoding="async" height="798" loading="lazy" src="../llm-barrage-interaction/images/figure-a6c40beabfaa.png" width="1080"/></div><figcaption class="publication-caption">商品库实时同步，以及语义召回与词频排序。</figcaption></figure>

- 每次检索宝贝口袋商品时，首先和实时宝贝口袋商品进行同步，输入商品信息，使用 BERT 计算上下文向量，新增向量库中没有的向量，剔除不存在于宝贝口袋的商品向量。每一条向量对应一个itemId。
- 商品库同步后，用 BERT 编码查询，按语义相似度召回候选，再用 BM25 对弹幕与商品文本做词频排序。两种信号共同过滤候选，最后返回商品信息列表。短查询常常只有一个品类词或规格，补上词频排序后，比只用向量相似度更容易收准。
- 通过添加词频精排模块可以有效解决短query难召回的问题。

## 回复生成

### 回复策略 {#不同问题用不同的回复方式}

- 闲聊：根据历史上下文和观众当前弹幕对观众进行回复

| 历史对话 | 当前弹幕 | 主播回复 |
| --- | --- | --- |
| user: 买好了  assistant: 太棒了，感谢支持！希望你会喜欢哦！  user: 忘记写手几号怎么办assistant: 没关系的，可以联系客服帮忙查询一下，他们会帮你解决的。 | 联系客服了 | 好的，客服会尽快帮你解决的，别担心。 |

- 商品问答：根据商品信息对用户弹幕进行回复，包括推荐、查询等

| 观众弹幕 | 主播回复 | 商品检索结果（实际商详过长，省略去无关信息） |
| --- | --- | --- |
| 你好，有3p的壁挂式空调吗 | 咱们209号链接的格力空调就是3匹的壁挂式哈，现在券后价6399，活动力度很大哦。 | [{  "商品名": "【Gree/格力官方】变频冷暖2匹大挂机家用客厅卧室两用空调清炫风",  "链接号": 208  },{  "商品名": "【Gree/格力官方】变频冷暖3匹大挂机家用客厅卧室两用空调清炫风",  "链接号": 209  },{  "商品名": "【Gree/格力官方】一级能效变频冷暖小2匹家用卧室空调挂机风纪元",  "链接号": 288  }] |

- 直播间优惠问答：

- 如果商家配有直播间优惠，会根据直播间优惠信息对用户弹幕进行回复，包括推荐、查询等。
- 此外，如果没有配直播间优惠或者直播间优惠信息无法回答观众问题，会采用通用的优惠话术，包括优惠券、红包、国补等。

| 观众弹幕 | 主播回复 | 优惠信息 |
| --- | --- | --- |
| 怎么拍划算 | 咱们下单前记得点击直播  间右下角的宝贝口袋，看  到有宠粉红包的哈，进店  查看宝贝后即可领取。 | {      "红包类型": "购前券",      "红包名称": "宠粉红包",      "金额门槛": "无门槛",      "优惠额度": "4.0元",      "红包限制": "限粉丝",      "领取方法": "进店查看宝贝"  } |
| 现在还有国补嘛 | 有宝宝问现在还有国补  吗，你可以直接在宝贝口  袋查看，有政府补贴的商  品会有标签的哈，点进去  领取就行，不同地区政策  不一样的。 |  |

### 回复模型的训练数据 {#回复模型的数据从哪里来}

<figure class="publication-figure figure-landscape" id="blog-figure-11"><div class="figure-heading"><span class="figure-label">图 11</span><button aria-label="放大查看：图 11" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="单轮与多轮互动模式的上下文差异。" decoding="async" height="784" loading="lazy" src="../llm-barrage-interaction/images/figure-8b5a4b0b6530.png" width="1080"/></div><figcaption class="publication-caption">单轮与多轮互动模式的上下文差异。</figcaption></figure>

| 意图 | 数据类型 | 数量 |
| --- | --- | ---: |
| 闲聊 | 单轮闲聊 | 1509 |
| 闲聊 | 多轮闲聊 | 181 |
| 直播间优惠 | 有优惠 | 278 |
| 直播间优惠 | 无优惠 | 121 |
| 商品问答 | 单商品、可回答 | 1678 |
| 商品问答 | 单商品、拒答 | 1249 |
| 商品问答 | 多商品、多轮 | 400 |
| 商品问答 | 多商品、单轮 | 399 |
| 商品推荐 | 初版推荐 | 400 |
| 商品推荐 | 多商品、单轮 | 400 |
| 商品推荐 | 多商品、多轮 | 249 |
| 商品查询 | 多商品、单轮 | 400 |
| 商品查询 | 多商品、多轮 | 354 |
| 无主语商品问答 | 单轮 | 400 |
| 无主语商品问答 | 多轮 | 398 |
| 总计 | 所有数据 | 8416 |

### 文本与口播的表达差异 {#同一个答案文本和口播各怎么说}

| 用户弹幕 | 弹幕版 | tts版 |
| --- | --- | --- |
| 直播间智能马桶优惠吗 | 17号链接原价9999现在券后2199，45号链接券后2799，31号链接券后2599，活动力度很大哦，现在入手很划算呢。 | 看到有宝宝问智能马桶的优惠，十七号链接原价九千九百九十九，现在券后只要两千一百九十九，四十五号链接券后两千七百九十九，三十一号链接券后两千五百九十九，现在不买可能就没活动了哦。那主播继续讲啦 |

- 弹幕版：直接对观众进行回复；不对数字和英文进行正则化；限制为60字（弹幕回复框限制）。
- tts版：首先对观众的弹幕进行简单复述，让观众知道在和他对话；对数字和英文进行正则化，便于tts生成；无字数限制。
- 模式区分实现方式：

- 弹幕版：从原始数据中使用 LLM 删去复述观众弹幕部分。
- tts版：对原始数据正则化处理。
- 使用系统指令区分两个版本的数据。

- 两种模式带来的问题：

- 同一个样本可能会在训练过程中被训练两次，导致过拟合。

- 解决方案：

- 先按原始对话划分训练集和验证集，再生成文本版、口播版。否则，同一条样本的两个改写版本可能分别进入训练和验证两侧，造成评估虚高。我们遇到过 eval accuracy 异常升到 95% 以上，而这组任务微调收敛时常见的范围是 70–80%。出现这种差异时，应先查数据划分，再判断模型是否有这么大的提升。
- 根据 learning curve 调整学习率，选取 eval loss 最低的 checkpoint。

## 部署检查 {#落地时最值得检查的几件事}

链路中的错误经常出在模块交接处：意图分对了，实体仍可能提错；实体找对了，商品可能已经不在售。单模块评测之外，我们还会回放完整请求，追查模型引用了哪个商品、拿到了哪份材料，以及回复中的事实来自哪里。只检查最终句子，容易漏掉前面的偏差。

数据增强也要在划分之后做。同一条对话衍生的改写、数字扰动和历史噪声样本，应留在同一侧，避免近似样本泄漏到验证集。分数过于乐观时，我们先回查数据构造和划分过程，排除泄漏，再决定是否调整模型。否则，虚高的基线会影响后续每一次比较。

这里的 80% 意图准确率、92% 实体解析准确率，都来自具体直播数据及其判分口径。长尾问题的后续改进仍依赖真实标注；相比单纯增加提示词，持续积累这些数据更有效。
