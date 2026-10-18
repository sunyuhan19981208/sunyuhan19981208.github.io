{
  "title": "LiveThinking: reasoning at livestream speed",
  "summary": "Distill the capability, then use reinforcement learning to remove unnecessary thinking."
}

A large reasoning model can answer product questions well—and finish after the conversation has moved on.

LiveThinking addresses this in two stages. Rejection Sampling Fine-Tuning (RFT) transfers capability to a compact model. GRPO then makes its reasoning shorter without sacrificing correctness or helpfulness.

## Distillation did not remove verbose reasoning

Our teacher is the 670B DeepSeek-R1. The student, Qwen3-30B-A3B, activates only 3B parameters at inference.

The teacher generates several trajectories per input. An LLM judge filters for both correctness and helpfulness. We retain at most one passing trajectory per input and discard inputs with none, then fine-tune the student on that set.

<!-- figure:livethinking:S3.F2 | The two stages target model size and reasoning length separately. -->

Filtering mattered more for helpfulness than straightforward SFT did. Not every teacher output is equally useful to imitate.

But the student also copied the teacher's verbosity. RFT alone still produced about 353 tokens per response. A smaller model was not automatically an efficient reasoner.

## Reward a useful length, not the shortest answer

The second stage uses GRPO with three rewards:

- **Correctness:** ground the response in product information without fabrication.
- **Helpfulness:** provide relevant, practical information rather than merely avoid mistakes.
- **Length:** reward a target interval and penalize both excessive length and over-compression.

The interval is relative to the RFT model's output. It avoids two failure modes: repetitive reasoning and reasoning that skips necessary steps.

<!-- figure:livethinking:S4.F3 | The length reward penalizes both verbosity and excessive compression. -->

Correctness alone can make the model conservative. Helpfulness pushes it to use the information it has. The brevity reward does more than save tokens: it can encourage a more direct reasoning path.

## Both stages contributed

On our internal product-QA benchmark, the Qwen3-30B-A3B ablation showed:

| Training | Correctness | Helpfulness | Tokens per response |
| --- | ---: | ---: | ---: |
| Base model | 67.3% | 56.5% | 396 |
| RFT only | 81.3% | 77.0% | 353 |
| RL only | 87.5% | 90.0% | 152 |
| RFT + RL | 92.3% | 96.8% | 153 |

RFT supplies a better starting point; RL refines it. The combination outperforms either alone and exceeds the teacher's 89.0% correctness and 75.0% helpfulness on this dataset.

On MuSiQue multi-hop QA, the final model improved EM from the teacher's 41.2 to 53.5 and F1 from 57.0 to 67.2, while reducing output length from 807 to 473 tokens.

These conversational quality scores depend on the judge. Against human labels, it reached 83% accuracy for correctness and 84% for helpfulness. We therefore read the automatic metrics alongside human and production evidence.

## Deployment is a different comparison

In July 2025, LiveThinking replaced a 14B dense production model on Taobao Live. The paper reports roughly 30× lower compute cost: about 12× from distillation and 2.5× from path compression.

Order conversion increased by 59.0%, and the proportion of multi-turn users rose by 50.5%. Those online comparisons use the previous production model as their baseline, not the reasoning teacher in the offline tables.

The lasting lesson is simple: **a compact model can still overthink, and longer reasoning is not always better reasoning.** Distillation needs a separate efficiency stage.
