{
  "title": "Agentic RL: from RLVR to Multi-Agent RL",
  "summary": "Tool use and final responses need different skills—and different rewards."
}

Our early interaction system followed intent recognition, retrieval, and generation. Adding a capability meant new labels, branches, and training. An incorrect routing decision was difficult to recover from.

We changed the system in two steps: let the model choose tools, then train tool use separately from response generation.


## From workflows to agents {#moving-beyond-a-fixed-workflow}

### Livestream interaction {#the-interaction-we-need-to-handle}

<!-- image:agenticrl:images/figure-fba13ebfdc1f.png | Digital avatars respond through text and synthesized speech. -->

- When viewers send comments in a digital-avatar livestream, the host replies through text and speech using product information and merchant-configured question–answer pairs.
- Our algorithm controls these interactions, including what to say and whether to move a requested product forward in the presentation order.

### Limits of the fixed workflow {#where-the-fixed-pipeline-got-stuck}

The fixed intent-recognition–retrieval–generation workflow was becoming hard to maintain as the live-room requirements changed. Three problems kept coming up:

- Limited flexibility and slow iteration: adding one intent required two months of work involving manual annotation. Less than 2% of configured FAQs were used, making rapid business iteration difficult.
- Weak context awareness and dead ends: the system could not connect product-list information, spoken scripts, and historical comments. After an intent error, it could not reflect or backtrack and instead mechanically referred viewers to customer service.
- No concurrent scheduling: high-frequency comments from multiple viewers were difficult to process, and richer actions or expressive interactions were hard to add.

A 30B MoE model could decode at 140 tokens/s on one H20, and base models had improved at tool use. That made replacing fixed branches with evidence-based decisions feasible at the serving cost. Latency and final-answer quality still needed optimization.

### Agent decision flow {#let-the-model-choose-the-next-action}

The migration changed three parts of the system:

- Perception: one-dimensional matching → global context awareness combining comments, history, and product information.
- Decision-making: one rigid classification → repeated, on-demand tool calls and reflective error correction.
- Execution: a script for one intent → multimodal responses, including selecting images, reordering products, and incorporating the spoken script.

Here is one interaction, simplified from the sanitized source. The host is presenting another item, so this question needs its own retrieval path:

```text
Viewer: Which has better noise cancellation, Sony XM4 or XM5?
Context: the host is presenting a different product.
1. Retrieve product evidence for XM4 and XM5.
2. Check whether the results support a comparison.
3. Load the relevant reply rules, then produce the final response.
```

We compared how the two systems handled actual viewer queries:

<!-- image:agenticrl:images/figure-361c075313bd.png | Comparing interaction behavior under Workflow and Agentic architectures. -->

Two examples were especially useful in a live room:

- Answering several comments together: one viewer asks about subsidies, another about a gift, and a third about delivery. The agent fetches the missing evidence and combines the questions into one reply, instead of forcing every fragment through an independent fixed route.

<!-- image:agenticrl:images/figure-72d67b403a61.png | Aggregating questions from several comments into one response. -->

- Reading the spoken script as context: “this one” often refers to what the host just said, not merely the current catalog item. Adding the avatar’s live script gives the agent another way to resolve that reference and respond to follow-up questions without guessing from the product list alone.

<!-- image:agenticrl:images/figure-e059d6809841.png | Using the current presentation script as interaction context. -->

### Latency and response quality {#bringing-latency-and-answer-quality-into-range}

Moving to an agent was only useful if it could reply quickly and reliably. We worked on those two constraints separately:

- Latency: teacher trajectories train separate tool-use and reply students. A tool call takes about 0.3 seconds to generate, at 140 tokens/s on one H20. This measurement covers tool-call generation rather than the complete viewer interaction.
- Then response quality: correctness and helpfulness rewards encourage replies grounded in tool evidence. We care especially about unsupported product facts and promises, including whether the model recognizes when it needs more information.

#### AgentTuning distillation

Each extra reflection or tool round costs time in a live room. AgentTuning moves planning, tool selection, and reply behavior from teacher trajectories into smaller models, keeping useful decisions within our deployment budget.

<!-- image:agenticrl:images/figure-9a1f6e0128ef.png | Distilling tool use and final responses from teacher trajectories separately. -->

- The teacher interacts with the environment over multiple turns to sample complete execution trajectories. Its tool-calling and response capabilities are distilled separately into two Qwen3-30B-A3B models.
- To minimize latency, both students use Instruct models, and teacher thinking sequences are removed during distillation:

- The tool-calling model learns only teacher-generated tool calls. We truncate the trajectory before the last tool call and mask tool outputs.
- The response model learns only the teacher's final answer; all preceding sequences are masked.

#### Response-model RLVR

After distillation, the students could plan and call tools but still misread evidence or make unsupported promises in the final reply. We continued from AgentTuning with GRPO on that reply. For each fixed tool-trajectory prefix, multiple answers receive correctness, helpfulness, and length rewards to constrain facts, excessive caution, and unnecessary expansion.

<!-- image:agenticrl:images/figure-827d2e0e6f54.jpeg | RLVR optimizes final responses from fixed tool-trajectory prefixes. -->

- Inputs are teacher-annotated tool-call chains. For each prefix, the model rolls out multiple final answers to form a group.
- Each answer is scored for factual correctness and helpfulness. Group means and standard deviations yield relative advantages, which determine the optimization loss.
- The overall goals are:

- Minimize hallucination and answer according to tool results.
- Include a helpfulness reward so that avoiding hallucination does not make the model excessively conservative or unresponsive to viewers' needs.

In ROLL, the teacher’s `messages[:-1]` remains the prefix and rollout generates only the last reply. `tokenizer.apply_chat_template` prepares the input; RLVR updates the generated response. The prefix supplies conditions and is excluded from the reply loss, so its mask needs checking separately.

#### Evaluation metrics

<!-- image:agenticrl:images/figure-2398e76c7bb3.png | Evaluation criteria for response correctness and helpfulness. -->

#### Evaluation dataset

We sanitize, filter, and clean production traffic to build the evaluation dataset. The metrics are factual correctness and response helpfulness.

#### Model improvements

<!-- image:agenticrl:images/figure-4d714dc120d8.png | Offline response-quality comparison after architecture and model optimization. -->

The agent improved correctness and helpfulness over Workflow and exceeded the reported Gemini-2.5-pro and Qwen3-235B-A22B baselines on this dataset. The comparison uses these task inputs and calling setups; it is not a general capability ranking.

### Production results {#what-changed-after-deployment}

- Human comparison: replay production agent traffic through the workflow service and compare replies for identical inputs.

<!-- image:agenticrl:images/figure-8ab8ca4507d6.png | Human comparison using replayed production requests. -->

- Latency comparison, measured in seconds:

- The new chain uses Instruct models, while Workflow used a Thinking model for its final reply. Planning, tool selection, and evidence checks now happen upstream. The final model mainly organizes those facts, a change in responsibility that also affects the latency comparison.
- Together with previous latency optimizations, this substantially reduces both mean latency and the P99 tail.

<!-- image:agenticrl:images/figure-03b1f72a6de6.png | Training the policy through multi-step tool interaction in a simulator. -->

## Agentic RL {#letting-the-student-practice-in-the-environment}
### Limits of distillation {#what-demonstrations-still-leave-out}

The deployed tool model learned from teacher trajectories, so the demonstrations still limited which paths it saw. We next tried letting the student call tools, observe consequences, and recover in a simulator. Agentic RL offered a way to learn from those interactions directly.

### RL over the full interaction {#trying-rl-over-the-complete-interaction}

<!-- image:agenticrl:images/figure-df52e743cd22.jpeg | The engineering path for rollouts, environment execution, and rewards. -->

Rollout:

1. The policy performs multi-turn tool interactions in a simulated environment, terminating after retrieving response rules and producing a non-tool-call answer.
2. Compute tool-use and final-response rewards for each rollout, then calculate group-relative advantages.

Training:

1. Compute loss only on model-generated tool calls and final responses. Mask input data and tool outputs.
2. Use the initial reference model for KL divergence; importance sampling follows the standard GRPO/PPO setup.
3. Synchronize updated training parameters to the inference model and continue the next iteration. Tool use and response generation are optimized together.

### Training workers and the sandbox {#connecting-rollout-workers-to-the-sandbox}

In ROLL, the simulation architecture separates the training side from the remote sandbox:

- Training cluster: drives rollout workers to generate complete trajectories, scores them with reward models, masks tokens excluded from optimization, and sends processed sequences and scores to training.
- Remote sandbox: handles external interactions that rollout workers cannot simulate directly, including restricted internal RPC services, stateful containers such as Computer Use environments, and real-time simulators such as games.

The training and interaction loop has four key steps:

- First, prepare an environment for each rollout worker. It gets an independent simulated live room, retrieves initial state, and initializes remote tools, including the semantic vector store. The model and executor need to begin with the same task context.

- Next, run the interaction loop. The worker generates through in-process vLLM or SGLang, parses a tool request, calls the remote sandbox, and feeds back the result. It continues until the turn limit or a terminal tool ends rollout. We retain the complete sequence.

- Then score and mask the trajectory. Internal LLM judges return episode rewards for the interaction. The loss mask excludes tool results, system messages, and inputs, leaving generated policy actions for optimization. Environment output belongs in the context, not in the policy loss.

- Finally, return sequences, masks, and episode scores to ROLL. It calculates advantages and losses, updates through Megatron, and synchronizes parameters to vLLM or SGLang. The next rollout must actually use the new policy for the iteration to be complete.

ROLL supplies much of the training loop; our implementation supplies rollout, token masks, and rewards. A chat-template mask may differ from the required loss mask. Tool results and system messages must be checked explicitly: their message format does not make them policy-generated actions.

Early runs were limited by simulator instability and rewards that failed to distinguish useful trajectories. Instability made feedback incomparable, while weak rewards gave the policy little direction. Both needed attention before the training curves could support a reliable conclusion.

### Limits of the final reward {#why-the-final-reward-was-not-enough}

Our initial end-to-end Agentic RL attempts did not produce a strong model, for several reasons:

- Correctness and helpfulness rewards primarily evaluate the response model. They provide no clear feedback on agentic competence, and inappropriate credit assignment can make tool use worse.
- Adding an LLM-judge tool-use reward gives some relevant feedback, but judge instability makes the reward noisier and convergence harder.
- Tool use needs contextual intent, correct interfaces and arguments, and decisions based on results. The reply needs factual grounding, relevance, and natural wording. A final-answer score can obscure these different responsibilities when assigned to every earlier action.

## Multi-Agent RL {#training-tool-use-and-replies-separately}

We therefore split tool use and final replies into two agents, retain their shared environment, and assign distinct rewards. One learns to gather evidence, the other to use it; both see the effects of their partner’s changing behavior.

### Joint training {#how-the-two-agents-learn-together}

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

The two-agent configuration converged more readily on this task because feedback was closer to each role’s responsibility. This still relies on correct environments, masks, and rewards; splitting the models alone does not guarantee the result.

Step-reward data flow is a useful starting point, including the GiGPO implementation in ROLL. With separate agent parameters, each sequence, reward, and checkpoint also needs to retain its model ownership.

We distinguish checkpoints with `cluster_name` at the `ckpt_id` level, then reuse ROLL’s automatic OPENLM MOS upload. Saving both models from the same iteration allows the trained pair to be loaded and replayed together.

### Reward design

<!-- image:agenticrl:images/figure-ccf4faac74d8.png | Training curves for Multi-Agent RL. -->

### Training curves {#what-we-look-for-in-the-training-curves}

<!-- image:agenticrl:images/figure-266baeef002c.png | Experimental response-quality and tool-rationality results. -->

The figure compares single-agent and multi-agent Agentic RL using the same four rewards and GRPO optimization:

- The single agent uses a weighted sum of all four rewards.
- The multi-agent response model combines correctness and helpfulness, while the tool model combines rule compliance and tool-call rationality.

Mixed rewards make single-agent Agentic RL difficult to improve or converge. Separating the models addresses this mismatch and yields stronger training behavior:

- Factual correctness and response helpfulness evaluate the final answer. Scoring tool competence from whether the final answer hallucinates is inappropriate.
- Tool-call rationality measures the tool model and should not be used to grade final response generation.

### Comparison with supervised fine-tuning {#comparing-with-the-supervised-version}

<!-- image:agenticrl:images/figure-bb193e83747b.png | Ablations of joint multi-agent training. -->

- This experiment was run separately from the earlier architecture comparison. We updated the factual-correctness and helpfulness judges and used a stronger distillation teacher, GLM 4.7.
- We also evaluate tool-call rationality separately to monitor tool competence, addressing the earlier problem of optimizing only the final answer while tool use deteriorated.

Relative to this experiment’s SFT baseline, correctness improved 4.1 points, helpfulness 23.6, and tool rationality 18.2. The response and tool improvements are recorded separately under this teacher and Judge configuration.

### Sources of improvement {#where-the-gains-come-from}

<!-- image:agenticrl:images/figure-087efade9246.png | Comparison of training and reward configurations. -->

- We fix the tool model and apply RLVR only to the final-response model as a control, testing whether gains come from better upstream tool use rather than merely fitting response style to the reward.
- Relative to this control, Multi-Agent RL improves factual correctness by 5.6 points and helpfulness by 6.6 points while retaining the 18.2-point tool-call rationality advantage over SFT.

## Results and limitations {#reading-the-results-in-context}

The production A/B comparison and the offline Multi-Agent RL experiments belong to different stages. The 1.79-second mean end-to-end latency, 1.36-second reduction, and 2.76% increase in multi-turn users concern the move from Workflow to the Agentic architecture. They should not all be attributed to the later Multi-Agent RL method.

The offline gains of 4.1 points in correctness, 23.6 in helpfulness, and 18.2 in tool rationality use the supervised baseline from those experiments. Teacher, Judge, inputs, and scoring rules differ across comparisons, so the tables do not form one controlled experiment.

Complete trajectories let us investigate missing evidence, tool choices, and whether rewards favor the intended behavior. Two agents make those issues easier to diagnose and optimize, with environment and reward validation still required.
