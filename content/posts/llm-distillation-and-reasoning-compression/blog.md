本专题是我们打造智能数字人的部分实践总结。我们将探讨六大核心环节：LLM文案生产赋予数字人思考和内容生成能力，如同其“大脑”；LLM互动能力则聚焦对话逻辑与拟人化交流，是实现自然交互的关键；TTS（语音合成）技术负责将文字转化为富含情感、个性化的“声音”；形象驱动技术让语音与表情、口型、肢体动作精准同步，塑造逼真视觉形象；音视频工程解决实时渲染、低延迟传输与高质量画面输出的技术挑战；最后，服务端工程构建稳定、弹性、高并发的后端支撑平台，确保数字人服务高效稳定运行。欢迎大家一起交流进步。

## TLDR

直播间弹幕互动是当前数字人直播场景中一个重要的用户交互形式，但也面临着复杂推理问题的严峻挑战。弹幕内容往往语义模糊、多样化，且需要在极短时间内完成商品信息、观众弹幕以及多轮对话历史理解与回复，这对模型的语义理解能力和推理效率提出了极高要求。此外，多轮对话中还需保持上下文连贯性，同时严格遵循业务规则和商品信息，避免因错误回答引发用户不满或舆情风险。在此背景下，以DeepSeek-R1、QwQ为代表的开源推理模型的发布为我们解决这些问题带来了新的希望。

首先，我们验证了DeepSeek-R1在直播数字人互动中的良好性能，然而由于DeepSeek-R1推理时长无法满足直播间互动的要求，我们需要将DeepSeek-R1的强大性能迁移到更小规模的模型上。为此，我们设计了三种蒸馏方案，并通过实验评估了它们在推理效率和性能上的表现，最终选择了以DeepSeek-R1-Distill-Qwen为基座的蒸馏方案，相比于线上非蒸馏模型性能有大幅提升（+8pt）。然而，蒸馏后的14B模型由于推理时间过长（int8量化后，平均5.58秒，最长11.87秒），无法满足直播场景的回复实时性要求，而7B模型的性能则显著低于14B模型（-9pt），无法满足性能要求。

为此，我们开始对推理路径压缩进行探索。我们先是复现了kimi1.5论文中的long2short DPO方法，成功将推理时间缩短至平均4.24秒，最长6.24秒（缩减时间接近50%）。然而，该方法在缩短推理路径的同时会导致性能上的下降（-1pt）。

为了解决效果下降的问题，我们对kimi k1.5论文中的long2short DPO进行了改良，使用质量-长度双偏好对蒸馏模型进行对齐训练，改良后的推理路径压缩方案DP-DPO（Dual-Preference DPO）不仅能够有效的压缩推理路径减少推理RT，和kimi long2short DPO后的方案缩减效果几乎相同，并且在性能上相较于原模型还有小幅提升（+0.4pt），性能已经接近于DeepSeek-R1（-0.2pt）。

DP-DPO模型上线后，我们使用线上数据上对各模型进行测试，发现DPO存在着将模型泛化性减弱的缺陷，为了解决DPO泛化性的缺陷，我们采取了扩大DPO数据规模的方案，泛化后的DP-DPO模型相较于泛化前模型在线上测试集上表现大幅提升（+2.3pt），并在验证集上性能超过了DeepSeek-R1（+1.8pt）,并且在推理路径压缩上也有着良好的表现。

## 数字人互动任务定义

### 2.1 任务列表与数据集的选取

数字人直播互动模型整体可以分为8个任务（任务划分由前置意图模型决定，不同任务的信息源与指令不同），我们选取其中对模型要求较高的商品问答任务进行实验，使用DeepSeek-R1构建reasoning数据，进行训练，选取商品问答任务进行蒸馏实验。

| 任务 | 模式 | 任务 | 模式 |
| --- | --- | --- | --- |
| 商品问答(实验选取任务) | 口播 | 直播间优惠问答 | 口播 |
| 商品问答 | 弹幕 | 直播间优惠问答 | 弹幕 |
| 闲聊 | 口播 | 无主语商品问答 | 口播 |
| 闲聊 | 弹幕 | 无主语商品问答 | 弹幕 |

- 我们从直播互动线上随机采样了5800条商品问答数据作为数据集进行了实验，其中训练验证集比例为9:1；
- 口播模式与弹幕回复模式存在部分区别。

### 2.2 商品问答任务示例

<div class="wide-table">

| 输入 · 商品信息 | 输入 · 对话历史 | 输入 · 观众问题 | 输出 · 能否回答观众问题 | 输出 · 主播回复 |
| --- | --- | --- | --- | --- |
| ['{"商品名": "香港X品牌PQQ童颜丸线粒体燕窝酸麦角硫因细胞营养内服高端美颜", "商家名": "X品牌", "主类别": "口服美容营养品", "次级类别": "保健食品/膳食营养补充食品", "品牌信息": "X品牌", "利益点": "","产品信息":["产品剂型:片剂;产地:香港特别行政区;功效:见详情;包装方式:瓶装;品名:PQQ;品牌:X品牌;有效期:24个月以上;用法:每天1次，每次2片;营养成分:见详情;适 用人群:成年人;适用性别:男女通用;颜色分类:1瓶体验装,3瓶周期装【买2送1】,5瓶尊享装【买3送2】,8瓶御龄装【买5送3】,御 老亮白⭐ 肌体年轻;食用提示:见详情\\n"],"是否包邮": "是", "链接号": 11, "原价": 4200.0, "折扣优惠": [{"优惠名": "", "折扣 价格": 20.0}, {"优惠名": "", "折扣价格": 150.0}], "券后价":1008.0}'] | [{'role': '观众', 'content': 'PQQ介绍下呢'}, {'role': 'assistant','主播': '下个品就是来讲 解11号宝贝，稍等一下 哈，主播先 把12号宝贝讲完哈。'}] | 为啥PQQ单瓶贵很多 | 是 | 看到有宝宝问单瓶价格，11号链接的X品牌PQQ是香港原产，每瓶都是独立包装，品质成本高 些，单瓶价格 自然贵一些哈，现在买还能叠加优惠 哦。 |

</div>

- 示例不代表真实模型效果，模型线上真实效果可见附录B。

### 2.3 测评方式

评测采用DeepSeek-R1对模型生成结果进行打分，DeepSeek-R1接受商品信息、对话历史、观众问题和AI主播回复作为输入给出一个对模型生成回复的评分。评分综合了以下4个维度：

- 数字人主播回复与观众问题一致性：是否正确理解观众意图，并针对观众问题正确给出了回复。如果有对话历史，需要考虑在对话历史下当前问题的真实意图；
- 数字人主播回复与商品信息的一致性：回复内容既不能超出给出的商品信息，也不能出现商品信息能够回答观众问题但是AI主播不回答的情况。如果商品信息不足以回答观众问题或者观众不是问的给出的商品，那么数字人主播应该引导观众咨询客服；
- 数字人主播回复本身一致性：回复内容本身前后不能有逻辑矛盾的情况，并且回复内容需要口播，不能出现语言不自然的回复；
- 数字人主播回复指令一致性：回复是否遵循prompt中对数字人主播的指令。

## 蒸馏DeepSeek-R1实验

在互动商品问答任务上，DeepSeek-R1在百分制回复质量评测中会比线上互动模型效果好11%（R186pt，线上互动模型75pt），为了将DeepSeek-R1的能力蒸馏到较小模型上，我们采取了三种方案进行蒸馏实验：

1. 以Qwen为基座仅蒸馏DeepSeek-R1回复部分，剔除思考部分；
2. 以Qwen为基座蒸馏DeepSeek-R1完整回复，包含思考部分；
3. 以DeepSeek-R1-Distill-Qwen为基座蒸馏DeepSeek-R1完整回复，包含思考部分。

通过实验，得到了以下几个结论：

1. 经过回复质量测评，方案C达到了三种蒸馏方案中最好的效果（83/100pt），既需要以DeepSeek- R1-Distill-Qwen为基座进行蒸馏；
2. 若以Qwen2.5-Instruct为基座进行蒸馏，是否添加cot部分没有明显区别；
3. 通过拒答一致性实验得到以下几个结论：拒答一致性会随着模型规模增长而增长，在相同数据下进行蒸馏，越大规模的模型的行为会与DeepSeek-R1更相似。拒答一致性与回复质量没有直接关联：存在大量部分可回答的边界样本，导致拒答一致性上限约为85%。

### 3.1 蒸馏方案

| 方案编号 | method | description |
| --- | --- | --- |
| A | Qwen直出答案 | 使用R1生成数据进行蒸馏，但剔除`<think>`标签包裹的思考部分 基座模型为Qwen2.5-Instruct各尺寸模型 |
| B | Qwencot | 使用R1生成数据进行蒸馏，包含`<think>`标签包裹的思考部分 基座模型为Qwen2.5-Instruct各尺寸模型 |
| C | DeepSeek-R1- Distill-Qwencot | 使用R1生成数据进行蒸馏，包含`<think>`标签包裹的思考部分 基座模型为DeepSeek-R1-Distill-Qwen各尺寸模型 |

### 3.2 生成质量实验

| 方案编号 | method | 生成质量平均分 |
| --- | --- | --- |
|  | DeepSeek-R1 | 86 |
| A | Qwen14B直出答案（5k8训练集） | 78 |
| B | Qwen14Bcot（5k8训练集） | 78 |
| C | DeepSeek-R1-Distill-Qwen-14Bcot（5k8训练集） | 83 |
|  | 线上效果 | 75 |

- 采用2.3中的评测方式对模型生成的回复进行评测

### 3.3 模型规模实验

- 模型在输出回复的同时也会输出是否能够回答问题的二分类，观众问题的问题和商品不符或者商品信息不足以回答观众弹幕均属于不能回答的类型，仅有观众问的确实是给出的商品且商品信息能够回答观众问题输出能够回答的类型。
- 在本实验中，我们希望通过对蒸馏模型和DeepSeek-R1的拒答一致性的探究来研究在直播互动域下模型规模和蒸馏效果的关系（拒答一致性不能完全代表模型性能，但是可以看出来大致的关系）。
- 验证三种方案（A、B、C）的三种尺寸模型（1.5B、7B、14B）与DeepSeek-R1的拒答一致率。

<figure class="publication-figure figure-landscape" id="blog-figure-1"><div class="figure-heading"><span class="figure-label">图 1</span><button aria-label="放大查看：图 1" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="不同模型规模与蒸馏方式下的拒答一致率。" decoding="async" height="648" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-1fd175734b7c.jpeg" width="1080"/></div><figcaption class="publication-caption">不同模型规模与蒸馏方式下的拒答一致率。</figcaption></figure>

不同蒸馏方法在各尺寸模型上与DeepSeek-R1的拒答一致率折线图

- 三种方案下，拒答一致性均随着模型规模的增长而增长，对于较小模型（1.5B）来说，直出答案是更好的蒸馏选择；
- DeepSeek-R1-Distill-Qwen在14B规模下超过直出答案，与Qwen   cot方案的拒答一致率接近。

### 3.4 量化&轻量化实验

如果直接使用bf16版的14B   reasoning模型，一次商品问答回复大约为10s，因此，需要对14B模型进行量化。量化后的RT可以达到5秒。如果使用7B模型进行reasoning，效果较差。

| 方案编号 | 精度 | 回复质量评分（百分制） | Runtime |
| --- | --- | --- | --- |
| 方案C-14B | bf16 | 83 | 10s |
| 方案C-14B | int8 | 80 | 5s |
| 方案C-7B | bf16 | 74 | 2.5s |
| 方案C-7B | int8 | 69 | 2.5s |
| 线上-14B | bf16 | 75 | 1s |

### 3.5 蒸馏探索实验小结

在本节中，我们设计并探索了三种蒸馏DeepSeek-R1的方案，并使用三种方案进行对比实验，最后去确定使用DeepSeek-R1-Distill-Qwen对完整DeepSeek-R1思考过程进行SFT的方案作为我们后续继续探索的蒸馏方案。并且，为了追求数字人互动回复速度，我们探索了模型规模的影响以及轻量化实验，在这两个实验中我们确定，由于小模型的能力不足，我们无法使用7B模型作为后续蒸馏模型的选型，仅能使用DeepSeek-R1-Distill-Qwen-14B作为后续继续优化的基座模型。而量化实验表明，int8虽然会降低模型性能，但是能够有效提升回复速度，因此我们后续将使用int8作为实际的上线模型精度进行实验。

## 推理路径压缩

### 4.1 背景

在蒸馏R1实验已经得到确切的结论后，使用了30k互动线上流量数据进行所有任务上的蒸馏，然而蒸馏完成之后，当我们准备上线前，对模型的时间进行了测试，由于R1本身的推理过程过长，导致蒸馏之后的模型同样会产生过长的输出，而超长的CoT过程，导致我们的模型虽然在性能上好于非推理模型，但RT几乎上涨了10倍（bf16模型），即使是做了int8量化，RT也上升了5倍以上，难以投入线上使用，因为在快速变化的直播间场景下，过慢的弹幕回复速度会对用户造成较差的体验。

在这个背景下，为了能够将Reasoning模型的RT降低以达到能够上到线上的标准，我们采用3种方案来压缩CoT推理路径：

A） 蒸馏过程中直接剔除所有超过400token样本；

B）复现kimi1.5 long2short DPO。使用A中剔除的样本进行重新采样，如果最短采样结果输出符合要求的样本，则将最短的采样结果作为chosen，最长采样结果作为reject进行DPO；

C）在kimi long2short DPO基础上进行改良并提出了长度-质量双偏好对齐方法DP DPO（Dual Preference DPO），将仅根据长度选择正负样本对的方式拓展为根据长度偏好和回复质量偏好两种偏好综合考量选择正负样本对的方式。

### 4.2 初步知识

- 平均rt估计方式，1\H20decodingspeed = 62.5tokens/ second，模型结构为Qwen2.5-14B。文中所有RT均为换算估计值；
- 在Reasoning  model推理过程中，主要推理耗时为decoding部分，通过阿里内部infra团队的优化，prefill部分RT可以忽略不计；
- 带有CoT的生成式奖励模型现在已经被广泛使用[3]，本文直接使用DeepSeek-R1作为奖励模型对回复质量偏好进行评分，测评方式参考2.3节；
- 推理路径压缩有类似的工作比如CoD，COCONUT  ，long2short  等较为知名的工作，拒绝采样DPO相关工作可以参考RS-DPO。（见下文参考资料）

### 4.3 剔除长样本蒸馏

<figure class="publication-figure figure-landscape" id="blog-figure-2"><div class="figure-heading"><span class="figure-label">图 2</span><button aria-label="放大查看：图 2" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="教师模型输出长度分布。" decoding="async" height="514" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-16d3885abf91.png" width="1026"/></div><figcaption class="publication-caption">教师模型输出长度分布。</figcaption></figure>

DeepSeek-R1生成样本输出长度分布图

- 上图为蒸馏训练样本长度分布，大部分输出结果token数在200-400这个区间；
- 直接过滤长decodingtoken样本：decodingtokens超过400直接舍弃，将平均decodingtoken降低至300；
- 方法缺陷：即使舍弃了所有400token以上的结果，模型仍然可能在完成训练后推理时产生400token长度以上的输出。

### 4.4 kimi1.5long2shortRejectionSamplingDPO复现

<figure class="publication-figure figure-landscape" id="blog-figure-3"><div class="figure-heading"><span class="figure-label">图 3</span><button aria-label="放大查看：图 3" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="kimi1.5long2shortRejectionSamplingDPO部分原文截图" decoding="async" height="246" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-9d7848f726f7.png" width="1022"/></div><figcaption class="publication-caption">kimi1.5long2shortRejectionSamplingDPO部分原文截图</figcaption></figure>

- follow  kimi  long2short的DPO方案，对方案A中被舍弃的样本（红色部分）使用DeepSeek-R1采样多次，如果采样到长度符合要求的结果（输出长度小于400token），则使用最短采样结果作为chosen，最长采样结果作为reject进行dpo；

- 采样结果：

| 平均chosen样本长度 | 平均reject样本长度 | 成功采样样本数 | 样本总数 |
| --- | --- | --- | --- |
| 300.1 | 515.8 | 4650 | 4915 |

- 方法缺陷：和kimi1.5原文描述的一致，该方案有效降低了模型推理长度，但与此同时也削弱了模型的回复性能。

### 4.5 DualPreference DPO：通过引入GenRM对kimi long2shortDPO方案进行改良

kimi的long2shortDPO中仅选择最短的样本和最长的样本作为正负例，而论文中提到了dpo后质量反而会下降，因此我们对质量下降的可能性进行了分析：

- 对于模型本身短cot会比长cot会有更差的表现，这点kimi1.5论文中亦有提及；
- DPO采样的样本中，短cot样本质量差于长cot样本。

基于上述分析，我们对kimi1.5  long2short中的DPO方案进行了改进，提出了新的long2short  DPO优化方法。我们希望在样本对构建时就选择那些短样本质量高于长样本的的样本对，以抵消短CoT带来的劣势，在这里，我们将DPO构造任务任务变成了多目标优化问题，一方面以回复长度短为目标进行优化，另外一方面以回复质量高作为目标进行优化，两个目标的权重则需要通过实际实验来进行trade-off。

<figure class="publication-figure figure-landscape" id="blog-figure-4"><div class="figure-heading"><span class="figure-label">图 4</span><button aria-label="放大查看：图 4" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="先做领域蒸馏,再通过质量与长度双偏好进行 DPO。" decoding="async" height="872" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-bb4538013d59.png" width="1030"/></div><figcaption class="publication-caption">先做领域蒸馏,再通过质量与长度双偏好进行 DPO。</figcaption></figure>

DP-DPO两阶段偏好对齐算法流程图

- 在阶段1中，我们基于蒸馏DeepSeek-R1实验的结论，使用30k直播互动领域数据对DeepSeek-R1-Distill-Qwen-14B进行领域适应蒸馏，由于剔除长样本之后无论长度还是评估分数均有所提升，我们直接使用剔除长样本后的数据进行领域适应蒸馏。
- 在阶段2中，我们通过双偏好拒绝采样DPO对模型进行对齐，从而实现推理路径压缩的目的：

- 首先我们使用DeepSeek-R1随机采样出K条结果；
- 在采样出了K条结果后，使用DeepSeek-R1以和Benchmark相同的测评方式，对多条采样结果进行了评估，并归一化到0~1分，将归一化之后的分数作为质量偏好分数；
- 我们将长度偏好和质量偏好均归一化为0~1的偏好分数，对两个分数加权得到一个融合分数，根据融合分数在每组采样结果中选取最高分作为DPO正样本，选取最低分作为DPO负样本；
- 如果上个步骤中正负样本的融合分数之差小于一定阈值，那么整组数据都会被舍弃，阈值由舍弃比例确定；
- 最后使用构建好的正负样本对对阶段1中领域蒸馏后的模型进行DPO对齐训练。

#### 4.5.1 质量-长度双偏好DPO样本构造

加权分数计算

对于每个有效样本<img alt="原文图 24" class="inline-equation" decoding="async" height="29" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-5cc443a86778.jpeg" width="75"/>（其中<img alt="原文图 32" class="inline-equation" decoding="async" height="25" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-a5d4d3e88922.jpeg" width="26"/>表示有效样本集合， <img alt="原文图 33" class="inline-equation" decoding="async" height="29" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-c6f25e8e2cd7.jpeg" width="26"/>代表样本<img alt="原文图 34" class="inline-equation" decoding="async" height="24" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-e1b430953f1c.jpeg" width="20"/>的质量分数），其加权分数<img alt="原文图 35" class="inline-equation" decoding="async" height="29" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-b1af5e323023.jpeg" width="31"/>定义为：

<figure class="publication-figure figure-landscape" id="blog-figure-5"><div class="figure-heading"><span class="figure-label">图 5</span><button aria-label="放大查看：图 5" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="归一化后组合长度偏好与质量偏好。" decoding="async" height="217" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-bdaec00ef893.jpeg" width="1080"/></div><figcaption class="publication-caption">归一化后组合长度偏好与质量偏好。</figcaption></figure>

其中：

- <img alt="原文图 44" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-bacd2b571179.jpeg" width="98"/>是权重参数，分别控制长度偏好和质量偏好的相对重要性；
- <img alt="原文图 52" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-d0369dcf2c57.jpeg" width="20"/>是样本<img alt="原文图 60" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-4bfbc07b3660.jpeg" width="23"/>的长度；
- <img alt="原文图 61" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-af00e06bbea3.png" width="47"/>是输出长度归一化的最大值；
- <img alt="原文图 69" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-a26944a9b2dc.png" width="45"/>是质量分数归一化的最大值。

样本选择

选择加权分数最高的样本作为 chosen，分数最低的作为 reject：

<figure class="publication-figure figure-landscape" id="blog-figure-6"><div class="figure-heading"><span class="figure-label">图 6</span><button aria-label="放大查看：图 6" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="按加权分数选取 chosen 与 reject 样本。" decoding="async" height="108" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-87bfb3ef07cf.jpeg" width="1080"/></div><figcaption class="publication-caption">按加权分数选取 chosen 与 reject 样本。</figcaption></figure>

最终的分数差<img alt="原文图 78" class="inline-equation" decoding="async" height="22" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-d8999e5cfbf1.png" width="34"/>定义为：

<img alt="原文图 79" class="inline-equation" decoding="async" height="32" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-5fd8183864c0.jpeg" width="216"/>

当<img alt="原文图 80" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-5c0ba50a96b5.png" width="68"/>时，正负样本对才会被选择为DPO偏好对齐数据，<img alt="原文图 88" class="inline-equation" decoding="async" height="28" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-f47520a9f387.jpeg" width="21"/>的选择与drop比例有关。

#### 4.5.2 质量-长度双偏好超参探索

推理长度、回复质量双目标权重搜索

<figure class="publication-figure figure-landscape" id="blog-figure-7"><div class="figure-heading"><span class="figure-label">图 7</span><button aria-label="放大查看：图 7" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="长度权重变化时,正负样本的长度差与质量差。" decoding="async" height="565" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-1bcd5b094eb2.png" width="1000"/></div><figcaption class="publication-caption">长度权重变化时,正负样本的长度差与质量差。</figcaption></figure>

偏好数据正负样本长度差、质量分数差随长度偏好权重变化折线图

- 蓝线为样本对平均长度差随长度偏好权重变化的折线，如果完全按照质量偏好选择正负样本对，正样本的平均长度会比负样本长10个token，如果比负样本短213个token，和4.4中的采样结果接近。
- 红线为样本对质量分数差随长度偏好权重变化的折线，如果完全按照质量偏好选择正负样本对，正样本的平均质量分数会比负样本高2.77/10分，如果完全按照长度偏好选择正负样本对，正负样本的平均质量分数几乎一致。
- 交叉处在0.4~0.6区域，最终超参选择一方面会考虑业务上对于长度和质量的偏好，另一方面会考虑drop掉部分尾部正负样本对后的结果。

在偏好权重调整的基础上，drop掉融合分数差靠后的样本对

<figure class="publication-figure figure-landscape" id="blog-figure-8"><div class="figure-heading"><span class="figure-label">图 8</span><button aria-label="放大查看：图 8" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="按综合分数差过滤区分度不足的偏好对。" decoding="async" height="444" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-3701b331d269.png" width="1000"/></div><figcaption class="publication-caption">按综合分数差过滤区分度不足的偏好对。</figcaption></figure>

左子图为正负样本平均长度差随drop比例和长度偏好权重变化热力图，右子图为回复质量热力图

- 左图为长度差随长度偏好权重和舍弃比例DropRatio变化的热力图，越黄的部分，正负样本长度差越大；
- 左图为质量分数差随长度偏好权重和舍弃比例Drop Ratio变化的热力图，越黄的部分，正负样本质量分数差越大；
- 选点的同时需要考虑不能使用太大的DropRatio<img alt="原文图 91" class="inline-equation" decoding="async" height="25" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-5d10756ef9e3.jpeg" width="28"/>，否则DPO对齐样本过少会降低泛化性；
- 最终超参选择：<img alt="原文图 99" class="inline-equation" decoding="async" height="33" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-1767d8d96e4e.jpeg" width="158"/>。

#### 4.5.3 多目标优化DPO样本构造结果

| <img alt="公式" class="inline-equation" decoding="async" height="29" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-9ca96967c70f.png" width="28"/> | <img alt="公式" class="inline-equation" decoding="async" height="34" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-d8220b7c2959.png" width="33"/> | <img alt="公式" class="inline-equation" decoding="async" height="26" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-bc0abb20e959.png" width="57"/> | <img alt="公式" class="inline-equation" decoding="async" height="29" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-53fb79ae46cf.png" width="63"/> |
| --- | --- | --- | --- |
| 1.0 | 0.0 | 213 | 0 |
| 0.6 | 0.3 | 204 | 2.57 |

- 按照最终超参选择后的正负样本对正样本平均长度比负样本短204token，正样本的平均质量分数比负样本高2.57分

#### 4.5.4 进行DPO偏好对齐训练

- 代表来自于SFT的loss，用于防止出现reward/chosen与reward/reject同时下降的情况，当同时下降时，模型虽然会学习到偏好但性能会大幅下降，通过调整中观察reward值来调整训练超参。

### 4.6 推理路径压缩实验结果

| method | 商品问答评测分数 | 平均长度 | 平均RT | 最长长度 | 最长RT |
| --- | --- | --- | --- | --- | --- |
| baseline | 84.0 | 349.0 | 5.58 | 742.1 | 11.87 |
| 剔除长样本蒸馏 （SFT模型） | 84.9 | 308.1 | 4.93 | 567.9 | 9.07 |
| long2short-DPO | 83.9(-1.0pt) | 265.1 | 4.24(-1.34s) | 390.2 | 6.24(-5.63s) |
| DP-DPO （ours） | 85.3(+0.4pt) | 266.0 | 4.26(-1.32s) | 408.0 | 6.53(-5.35s) |

- baseline为直接进行蒸馏，不对数据进行任何操作，具体蒸馏方案为第3大节中使用DeepSeek-R1-Distill-Qwen进行蒸馏的方案；
- 剔除长样本蒸馏为直接按token数剔除长样本进行蒸馏，不仅在推理长度上短于baseline，而且性能表现上也更好；
- 表中正负值的参照方法为剔除长样本蒸馏（SFT模型）；
- long2short-DPO和DP-DPO均在SFT模型基础上进行训练，分别是第4.4节中对kimi long2short-DPO的复现以及第4.5节中我们提出的双偏好DPO方法。

### 4.7 DPO泛化性问题与解决方案

尽管DPO在验证集上表现良好，但实际上线后，在线上流量测试中虽好于long2short DPO但综合测评分大幅下降，且低于未推理压缩的SFT模型，经过对线上流量测试集表现的分析，我们确定是DPO带来的泛化性问题，为了解决DPO带来的泛化性问题，我们采用了简单直接的解决方案：扩大数据规模。我们对所有训练集中商品问答数据进行4.5节中所提到的双偏好数据构造流程，将数据规模扩增了5倍后进行双偏好DPO：

| method | 验证集综合 评测分数 | 验证集多轮 评测分数 | 线上流量综合 评测分数 | 线上流量多轮 评测分数 |
| --- | --- | --- | --- | --- |
| DeepSeek-R1 | 85.5 | 84.6 | 86.0 | 84.4 |
| 剔除长样本蒸馏（SFT模型） | 84.9 | 82.3 | 83.0 | 80.8 |
| long2short-DPO | 83.9 | 81.5 | 81.9 | 78.7 |
| DP-DPO w/ 3k data | 85.3 | 83.3 | 82.5 | 81.2 |
| DP-DPO w/ 15k data | 87.3 | 86.6 | 84.8 | 82.4 |

- 线上流量测试集与验证集的构建方式一致，区别在于验证集和训练集是从同一时间段的互动流量上构建，而线上流量测试集是在推理模型上线之后的流量上构建；
- 扩增数据行为是在训练集上DPO部分扩增，扩增数据不包括推理模型上线后的流量数据；
- 切换为线上流量进行测试后，我们自己训练的所有模型在性能上均有所下降，说明过拟合现象普遍存在，其中DPO模型性能下降幅度较于SFT模型更大，其原因在于在较小规模数据集上进行DPO后削弱了模型的泛化性；
- 双偏好DPO性能好于long2short DPO在线上流量上依然成立；
- 使用大规模数据进行双偏好DPO后，DP-DPO在线上流量上的评测表现大幅超过SFT模型。

### 4.8 消融实验

为了确定性能的提升与长度的缩短这两个优化以及4.7节中所提到的泛化性提升来自于DPO而非在之前所提到的数据构造流程，我们对比了两种方案：

1. 仅使用双偏好拒绝采样构建的样本对中的正样本进行SFT（DP-SFT）；

2. 在方案1 SFT模型的基础上进行双偏好DPO（DP-DPO）。

可以保证两种方案所使用的数据完全相同（15k双偏好对比数据），区别只在于一个进行了后续的DPO，一个没有。测试集与4.7节中的线上流量测试数据集保持一致。这里给出了仅剔除长样本进行蒸馏的SFT模型（4.3节）作为参照方法。

对比实验结果如下：

| method | 验证集综合评测分数 | 验证集多轮评测分数 | 平均长度 | 平均RT | 最长长度 | 最长RT |
| --- | --- | --- | --- | --- | --- | --- |
| SFT模型 | 83.0 | 80.8 | 309.9 | 4.96 | 677.9 | 10.85 |
| DP-SFTonly | 83.3 | 80.3 | 302.1 | 4.83 | 490.5 | 7.85 |
| DP-SFT+ DP-DPO | 84.8(+1.5pt) | 82.4(+1.9pt) | 272.3 | 4.36(-0.47s) | 382.8 | 6.12(-1.73s) |

- 使用双偏好构造数据集进行SFT无法直接提升模型性能，但是可以有效降低模型的最长输出长度；
- 双偏好DPO模型不仅在性能上远好于在双偏好数据集正样本上进行SFT的模型，而且在推理路径压缩效果上也有明显的提升。

### 4.9 讨论：DPO训练过程中质量性能和长度随epoch变化

| epoch | kimilong2short DPO · 平均回复长度 | kimilong2short DPO · 平均回复质量 | DP-DPO(ours) · 平均回复长度 | DP-DPO(ours) · 平均回复质量 |
| --- | --- | --- | --- | --- |
| 0 | 308.1 | 84.9 | 308.1 | 84.9 |
| 1 | 265.1 | 83.9↓ | 259.3 | 83.9↓ |
| 2 | 269.8 | 83.3↓ | 266.0 | 85.3↑ |
| 3 | 271.5 | 81.6↓ | 271.1 | 85.1↓ |

- 在训练过程中，单一偏好DPO训练会使得平均回复质量一直下降；
- 双偏好DPO训练会在第一个epoch学习long2short偏好时回复质量下降，而在后面两个epoch质量达到超过原模型的水位。

## 总结

首先我们在互动测试集上发现了DeepSeek-R1在互动任务中的优异表现，于是我们展开如何将DeepSeek-R1能力蒸馏到我们互动小模型中的探索，我们设计了三种蒸馏方案，并通过实验，确定了以 DeepSeek-R1-Distill-Qwen-14B模型作为蒸馏实验基座模型的方案。

完成蒸馏后，由于长推理的耗时过长无法满足直播数字人互动的时间要求，我们开始对推理路径压缩进行探索。我们首先尝试了直接较为简单的剔除长样本进行SFT的方案，而后为了进一步压缩推理路径，我们对kimi 1.5中提到的long2short的DPO方案进行了复现，并成功大幅压缩了推理路径长度。

然而，kimi1.5在推理路径压缩的过程中也削弱了模型本身的回复性能，为了达到在压缩推理路径的同时保持模型性能的目的，我们对kimi的long2short DPO方案进行了改良，提出了DP DPO双偏好对齐方案，使用DeepSeek-R1作为质量奖励模型用于评估模型生成质量，在长度-质量两种偏好上进行DPO对齐训练，训练后的模型不仅推理路径压缩效果与long2short DPO接近，而且回复质量相较于SFT模型不仅不下降反而会有所提升。

我们将DP DPO模型进行了上线，然而上线之后，我们在回流数据中发现了DPO会显著降低模型泛化性的问题，为了解决泛化性问题，我们将DPO数据规模扩大了5倍，大幅提升了DPO模型在线上流量上的表现，这也证明了DPO虽然会带来泛化性问题但是能够通过增大训练数据量的方式来解决这一缺陷。

### 未来展望

1. 目前我们最好的模型相比于DeepSeek-R1仍有差距，在线上测试集中，我们最好的模型评分为84.8，而DeepSeek-R1为86.0，希望能通过后续持续不懈的探索与优化，研发出低延迟且性能超过DeepSeek-R1的互动模型；
2. 研发能够在测评上超过DeepSeek-R1的奖励模型，从而更好的评估&优化互动模型，且如果我们有足够强大的奖励模型后，我们就可以摆脱目前只能进行离线偏好对齐的困境，进入在线强化学习的阶段；
3. 随着业务的快速发展，数字人的能力日益强大，会有更加复杂的信息（更复杂的商品信息、直播间信息、讲解信息以及多模态信息）掺杂在互动问答当中，这些日益复杂的信息也会对我们的互动模型带来新的挑战。

## 参考资料

1. KIMI K1.5:SCALING REINFORCEMENT LEARNING WITH LLMS

   https://arxiv.org/pdf/2501.12599
2. RS-DPO:A Hybrid Rejection Sampling and Direct Preference Optimization

   Method for Alignment of Large Language Models

   https://arxiv.org/pdf/2402.10038
3. Generative Verifiers: Reward Modeling as Next-Token Prediction

   https://arxiv.org/pdf/2408.15240
4. Chain of Draft:Thinking Faster by Writing Less

   https://arxiv.org/pdf/2502.18600
5. Training Large Language Models to Reason in a Continuous Latent Space

   https://arxiv.org/pdf/2412.06769

## 附录

### A. 互动基座模型验证集完整Benchmark

| method | 描述 | 综合评分 | 多轮回复质量评分 |
| --- | --- | --- | --- |
| 无cot互动模型 | GPT4o生成数据+DeepSeek-V3生成数据+DeepSeek-R1生成数据+部分人工数据 sft Qwen2.5-14B | 79.7 | 74.7 |
| DeepSeek-R1 | 直接调用dpsk-r1 | 85.5 | 84.6 |
| QwQ-32B | 直接调用QwQ-32B | 84.6 | 80.5 |
| 蒸馏版互动模型 | 使用30k互动数据蒸馏Qwen-Distill-dpsk- 14B | 84.0 | 82.0 |
| 推理路径压缩w/ sft | 剔除所有输出长度超过 400token的样本 蒸馏Qwen-Distilldpsk- 14B | 84.9 | 82.3 |
| 长度偏好对齐 long2short DPO | 复现kimi long2short RS DPO压缩推理路径 | 83.9 | 81.5 |
| 双偏好对齐DP-DPO | kimi的long2short DPO 采样策略改良版本的推 理路径压缩方案 | 85.3 | 83.3 |
| 泛化性双偏好对齐 DP-DPO | 使用更大规模数据改善 DPO泛化性问题 | 87.3 | 86.6 |

### B. 互动推理模型真实流量示例

- 示例为线上真实回复，生成模型为未经泛化性优化的DP-DPO模型；
- 示例中对商品品牌、型号信息进行了脱敏，除脱敏内容外为真实线上回复。

<div class="wide-table">

| 弹幕 | 对话历史 | 回复 | 模型思考 |
| --- | --- | --- | --- |
| H品牌500是底部散热？还是两侧散热？ | [] | 家人问的是H品牌500冰箱的散热方式哈，50号链接51号链接都是两侧散热设计的，散热边距是零距离嵌入哈，可以看下这两个链接的详情页哦 | 好的，我需要处理观众的问题：“H品牌500是底部散热？还是两侧散热？”。首先，查看商品信息中的三个链接。 第一个商品是链接51，型号B，产品信息中提到两侧散热边距是零距离嵌入（0cm≤边距<2cm）。第二个商品是链接50，型号B，同样两侧散热边距也是零距离嵌入。第三个商品是链接49，型号B，同样两侧散热边距是零距离嵌入。所有三个商品的信息都显示是两侧散热，没有提到底部散热。因此，观众的问题可以通过商品信息回答。 根据要求，需要明确告知链接号。观众的问题没有提到具体链接号，所以回复时需要指出链接号。例如，三个链接都是两侧散热，所以可以统一回复。同时，保持口语化，使用“家人”称呼，结尾用“哈”等词。确保回复在80字内，不涉及其他信息。 |
| 哪款可以去口臭 | [] | 家人问哪款去口臭哈，22号链接的益生菌 牙膏和54、55 号链接的漱口水都有清新口气功能哦，需要的话可以看下链接哈 | 好的，我需要处理观众的问题：“哪款可以去口臭”。首先，查看商品信息。有三个商品，都是舒客的牙膏和漱口水。 第一个商品是S品牌益生菌牙膏，产品信息中功能包括清新口气和清洁，适用对象是除儿童以外。第二个是S品牌漱口水，功能有抑菌、清新口气、牙周护理、防蛀。第三个也是漱口水，功能是清新口气和牙周护理。观众问的是去口臭，这三个商品都提到了清 新口气，所以都能去口臭。 根据规则，如果商品信息可以回答，需要明确链接号。观众没有提到具体链接号，所以需要指出。回复时要口语化，提到链接号，并简要说明各款的功能。比如22号链接的牙膏，54和55号的漱口水都有去口臭的功能。同时要符合字数限制，不超过80字。检查是否满足所有要求，比如称呼多样化，使用“家人”或“亲”等。最后确保回复正确，没有使用其他标点，口语化。 |
| Y品牌1.5匹空调效果？安装？我现在直播间卖的国补后价格是多少？ | [{"role":"user","content":"主播你好。1.5匹Y品牌空调介绍下直播间的福利价格"}, {"role":"assistant","content":"下个品就是来讲解21号宝贝，稍等一下哈。"}] | 家人说的Y品牌1.5匹空调效果和安装问题比较专业呢，具体细节得问客服哈，他们肯定清楚。国补价格可以看21号链接的G品牌空调，点进去领取补贴就行，不同地区政策不一样哦。 | 好的，我需要处理观众的问题：“Y品牌1.5匹空调效果？安装？我现在直播间卖的国补后价格是多少？”。 首先，查看商品信息。有三个链接：21号、253号和171号。其中，21号和253号都是1.5匹的Y品牌空调，而171号是1匹的。观众明确提到1.5匹，所以排除171号。 接下来，检查商品信息是否能回答问题。关于效果，产品信息中有制冷量、制热量等参数，但没有直接的效果描述。安装方面，商品信息里没有提到安装服务或流程。价格方面，21号和253号的券后价都是4199元，但观众问的是国补后的价格。根据规则5，政府 补贴相关问题需要引导查看商品页是否有标签，不同地区政策不同。因此，无法直接回答国补后的价格，需要引导观众查看商品页。此外，观众之前询问过价格，主播回复了21号链接，现在观众再次提问，可能需要确认是否是同一商品。但当前问题涉及效果和安装，商品信息中没有足够的细节，所以不能直接回答。需要引导观众咨询客服，并提到链接号，让观众明确商品。 最后，确保回复口语化，符合要求，不超过80字。称呼使用“家人”，并正确提及链接号。 |
| 已下单已备注暗号 | [{"role":"user","content":"暗号是什么"}, {"role":"assistant","content":"直播间暗号：我爱D品牌"}] | 哇哦，这位家人手速快过火箭呢，备注暗号的宝宝们记得截图保留哈，下单后找客服核对暗号就能享受专属优惠啦，感谢支持哦。 | 好的，我需要处理观众的问题：“已下单已备注暗号”。首先，根据对话历史，观众之前问过暗号是什么，主播回复了正确的暗号。现在观众确认已经下单并备注了暗号，所以需要感谢观众的支持。根据要求，如果观众已经拍下商品，必须感谢他们。 同时，要保持口语化，使用活泼的语气词，比如“哦”或“哈”。另外，回复要简短，不超过80字。需要避免重复之前的回复，所以不能直接复制之前的感谢语句。结合历史对话，观众正确使用了暗号，所以应该肯定他们的正确操作，并再次感谢。可以加入一些幽默或亲切的元素，比如提到“手速快过火箭”来增加趣味性。同时，结尾用“哈”符合要求。检查是否有其他需要注意的点，比如售后问题、是否负面情绪等，这里没有，所以直接感谢即可。确保标点正确，只用逗号和句号。最终回复应该符合所有要求，既专业又亲切。 |
| 12链接16+512有什么赠品 | [] | 宝宝，12号链接的O品牌手机现在下单赠送半入耳式有线耳机哈，其他规格也是一样的赠品哦。 | 好的，我需要处理观众的问题：“12链接16+512有什么赠品”。首先，查看商品信息。商品信息中的链接号是12，对应的是O品牌 R型号13手机。观众明确提到了链接号12，所以不需要引导他们确认链接号。商品 信息中的赠品部分显示是直播间赠品专用的耳机，但赠品信息可能与存储容量无关。 根据规则，如果商品信息中有明确的赠品信息，就直接回答。这里赠品是针对所有购买的，所以应该告诉观众赠品是耳机。需要确认是否所有规格都赠送，但商品信息中没有特别说明不同规格是否有不同赠品，所以按统一回复。然后按照要求，回复时要口语化，使用活泼的结尾词，比如“哈”。所以回答应该是：“宝宝，12号链接的O品牌手机现在下单赠送半入耳式有线耳机哈，其他规格也是一样的赠品哦。” |
| 我还以为是真人主播 [-666] | [] | 哎呀被发现了呢，其实我是充电两小时待机一整天的数字人哈，不过我的段子都是新鲜的，保证不卡壳，要听我讲冷笑话吗。 | 好的，用户说“我还以为是真人主播”，这可能是在质疑主播的身份。根据规则，当被问到是否是AI、机器人或数字人时，需要明确告知是数字人，并且用幽默的方式回应。我需要先确认用户的问题类型，这里属于询问是否是真人，所以需要触发规则5。 接下来，我需要编一个笑话，同时明确说明自己是数字人。笑话需要符合幽默风格，同时保持口语化。比如，可以拿数字人的特点开玩笑，比如充电或者吃数据之类的，这样既有趣又符合身份。 然后，检查回复是否符合其他要求：口语化，标点正确，长度限制在80字内。比如，用“充电两小时待机一整天”这样的梗，比较贴近生活，容易引起共鸣。结尾加上“哈”来增加活泼感。 最后，确保没有重复历史回复，因为对话历史是空的，所以没问题。整体结构要自然，符合主播开朗幽默的性格设定。 |
| 哪里发货 | [] | 亲，这个吐司是山东发货的哈，有次日达服务的，到手很快哦。 | 好的，我需要处理观众的问题“哪里发货”。首先查看当前商品信息，里面有一个字段是“省份:山东省”。这说明商品的发货地是山东。根据要求，如果商品信息足够回答问题，就严格按照信息回复。所以这里可以回答观众的问题。然后检查回复是否符合口语化，不使用特殊符号，称呼可以多样化。比如用“亲”来称呼，然后说明发货地是山东，并提到次日达服务。确保回复在80字以内，没有多余内容。确认没有历史对话需要参考，所以直接回复即可。 |
| 35号链接和36号链接有什么区别 | [] | 家人问35和36 号链接区别哈，35号是儿童专用EVA材质券后39.8，36号是通用款PEVA材质券后35.9，适用对象和材质不同哦。 | 好的，我需要处理观众的问题：“35号链接和36号链接有什么区别”。首先，查看商品信息。35号链接的商品是B品牌儿童雨衣，型号F-Ffr0046，材质是EVA，适用对象是儿童，颜色分类有多种，原价45.8，券后39.8。36号链接的商品同样是B品牌，但型号F040，材质PEVA，适用对象是通用，颜色分类不同，原价和券后价都是35.9。 观众明确提到了两个链接号，所以需要比较两者。主要区别在于型号、材质、适用对象和价格。35号针对儿童，材质EVA，价格稍高；36号适用通用，材质PEVA，价格更低。需要将这些信息用口语化的方式告诉观众，并指出链接号。同时，确保回复在80字内，使用不同的称呼，比如“家人”。不需要引导客服，因为商品信息足够回答问题。 |
| 链接47和93有什么区别 | [] | 家人问的47和93号链接区别哈，47号是B品牌1 Ring蓝牙5.3版券后138，93号是小云朵MC1蓝牙5.4版券后269，型号和配置不同价格也差挺多的哦 | 好的，我需要处理观众的问题：“链接47和93有什么区别”。首先，查看商品信息。链接47的商品是B品牌1 Ring蓝牙耳机，型号是B品牌1 Ring，蓝牙版本5.3，原价169，券后138。链接93的是B品牌MC1，型号B品牌小云朵MC1，蓝牙5.4，原价409，券后269。两者型号不同，属于不同产品。 根据规则，观众明确提到了链接号，所以需要比较这两个链接的商品。商品信息中有足够的信息来回答区别，比如型号、蓝牙版本、价格等。需要明确指出链接号，并说明主要区别，比如型号、蓝牙版本和价格。同时要口语化，保持简洁，不超过80字。不需要引导客服，因为信息足够。还要注意称呼多样化，比如用“家人”或“亲”。 |
| 您好多Tc 口的有推荐么 | [{"role":"user","content":"请问C1和MC1有舍区别"}, {"role":"assistant",""content":"家人说的C1和MC1区别我这边没找到呢，不过93号链接的A品牌MC1现在有活动哦，券后269就能带回家，家人可以看下是不是这个哈"}] | 家人想要多Type-C口的话可以看下59号链接的拓展坞和84号链接的耳机哈，拓展坞有Type-C接口，耳机也有Type-C款，具体需要哪个可以告诉我链接号哦 | 好的，我需要处理观众的问题：“您好多 Tc 口的有推荐么”。首先，观众提到的“多 Tc 口”可能是指Type-C接口的设备。接下来，我要检查商品信息中是否有相关产品。查看商品信息，第一个商品是A品牌的有线耳机，支持Type-C接口，链接号84。第二个商品是A品牌的拓展坞，同样支持Type-C接口，链接号59。这两个商品都涉及Type-C接口，但观众的问题比较笼统，没有指定具体类型，比如耳机还是扩展坞。 根据规则，如果观众的问题涉及多个商品，需要明确回复并提及链接号。这里两个商品都符合条件，所以需要推荐两者。同时，需要口语化，使用不同的称呼，比如“家人”或“亲”，并引导观众说明具体需求或链接号。此外，要确保回复简短，不超过80字。 因此，回复应指出两个链接号的商品，并简要描述它们的用途，同时询问观众具体需求。这样既符合商品信息，又引导观众进一步明确问题。 |

</div>
