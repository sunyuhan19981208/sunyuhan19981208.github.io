Our early interaction system followed intent recognition, retrieval, and generation. Adding a capability meant new labels, branches, and training. An incorrect routing decision was difficult to recover from.

We changed the system in two steps: let the model choose tools, then train tool use separately from response generation.

## Let the model choose the next action

The agent sees products, dialogue history, and the current spoken script. It decides what to look up, inspects tool results, and can query again or correct itself before answering under the response rules.

This lets it combine several viewers' questions and use the spoken presentation as context. The cost is additional model calls.

To control latency, a large teacher generates complete trajectories. We distill tool calling and response generation into two Qwen3-30B-A3B Instruct models, excluding explicit teacher thinking. A tool call takes about 0.3 seconds; decoding on one H20 reaches roughly 140 tokens/s.

<figure class="publication-figure figure-landscape" id="blog-figure-1"><div class="figure-heading"><span class="figure-label">Figure 1</span><button aria-label="Enlarge Figure 1" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="AgentTuning distills tool calling and response generation separately." decoding="async" height="603" loading="lazy" src="../agenticrl/images/figure-9a1f6e0128ef.png" width="1080"/></div><figcaption class="publication-caption">AgentTuning distills tool calling and response generation separately.</figcaption></figure>

## Improve the answer first

Distillation produces competent tool use, but answers can still make unsupported promises or offer little help. We first keep tool-call prefixes fixed and apply GRPO only to final responses, rewarding correctness, helpfulness, and length.

Inputs and tool outputs are masked. Only the generated answer receives gradients. Correctness constrains facts; helpfulness discourages the model from referring every difficult question to customer service.

In this stage's online A/B test, mean end-to-end latency fell to 1.79 seconds, down 1.36 seconds. The proportion of users having multi-turn conversations rose by 2.76%.

## Why end-to-end RL struggled

We then built simulated livestream environments so tool use could improve through interaction rather than remain bounded by teacher imitation.

ROLL handles training; remote environments maintain state and execute product tools. After each rollout, we score the trajectory, mask non-policy tokens, update parameters, and synchronize the inference engines.

Environment stability and reward discrimination consumed more effort than expected. Intermittent simulator failures obscure the training signal. An algorithm cannot compensate for rewards that fail to distinguish good trajectories from bad ones.

The deeper issue was credit assignment: **a correct final answer does not establish that earlier tool calls were sensible**. Combining all rewards for one model could actually weaken tool competence.

## Two agents, separate credit

We split tool calling and final response generation. Both models participate in complete trajectories, but each trains only on its own generated tokens and receives relevant rewards.

<figure class="publication-figure figure-landscape" id="blog-figure-2"><div class="figure-heading"><span class="figure-label">Figure 2</span><button aria-label="Enlarge Figure 2" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Joint training of the tool and response models." decoding="async" height="372" loading="lazy" src="../agenticrl/images/figure-d8f26ee8a122.png" width="1080"/></div><figcaption class="publication-caption">Joint training of the tool and response models.</figcaption></figure>

| Model | Main rewards | Tokens optimized |
| --- | --- | --- |
| Tool calling | Rule compliance, tool-call rationality | Generated tool calls |
| Response generation | Correctness, helpfulness | Final answer |

We calculate stage-specific group advantages, exclude tool outputs from loss, and retain separate reference models. Both updated policies enter the next interaction round.

Relative to SFT, the later experiments improved factual correctness by 4.1 points, helpfulness by 23.6 points, and tool-call rationality by 18.2 points. An ablation that fixed the tool model confirmed that the gains were not solely response-style alignment.

These offline experiments were independent of the earlier online A/B test, with updated teachers and judges. Their absolute scores should not be compared directly.

## The next limitation

This is a staged, serial decomposition, not yet a system that benefits from parallel agent collaboration. Training also remains tied to particular tools and tasks: changing the tool environment usually requires more adaptation.

That leads to the question behind our later Harness-Aware Training work: can a compact model keep working as its runtime changes?
