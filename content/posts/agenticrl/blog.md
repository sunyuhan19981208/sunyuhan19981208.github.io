早期数字人互动是一条“意图识别—检索—生成”工作流。它能处理常见问题，但每增加一种能力，都要补标签、改分支、重新训练。一次意图判断错了，后面也很难纠正。

我们后来做了两步改造：先让模型按需调用工具，再把工具调用与回复生成拆开训练。

## 第一步：把路由交给模型

Agent 同时看到商品、历史弹幕和当前口播，决定还需要查什么。拿到工具结果后，可以继续查询或纠错；信息收集完成，再按回复规则作答。

这带来两个直接变化：多条观众问题可以合并处理，当前口播也能成为理解问题的上下文。

但多次模型调用会增加延迟。我们用大教师生成完整轨迹，再将工具调用和回复能力分别蒸馏到两个 Qwen3-30B-A3B Instruct 模型。学生不学习教师的显式思考序列，单次工具调用耗时约 0.3 秒，单卡 H20 解码约 140 tokens/s。

<figure class="publication-figure figure-landscape" id="blog-figure-1"><div class="figure-heading"><span class="figure-label">图 1</span><button aria-label="放大查看：图 1" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="AgentTuning：分别蒸馏工具调用与最终回复。" decoding="async" height="603" loading="lazy" src="../agenticrl/images/figure-9a1f6e0128ef.png" width="1080"/></div><figcaption class="publication-caption">AgentTuning：分别蒸馏工具调用与最终回复。</figcaption></figure>

## 先把最终回复练好

蒸馏后的模型能调用工具，但仍可能过度承诺或回答得不够有用。我们先固定工具调用链，只对最终回复做 GRPO，用正确性、帮助性和长度作为奖励。

训练时，工具结果和输入全部 mask，梯度只作用于最终回复。正确性约束事实，帮助性则防止模型为了避错而一味转客服。

这一阶段的线上 A/B 中，平均端到端延迟降到 1.79 秒，比原方案少 1.36 秒；多轮对话用户占比提升 2.76%。

## 端到端 RL 为什么没有顺利收敛

我们希望工具模型不再只模仿教师，于是搭建模拟直播间，让 Agent 自己进行多轮交互。

ROLL 负责训练闭环，远程环境负责商品查询、状态维护和工具执行。每次 rollout 结束后，计算奖励、屏蔽非模型生成的 token，再更新参数并同步到推理引擎。

工程上最费时间的是环境稳定性和奖励区分度。环境偶发错误足以淹没训练信号；奖励分不清好坏轨迹，调整算法也很难见效。

更关键的是信用分配：**最终回复是否正确，并不能直接说明前面的工具调用是否合理。** 把四个奖励简单加权给一个模型，反而可能让工具能力退化。

## 两个 Agent，各学自己的部分

我们把系统拆成工具调用模型和回复模型。二者共享完整交互轨迹，但只训练各自生成的部分，并使用不同奖励。

<figure class="publication-figure figure-landscape" id="blog-figure-2"><div class="figure-heading"><span class="figure-label">图 2</span><button aria-label="放大查看：图 2" class="figure-expand" type="button">查看大图 ↗</button></div><div class="figure-media"><img alt="Multi-Agent RL 的协同训练流程。" decoding="async" height="372" loading="lazy" src="../agenticrl/images/figure-d8f26ee8a122.png" width="1080"/></div><figcaption class="publication-caption">Multi-Agent RL 的协同训练流程。</figcaption></figure>

| 模型 | 主要奖励 | 训练范围 |
| --- | --- | --- |
| 工具调用 | 规则遵守、调用合理性 | 模型生成的工具调用 |
| 最终回复 | 正确性、帮助性 | 最终回复 |

每组采样分别计算两个阶段的优势，工具返回始终不参与 loss；两个模型各自保留 reference model，更新后同步进入下一轮交互。

相较 SFT，后续实验中回复正确性提升 4.1pt、帮助性提升 23.6pt，工具调用合理性提升 18.2pt。固定工具模型、只优化回复的消融也说明，收益不只是回复风格更贴合奖励。

这组离线实验与前面的线上 A/B 独立设计，教师模型和 Judge 也做过升级，不能直接横向比较绝对分数。

## 还没有解决什么

当前方案更接近串行 Agent 的阶段拆分，还没有体现并行协作的优势。模型也依然依赖特定工具和任务：新增工具后，通常不能直接沿用原模型。

下一步的问题因此变成了：运行环境变了，模型能不能跟着适应？这也是后续 Harness-Aware Training 的出发点。
