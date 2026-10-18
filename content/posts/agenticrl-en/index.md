{
  "slug": "agenticrl-en",
  "title": "Taobao Live Digital Avatars: From RLVR to Multi-Agent Reinforcement Learning",
  "shortTitle": "From RLVR to Multi-Agent RL",
  "language": "en",
  "tags": [
    "Reinforcement Learning",
    "Agents",
    "Multi-Agent"
  ],
  "description": "Migrating from a static workflow to agents and jointly training tool-calling and response models with separate rewards.",
  "lead": "From a fixed workflow to an avatar that plans and uses tools.",
  "highlights": [
    [
      "Upgrade the architecture",
      "Replace rigid intent routing with contextual, on-demand tool use."
    ],
    [
      "Be fast and reliable",
      "Combine AgentTuning and RLVR to reduce latency and improve factual responses."
    ],
    [
      "Optimize together",
      "Separate tool use and response generation, then jointly train their distinct skills."
    ]
  ],
  "date": "2026-07-13",
  "authors": "Taobao Live AIGC Team",
  "readingMinutes": 14,
  "source": "https://mp.weixin.qq.com/s/7A3QbSMM6gxG9d1LpYDIPQ",
  "publicationType": "Technical practice",
  "workId": "agenticrl",
  "counterpart": "agenticrl",
  "secondaryVersion": true,
  "sourceTitle": "淘宝直播数字人 AgenticRL 实践：从 RLVR 到 MultiAgent RL",
  "isTranslation": true,
  "sourceLanguage": "zh-CN"
}

This article describes the migration of Taobao Live digital-avatar interaction from a static workflow to a dynamic agentic architecture. We combine LLM capabilities with autonomous planning, reduce latency through AgentTuning distillation, mitigate hallucination with RLVR, and develop Multi-Agent RL to jointly optimize separate tool-calling and response models. The resulting system supports natural, substantive interaction at low latency (1.79 seconds), with improvements in factual correctness, helpfulness, and the proportion of users engaging in multi-turn conversations.

## Abstract

Digital-avatar interactions often lack depth, while conventional workflows suffer from limited flexibility, weak generalization, and high maintenance costs. We combine the world knowledge of LLMs with agents' autonomous planning and decision-making to give the avatar an agentic brain capable of useful, professional, and emotionally engaging interactions. Our long-term goal is a humanlike host agent with a closed loop of perception, reasoning, expression, and execution: it should understand complex contexts and generate high-quality content from real-time feedback, supporting more natural interaction and business growth.

- Chapter 2 describes the migration from workflow to agentic architecture: redesigning the runtime, transferring large-model capabilities to compact models through AgentTuning supervised fine-tuning, and using RLVR to reduce hallucinations when responding from tool results. In the A/B test, mean end-to-end latency fell to 1.79 seconds, a reduction of 1.36 seconds, while the proportion of users having multi-turn conversations rose by 2.76%.
- Chapter 3 presents our Agentic RL implementation on Alibaba's infrastructure. Built on ROLL, it trains multi-turn tool use and responses grounded in tool results. We discuss engineering details and practical deployment challenges.
- Chapter 4 introduces our business-specific Multi-Agent RL algorithm. Tool-use rewards do not directly measure response quality, and response-quality rewards do not fully measure tool competence. We therefore separate tool calling and final response generation into two agents and jointly train them with different rewards. This addresses the convergence difficulties of single-agent GRPO with mixed rewards. Relative to supervised fine-tuning, factual correctness improves by 4.1 points, helpfulness by 23.6 points, and tool-call rationality by 18.2 points.

## From Workflow to Agentic Interaction

### Application scenario

![Original figure 4](../agenticrl/images/figure-fba13ebfdc1f.png)

- When viewers send comments in a digital-avatar livestream, the host replies through text and speech using product information and merchant-configured question–answer pairs.
- Our algorithm controls these interactions, including what to say and whether to move a requested product forward in the presentation order.

### Why the architecture needed to change

The original static intent-recognition–retrieval–generation workflow* had become a bottleneck as livestreaming requirements changed rapidly. Three limitations stood out:

- Limited flexibility and slow iteration: adding one intent required two months of work involving manual annotation. Less than 2% of configured FAQs were used, making rapid business iteration difficult.
- Weak context awareness and dead ends: the system could not connect product-list information, spoken scripts, and historical comments. After an intent error, it could not reflect or backtrack and instead mechanically referred viewers to customer service.
- No concurrent scheduling: high-frequency comments from multiple viewers were difficult to process, and richer actions or expressive interactions were hard to add.

Advances in agentic models created an opportunity to move from static workflows to contextual, reflective decision-making. A 30B MoE model deployed on one H20 already reached 140 tokens/s, and base-model tool-use capabilities had improved substantially. This made a more capable agentic digital avatar technically feasible.

### Architecture improvements

The migration changed three parts of the system:

- Perception: one-dimensional matching → global context awareness combining comments, history, and product information.
- Decision-making: one rigid classification → repeated, on-demand tool calls and reflective error correction.
- Execution: a script for one intent → multimodal responses, including selecting images, reordering products, and incorporating the spoken script.

| Architecture | Source illustration |
| --- | --- |
| Original workflow | Original figure 5 |
| Agentic architecture | Original figure 6 |

The following sanitized trajectory illustrates the complete agent execution flow. The original Chinese prompts and tool data are retained as executable-format examples; actual retrieval results and subsequent steps were redacted in the source:

```
// 注：本示例为脱敏版本。系统提示词与样例输入保留；真实检索结果（商家名/价格/库存/条形码）及后续完整 trajectory 已替换/省略
[
{
    "role": "system",
    "content": "\n## 指令\n你是一名淘宝数字人主播，你现在正在运营这个直播间，并且你有很多工具可以调用，请选择调用一些工具获取更多信息用于更好的回复观众的问题。\n## 要求\n1. 你需要理解观众的问题，明确观众想问什么，你需要显示的补全观众想问的真实问题\n2. 如果观众问的问题能够调用工具搜集资料来回答那么就调用工具搜集资料\n3. 如果信息已经搜集完毕或者信息不足需要向观众进行多轮澄清，就调用回复规则查询工具来查询不同意图类型问题的回复规则，根据查询到的规则回答问题\n4. 同一个工具不要使用两次以上，如果在历史中已经调用了两次相同的工具那么不应该继续调用了，你需要保持使用工具的高效性，因为需要实时对观众进行回复\n5. 在进行最终回复前**必须**先查询回复规则\n"
},
{
    "role": "user",
    "content": "\n## 真实输入\n{\n    \"当前商品名\":超市定制伊利金典纯牛奶250ml*24盒整箱儿童学生高端营养礼盒,\n    \"对话历史\":[],\n    \"观众问题\":索尼xm4和5哪个降噪好呢,\n    \"相关预置FAQ\":[]\n}\n\n## 现在开始\n请先按照要求进行一步一步思考，通过调用工具收集更多信息用于回答观众问题\n",
},
{
    "role": "assistant",
    "content": "\n<tool_call>\n{\"name\": \"search_product_by_keyword\", \"arguments\": {\"keyword\": \"索尼xm4\"}}\n</tool_call>\n\n<tool_call>\n{\"name\": \"search_product_by_keyword\", \"arguments\": {\"keyword\": \"索尼xm5\"}}\n</tool_call>\n"
},
{
    "role": "tool",
    "content": "已找到相关商品：[{\"商品名\": \"<示例商品名>\", \"商家名\": \"某商家\", \"券后价\": ***, \"库存\": \"***\", \"商品条形码\": \"***\", \"链接号\": <编号>}]（注：真实检索返回的多条商家/价格/库存/条形码数据，以及后续查询回复规则、最终回复等 trajectory 内容，为对外脱敏已省略）"
}
]
```

The architectural benefits become clear when comparing actual viewer queries:

- General improvements

![Original figure 7](../agenticrl/images/figure-361c075313bd.png)

- Livestream-specific improvements

- Responding to multiple comments: adaptive, concurrent tool use and aggregation across information sources turn fragmented questions into one structured response. The agent can address different viewers' product questions together, including subsidy policies, gifts, and delivery times.

![Original figure 8](../agenticrl/images/figure-72d67b403a61.png)

- Incorporating the spoken script: viewer questions are often closely tied to what the host is currently presenting. The flexible agentic architecture and global context awareness let the system incorporate the avatar's live script, understand the intended question more accurately, and give a more relevant answer.

![Original figure 9](../agenticrl/images/figure-e059d6809841.png)

### Model optimization: AgentTuning and RLVR

We developed a model-optimization approach to meet strict latency requirements while improving correctness and helpfulness:

- Reducing latency through AgentTuning distillation: a large teacher generates trajectories that are distilled into a compact 30B-A3B model. A single tool call takes 0.3 seconds, and decoding on one H20 reaches 140 tokens/s.
- Reducing hallucination through response-model RLVR: domain-specific evaluation metrics and appropriate reward models encourage factually correct, helpful replies, reducing unsupported answers and promises during live commerce.

#### AgentTuning distillation

Multi-turn reflection adds reasoning overhead and creates a substantial latency challenge. AgentTuning distillation gives compact models planning, tool-use, and reflective decision-making capabilities approaching those of a much larger agent.

![Original figure 10](../agenticrl/images/figure-9a1f6e0128ef.png)

- The teacher interacts with the environment over multiple turns to sample complete execution trajectories. Its tool-calling and response capabilities are distilled separately into two Qwen3-30B-A3B models.
- To minimize latency, both students use Instruct models, and teacher thinking sequences are removed during distillation:

- The tool-calling model learns only teacher-generated tool calls. We truncate the trajectory before the last tool call and mask tool outputs.
- The response model learns only the teacher's final answer; all preceding sequences are masked.

#### Response-model RLVR

After AgentTuning, planning, tool use, and reflective decision-making are already strong, but supervised learning leaves room to improve factual correctness and helpfulness. Starting from the AgentTuning model, we train the response component with GRPO using correctness, helpfulness, and length rewards. Optimization acts directly on the final response to reduce hallucination and align preferences, producing an agent pipeline suitable for deployment.

![Original figure 11](../agenticrl/images/figure-827d2e0e6f54.jpeg)

- Inputs are teacher-annotated tool-call chains. For each prefix, the model rolls out multiple final answers to form a group.
- Each answer is scored for factual correctness and helpfulness (see Section 2.3.3). Group means and standard deviations yield relative advantages, which determine the optimization loss.
- The overall goals are:

- Minimize hallucination and answer according to tool results.
- Include a helpfulness reward so that avoiding hallucination does not make the model excessively conservative or unresponsive to viewers' needs.

![Original figure 12](../agenticrl/images/figure-78273b848570.png) TAKEAWAY: We implement this algorithm in ROLL. Remove the final response from a teacher trajectory and retain `messages[:-1]` as the training prefix. `tokenizer.apply_chat_template` formats the messages; rollout generates only the final answer, and RLVR optimizes only that answer.

#### Evaluation metrics

![Original figure 13](../agenticrl/images/figure-2398e76c7bb3.png)

#### Evaluation dataset

We sanitize, filter, and clean production traffic to build the evaluation dataset. The metrics are factual correctness and response helpfulness.

#### Model improvements

![Original figure 14](../agenticrl/images/figure-4d714dc120d8.png)

The agent substantially improves correctness and helpfulness relative to the workflow and also outperforms leading open and closed models, Gemini-2.5-pro and Qwen3-235B-A22B, on our interaction-response task. These results support the effectiveness of our optimization approach.

### Production results

- Human comparison: replay production agent traffic through the workflow service and compare replies for identical inputs.

![Original figure 15](../agenticrl/images/figure-8ab8ca4507d6.png)

- Latency comparison, measured in seconds:

- The agentic architecture uses Instruct models throughout; the original workflow used a Thinking model for final response generation. Because upstream agent decisions already perform planning and tool selection, the final model does not need to compensate for unknown retrieval conditions as it did in the workflow.
- Together with previous latency optimizations, this substantially reduces both mean latency and the P99 tail.

![Original figure 16](../agenticrl/images/figure-03b1f72a6de6.png)

## Agentic RL in Practice
### Background

The deployed agent in Chapter 2 learns tool calling through AgentTuning supervised distillation. Although effective, this approach fundamentally bounds the student's tool-use and intent-understanding abilities by the teacher. We therefore explore Agentic RL to train tool use inside a simulated environment and potentially surpass the teacher's ceiling.

### End-to-end Agentic RL

![Original figure 18](../agenticrl/images/figure-df52e743cd22.jpeg)

Rollout:

1. The policy performs multi-turn tool interactions in a simulated environment, terminating after retrieving response rules and producing a non-tool-call answer.
2. Compute tool-use and final-response rewards for each rollout, then calculate group-relative advantages.

Training:

1. Compute loss only on model-generated tool calls and final responses. Mask input data and tool outputs.
2. Use the initial reference model for KL divergence; importance sampling follows the standard GRPO/PPO setup.
3. Synchronize updated training parameters to the inference model and continue the next iteration. Tool use and response generation are optimized together.

### Simulation environment and engineering

In ROLL, the simulation architecture separates the training side from the remote sandbox:

- Training cluster: drives rollout workers to generate complete trajectories, scores them with reward models, masks tokens excluded from optimization, and sends processed sequences and scores to training.
- Remote sandbox: handles external interactions that rollout workers cannot simulate directly, including restricted internal RPC services, stateful containers such as Computer Use environments, and real-time simulators such as games.

The training and interaction loop has four key steps:

- Step 1 — Initialize and connect: each rollout worker maps to an independent simulated environment. It requests a livestream environment from the simulation platform and retrieves initial data to prepare remote tools, including the semantic vector store.

- Step 2 — Multi-turn rollout: the worker generates through an in-process vLLM or SGLang engine. After parsing a tool request, it contacts the sandbox over the network and receives the result. The model adapts its next action to feedback until the maximum number of turns or a designated rule tool, such as final-response retrieval, terminates the rollout.

- Step 3 — Reward evaluation and processing: after rollout, internal LLM judges accessed through the cloud protocol evaluate the full interaction and return scalar rewards. The algorithm masks tool outputs, system prompts, and input tokens so that gradients act only on valid policy-generated tokens.

- Step 4 — Advantages and model updates: custom code returns processed token sequences, masks, and the episode score to ROLL. The framework calculates advantages and losses, uses Megatron for distributed optimization, and synchronizes new parameters to vLLM/SGLang, completing one iteration.

![Original figure 19](../agenticrl/images/figure-78273b848570.png) TAKEAWAY: ROLL's abstractions and extension points mean that implementing rollout, correctly masked sequences, and reward scoring is enough to run the basic Agentic RL loop. The masks from `tokenizer.apply_chat_template` may not meet task requirements; explicitly mask tokens that should not be trained.

![Original figure 20](../agenticrl/images/figure-78273b848570.png) TAKEAWAY: Early convergence was limited less by algorithm design than by environment stability and reward quality. An unstable simulator makes positive conclusions almost impossible. Rewards must distinguish genuinely good trajectories from bad ones; in practice, this is among the hardest and messiest parts of deployment.

### Limitations and deployment challenges

Our initial end-to-end Agentic RL attempts did not produce a strong model, for several reasons:

- Correctness and helpfulness rewards primarily evaluate the response model. They provide no clear feedback on agentic competence, and inappropriate credit assignment can make tool use worse.
- Adding an LLM-judge tool-use reward gives some relevant feedback, but judge instability makes the reward noisier and convergence harder.
- Tool use and response generation require different skills: tool use relies on contextual intent understanding, accurate calls, and reflection on results; response generation prioritizes low hallucination, satisfaction of the actual request, and natural expression.

## Multi-Agent Reinforcement Learning

Based on these observations, we separate tool calling and final response generation into two agents and jointly optimize them online with different rewards. This shifts optimization from one model to the whole system.

### Joint optimization of the two agents

We explicitly divide the interaction system into a tool-calling model and a response/summarization model. During training, each optimizes only its own stage:

![Original figure 22](../agenticrl/images/figure-d8f26ee8a122.png)

The tool model interacts over multiple turns with a simulated livestream environment to obtain K tool-use trajectories. Retrieving response rules marks the end of tool calling. If the rules have not been retrieved, no final answer is generated.

![Original figure 23](../agenticrl/images/figure-7eced5389703.png)

Rollout:

1. The tool model interacts with the internal simulation platform. Tool calling ends when the turn limit is reached or the response-rule retrieval tool is invoked.
2. The response model uses the resulting tool chain as a prefix and generates an answer according to the response rules.
3. Score tool use and final response separately using the complete trajectory.
4. Assign a weighted reward to each model and calculate its group-relative advantages.

Training:

1. Tool model: truncate at the final tool-call turn before the response, mask tool outputs, and calculate loss from tool-use advantages.
2. Response model: use the complete trajectory, mask everything before the final response, and calculate loss from response advantages.
3. Each model uses its own initial reference model for KL divergence. Importance sampling follows the basic GRPO/PPO setup.
4. Synchronize parameters from the Megatron training models to the vLLM inference models and start the next iteration.

![Original figure 24](../agenticrl/images/figure-78273b848570.png) TAKEAWAY: In a correct implementation, Multi-Agent RL converges more readily than end-to-end Agentic RL, effectively dividing the latter into several subtasks closer to RLVR.

![Original figure 25](../agenticrl/images/figure-78273b848570.png) TAKEAWAY: The implementation closely resembles step-reward training. If model-parameter differences are set aside, a step-reward implementation can directly support Multi-Agent RL. ROLL already provides algorithms such as GiGPO.

![Original figure 26](../agenticrl/images/figure-78273b848570.png) TAKEAWAY: Automatically uploading multiple models' checkpoints to OPENLM MOS is a challenge. We distinguish model checkpoints through `cluster_name` at the `ckpt_id` level and reuse ROLL's automatic MOS upload mechanism.

### Reward design

![Original figure 27](../agenticrl/images/figure-ccf4faac74d8.png)

### Training behavior

![Original figure 28](../agenticrl/images/figure-266baeef002c.png)

The figure compares single-agent and multi-agent Agentic RL using the same four rewards and GRPO optimization:

- The single agent uses a weighted sum of all four rewards.
- The multi-agent response model combines correctness and helpfulness, while the tool model combines rule compliance and tool-call rationality.

Mixed rewards make single-agent Agentic RL difficult to improve or converge. Separating the models addresses this mismatch and yields stronger training behavior:

- Factual correctness and response helpfulness evaluate the final answer. Scoring tool competence from whether the final answer hallucinates is inappropriate.
- Tool-call rationality measures the tool model and should not be used to grade final response generation.

### Experimental results*

![Original figure 29](../agenticrl/images/figure-bb193e83747b.png)

- *This experiment was designed independently of the Chapter 2 experiment. The main changes are improved factual-correctness and helpfulness judges and a stronger distillation teacher, GLM 4.7.
- We also evaluate tool-call rationality separately to monitor tool competence, addressing the earlier problem of optimizing only the final answer while tool use deteriorated.

The method trains two models. Relative to SFT, the response model improves factual correctness by 4.1 points and helpfulness by 23.6 points; the tool model improves tool-call rationality by 18.2 points, improving the overall system.

### Ablation study

![Original figure 30](../agenticrl/images/figure-087efade9246.png)

- We fix the tool model and apply RLVR only to the final-response model as a control, testing whether gains come from better upstream tool use rather than merely fitting response style to the reward.
- Relative to this control, Multi-Agent RL improves factual correctness by 5.6 points and helpfulness by 6.6 points while retaining the 18.2-point tool-call rationality advantage over SFT.

## Conclusions and Future Work

Our main findings:

- We migrated a rigid, weakly contextual workflow to an agentic system. Distilling large-model capabilities into compact MoE models achieved subsecond model-response latency. RLVR reduced unsupported promises and other hallucinations, improved factual correctness and helpfulness, and delivered positive A/B results before full rollout.
- We then built a simulator and explored end-to-end Agentic RL. Because final-response rewards did not adequately measure tool use, we introduced an LLM-judge tool-call rationality reward and separated tool calling from response generation. Joint multi-agent training produced stable, substantial gains across the system.

Current limitations and next steps:

- The workflow-to-agent migration is complete, but richer digital-avatar tools and higher-level interactions are needed to realize the architecture's potential.
- Our current MultiAgent system is a staged decomposition of a single-agent ReAct pipeline, closer to serial systems such as Dr.MAS. It does not yet exploit parallel subagents or agent swarms.
- Both SFT and RL remain task-specific: adding tools or information cannot simply reuse the same model unchanged. We plan to improve generalization and introduce tools through progressively disclosed Skills.
