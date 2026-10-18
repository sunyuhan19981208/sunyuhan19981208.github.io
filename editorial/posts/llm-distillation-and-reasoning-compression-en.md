{
  "title": "Making reasoning models respond sooner",
  "summary": "Distill the model, then shorten its reasoning without teaching it to give worse answers."
}

DeepSeek-R1 scored 86 on our product-QA task; the production model scored 75. But a livestream cannot wait many seconds for every answer.

We tackled two separate costs: distillation made the model smaller, then preference training shortened what it generated.

## The starting model mattered more than adding CoT

Using 5800 product questions with a 9:1 training/validation split, we compared three approaches:

| Student and supervision | Response-quality score |
| --- | ---: |
| Qwen2.5-14B, final answers only | 78 |
| Qwen2.5-14B, full reasoning and answers | 78 |
| DeepSeek-R1-Distill-Qwen-14B, full outputs | 83 |

Adding teacher reasoning to Qwen did little. Starting from R1-Distill-Qwen worked better. Its 7B variant lacked sufficient capability, so we continued with 14B.

Quantization reduced compute but not verbosity. After expanding distillation to 30k interactions, the int8 model still averaged 5.58 seconds, with a longest runtime of about 11.87 seconds. That was too slow for comments.

## Short examples did not guarantee short inference

We first removed teacher outputs longer than 400 tokens before SFT. Average length fell, but the trained model could still generate long responses.

Next we reproduced Kimi's long2short DPO: sample several responses for a question, choose the shortest as positive and the longest as negative. This shortened reasoning further, but quality fell from 84.9 to 83.9.

The preference said “be shorter” without establishing that the short response was better.

## Select for quality and length together

DP-DPO changes pair construction. R1 scores sampled responses; normalized length and quality preferences are combined into one weighted score.

<!-- image:llm-distillation-and-reasoning-compression:images/figure-bb4538013d59.png | Domain distillation followed by quality–length preference training. -->

<!-- image:llm-distillation-and-reasoning-compression:images/figure-bdaec00ef893.jpeg | The weighted length and quality score. -->

The length term favors shorter outputs; the quality term favors better answers. Within each group, the highest score becomes chosen and the lowest rejected. Groups with too little separation are discarded.

This avoids automatically labeling a worse short trajectory as desirable. Weighting and drop ratio need joint tuning: discarding too much produces cleaner-looking pairs but too little data for generalization. Our selected positives averaged 204 fewer tokens and 2.57 higher quality points than negatives.

## What compression achieved

| Method | QA score | Mean tokens | Mean runtime | Longest runtime |
| --- | ---: | ---: | ---: | ---: |
| Distillation baseline | 84.0 | 349.0 | 5.58s | 11.87s |
| Long-example filtering + SFT | 84.9 | 308.1 | 4.93s | 9.07s |
| long2short DPO | 83.9 | 265.1 | 4.24s | 6.24s |
| DP-DPO | 85.3 | 266.0 | 4.26s | 6.53s |

Runtimes are estimates converted at 62.5 tokens/s on one H20. They primarily describe decoding cost, not measured end-to-end service latency.

Dual preferences did not produce a shorter output than length-only DPO. They preserved quality at roughly the same length.

## Validation was not the deployment test

On fresh production traffic, the 3k-data DP-DPO model fell from 85.3 on validation to 82.5, below SFT's production score of 83.0.

Expanding preference data to 15k helped substantially:

| Method | Validation | Fresh production traffic |
| --- | ---: | ---: |
| DeepSeek-R1 | 85.5 | 86.0 |
| SFT | 84.9 | 83.0 |
| DP-DPO, 3k examples | 85.3 | 82.5 |
| DP-DPO, 15k examples | 87.3 | 84.8 |

The extra preference examples came from the original training period, not the new test traffic. SFT on their chosen responses alone did not match DPO, so better data selection was not the entire explanation.

Two lessons outlast the particular hyperparameters: **optimize brevity together with quality, and evaluate preference alignment on fresh traffic.**
