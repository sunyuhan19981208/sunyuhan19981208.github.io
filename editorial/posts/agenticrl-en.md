{
  "title": "From workflows to Multi-Agent RL",
  "summary": "Tool use and final responses need different skills—and different rewards."
}

Our early interaction system followed intent recognition, retrieval, and generation. Adding a capability meant new labels, branches, and training. An incorrect routing decision was difficult to recover from.

We changed the system in two steps: let the model choose tools, then train tool use separately from response generation.


## From Workflow to Agentic Interaction

### Application scenario

<!-- image:agenticrl:images/figure-fba13ebfdc1f.png | Digital avatars respond through text and synthesized speech. -->

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

The following sanitized trajectory illustrates the complete agent execution flow. The original Chinese prompts and tool data are retained as executable-format examples; actual retrieval results and subsequent steps were redacted in the source:

```text
Viewer: Which has better noise cancellation, Sony XM4 or XM5?
Context: the host is presenting a different product.
1. Retrieve product evidence for XM4 and XM5.
2. Check whether the results support a comparison.
3. Load the relevant reply rules, then produce the final response.
```

The architectural benefits become clear when comparing actual viewer queries:

- General improvements

<!-- image:agenticrl:images/figure-361c075313bd.png | Comparing interaction behavior under Workflow and Agentic architectures. -->

- Livestream-specific improvements

- Responding to multiple comments: adaptive, concurrent tool use and aggregation across information sources turn fragmented questions into one structured response. The agent can address different viewers' product questions together, including subsidy policies, gifts, and delivery times.

<!-- image:agenticrl:images/figure-72d67b403a61.png | Aggregating questions from several comments into one response. -->

- Incorporating the spoken script: viewer questions are often closely tied to what the host is currently presenting. The flexible agentic architecture and global context awareness let the system incorporate the avatar's live script, understand the intended question more accurately, and give a more relevant answer.

<!-- image:agenticrl:images/figure-e059d6809841.png | Using the current presentation script as interaction context. -->

### Model optimization: AgentTuning and RLVR

We developed a model-optimization approach to meet strict latency requirements while improving correctness and helpfulness:

- Reducing latency through AgentTuning distillation: a large teacher generates trajectories that are distilled into a compact 30B-A3B model. A single tool call takes 0.3 seconds, and decoding on one H20 reaches 140 tokens/s.
- Reducing hallucination through response-model RLVR: domain-specific evaluation metrics and appropriate reward models encourage factually correct, helpful replies, reducing unsupported answers and promises during live commerce.

#### AgentTuning distillation

Multi-turn reflection adds reasoning overhead and creates a substantial latency challenge. AgentTuning distillation gives compact models planning, tool-use, and reflective decision-making capabilities approaching those of a much larger agent.

<!-- image:agenticrl:images/figure-9a1f6e0128ef.png | Distilling tool use and final responses from teacher trajectories separately. -->

- The teacher interacts with the environment over multiple turns to sample complete execution trajectories. Its tool-calling and response capabilities are distilled separately into two Qwen3-30B-A3B models.
- To minimize latency, both students use Instruct models, and teacher thinking sequences are removed during distillation:

- The tool-calling model learns only teacher-generated tool calls. We truncate the trajectory before the last tool call and mask tool outputs.
- The response model learns only the teacher's final answer; all preceding sequences are masked.

#### Response-model RLVR

After AgentTuning, planning, tool use, and reflective decision-making are already strong, but supervised learning leaves room to improve factual correctness and helpfulness. Starting from the AgentTuning model, we train the response component with GRPO using correctness, helpfulness, and length rewards. Optimization acts directly on the final response to reduce hallucination and align preferences, producing an agent pipeline suitable for deployment.

<!-- image:agenticrl:images/figure-827d2e0e6f54.jpeg | RLVR optimizes final responses from fixed tool-trajectory prefixes. -->

- Inputs are teacher-annotated tool-call chains. For each prefix, the model rolls out multiple final answers to form a group.
- Each answer is scored for factual correctness and helpfulness. Group means and standard deviations yield relative advantages, which determine the optimization loss.
- The overall goals are:

- Minimize hallucination and answer according to tool results.
- Include a helpfulness reward so that avoiding hallucination does not make the model excessively conservative or unresponsive to viewers' needs.

**Implementation note:** We implement this algorithm in ROLL. Remove the final response from a teacher trajectory and retain `messages[:-1]` as the training prefix. `tokenizer.apply_chat_template` formats the messages; rollout generates only the final answer, and RLVR optimizes only that answer.

#### Evaluation metrics

<!-- image:agenticrl:images/figure-2398e76c7bb3.png | Evaluation criteria for response correctness and helpfulness. -->

#### Evaluation dataset

We sanitize, filter, and clean production traffic to build the evaluation dataset. The metrics are factual correctness and response helpfulness.

#### Model improvements

<!-- image:agenticrl:images/figure-4d714dc120d8.png | Offline response-quality comparison after architecture and model optimization. -->

The agent substantially improves correctness and helpfulness relative to the workflow and also outperforms leading open and closed models, Gemini-2.5-pro and Qwen3-235B-A22B, on our interaction-response task. These results support the effectiveness of our optimization approach.

### Production results

- Human comparison: replay production agent traffic through the workflow service and compare replies for identical inputs.

<!-- image:agenticrl:images/figure-8ab8ca4507d6.png | Human comparison using replayed production requests. -->

- Latency comparison, measured in seconds:

- The agentic architecture uses Instruct models throughout; the original workflow used a Thinking model for final response generation. Because upstream agent decisions already perform planning and tool selection, the final model does not need to compensate for unknown retrieval conditions as it did in the workflow.
- Together with previous latency optimizations, this substantially reduces both mean latency and the P99 tail.

<!-- image:agenticrl:images/figure-03b1f72a6de6.png | Training the policy through multi-step tool interaction in a simulator. -->

## Agentic RL in Practice
### Background

The deployed agent in Chapter 2 learns tool calling through AgentTuning supervised distillation. Although effective, this approach fundamentally bounds the student's tool-use and intent-understanding abilities by the teacher. We therefore explore Agentic RL to train tool use inside a simulated environment and potentially surpass the teacher's ceiling.

### End-to-end Agentic RL

<!-- image:agenticrl:images/figure-df52e743cd22.jpeg | The engineering path for rollouts, environment execution, and rewards. -->

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

**Implementation note:** ROLL's abstractions and extension points mean that implementing rollout, correctly masked sequences, and reward scoring is enough to run the basic Agentic RL loop. The masks from `tokenizer.apply_chat_template` may not meet task requirements; explicitly mask tokens that should not be trained.

**Implementation note:** Early convergence was limited less by algorithm design than by environment stability and reward quality. An unstable simulator makes positive conclusions almost impossible. Rewards must distinguish genuinely good trajectories from bad ones; in practice, this is among the hardest and messiest parts of deployment.

### Limitations and deployment challenges

Our initial end-to-end Agentic RL attempts did not produce a strong model, for several reasons:

- Correctness and helpfulness rewards primarily evaluate the response model. They provide no clear feedback on agentic competence, and inappropriate credit assignment can make tool use worse.
- Adding an LLM-judge tool-use reward gives some relevant feedback, but judge instability makes the reward noisier and convergence harder.
- Tool use and response generation require different skills: tool use relies on contextual intent understanding, accurate calls, and reflection on results; response generation prioritizes low hallucination, satisfaction of the actual request, and natural expression.

## Multi-Agent Reinforcement Learning

Based on these observations, we separate tool calling and final response generation into two agents and jointly optimize them online with different rewards. This shifts optimization from one model to the whole system.

### Joint optimization of the two agents

We explicitly divide the interaction system into a tool-calling model and a response/summarization model. During training, each optimizes only its own stage:

<!-- image:agenticrl:images/figure-d8f26ee8a122.png | Tool and response agents share the environment while receiving distinct rewards. -->

The tool model interacts over multiple turns with a simulated livestream environment to obtain K tool-use trajectories. Retrieving response rules marks the end of tool calling. If the rules have not been retrieved, no final answer is generated.

<!-- image:agenticrl:images/figure-7eced5389703.png | Reward allocation across agents. -->

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

**Implementation note:** In a correct implementation, Multi-Agent RL converges more readily than end-to-end Agentic RL, effectively dividing the latter into several subtasks closer to RLVR.

**Implementation note:** The implementation closely resembles step-reward training. If model-parameter differences are set aside, a step-reward implementation can directly support Multi-Agent RL. ROLL already provides algorithms such as GiGPO.

**Implementation note:** Automatically uploading multiple models' checkpoints to OPENLM MOS is a challenge. We distinguish model checkpoints through `cluster_name` at the `ckpt_id` level and reuse ROLL's automatic MOS upload mechanism.

### Reward design

<!-- image:agenticrl:images/figure-ccf4faac74d8.png | Training curves for Multi-Agent RL. -->

### Training behavior

<!-- image:agenticrl:images/figure-266baeef002c.png | Experimental response-quality and tool-rationality results. -->

The figure compares single-agent and multi-agent Agentic RL using the same four rewards and GRPO optimization:

- The single agent uses a weighted sum of all four rewards.
- The multi-agent response model combines correctness and helpfulness, while the tool model combines rule compliance and tool-call rationality.

Mixed rewards make single-agent Agentic RL difficult to improve or converge. Separating the models addresses this mismatch and yields stronger training behavior:

- Factual correctness and response helpfulness evaluate the final answer. Scoring tool competence from whether the final answer hallucinates is inappropriate.
- Tool-call rationality measures the tool model and should not be used to grade final response generation.

### Experimental results*

<!-- image:agenticrl:images/figure-bb193e83747b.png | Ablations of joint multi-agent training. -->

- *This experiment was designed independently of the earlier architecture experiment. The main changes are improved factual-correctness and helpfulness judges and a stronger distillation teacher, GLM 4.7.
- We also evaluate tool-call rationality separately to monitor tool competence, addressing the earlier problem of optimizing only the final answer while tool use deteriorated.

The method trains two models. Relative to SFT, the response model improves factual correctness by 4.1 points and helpfulness by 23.6 points; the tool model improves tool-call rationality by 18.2 points, improving the overall system.

### Ablation study

<!-- image:agenticrl:images/figure-087efade9246.png | Comparison of training and reward configurations. -->

- We fix the tool model and apply RLVR only to the final-response model as a control, testing whether gains come from better upstream tool use rather than merely fitting response style to the reward.
- Relative to this control, Multi-Agent RL improves factual correctness by 5.6 points and helpfulness by 6.6 points while retaining the 18.2-point tool-call rationality advantage over SFT.

## Reading the results in context

The production A/B comparison and the offline Multi-Agent RL experiments belong to different stages. The 1.79-second mean end-to-end latency, 1.36-second reduction, and 2.76% increase in multi-turn users concern the move from Workflow to the Agentic architecture. They should not all be attributed to the later Multi-Agent RL method.

The offline gains of 4.1 points in correctness, 23.6 in helpfulness, and 18.2 in tool rationality are relative to the supervised baseline in those experiments. Teacher and Judge configurations also matter. Read each comparison with its own baseline, input set, and scoring protocol rather than treating several tables as one controlled experiment.

For deployment, the useful outcome is an inspectable trajectory: what evidence was missing, why a tool was called, and whether the reward encouraged the intended behavior. Splitting the task across two agents makes these questions easier to diagnose; it does not remove the need to validate the environment and the reward.
