DeepSeek-R1 scored 86 on our product-QA task; the production model scored 75. But a livestream cannot wait many seconds for every answer.

We tackled two separate costs: distillation made the model smaller, then preference training shortened what it generated.


## Distillation task and evaluation {#starting-with-a-task-worth-distilling}

### Product QA {#why-we-started-with-product-questions}

Our chain has eight intent-based tasks, each with its own evidence and instructions. We started with product questions: the model must understand the viewer and decide what the material supports. DeepSeek-R1 supplies the reasoning demonstrations; we first test whether a smaller model can learn from them.

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

### Answer quality evaluation {#how-we-tell-whether-an-answer-improved}

DeepSeek-R1 scores responses from the product information, dialogue history, viewer question, and AI-host answer. Evaluation combines four dimensions:

- Consistency with the question: understand the viewer's actual intent and answer correctly, using history when present.
- Consistency with product information: neither invent facts nor refuse when the provided information suffices. If information is insufficient or the question concerns another product, refer the viewer to customer service.
- Internal consistency: avoid logical contradictions and produce natural language suitable for speech.
- Instruction consistency: follow the avatar-host requirements in the prompt.

## R1 distillation {#moving-r1s-answer-behavior-into-a-smaller-model}

On product questions, DeepSeek-R1 scores 86/100 versus 75 for the production model, an 11-point gap. We investigate three ways to transfer its capabilities to compact models:

1. Start from Qwen and distill only R1's final answer, excluding thinking.
2. Start from Qwen and distill the complete response, including thinking.
3. Start from DeepSeek-R1-Distill-Qwen and distill the complete response, including thinking.

The experiments support three conclusions:

1. Scheme C achieves the best response quality, 83/100, supporting DeepSeek-R1-Distill-Qwen as the starting point.
2. With Qwen2.5-Instruct as the base, including CoT makes little difference.
3. Refusal agreement with R1 rose with size, approaching roughly 85% on this data. Partially answerable questions create boundary cases, so we treat agreement as a clue to the student’s decision habits, not its final answer quality.

### Distillation schemes

| Scheme | Method | Description |
| --- | --- | --- |
| A | Qwen, direct answer | R1-generated data excluding the thinking inside `<think>` tags; Qwen2.5-Instruct bases at several sizes. |
| B | Qwen with CoT | R1-generated data including `<think>` sequences; Qwen2.5-Instruct bases at several sizes. |
| C | DeepSeek-R1-Distill-Qwen with CoT | Complete R1-generated sequences including thinking; DeepSeek-R1-Distill-Qwen bases at several sizes. |

### Distillation comparison {#comparing-three-ways-to-distill}

| Scheme | Model/method | Mean quality score |
| --- | --- | --- |
| — | DeepSeek-R1 | 86 |
| A | Qwen14B, direct answer, 5.8k dataset | 78 |
| B | Qwen14B with CoT, 5.8k dataset | 78 |
| C | DeepSeek-R1-Distill-Qwen-14B with CoT, 5.8k dataset | 83 |
| — | Production model | 75 |

Evaluate generated responses using the quality-evaluation procedure above.

### Student model size {#how-small-can-we-go}

- The model also decides whether the evidence can answer the question. Both the product and facts must match. We want it to separate what it knows from what it cannot confirm before replying, rather than maximize refusal.
- We study how model size relates to distillation by measuring refusal agreement with DeepSeek-R1. This is an approximate behavioral indicator rather than a complete quality metric.
- Compare schemes A, B, and C at 1.5B, 7B, and 14B.

<figure class="publication-figure figure-landscape" id="blog-figure-1"><div class="figure-heading"><span class="figure-label">Figure 1</span><button aria-label="Enlarge Figure 1" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Refusal agreement across model sizes and distillation schemes." decoding="async" height="648" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-1fd175734b7c.jpeg" width="1080"/></div><figcaption class="publication-caption">Refusal agreement across model sizes and distillation schemes.</figcaption></figure>

- Agreement rises with model size for all three schemes. Direct-answer distillation is preferable at 1.5B.
- At 14B, DeepSeek-R1-Distill-Qwen exceeds direct-answer distillation and approaches Qwen-with-CoT agreement.

### Quantization results {#what-quantization-saves-and-what-it-costs}

The bf16 14B model took about 10 seconds per answer. Quantization brought it to roughly 5 seconds with a quality cost; 7B was faster but answered less well. We needed both comparisons before choosing the next model.

| Method | Precision | Quality /100 | Runtime |
| --- | --- | --- | --- |
| Scheme C, 14B | bf16 | 83 | 10s |
| Scheme C, 14B | int8 | 80 | 5s |
| Scheme C, 7B | bf16 | 74 | 2.5s |
| Scheme C, 7B | int8 | 69 | 2.5s |
| Production 14B | bf16 | 75 | 1s |

### Model choice {#the-choice-we-took-into-the-next-round}

We continued with DeepSeek-R1-Distill-Qwen-14B, training on the teacher’s complete reasoning and answer. Int8 reduced deployment cost at some loss of quality relative to bf16. The student answered better but retained the teacher’s long outputs, which quantization alone did not resolve.

## Reasoning-path compression {#reasoning-path-compression}

### Reasoning latency after distillation {#the-student-learned-the-waiting-time-too}

Distillation then expanded to 30k production interactions covering all tasks. Before launch, bf16 latency was almost ten times that of the non-reasoning model; int8 remained over five times higher. The longer reasoning made replies too slow for livestreams, so we compared three compression methods:

To meet production latency requirements, we examine three CoT-compression methods:

A. Discard all training examples with outputs longer than 400 tokens during distillation.

B. Reproduce Kimi 1.5 long2short DPO. Resample the examples discarded in A; if a sufficiently short response is found, select the shortest response as chosen and the longest as rejected.

C. Extend length-only selection to quality–length Dual-Preference DPO, considering both response length and quality when choosing positive and negative examples.

### Timing and scoring {#a-note-on-timing-and-quality-scores}

- Runtime estimates assume Qwen2.5-14B decoding at 62.5 tokens/s on one H20. All runtimes in this article are converted estimates.
- Decoding dominates reasoning latency. Infrastructure optimization makes prefill time negligible here.
- Generative reward models with CoT are used to score preferences. We use DeepSeek-R1 to score response-quality preferences with the same quality-evaluation procedure.
- Related reasoning-compression work includes CoD, COCONUT, and long2short. For rejection-sampling DPO, see RS-DPO in the references below.

### Filtering long examples {#first-try-discard-long-examples}

<figure class="publication-figure figure-landscape" id="blog-figure-2"><div class="figure-heading"><span class="figure-label">Figure 2</span><button aria-label="Enlarge Figure 2" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Distribution of teacher-generated output lengths." decoding="async" height="514" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-16d3885abf91.png" width="1026"/></div><figcaption class="publication-caption">Distribution of teacher-generated output lengths.</figcaption></figure>

- Most generated outputs contain 200–400 tokens.
- Discarding outputs above 400 tokens lowers the average decoding length to 300 tokens.
- Limitation: filtering training examples does not prevent the trained model from generating more than 400 tokens at inference time.

### long2short training {#next-try-prefer-shorter-answers-with-long2short}

Excerpt from the original Kimi 1.5 long2short rejection-sampling DPO description.

We repeatedly sampled R1 on examples discarded by scheme A. Once a response below 400 tokens appeared, the shortest candidate became chosen and the longest became rejected for DPO. This follows long2short and tests a preference based on length alone.

Sampling results:

| Mean chosen length | Mean rejected length | Successfully sampled examples | Total examples |
| --- | --- | --- | --- |
| 300.1 | 515.8 | 4650 | 4915 |

Limitation: as reported in Kimi 1.5, this effectively shortens reasoning but also reduces response quality.

### DP-DPO: quality and length preferences {#dp-dpo-consider-quality-when-choosing-the-shorter-answer}

Kimi's method selects only the shortest and longest responses as positive and negative examples. Its reported quality decrease suggests two issues:

- Short CoT can perform worse than long CoT, as Kimi 1.5 also observes.
- Short sampled responses may have lower quality than long ones.

DP-DPO selects pairs using both quality and length. We inspect their score gap, length gap, and retained sample count before setting the weights, checking whether compression preserves the information needed to answer.

<figure class="publication-figure figure-landscape" id="blog-figure-3"><div class="figure-heading"><span class="figure-label">Figure 3</span><button aria-label="Enlarge Figure 3" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Domain distillation followed by DPO with quality and length preferences." decoding="async" height="872" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-bb4538013d59.png" width="1030"/></div><figcaption class="publication-caption">Domain distillation followed by DPO with quality and length preferences.</figcaption></figure>

- Stage 1 remains domain distillation on 30k interactions using DeepSeek-R1-Distill-Qwen-14B. Filtering long examples improved both length and evaluation scores in the earlier comparison, so we use that filtered corpus before applying preference optimization.
- Stage 2: compress reasoning through dual-preference rejection-sampling DPO:

- Randomly sample K responses with DeepSeek-R1.
- Evaluate them with the same benchmark procedure and normalize the quality scores to [0,1].
- Normalize both length and quality preferences to [0,1] and combine them with weights. Select the highest combined score as chosen and the lowest as rejected within each group.
- Discard a group if the positive–negative score gap is below a threshold determined by the desired drop ratio.
- Train the domain-distilled Stage 1 model on the resulting DPO pairs.

#### Preference-pair construction {#constructing-qualitylength-preference-pairs}

Each candidate gets one combined score. Its first term favors shorter output, and its second favors higher quality. Here l is length, s is quality, and alpha/beta set the balance. We keep the normalization constants fixed within an experiment so the candidate scores remain comparable.

<figure class="publication-figure figure-landscape" id="blog-figure-4"><div class="figure-heading"><span class="figure-label">Figure 4</span><button aria-label="Enlarge Figure 4" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Combining normalized length and quality preferences." decoding="async" height="217" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-bdaec00ef893.jpeg" width="1080"/></div><figcaption class="publication-caption">Combining normalized length and quality preferences.</figcaption></figure>

Within each question’s candidates, the highest combined score becomes chosen and the lowest rejected. Pairs below the score-gap threshold are discarded to avoid imposing strong preferences on near-equivalent answers. Selection therefore depends on quality and length, not shortest output alone.

#### Quality and length weights {#hyperparameter-search-for-the-two-preferences}

Searching weights for reasoning length and response quality.

<figure class="publication-figure figure-landscape" id="blog-figure-5"><div class="figure-heading"><span class="figure-label">Figure 5</span><button aria-label="Enlarge Figure 5" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Length and quality gaps as the length-preference weight changes." decoding="async" height="565" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-1bcd5b094eb2.png" width="1000"/></div><figcaption class="publication-caption">Length and quality gaps as the length-preference weight changes.</figcaption></figure>

- The blue curve shows the mean length difference. Quality-only selection produces chosen responses about 10 tokens longer than rejected ones. At the other extreme, chosen responses are about 213 tokens shorter, close to the length-only sampling results.
- The red curve shows the mean quality gap. Quality-only selection gives chosen responses a 2.77/10 advantage; length-only selection yields almost no quality difference.
- The curves cross in the 0.4–0.6 range. Final weights account for business preferences and the effect of discarding low-gap pairs.

After selecting preference weights, discard pairs at the low end of the combined-score-gap distribution.

<figure class="publication-figure figure-landscape" id="blog-figure-6"><div class="figure-heading"><span class="figure-label">Figure 6</span><button aria-label="Enlarge Figure 6" class="figure-expand" type="button">View figure ↗</button></div><div class="figure-media"><img alt="Filtering preference pairs with insufficient combined-score separation." decoding="async" height="444" loading="lazy" src="../llm-distillation-and-reasoning-compression/images/figure-3701b331d269.png" width="1000"/></div><figcaption class="publication-caption">Filtering preference pairs with insufficient combined-score separation.</figcaption></figure>

Left: mean chosen–rejected length gap versus drop ratio and length-preference weight. Right: corresponding quality gap.

- In the left heatmap, yellower regions indicate larger length differences as length weight and DropRatio vary.
- In the right quality heatmap, yellower regions indicate larger quality-score differences.
- Avoid an excessively large DropRatio: too few DPO examples can damage generalization.
- Final hyperparameters: length-preference weight alpha = 0.6 and score-gap threshold tau = 0.3.

#### Pair-construction results

Under the selected hyperparameters, chosen responses are on average 204 tokens shorter and score 2.57 points higher than rejected responses.

#### Domain-model DPO training {#dpo-preference-training}

The additional SFT loss helps prevent the chosen and rejected rewards from falling together. Otherwise, the model may learn a relative preference while its absolute quality deteriorates. We monitor reward values while tuning training hyperparameters.

### Answer quality after compression {#did-quality-survive-the-shorter-output}

| Method | Product-QA score | Mean length | Mean RT | Longest length | Longest RT |
| --- | --- | --- | --- | --- | --- |
| Baseline | 84.0 | 349.0 | 5.58 | 742.1 | 11.87 |
| Long-example filtering, SFT | 84.9 | 308.1 | 4.93 | 567.9 | 9.07 |
| long2short-DPO | 83.9 (-1.0pt) | 265.1 | 4.24 (-1.34s) | 390.2 | 6.24 (-5.63s) |
| DP-DPO, ours | 85.3 (+0.4pt) | 266.0 | 4.26 (-1.32s) | 408.0 | 6.53 (-5.35s) |

- Baseline: the distillation scheme described above using DeepSeek-R1-Distill-Qwen without additional filtering.
- Filtering long examples yields shorter reasoning and better quality than baseline.
- Signed score changes use filtered SFT as the reference; signed latency changes use the unfiltered baseline. The table uses different references for these two metrics.
- Both DPO models start from the filtered SFT model: the length-only branch reproduces long2short, while the dual-preference branch introduces DP-DPO.

### Quality regression on new traffic {#validation-improved-but-fresh-traffic-did-not}

DP-DPO scored well on validation but fell below uncompressed SFT on fresh production traffic, while remaining above long2short. We expanded preference construction to every training product question, increasing data fivefold, then repeated training. Validation and fresh-traffic results are reported separately.

| Method | Validation overall | Validation multi-turn | Production overall | Production multi-turn |
| --- | --- | --- | --- | --- |
| DeepSeek-R1 | 85.5 | 84.6 | 86.0 | 84.4 |
| Filtered SFT | 84.9 | 82.3 | 83.0 | 80.8 |
| long2short-DPO | 83.9 | 81.5 | 81.9 | 78.7 |
| DP-DPO, 3k examples | 85.3 | 83.3 | 82.5 | 81.2 |
| DP-DPO, 15k examples | 87.3 | 86.6 | 84.8 | 82.4 |

- Validation and production tests use the same construction procedure, but validation shares the training collection period while the production test uses traffic after the reasoning model went live.
- Expansion affects only the training-set DPO data; it does not include post-deployment traffic.
- All trained models lost quality on fresh traffic, more so for DPO than SFT. This raised concerns about overfitting on the small preference set. Coverage, near-duplicates, and traffic changes also need checking; this comparison cannot attribute the entire gap to DPO.
- DP-DPO continues to outperform long2short DPO on production traffic.
- Expanding to 15k examples raises DP-DPO’s overall fresh-traffic score from 82.5 to 84.8, above the SFT reference in this comparison.

### Data selection and DPO ablations {#better-selected-data-or-a-useful-dpo-step}

Better selected examples could explain part of the gains after data expansion. We compared two configurations to test the additional contribution of DPO:

1. SFT using only chosen examples from dual-preference rejection sampling (DP-SFT).

2. Additional dual-preference DPO on the model from approach 1 (DP-DPO).

Both use the same 15k preference pairs and differ only in the later DPO step. Evaluation retains the fresh-traffic test and long-filtered SFT reference, separating the effect of example selection from that of preference optimization.

Results:

| Method | Overall score | Multi-turn score | Mean length | Mean RT | Longest length | Longest RT |
| --- | --- | --- | --- | --- | --- | --- |
| SFT | 83.0 | 80.8 | 309.9 | 4.96 | 677.9 | 10.85 |
| DP-SFT only | 83.3 | 80.3 | 302.1 | 4.83 | 490.5 | 7.85 |
| DP-SFT + DP-DPO | 84.8 (+1.5pt) | 82.4 (+1.9pt) | 272.3 | 4.36 (-0.47s) | 382.8 | 6.12 (-1.73s) |

- SFT on the chosen examples barely changes the overall score and slightly lowers the multi-turn score, although it shortens the longest outputs.
- Continuing with DPO improves both scores and reasoning length. This comparison gives us more reason to connect the additional gains to the preference update.

### Effect of training epochs {#what-changed-with-more-epochs}

| Epoch | Kimi long2short mean length | Kimi quality | DP-DPO mean length | DP-DPO quality |
| --- | --- | --- | --- | --- |
| 0 | 308.1 | 84.9 | 308.1 | 84.9 |
| 1 | 265.1 | 83.9 ↓ | 259.3 | 83.9 ↓ |
| 2 | 269.8 | 83.3 ↓ | 266.0 | 85.3 ↑ |
| 3 | 271.5 | 81.6 ↓ | 271.1 | 85.1 ↓ |

- Single-preference DPO continuously lowers mean response quality during training.
- Dual-preference DPO initially sacrifices quality while learning shorter reasoning, then surpasses the original model in the next two epochs.

## Results {#conclusions}

DeepSeek-R1's strong interaction benchmark performance motivated distillation into compact models. Comparing three approaches led us to choose DeepSeek-R1-Distill-Qwen-14B as the base.

Long reasoning still violated livestream response-time requirements. We first removed long examples before SFT, then reproduced Kimi 1.5 long2short DPO to compress reasoning substantially further.

That quality drop led us to DP-DPO: DeepSeek-R1 scores the candidates, and pair selection weighs quality with length. Compression remains close to long2short, while reply quality improves over SFT in this comparison.

The fresh-traffic drop led us to expand preference data fivefold, which improved that test. Data coverage therefore needed investigation beyond the apparent validation gain.

### Planned improvements {#future-work}

1. Our best production-test score, 84.8, still trails DeepSeek-R1's 86.0. We aim to develop a low-latency interaction model that exceeds R1.
2. A stronger reward model could evaluate and optimize interactions better than R1, allowing a transition from offline preference alignment to online reinforcement learning.
3. As the product develops, richer product facts, livestream state, spoken explanations, and multimodal information will pose new modeling challenges.

## Serving latency and offline timing {#from-decoding-estimates-to-service-latency}

The compression tables convert output lengths into time using 62.5 tokens/s on one H20. These estimates compare generation volume; they exclude production queueing, prefill, retrieval, and business processing. They are separate from the earlier quantization measurements and from actual end-to-end latency.

Capability transfer, preference quality, and deployment latency need separate checks. Smaller models and shorter sequences may lose information. Hold out fresh traffic and check near-duplicates between preference training and validation before judging whether compression generalizes beyond the validation mean.
