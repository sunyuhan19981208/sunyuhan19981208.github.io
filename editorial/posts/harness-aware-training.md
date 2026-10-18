{
  "title": "Training for a changing Harness",
  "summary": "Tools, rules, and prompts change. Training should not assume one fixed runtime."
}

We moved business rules, tools, and prompts into a Harness so that every operational change would not require retraining. Then we met a second problem: the compact model did not always follow the updated runtime.

Large models could often interpret new configurations, but were too slow. Small models were fast, yet fixed-configuration fine-tuning encouraged them to memorize tool names, Skill identifiers, and prompt wording.

Harness-Aware Training (HAT) addresses that mismatch: the environment keeps changing after deployment, while training usually exposes the model to one version.

## What belongs in the Harness

Our runtime separates four components:

| Component | Responsibility |
| --- | --- |
| Skills | Load business rules and response strategies on demand |
| Tools | Retrieve external product, inventory, and other facts |
| Prompt Pipeline | Assemble context for the current request |
| Hooks | Validate inputs, tool arguments, responses, and stopping conditions |

Editing these components changes behavior without changing model weights. Iteration still involves people: diagnose failures, review a proposed edit, run regressions, and decide whether to deploy.

More rules did not always help. The second Harness revision improved both development-set accuracy and effectiveness; later long-tail additions caused regressions. That made regression checks and explicit stopping criteria part of the process.

## Vary the environment during training

The central technique is Harness-State Augmentation (HSA). We change Skill identifiers and wording, tool schemas, prompt structure, and Hook configuration while preserving the task's meaning.

The aim is not to break the runtime randomly. It is to teach the model to read the rules it receives instead of relying on one familiar surface form.

<!-- figure:harness-aware-training:S3.F4 | HSA spans supervised and reinforcement learning; general distillation restores broader capabilities. -->

Training has three stages:

1. **HSA-SFT:** a strong teacher generates trajectories under varied configurations; filtered examples train the compact model.
2. **General OPD:** on-policy distillation on general data recovers capabilities lost during domain fine-tuning.
3. **HSA-RL:** the model uses tools and handles failures in changing simulated environments, then learns from the outcomes.

The stages have distinct jobs: learn the task, recover general ability, then practice interaction under variation.

## Test the task—and the changed configuration

With Qwen3.6-35B-A3B, the results were:

| Metric | Base model | HAT |
| --- | ---: | ---: |
| Live-Stream QA | 80.3 | 94.8 |
| Harness-Variant QA | 75.4 | 94.6 |

HAT retained an IFEval Prompt score of 83.5. Fixed-Harness SFT, by comparison, lost 7.7 points from the base model. Better domain scores are not enough if the model becomes worse at following new instructions.

Evaluation roles also matter. The data-generation teacher, RL reward judge, final evaluation judge, and human calibration should not be treated as one interchangeable signal. The report examines their relationships separately.

## MTP was not a free deployment switch

A task-trained model cannot simply reuse an unadapted draft head and expect useful speculative decoding. We trained the MTP head on domain outputs to improve acceptance, then measured the complete agent.

On one H20 with MTP enabled, end-to-end latency was 3.407 seconds at P50 and 8.114 seconds at P95. Gains were stronger at low concurrency and should not be extrapolated to every workload.

HAT does not make a model robust to every imaginable change. It brings the configuration changes that actually occur in the business into training and evaluation. **If the Harness will evolve, that evolution belongs in the training conditions.**
