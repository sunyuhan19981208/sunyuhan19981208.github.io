{
  "title": "Making reasoning models respond sooner",
  "summary": "Distill the model, then shorten its reasoning without teaching it to give worse answers."
}

DeepSeek-R1 scored 86 on our product-QA task; the production model scored 75. But a livestream cannot wait many seconds for every answer.

We tackled two separate costs: distillation made the model smaller, then preference training shortened what it generated.


## Digital-Avatar Interaction Tasks

### Tasks and dataset selection

The interaction system comprises eight tasks, selected by an upstream intent model with different information sources and instructions. We use the more demanding product-question task for the initial distillation experiments and generate reasoning supervision with DeepSeek-R1.

| Task | Mode | Task | Mode |
| --- | --- | --- | --- |
| Product questions, selected for the experiment | Speech | Livestream promotions | Speech |
| Product questions | Comments | Livestream promotions | Comments |
| Casual chat | Speech | Questions without an explicit product subject | Speech |
| Casual chat | Comments | Questions without an explicit product subject | Comments |

- Randomly sample 5800 production product-question examples and split training/validation 9:1.
- Spoken and text-comment response modes differ in some requirements.

### Example product question

| Product information | Dialogue history | Viewer question | Answerable? | Host response |
| --- | --- | --- | --- | --- |
| X-brand Hong Kong PQQ nutritional tablets with bird's-nest acid and ergothioneine; merchant/brand: X; category: oral beauty/nutritional health food; tablet form, bottled, Hong Kong origin; shelf life: at least 24 months; adults of either sex; two tablets once a day; ingredients and effects: see details; options: 1 bottle trial, 3 bottles (buy 2 get 1), 5 bottles (buy 3 get 2), 8 bottles (buy 5 get 3), anti-aging/brightening variant; usage guidance: see details; free shipping; link 11; original price 4200.0; discounts 20.0 and 150.0; post-coupon price 1008.0. | Viewer: Please introduce PQQ. Host: Link 11 is next; let me finish link 12 first. | Why is a single bottle of PQQ much more expensive? | Yes | You are asking about the single-bottle price. X-brand PQQ at link 11 is made in Hong Kong and individually packaged, which raises quality-related costs and the single-bottle price. Additional discounts are available now. |

This illustration does not establish actual model quality. Appendix B contains real production examples.

### Evaluation

DeepSeek-R1 scores responses from the product information, dialogue history, viewer question, and AI-host answer. Evaluation combines four dimensions:

- Consistency with the question: understand the viewer's actual intent and answer correctly, using history when present.
- Consistency with product information: neither invent facts nor refuse when the provided information suffices. If information is insufficient or the question concerns another product, refer the viewer to customer service.
- Internal consistency: avoid logical contradictions and produce natural language suitable for speech.
- Instruction consistency: follow the avatar-host requirements in the prompt.

## Distilling DeepSeek-R1

On product questions, DeepSeek-R1 scores 86/100 versus 75 for the production model, an 11-point gap. We investigate three ways to transfer its capabilities to compact models:

1. Start from Qwen and distill only R1's final answer, excluding thinking.
2. Start from Qwen and distill the complete response, including thinking.
3. Start from DeepSeek-R1-Distill-Qwen and distill the complete response, including thinking.

The experiments support three conclusions:

1. Scheme C achieves the best response quality, 83/100, supporting DeepSeek-R1-Distill-Qwen as the starting point.
2. With Qwen2.5-Instruct as the base, including CoT makes little difference.
3. Refusal agreement with R1 increases with model size under identical training data. Agreement does not directly determine response quality: many partially answerable boundary cases limit agreement to approximately 85%.

### Distillation schemes

| Scheme | Method | Description |
| --- | --- | --- |
| A | Qwen, direct answer | R1-generated data excluding the thinking inside `<think>` tags; Qwen2.5-Instruct bases at several sizes. |
| B | Qwen with CoT | R1-generated data including `<think>` sequences; Qwen2.5-Instruct bases at several sizes. |
| C | DeepSeek-R1-Distill-Qwen with CoT | Complete R1-generated sequences including thinking; DeepSeek-R1-Distill-Qwen bases at several sizes. |

### Generation quality

| Scheme | Model/method | Mean quality score |
| --- | --- | --- |
| — | DeepSeek-R1 | 86 |
| A | Qwen14B, direct answer, 5.8k dataset | 78 |
| B | Qwen14B with CoT, 5.8k dataset | 78 |
| C | DeepSeek-R1-Distill-Qwen-14B with CoT, 5.8k dataset | 83 |
| — | Production model | 75 |

Evaluate generated responses using the quality-evaluation procedure above.

### Model size

- The model also predicts whether the question is answerable. A mismatched product or insufficient facts means unanswerable; answerable requires both a matching product and sufficient information.
- We study how model size relates to distillation by measuring refusal agreement with DeepSeek-R1. This is an approximate behavioral indicator rather than a complete quality metric.
- Compare schemes A, B, and C at 1.5B, 7B, and 14B.

<!-- image:llm-distillation-and-reasoning-compression:images/figure-1fd175734b7c.jpeg | Refusal agreement across model sizes and distillation schemes. -->

- Agreement rises with model size for all three schemes. Direct-answer distillation is preferable at 1.5B.
- At 14B, DeepSeek-R1-Distill-Qwen exceeds direct-answer distillation and approaches Qwen-with-CoT agreement.

### Quantization and smaller models

A bf16 14B reasoning model takes about 10 seconds per product answer, so quantization is necessary. Quantized latency reaches approximately 5 seconds. The 7B reasoning model has insufficient quality.

| Method | Precision | Quality /100 | Runtime |
| --- | --- | --- | --- |
| Scheme C, 14B | bf16 | 83 | 10s |
| Scheme C, 14B | int8 | 80 | 5s |
| Scheme C, 7B | bf16 | 74 | 2.5s |
| Scheme C, 7B | int8 | 69 | 2.5s |
| Production 14B | bf16 | 75 | 1s |

### Findings from distillation

The three-way comparison led us to fine-tune DeepSeek-R1-Distill-Qwen on R1's complete reasoning sequences. Size and lightweight-deployment experiments ruled out 7B because of limited capability, leaving the 14B model for further optimization. Although int8 quantization reduces quality, its latency benefit makes it our deployment precision in subsequent experiments.

## Reasoning-Path Compression

### Background

After selecting the distillation approach, we trained across all tasks using 30k production interactions. Before deployment, we found that students inherited R1's long outputs. Quality surpassed the non-reasoning model, but bf16 latency rose almost tenfold; even int8 latency increased more than fivefold. Such slow replies are unsuitable for rapidly changing livestreams.

To meet production latency requirements, we examine three CoT-compression methods:

A. Discard all training examples with outputs longer than 400 tokens during distillation.

B. Reproduce Kimi 1.5 long2short DPO. Resample the examples discarded in A; if a sufficiently short response is found, select the shortest response as chosen and the longest as rejected.

C. Extend length-only selection to quality–length Dual-Preference DPO, considering both response length and quality when choosing positive and negative examples.

### Preliminaries

- Runtime estimates assume Qwen2.5-14B decoding at 62.5 tokens/s on one H20. All runtimes in this article are converted estimates.
- Decoding dominates reasoning latency. Infrastructure optimization makes prefill time negligible here.
- Generative reward models with CoT are used to score preferences. We use DeepSeek-R1 to score response-quality preferences with the same quality-evaluation procedure.
- Related reasoning-compression work includes CoD, COCONUT, and long2short. For rejection-sampling DPO, see RS-DPO in the references below.

### Distillation after removing long examples

<!-- image:llm-distillation-and-reasoning-compression:images/figure-16d3885abf91.png | Distribution of teacher-generated output lengths. -->

- Most generated outputs contain 200–400 tokens.
- Discarding outputs above 400 tokens lowers the average decoding length to 300 tokens.
- Limitation: filtering training examples does not prevent the trained model from generating more than 400 tokens at inference time.

### Reproducing Kimi 1.5 long2short rejection-sampling DPO

Excerpt from the original Kimi 1.5 long2short rejection-sampling DPO description.

Following Kimi, repeatedly sample R1 responses for the examples discarded by scheme A, shown in red. If an output under 400 tokens is found, use the shortest sampled response as chosen and the longest as rejected for DPO.

Sampling results:

| Mean chosen length | Mean rejected length | Successfully sampled examples | Total examples |
| --- | --- | --- | --- |
| 300.1 | 515.8 | 4650 | 4915 |

Limitation: as reported in Kimi 1.5, this effectively shortens reasoning but also reduces response quality.

### Dual-Preference DPO: improving long2short with a generative reward model

Kimi's method selects only the shortest and longest responses as positive and negative examples. Its reported quality decrease suggests two issues:

- Short CoT can perform worse than long CoT, as Kimi 1.5 also observes.
- Short sampled responses may have lower quality than long ones.

We therefore prefer pairs where the shorter response also has higher quality, compensating for the disadvantage of short CoT. Pair construction becomes multi-objective optimization over short length and high response quality; their weights must be balanced empirically.

<!-- image:llm-distillation-and-reasoning-compression:images/figure-bb4538013d59.png | Domain distillation followed by DPO with quality and length preferences. -->

- Stage 1: perform domain-adaptive distillation on 30k livestream interactions using DeepSeek-R1-Distill-Qwen-14B. Since removing long examples improves both length and quality, use the filtered data.
- Stage 2: compress reasoning through dual-preference rejection-sampling DPO:

- Randomly sample K responses with DeepSeek-R1.
- Evaluate them with the same benchmark procedure and normalize the quality scores to [0,1].
- Normalize both length and quality preferences to [0,1] and combine them with weights. Select the highest combined score as chosen and the lowest as rejected within each group.
- Discard a group if the positive–negative score gap is below a threshold determined by the desired drop ratio.
- Train the domain-distilled Stage 1 model on the resulting DPO pairs.

#### Constructing quality–length preference pairs

Each candidate receives a weighted score. The first term rewards shorter output, the second higher quality. Here l is output length, s is the quality score, and alpha/beta set the trade-off. Keep normalization constants fixed within the same experiment.

<!-- image:llm-distillation-and-reasoning-compression:images/figure-bdaec00ef893.jpeg | Combining normalized length and quality preferences. -->

Choose the highest-scoring candidate as preferred and the lowest as rejected. Drop a pair when its combined-score gap is below the selected threshold. This avoids treating two nearly equivalent answers as a strong preference. The shortest candidate is not automatically the best candidate.

#### Hyperparameter search for the two preferences

Searching weights for reasoning length and response quality.

<!-- image:llm-distillation-and-reasoning-compression:images/figure-1bcd5b094eb2.png | Length and quality gaps as the length-preference weight changes. -->

- The blue curve shows the mean length difference. Quality-only selection produces chosen responses about 10 tokens longer than rejected ones. At the other extreme, chosen responses are about 213 tokens shorter, close to the length-only sampling results.
- The red curve shows the mean quality gap. Quality-only selection gives chosen responses a 2.77/10 advantage; length-only selection yields almost no quality difference.
- The curves cross in the 0.4–0.6 range. Final weights account for business preferences and the effect of discarding low-gap pairs.

After selecting preference weights, discard pairs at the low end of the combined-score-gap distribution.

<!-- image:llm-distillation-and-reasoning-compression:images/figure-3701b331d269.png | Filtering preference pairs with insufficient combined-score separation. -->

Left: mean chosen–rejected length gap versus drop ratio and length-preference weight. Right: corresponding quality gap.

- In the left heatmap, yellower regions indicate larger length differences as length weight and DropRatio vary.
- In the right quality heatmap, yellower regions indicate larger quality-score differences.
- Avoid an excessively large DropRatio: too few DPO examples can damage generalization.
- Final hyperparameters: length-preference weight alpha = 0.6 and score-gap threshold tau = 0.3.

#### Pair-construction results

Under the selected hyperparameters, chosen responses are on average 204 tokens shorter and score 2.57 points higher than rejected responses.

#### DPO preference training

The additional SFT loss helps prevent the chosen and rejected rewards from falling together. Otherwise, the model may learn a relative preference while its absolute quality deteriorates. We monitor reward values while tuning training hyperparameters.

### Compression results

| Method | Product-QA score | Mean length | Mean RT | Longest length | Longest RT |
| --- | --- | --- | --- | --- | --- |
| Baseline | 84.0 | 349.0 | 5.58 | 742.1 | 11.87 |
| Long-example filtering, SFT | 84.9 | 308.1 | 4.93 | 567.9 | 9.07 |
| long2short-DPO | 83.9 (-1.0pt) | 265.1 | 4.24 (-1.34s) | 390.2 | 6.24 (-5.63s) |
| DP-DPO, ours | 85.3 (+0.4pt) | 266.0 | 4.26 (-1.32s) | 408.0 | 6.53 (-5.35s) |

- Baseline: the distillation scheme described above using DeepSeek-R1-Distill-Qwen without additional filtering.
- Filtering long examples yields shorter reasoning and better quality than baseline.
- The source reports signed changes in the table relative to the filtered SFT method; values are reproduced as published.
- Both DPO models start from the filtered SFT model: the length-only branch reproduces long2short, while the dual-preference branch introduces DP-DPO.

### Generalization after DPO

Although DPO works well on validation, deployment traffic exposes a substantial score decrease: DP-DPO still exceeds long2short DPO but falls below the uncompressed SFT model. We attribute this to reduced generalization and take a straightforward approach: apply the dual-preference pair-construction procedure to all training product questions, increasing preference data fivefold before DP-DPO.

| Method | Validation overall | Validation multi-turn | Production overall | Production multi-turn |
| --- | --- | --- | --- | --- |
| DeepSeek-R1 | 85.5 | 84.6 | 86.0 | 84.4 |
| Filtered SFT | 84.9 | 82.3 | 83.0 | 80.8 |
| long2short-DPO | 83.9 | 81.5 | 81.9 | 78.7 |
| DP-DPO, 3k examples | 85.3 | 83.3 | 82.5 | 81.2 |
| DP-DPO, 15k examples | 87.3 | 86.6 | 84.8 | 82.4 |

- Validation and production tests use the same construction procedure, but validation shares the training collection period while the production test uses traffic after the reasoning model went live.
- Expansion affects only the training-set DPO data; it does not include post-deployment traffic.
- All our trained models lose some quality on fresh traffic, indicating widespread overfitting. DPO drops more than SFT, consistent with reduced generalization from preference learning on a small dataset.
- DP-DPO continues to outperform long2short DPO on production traffic.
- Large-data DP-DPO substantially exceeds SFT on that traffic.

### Ablation study

To determine whether quality, length, and generalization improvements come from DPO rather than pair construction alone, compare:

1. SFT using only chosen examples from dual-preference rejection sampling (DP-SFT).

2. Additional dual-preference DPO on the model from approach 1 (DP-DPO).

Both use exactly the same 15k preference pairs; only the subsequent DPO differs. The test set is the production-traffic test described in the generalization comparison. The long-filtered SFT model described in the filtering experiment is also included as a reference.

Results:

| Method | Overall score | Multi-turn score | Mean length | Mean RT | Longest length | Longest RT |
| --- | --- | --- | --- | --- | --- | --- |
| SFT | 83.0 | 80.8 | 309.9 | 4.96 | 677.9 | 10.85 |
| DP-SFT only | 83.3 | 80.3 | 302.1 | 4.83 | 490.5 | 7.85 |
| DP-SFT + DP-DPO | 84.8 (+1.5pt) | 82.4 (+1.9pt) | 272.3 | 4.36 (-0.47s) | 382.8 | 6.12 (-1.73s) |

- SFT on chosen dual-preference examples does not directly improve model quality, although it reduces the longest outputs.
- DP-DPO yields clearly better response quality and reasoning compression than SFT on the chosen examples alone.

### Quality and length across DPO epochs

| Epoch | Kimi long2short mean length | Kimi quality | DP-DPO mean length | DP-DPO quality |
| --- | --- | --- | --- | --- |
| 0 | 308.1 | 84.9 | 308.1 | 84.9 |
| 1 | 265.1 | 83.9 ↓ | 259.3 | 83.9 ↓ |
| 2 | 269.8 | 83.3 ↓ | 266.0 | 85.3 ↑ |
| 3 | 271.5 | 81.6 ↓ | 271.1 | 85.1 ↓ |

- Single-preference DPO continuously lowers mean response quality during training.
- Dual-preference DPO initially sacrifices quality while learning shorter reasoning, then surpasses the original model in the next two epochs.

## Conclusions

DeepSeek-R1's strong interaction benchmark performance motivated distillation into compact models. Comparing three approaches led us to choose DeepSeek-R1-Distill-Qwen-14B as the base.

Long reasoning still violated livestream response-time requirements. We first removed long examples before SFT, then reproduced Kimi 1.5 long2short DPO to compress reasoning substantially further.

Because length-only DPO reduced response quality, we proposed DP-DPO, using DeepSeek-R1 as a generative quality reward model and aligning both length and quality preferences. Compression remained comparable to long2short DPO, while response quality improved over SFT rather than deteriorating.

After deployment, fresh traffic revealed a significant DPO generalization problem. Expanding preference data fivefold greatly improved production-test performance, showing that more training data can mitigate this weakness.

### Future work

1. Our best production-test score, 84.8, still trails DeepSeek-R1's 86.0. We aim to develop a low-latency interaction model that exceeds R1.
2. A stronger reward model could evaluate and optimize interactions better than R1, allowing a transition from offline preference alignment to online reinforcement learning.
3. As the product develops, richer product facts, livestream state, spoken explanations, and multimodal information will pose new modeling challenges.

## From decoding estimates to service latency

The compression tables use a fixed 62.5 tokens/s decoding rate on one H20 to convert output lengths into time estimates. These estimates help compare generation volume; they do not measure production queueing, prefill, retrieval, or the rest of the service. The earlier quantization comparison and the later length-based estimates should therefore be read separately.

Keep capability transfer, preference preservation, and deployment latency as separate checks. Smaller models and shorter sequences can both lose useful information. An independent fresh-traffic set, plus a near-duplicate audit of preference-training and validation data, provides stronger evidence of generalization than a validation mean alone.
