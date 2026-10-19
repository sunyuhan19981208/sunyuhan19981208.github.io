{
  "title": "ControlPE: a strength dial for prompts",
  "summary": "Distill a prompt’s effect into LoRA, then explore the space between applying it fully and leaving it out."
}

Asking a model to be concise is easy. Asking it to be only a little more concise is harder. A useful instruction may remove half the answer when all we wanted was less preamble. Rewriting an adjective can change the result, but it does not give us a dependable scale.

ControlPE was our 2023 attempt to make that scale explicit: learn a prompt-induced behavior in a LoRA adapter, then vary the weight of that adapter. This post walks through the mechanism, three small experiments, and what the resulting dial does—and does not—control.

## Finding the instruction leaves another decision

Prompt optimization usually searches over words. We can rewrite instructions by hand or generate candidates and evaluate them automatically. After finding a useful instruction, however, the most direct choices remain including it or leaving it out. Words such as “slightly” express intent without defining a calibrated amount.

Length makes the problem easy to see. A brevity instruction can shorten replies while also removing explanations. In document question answering, stronger instructions to abstain without evidence can reduce fabrication while increasing refusals on answerable questions. The variable we want to adjust is the behavioral influence of an instruction, rather than its wording alone.

ControlPE comes after choosing that behavior. It learns a parameter update associated with the instruction and exposes a coefficient on that update. This requires access to model weights and an adapter-training step. A generation-only API is not enough to run the method as described. The extra work makes more sense when the same behavior needs repeated calibration.

<!-- image:controlpe:images/main-pic.png | The original length-control example: varying an instruction’s influence rather than only including or removing it. -->

The coefficient is continuous; generated text is not. Changing the coefficient need not change every answer smoothly, or by the same amount. Our curves describe behavior over a set of questions, not an exact word budget for each reply.

## Turn the instruction into an adapter

The method has three steps. The important detail is a deliberate difference between the input used to produce labels and the input used to train the adapter.

<!-- image:controlpe:images/method.png | Generate labels with the target instruction, train LoRA without it, then vary the adapter’s merge weight. -->

### Generate demonstrations with the target prompt

We start with task inputs, an original prompt template, and a target instruction. The base model sees all three and generates the labels for a distillation dataset. There is no larger external teacher in this procedure: the same model supplies demonstrations under an additional instruction.

<!-- equation:controlpe-data -->

The original template organizes the task; the target prompt specifies the behavior to add. For brevity, the labels come from responses generated with a brevity instruction. For step-by-step reasoning, they come from generation with a reasoning instruction. The dataset retains the task input and the generated response.

This also limits what distillation can learn. If the prompted base model still performs the task poorly, its demonstrations do not supply a missing capability by themselves. A shorter label is not necessarily a better label. We need to inspect task completion alongside the behavior we intend to transfer.

### Remove the target prompt during training

We freeze the base model and train LoRA on those input–response pairs. Training uses the original template and task input, but omits the target instruction. The desired response still comes from the prompted generation. The adapter must therefore account for an influence that is no longer present in the text input.

<!-- equation:controlpe-loss -->

Keeping the target instruction in the training input would weaken this separation. The model could continue to rely on its wording, and we would have less reason to expect the adapter alone to reproduce the behavior. The intended inference setup uses the original prompt plus the trained adapter, without repeating the distilled instruction.

Reproduction remains approximate. We fit outputs on finite data; we do not establish that a parameter update and a natural-language instruction are equivalent for every input. The base model, template, and data distribution remain part of the experiment. Changing them calls for another check.

### Scale the update, not the base model

LoRA represents a weight update using two low-rank matrices. We attach a coefficient to the resulting update. In the expression below, λ is the coefficient we vary, while s is the adapter’s existing scaling factor. Keeping those concepts separate makes implementation easier to reason about.

<!-- equation:controlpe-scale -->

At zero, the learned update is absent. At one, it is fully applied. Intermediate values give us a range to scan without retraining. The update is linear in this coefficient; answer length, quality, and refusal behavior need not be.

One practical detail matters here. Multiplying both low-rank matrices by λ scales their product by λ squared. That is a different parameterization from scaling one matrix. The paper compares these choices and uses single-matrix scaling in the later experiments. Otherwise, two implementations with the same displayed weight could apply different update strengths.

## Start with response length

The experiments use LLaMA2-7B-chat, with rank-16 LoRA adapters on every attention `q_proj` and `v_proj`. Training uses batch size 128, a learning rate of 3e-4, and three epochs. These describe the historical setup, rather than defaults we would automatically recommend for another model.

For length control, the first 10,000 Alpaca instructions supply the distillation inputs. Instructions 10,001–10,100 form the test set. The reported number is the total response-token count for all 100 test instructions, not the mean length of one response.

| Configuration | Total tokens across 100 test responses |
| --- | ---: |
| Original template | 14,766 |
| With the brevity instruction | 7,096 |
| Full distilled LoRA | 6,640 |

The instruction already causes a large change, and the full adapter produces a similar brevity effect. The more useful question is what happens between the endpoints. Scanning the merge weight produces a range of response lengths without choosing another natural-language formulation each time.

<!-- image:controlpe:images/short-prompt-lora.png | Response length under single-matrix and two-matrix scaling. Approximate linearity is an observation on this test set. -->

Single-matrix scaling gives an approximately linear aggregate trend in this experiment. That supports the idea of an adjustable influence, but does not establish equal answer quality at every setting. A practical evaluation should also check whether essential facts survive, required steps remain, and unusually long answers are still a problem.

An aggregate can hide different reactions. A factual lookup may already need only a sentence; a multi-step explanation may become shorter by losing a necessary step. I would use the curve to identify a promising region, then inspect questions inside that region. The coefficient should not be read as a universal per-answer length setting.

## Refusal is a trade-off, not a rate to maximize

The second experiment uses document question answering. A reply should draw on the supplied material and abstain when that material cannot answer the question. We distill an instruction expressing that requirement, then adjust its influence between answering too readily and refusing too often.

The first 10,000 wikipedia-trivia examples supply distillation inputs. Examples 10,001–10,200 form the test set, with sufficient evidence in 80% of cases and insufficient evidence in 20%. Direct refusal is 0% without the instruction, 27% with it, and 29% with the full distilled adapter.

<!-- image:controlpe:images/refuse-lora.png | Direct-refusal rate as the adapter weight changes. This measure counts an explicit refusal form, not every indirect expression of uncertainty. -->

A rate of 29% is not inherently better than 27%. We need to know which questions were refused: unsupported questions should be caught, while supported questions should remain answerable. The paper also examines refusal precision and recall. Stronger refusal behavior trades these off rather than improving both together.

<!-- image:controlpe:images/refuse_quality.png | Refusal precision and recall under changing weights. How often the model refuses and whether those refusals are appropriate are separate questions. -->

The scoring rule explains another feature of the curve. Direct refusal is counted through a particular explicit response. At weights of 0.1–0.5, some outputs become more cautious or avoid fabrication without using that response. The direct-refusal curve changes more visibly in the 0.6–1.0 range. A low value can therefore describe either continued unsupported answering or a different way of expressing uncertainty.

The useful lesson is to calibrate against evidence availability. Maximizing refusal frequency alone can favor a model that says nothing useful; maximizing answer frequency can conceal unsupported claims. The dial makes the trade-off easier to explore, but still needs separate checks on answerable and unanswerable examples.

## A stronger reasoning prompt is not always better

We next distill step-by-step reasoning. The first 10,000 Alpaca instructions again supply the demonstrations, and GSM8K supplies the evaluation task. The distillation data is therefore different from the benchmark; this procedure does not construct labels from GSM8K reference solutions.

| Configuration | GSM8K accuracy |
| --- | ---: |
| Without the step-by-step instruction | 12.6% |
| With the instruction | 14.6% |
| Full distilled LoRA | 14.9% |

<!-- image:controlpe:images/cot.png | Scanning the reasoning adapter: a stronger result appears near 0.8 rather than at full strength in this experiment. -->

The best region in the weight scan is around 0.8, rather than the fully applied adapter. Even when an instruction helps on average, maximizing its influence need not maximize task accuracy. A stronger tendency to reason changes the generation process without guaranteeing that the final answer improves.

These results belong to a particular 7B model and evaluation setup from 2023. They do not make 0.8 a reusable setting for reasoning models, and the reported accuracy differences should not be transferred to newer systems. What matters for this method is that an intermediate region could be examined at all. A binary prompted/unprompted comparison would miss it.

## Two adapters give a surface to calibrate

We also combine brevity and refusal control. This experiment reuses the two adapters already trained; it does not train a new adapter for their combination. Written as a sum of updates, the idea is:

<!-- equation:controlpe-compose -->

The two coefficients scale different updates. They do not make the resulting behaviors independent. Refusals can change response length, and compression can change the wording used to express insufficient evidence. A setting that looks useful along one axis can behave differently once the other adapter is active.

<!-- image:controlpe:images/length_heatmap.png | Response length across the two adapter weights. The joint setting is a calibration surface, not two guaranteed independent controls. -->

<!-- image:controlpe:images/refuse_heatmap.png | Refusal counts over the same joint scan. Each adapter remains adjustable, with interaction between their effects. -->

The test uses the same 200 DocQA examples. Although the brevity adapter was trained on Alpaca rather than wikipedia-trivia, it retains an observable length-control effect in this combination. Refusal behavior also remains adjustable. This makes reuse worth exploring, while leaving a substantial gap between one observed transfer and reliable generalization across arbitrary tasks.

For a reproduction, I would retain both the individual adapter scans and the joint scan. First establish what each update changes on its own, then look for departures when they are combined. A favorable final metric could otherwise reflect side effects cancelling each other rather than both intended behaviors improving.

The same reasoning argues against assuming that many adapters will compose cleanly. This experiment covers two specific behaviors, datasets, and updates. Each extra control would introduce another interaction to inspect. The coefficients offer a convenient experimental space, not a guarantee that the space remains easy to calibrate as it grows.

## Two meanings of continuous control

ControlPE can be confused with soft prompts or prompt tuning. Those also involve continuous parameters, but this method does not replace an input instruction with trainable embeddings. The learned change lives in internal LoRA updates, while the inference input can keep the original text template. Where the update lives matters when deciding whether an existing serving stack can support it.

It also differs from changing sampling temperature. Temperature changes how the output distribution is sampled; ControlPE changes the weights used to compute that distribution. One is a generation setting, the other a learned behavioral update. In a reproduction, I would hold sampling settings fixed while scanning the adapter coefficient so that length changes have an interpretable source.

The adapter’s existing scaling constant and the additional control coefficient need separate attention too. A tool may fold scaling into a matrix or apply it during the forward pass. What matters is the effective update, not a particular configuration-field name. Before trusting intermediate settings, I would verify that zero recovers the base model and full strength recovers the trained adapter.

## A calibration pass I would run

I would start with one behavior and retain three references: the original template, the template with the target prompt, and the template with the full adapter. The first pair checks whether the instruction works. The third checks whether distillation transfers a comparable change. If the full adapter does not learn the intended behavior, a finer coefficient scan cannot repair the earlier data or training problem.

Next, I would generate responses for the same held-out inputs across several coefficients. Aggregate metrics identify regions worth inspecting, while matched questions show what each setting removes or retains. Length control needs checks on facts and explanatory steps. Refusal control needs separate answerable and unanswerable subsets. For reasoning, final correctness matters alongside the generated process; counting reasoning paragraphs is not enough.

Selecting a coefficient also calls for a separate final test set. Using one small set both to choose a weight and to report its performance can make calibration look more stable than it is. The paper’s length test has 100 instructions and its refusal test has 200 examples. They reveal useful trends without supporting very fine-grained subgroup conclusions. A domain change needs another check rather than inheriting a historical curve.

For two adapters, I would begin with a sparse grid and compare its edges against the individual scans before refining a promising region. The goal would be an area with acceptable task quality and target behavior, not merely the best-looking isolated point. A result that works only in a very narrow region raises a different deployment question: why is the setting so sensitive?

This calibration procedure is my suggested way to use the method, rather than additional product validation reported in the paper. The experiments show that adapter weights can change behavior. A deployment must still establish whether that calibration survives a new base model, a different template, or a different mix of questions.

## How I would use the dial

The main idea I take from ControlPE is to separate choosing an instruction from choosing its strength. The instruction defines the behavior, distillation turns its influence into a reusable update, and a weight scan helps locate a suitable operating region. These steps do different jobs, and the final coefficient is hard to interpret if any of them is unclear.

Before interpreting a scan, I would check four things: the target prompt is present during label generation and absent during adapter training; the base model and original template stay fixed; scaling affects the learned update rather than the whole base model; and evaluation inputs are held out from label generation. I would then report both behavior and task metrics. Shorter, more cautious, or more elaborate outputs are descriptions, not automatic improvements.

The scope is modest: one model family, small experimental tests, no exact control of individual outputs, and no general guarantee for adapter composition. Within that scope, the method opens a parameter space we can test. When an effective prompt repeatedly swings between too much influence and too little, exploring the space between those endpoints can be useful.
