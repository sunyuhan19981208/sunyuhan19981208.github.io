{
  "title": "Harness-Aware Training：适应运行环境的变化",
  "summary": "工具、规则和提示词会变，训练也不能只认一个版本。"
}

我们把直播 Agent 的规则、工具和提示词拆到了 Harness 里，希望业务改动不必每次都重新训练模型。但很快遇到另一个问题：运行环境改了，小模型未必跟得上。

大模型通常能读懂新配置，延迟却太高；小模型够快，但在固定配置上微调后，容易记住工具名、Skill 名称和提示词的写法。

Harness-Aware Training（HAT）要解决的，就是这种“上线后环境一直变，训练时却只见过一个版本”的错位。


## 直播场景的约束 {#先看直播间里的约束}

<!-- image:harness-aware-training-cn:images/figure-131cab4defa7.png | 直播数字人系统中，互动 Agent 连接弹幕输入与口播输出。 -->

在直播电商场景中，数字人主播需要：

- 实时回答观众弹幕中的商品问题（价格、优惠、规格对比等）；
- 执行运营策略（调整讲品顺序、触发优惠话术、处理售后问题等）；
- 公开口播到整个直播间（回复会通过 TTS 合成为语音，由数字人公开说出）；

互动 Agent 位于弹幕输入与口播输出之间：结合上下文理解问题，调用业务工具找资料，按 SOP 生成回复，再交给 TTS 和数字人渲染。同一时段的多条弹幕也可合成一个请求。这里讨论的是收到观众消息到产出公开回复的这一段，需要同时满足信息准确、规则遵循和低延迟。

数字人主播的每次回复是面向整个直播间的公开发言，这意味着一次错误回复（比如虚假承诺、价格错误）可能引发客诉。这对算法的准确性要求极高。

业务规则更新快，模型训练往往跟不上。通用大模型更能读懂新配置，但延迟高；小模型便于部署，微调后却可能只熟悉训练时的 Harness。我们希望保留小模型的速度，让它按当前规则执行，减少配置变动后重新训练的需要。

## Harness 设计与迭代 {#先迭代运行环境再讨论训练}

### Harness 的职责 {#哪些能力放进-harness}

<!-- image:harness-aware-training-cn:images/figure-5e18cb6523c1.png | 可独立更新的 Harness 模块与 Agent 执行循环。 -->

我们将 Agent 的执行环境定义为一个 Harness 状态，它由四个独立可更新的模块组成：

每个模块的职责如下：

<!-- image:harness-aware-training-cn:images/figure-8d63760cf7b9.png | Skills、Tools、Prompt Pipeline 与 Hooks 的职责。 -->

四个模块与模型权重分别做版本管理。修改 Skill 或新增 Hook 后，可以先回归运行配置，不必立即重训。Skill 是带描述的 Markdown 模块，完整内容按需加载。最终回复前至少加载一个 Reply Skill；需要特定工具链时再加载 Strategy Skill。规则加载有明确记录，开发者也能查到回复使用了哪一版策略。

### 请求处理流程 {#一次请求怎么走完}

一个完整的请求经过以下阶段：

1. 加载与规范化上下文：校验请求，组装商品/FAQ/直播间/对话状态
2. 组装 Prompt：结合基础指令、商品配置、检索上下文和已加载 Skills
3. 运行 Agent Loop：在可配置的轮次限制下，策略模型可以加载 Skill、发起工具调用、处理返回结果、提出最终回复
4. 应用 Hook 检查：覆盖输入校验、工具参数、Skill 加载要求、回复格式、事实风险、重试控制
5. 提取与分发回复：移除内部推理字段，保留结构化轨迹，路由到下游通道

一个典型的轨迹记录如下：

```
input.danmaku = "3号链接多少钱？"
context.current_link_id = 1
call[1] = get_product_info_by_link_id(link_id=3)
result[1] = {name: "防晒霜SPF50", price: 89}
call[2] = load_skill(skill="item_qa")
reply = "3号链接是防晒霜SPF50，现在券后价89元哈。"
```

### 固定权重下的规则迭代 {#先固定权重试着改规则}

Harness Evolution：在模型权重完全固定的情况下，通过修改 Skills、Prompts、Hooks 和 Tools 来改善 Agent 表现。它是人机协同的，而非全自动：

```
Diagnose → Confirm → Edit Harness → Evaluate → Regression Check
```

五步循环详解：

1. AI 诊断（Diagnose）：分析最新评测结果，聚类主要失败原因，附上代表性 bad case，提出根因假设；
2. 人工确认（Confirm）：开发者审查提议的 Skill/Prompt/Hook/Tool 修改，接受、修改或拒绝；
3. AI 辅助编辑（Edit）：执行确认的修改，保留版本化配置快照；
4. 人工触发评测（Evaluate）：在dev-set上运行推理和评分；
5. 回归检查与规划（Regression）：对比变更效果，检查新引入的回归，由人决定是发布、回滚、继续迭代还是停止；

停止规则： 当剩余错误是稀疏的长尾case，且局部规则添加更可能导致跨类别回归而非系统性改善时，停止迭代。

### 规则迭代中的取舍 {#迭代过程中规则并非越多越好}

<!-- image:harness-aware-training-cn:images/figure-b762faa31e57.png | 固定模型权重下的 Harness 迭代；后续长尾修复可能带来回归。 -->

先看固定权重的结果：Baseline 的准确性 / 有效性为 82.40 / 87.16，Evolution 2 达到 92.55 / 92.75，分别提高 10.15 / 5.59 个百分点。这段没有更新模型，改的是 Skills、提示词、Hooks 和工具配置。

Evolution 3–4 继续修长尾问题，Skills、Hooks 与全局指令之间却引入相互影响，两项指标都回退了。因此，每轮编辑都需要回归检查，并在继续修复已无整体收益时早停。

固定权重迭代时，需要注意：

- Harness Evolution非单调性：更多规则不一定更好，长尾 fix 容易引发跨类别回归；
- 早停很重要：当剩余 bad case 都是稀疏长尾时，继续加规则的边际收益为负；
- 人机协同：AI 负责诊断和编辑，人负责确认和决策——全自动 Harness 自进化目前尚不成熟；
- 版本绑定：每个发布必须绑定 Harness commit，否则朝错误方向自进化后无法进行恢复。

## Harness-Aware Training {#把环境变化放进训练分布}

### 固定配置训练的局限 {#配置改了模型为什么跟不上}

只在一版 Harness 上做 Fixed-Harness SFT，模型可能记住配置的写法，而未学会读取环境。排查时关注几种依赖：

- 记住特定 Skill 名称，而不是理解 Skill 的语义；
- 根据熟悉的 schema 字符串选择工具，而不是读取工具描述；
- 只在特定 Prompt 格式下遵守规则。

我们的预实验结果清楚地展示了这一问题：

<!-- image:harness-aware-training-cn:images/figure-6256ef1cf6ff.png | 固定 Harness 微调后的任务收益与泛化退化。 -->

这次 Fixed-Harness SFT 虽然提高了业务指标，通用指令遵循和 Prompt 鲁棒性却下降了。模型要适应新的 Harness，又离不开这两种能力。

HAT 把配置变化放进训练。同一个业务任务在不同 Skill 名称、工具描述和提示词布局下出现，要求模型读取当前规则，以适应部署后的环境更新。

### Harness 状态增强 {#让模型少认名字多读规则}

<!-- image:harness-aware-training-cn:images/figure-c70902541e19.png | Harness 状态增强及训练过程。 -->

左侧为 Harness State Augmentation示例；右侧为RL/RFT 示意图

Harness-State Augmentation（HSA）沿五个维度改变 Harness 的表达与组织方式，减少模型对固定字符串的依赖。增强后仍需保留任务语义，才能训练模型适应真实更新；若环境本身被改坏，样本就失去了这个作用。

<!-- image:harness-aware-training-cn:images/figure-761d4a0a132c.png | HSA 覆盖的五类运行环境扰动。 -->

### 三阶段训练 {#三个训练阶段各补哪一块}

完整的训练 Pipeline 包含三个阶段，每个阶段解决一个不同的能力缺口：

#### HSA-SFT：任务训练 {#第一步hsa-sft先学会任务}

HSA-SFT 从真实直播间交互数据出发构造训练样本。流程如下：

1. 数据准备：每个样本包含观众问题、直播间/商品上下文，以及对应的 Harness 配置；
2. HSA增强：对 Harness 状态进维增强，强模型（DeepSeek-V4-pro）分别在原始和增强 Harness 下生成候选轨迹标签；
3. 质量过滤：用Judge根据准确性、有效性进行过滤，只保留高质量样本；
4. SFT 训练：学生模型在多种 Harness 变体下学习相同任务语义。

Hook 重试轨迹的处理策略： 生产中 Hook 可能提示格式错误并要求修正。我们希望模型学会纠错，但不希望它学会"先出错再靠重试"的策略。因此：

- 绝大多数重试轨迹：删除中间失败和 Hook 交互，只保留最终正确行为；
- 少量完整重试轨迹：保留，使模型具备理解 Hook 提醒并恢复的能力；

训练数据规模：万级数量下的 RFT 执行轨迹，输入数据来自真实数字人直播日志。

#### General OPD：恢复通用能力 {#第二步general-opd补回通用能力}

Domain-specific SFT（即便是 HSA-SFT）仍可能侵蚀通用能力。为了对抗这种退化，我们进行OPD来恢复模型在 SFT 过程中灾难性遗忘的通用能力：

- 教师模型：HSA-SFT 之前的基座模型（Qwen3.6-35B-A3B）；
- 数据：Tulu3通用指令数据集；
- 方法：学生以on-policy方式采样回复，最小化与基座模型分布的KL散度；

直觉解释：让学生模型在通用任务上"回忆"起它作为基座模型时的能力。

General OPD 在 Fixed-Harness SFT 后恢复了 8.5 分 IFEval，在 HSA-SFT 后增加 0.2 分。这与 HSA-SFT 先保留通用能力、OPD 再恢复残余损失的分工相符。OPD 增幅较小，也可能因为前一步保留得更多。

#### HSA-RL：交互训练 {#第三步hsa-rl自己进环境练习}

<!-- image:harness-aware-training-cn:images/figure-0dc59e2b40bc.png | HSA-RL 在工具调用段与回复段分别分配奖励。 -->

HSA-RL 从 HSA-SFT + General OPD checkpoint 开始，让学生在仿真环境里交互。监督数据覆盖了多种配置，但主要是教师的成功路径；学生部署时还会选错 Skill、遇到工具异常或被 Hook 要求重试。RL 让这些动作和反馈进入训练，学习继续执行与错误恢复，同时接触变化后的 Harness。

RL 训练设计：

- 优化算法基于 GRPO，整合入GDPO 的reward normalization策略以及GSPO的sequence-level重要性采样策略；
- 四维奖励信号：准确性（Accuracy）、有效性（Effectiveness）、工具调用合理性（Tool Rationality）、Skill 选择合理性（Skill Selection）；
- 工具调用段和回复段作为两个独立的state group分别计算advantage；
- 辅助 CoT 长度惩罚：抑制不必要的过长推理；
- HSA应用于rollout前：部分rollout使用原始 Harness，部分使用增强 Harness；

训练数据规模：千级数量的交互任务。

### 仿真环境与失败恢复 {#让失败和恢复也进入训练}

仿真环境是HSA-RL的基础。它需要实现完整的 Harness Agent 控制流，包含四个组件：

- 输入仿真：经过合规处理后的直播场景日志池中采样真实用户输入：商品问询、闲聊、购买意图、售后问题、多意图弹幕。每个输入配以模拟的直播间状态（商品列表、对话历史、观众行为信号）。
- Harness Agent 调度：实现完整的 Harness Agent 控制流：Skill 路由逻辑、Hook 检查点触发（输入校验、参数检查、回复格式、Skill 加载强制）、多轮交互循环管理。
- 工具执行仿真：工具调用在沙盒化的服务器上执行，返回通过日志还原的真实的商品详情、价格和库存信息。同时注入受控故障（超时、格式错误、权限拒绝）以暴露模型于错误恢复场景。
- 增强 Harness 配置：环境在增强的 Harness 状态下运行，从而模拟出 Harness 变化的场景。

训练与仿真需要配合：

1. 三阶段各司其职：HSA-SFT 建立 Harness 鲁棒性，OPD修复通用能力，HSA-RL强化真实交互；
2. 仿真环境的故障注入很关键：没有错误恢复经验的模型，线上遇到工具异常时更难恢复；
3. CoT 长度惩罚：不加惩罚，模型的思维链会越来越长，直接推高线上延迟；

## 评测设计 {#除了答得好还要测什么}

### 评测数据 {#几组互补的评测数据}

我们构建了四个互补的离线评测集，总计数千条：

<!-- image:harness-aware-training-cn:images/figure-e408bd74ca9a.png | 四个互补的离线评测集。 -->

此外还有：

- Judge校准集：合规处理后的真实直播交互 + 人工标注，用于对齐 Judge；同时也被用于 Harness 的非训练优化。
- 部署回放集：测量实际端到端部署延迟；

评测维度定义：

- Accuracy（准确性）：二值指标，惩罚事实错误、无依据的商品声明、虚假承诺；
- Effectiveness（有效性）：0/0.5/1 三档，衡量回复是否满足观众意图并提供有用信息；

### Judge 与人工评分的一致性 {#先看看-judge-和人工是否一致}

<!-- image:harness-aware-training-cn:images/figure-55b4328e73ac.png | Judge 与人工标注的一致率随校准迭代提高。 -->

Judge Agent 用 Skills 写评分规则、Tools 查商品依据、Hooks 约束流程。我们根据它与人工的分歧修改评分和取证方式，最终由 3 个模型投票。6 轮后，Accuracy 一致率从 81.54% 升至 90.46%，Effectiveness 从 63.70% 升至 82.2%。这两项衡量 Judge 与人工的一致程度，不是被评模型的回答准确率。

校准过程：

1. 多位标注员对真实交互独立标注；
2. 使用标注后数据自动校准 Agent-as-a-Judge；
3. 最终配置：Accuracy 一致率 90.46%，Effectiveness 一致率 82.2%。

Judge 校准中需要检查：

1. 评测 Judge 也需要迭代 Harness。我们做了 6 轮 Judge Evolution，Accuracy 一致率才超过 90%；
2. Judge 的角色、数据与配置应单独记录，并检查训练奖励与最终评测之间的依赖；
3. 校准集和测试集分开使用：前者用于改进 Judge，后者用于模型评测。

## 效果、消融与部署

### 业务效果与通用能力 {#业务效果和通用能力一起看}

<!-- image:harness-aware-training-cn:images/figure-b533878691cf.png | 任务质量、Harness 变化与通用指令遵循的主实验。 -->

关键结论：

- HAT在T1上达到 94.8，超越了最强Top模型GLM-5.2的93.0——用一个35B-A3B的轻量级MoE模型超过了千亿参数级大模型；
- HAT在T2上达到 94.6，与T1几乎持平（仅差 0.2），说明对 Harness 变化高度鲁棒；
- Fixed-Harness SFT 的 IFEval 下降 7.7 分，HAT 反而上升了 2.0 分

<!-- image:harness-aware-training-cn:images/figure-1cf4ed652a6f.png | 合成场景中的工具和提示词鲁棒性。 -->

T3 的 Prompt Robustness 子集上，Fixed-Harness SFT 比基座低 4.6 分。业务指标改善的同时，模型对提示词变化的适应能力可能下降。

### 训练阶段消融 {#把训练阶段拆开看}

<!-- image:harness-aware-training-cn:images/figure-ddf46a65f883.png | HSA、General OPD 与 RL 的阶段消融。 -->

各训练阶段的作用：

1. 固定环境微调容易产生过拟合导致泛化变差，用 Harness 增强（HSA）微调能兼顾任务性能和泛化能力；
2. General OPD能恢复 SFT 训练后灾难性遗忘导致的基础能力退化，HSA能提前防止泛化退化，这俩方法组合起来整体效果最好；
3. RL阶段虽然能继续拉高业务指标，但在固定环境下会严重掉泛化，必须配合HSA才能防止过拟合。

### Harness 变更测试 {#真改一次-harness再测模型}

<!-- image:harness-aware-training-cn:images/figure-e88ed0f7d182.png | Harness 更新后，两类模型对新规则的遵循差异。 -->

我们从线上新流量取 1，500 条样本，分为 500 条开发与 1，000 条测试。在开发集上诊断并修改 Harness，将相同修改用于两个模型，再用留出的测试集比较。编辑和判效果使用不同案例，以检查真实业务更新能否让模型受益。

<!-- image:harness-aware-training-cn:images/figure-3e236796f3f6.png | 独立留出流量上的 Harness 编辑效果。 -->

留出测试中，HAT 的错误减少率接近 Fixed-Harness SFT 的 3 倍。同一处 Harness 修改，两个模型的遵循程度不同；这一结果对应本次编辑范围与测试分布。

### 推理压缩与 MTP 加速 {#部署时再省掉一部分生成开销}

单张 H20 部署使用 MTP 减少解码开销。NextN 头提出多个后续 token，推理引擎沿 EAGLE-style 投机解码路径验证、接受。收益取决于草稿与主模型的匹配程度，完整 Agent 链路仍需另外测时。

MTP 训练：

<!-- image:harness-aware-training-cn:images/figure-10d584cdba00.png | 领域适配过程中的 MTP 训练损失。 -->

MTP 适配放在 RL 阶段：主模型从前两阶段 checkpoint 开始，MTP 头由 Qwen3.6-35B-A3B 初始化，以 standalone 方式训练。蓝线是嫁接头 loss，绿线是原生基座在同配置下的 loss。Rollout 序列用于适应主模型分布，部署前再检查接受率、质量与完整链路耗时。

加速效果（Concurrency=1，单 H20）：

<!-- image:harness-aware-training-cn:images/figure-42ed1e2de607.png | 单 H20 低并发条件下的 MTP 推理加速。 -->

关键工程细节：

- MTP 对 HAT checkpoint 的加速（1.69×）高于 Base checkpoint（1.11×），因为 MTP 在垂域数据下训练后的投机解码接受率显著更高（平均接受率0.780 vs 0.735，平均接受长度3.12 vs 2.94）；
- MTP 是低并发优化：并发线程数=1-2 效果显著，并发线程数=4-8 加速降到 1.27×/1.19×；
- 开启 MTP 后质量无损失，略微上升基本为波动；

MTP 的适配和部署：

1. 任务训练会改变输出分布，未适配的 MTP 头可能失效；需要实际检查草稿接受率，并进行领域适配；
2. 开启 MTP 后质量无损失，略微上升基本为波动；
3. MTP 可直接通过嫁接的方式在RL阶段进行训练，此时 MTP 训练数据直接是主模的输出，反而更能拟合主模在对应域上的输出；
4. 我们也做过freeze住主模，在RL阶段只去rollout产生数据进行 MTP 训练，同样能work。

推理路径压缩：

<!-- image:harness-aware-training-cn:images/figure-0b71fe855fd5.png | 分别压缩工具调用与最终回复的推理长度。 -->

我们分别约束工具调用与回复段的 CoT，避免 RL 训练后推理越来越长。这次训练中，工具调用 CoT 从 290.6 tokens 降至 171.2，回复 CoT 从 93.6 降至 37.0。分别记录能看出生成量省在决策还是回复组织阶段，总长度无法区分这两种变化。

### 端到端延迟 {#最后看完整链路的延迟}

完整的部署延迟对比：

<!-- image:harness-aware-training-cn:images/figure-50fa756e2cd5.png | 完整 Agent 链路的部署延迟对比。 -->

完整回放中，单张 H20 的 HAT 端到端中位延迟约 3.4 秒，P95 约 8.1 秒。百炼 API 的 DeepSeek-V4 系列在同批请求中有 29%–39% 超过 15 秒。领域适配后的 MTP 草稿接受率为 78%，原生模型为 73.5%，解码速度分别为 271 和 216 tokens/s。模型与推理配置都影响结果，因此完整链路耗时和草稿头指标分别记录，吞吐量不能直接代表观众等待时间。

## 结果与限制 {#这些结果能说明什么}

独立数据上的 Harness 编辑测试使用 1，500 条新样本，其中 500 条开发、1，000 条测试，测试集不参与诊断和修改。固定 Harness 微调模型错误减少 18.1%，HAT 减少 51.7%。这验证了模型对指定变化范围的适应能力，任意新工具或新业务仍需另测。

英文报告更新版补充了人工盲测和线上 A/B。100 条成对请求中，64 条无明确偏好、35 条偏好 Harness、1 条偏好 ReAct。97.2% 胜率的分母是 36 条非平局样本。线上商品详情页浏览量按参与 UV 归一化后提高约 0.91%，这是业务参与指标，不是成交提升。

P50 3.407 秒、P95 8.114 秒来自指定 H20、MTP 配置和低并发完整回放，高并发时投机解码收益会减弱。复现还需要模型 checkpoint、Harness 版本、工具配置和推理参数，才能追查各项收益来自哪里。

系统迭代与模型训练需要配合：Harness 表达业务规则，HSA 让模型在训练中适应规则变化，评测和回放检查实际效果。新增规则也要经过这套检查，不能只修好当前案例就继续堆叠。
