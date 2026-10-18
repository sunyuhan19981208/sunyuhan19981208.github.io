{
  "title": "Making sense of livestream comments",
  "summary": "Intent recognition, entity parsing, retrieval, and the context a short comment leaves unsaid."
}

A viewer asks for a toilet recommendation, then sends just two words: “smart toilet.” In isolation, that looks like a request for a product presentation. In context, it is still a shopping question.

Fragments like this are common in livestreams. The system needs the viewer's history, the product currently on screen, and the live product list—not just the latest message.

## Start with a clear pipeline

Our early system followed a fixed workflow: **FAQ matching → intent recognition → entity parsing → retrieval → generation**.

<!-- image:llm-barrage-interaction:images/figure-92603a48521c.png | The original viewer-interaction workflow. -->

A merchant FAQ match produces a direct answer. Otherwise, intent determines the next action. An item-link question triggers lookup by link number; a question without a named product uses the current presentation. A request to introduce a product changes the presentation order instead of generating another answer.

Many apparent generation failures actually start earlier: the system has misunderstood the question or retrieved the wrong product.

## More context before more reasoning

We replaced single-turn BERT classification with Qwen2.5-7B. The model receives the current product, dialogue history, and comment, then directly predicts the intent label.

We collected disagreements between the old model and DeepSeek-V3, annotated and reviewed them, and retained over 3000 multi-turn examples. Adding the existing single-turn data produced these results:

| Method | Accuracy |
| --- | ---: |
| DeepSeek-R1 with prompting | 71% |
| BERT with the same single- and multi-turn data | 69% |
| Qwen2.5-7B, multi-turn SFT | 77% |
| Qwen2.5-7B, single- and multi-turn SFT | 80% |

We also asked R1 to generate reasoning for examples with known labels. Training on those chains reduced accuracy from 77% to 68%. For this classification task, generated reasoning diluted the supervision we actually needed.

The practical lesson was to fix context and labels before adding more thinking.

## “Size 39” is not “link 39”

Entity parsing extracts product names, attributes, and item-link numbers. Three recurring errors shaped our augmentation data:

- Numbers in specifications—2 HP, size 39, iPhone 15—get mistaken for links.
- A specific product from history overrides a new request for a broader category.
- The viewer switches products, but the model keeps using the previous entity.

We generated adversarial examples with DeepSeek-R1 and filtered them manually. LoRA fine-tuning of a 7B model reached 92% entity-parsing accuracy, versus 87% for R1. Evaluation used character 2-gram Jaccard similarity with a 0.7 correctness threshold.

## Keep retrieval and generation focused

The vector store stays synchronized with the live product list, with one vector per `itemId`. Semantic retrieval is followed by BM25 reranking and combined lexical–semantic filtering. Lexical matching helps with short queries.

The generation model then handles product questions, casual chat, or promotions using the retrieved facts. Missing information should remain missing; fluent wording cannot substitute for evidence.

We train separate presentation modes: text replies answer directly within a 60-Chinese-character limit; spoken replies briefly restate the question and normalize numbers and English for TTS.

One data detail matters: **split training and validation before creating the two modes**. Otherwise, variants of the same example leak across the split. We saw validation accuracy exceed 95% under this leakage.

## Where the workflow ran out of room

The system eventually covered more than 80% of valid viewer intents. But fixed routing became awkward when multiple comments arrived together, questions depended on the spoken script, or answering required several tools.

Those cases became the starting point for the later agentic redesign.
