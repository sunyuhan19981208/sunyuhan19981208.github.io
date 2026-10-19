{
  "title": "Making sense of livestream comments",
  "summary": "Intent recognition, entity parsing, retrieval, and the context a short comment leaves unsaid."
}

A viewer asks for a toilet recommendation, then sends just two words: “smart toilet.” In isolation, that looks like a request for a product presentation. In context, it is still a shopping question.

Fragments like this are common in livestreams. The system needs the viewer's history, the product currently on screen, and the live product list—not just the latest message.


## Text replies and spoken replies need different treatment

We answer comments in two ways: text in the chat area, or TTS and lip synchronization so the avatar can speak. The inputs are similar, but resource cost, waiting time, and wording differ. Spoken replies mainly run in the more resource-intensive flagship version; other versions rely more on text. Before choosing how to present an answer, both need the same decision: what is the viewer asking, and which product evidence can answer it? This post follows that path through the system.

## What happens to one comment

<!-- image:llm-barrage-interaction:images/figure-92603a48521c.png | The interaction workflow: intent and entities determine retrieval before response generation. -->

The interaction pipeline includes the following components:

- Preset FAQ matching: retrieve merchant-configured FAQ pairs using the viewer comment. A match bypasses intent recognition; the configured intent and answer are used directly. Embeddings provide initial retrieval and a reranker filters candidates.
- Intent recognition: if there is no FAQ match, identify the actual intent using the comment, conversation history, and livestream state. Different intents lead to different downstream logic.
- Entity parsing: extract product names, attributes, and item-link numbers from the history and recognized intent.
- Retrieval:

- For item-link product questions or presentation requests, retrieve product information by link number.
- For questions without an explicit product subject, use the product currently being presented.
- For general product questions or presentation requests, use the current comment as a query to retrieve the best-matching product from the vector store.

- Generation: place retrieved information, the comment, and dialogue history into task-specific prompts for the LLM. Templates cover casual chat, product questions, and promotion questions.
- Presentation reordering: a product-presentation request changes the presentation order and receives a fixed response rather than an LLM-generated answer.

## Carrying intent across turns

### Let the next question build on the last

We started focusing on multi-turn interaction in December 2024. Viewers routinely leave out the subject or continue an earlier question with only a few words. Treating each comment as a fresh request makes those conversations brittle. We needed to carry context forward without throwing away the single-turn data we had already collected.

- Design a suitable multi-turn dialogue architecture and accumulate data to support the desired interaction quality.
- Improve the existing intent model while reusing the substantial single-turn classification dataset and supporting new capabilities.

We changed the input and the model together. Intent recognition now sees live-room products, history, and the comment; an LLM replaces BERT and emits the label. On this dataset, accuracy reached 80%, against 71% for DeepSeek-R1 and 69% for BERT trained on the same mixed data. The useful lesson for us was how much business labels and context helped with these boundaries.

### Multi-turn interaction architecture

<!-- image:llm-barrage-interaction:images/figure-385eb43e3f0f.png | Context flow across turns. -->

- Before each turn, the information in the green boxes is passed to the intent model.
- The recognized intent determines retrieval behavior and system instructions.
- After retrieving intent-specific information, the content in the dashed box becomes the generation LLM's input for the next host response.

### Intent categories

<!-- image:llm-barrage-interaction:images/figure-ffd9170fc0ec.png | Business intents and their downstream routes. -->

The intent taxonomy changed twice:

- July 2024: added product recommendations and livestream promotion questions.
- January 2025: merged product recommendations and product searches into product questions.

### Looking at actual conversations

| Viewer comment | Dialogue history | Recognized intent | Avatar response |
| --- | --- | --- | --- |
| Smart toilet | User: Can you recommend a toilet? Assistant: Look at link 17. This smart toilet supports power-outage flushing, automatic seat and water temperature control, and foot-sensor flushing. It suits small homes and offers good value. | Product question | The Jomoo smart toilet at link 17 supports power-outage flushing, automatic water-temperature adjustment, and foot-sensor flushing. The post-coupon price is 2199. |
| Which one connects through Bluetooth? | User: Does the lapel microphone need Bluetooth? Assistant: This lapel microphone connects through Bluetooth and is convenient to use. | Product question | Look at the Jinyun wireless Bluetooth headphones at link 6 or the in-ear model at link 11. Both use Bluetooth. |
| Okay | User: How do I enter the draw? Assistant: Please ask customer service about the detailed draw rules. | Casual chat | Okay, good luck with the draw! |

### Why we moved to an LLM with context

<!-- image:llm-barrage-interaction:images/figure-c8b91623c77e.png | Moving from single-turn classification to an LLM with live-room context. -->

- The single-turn model uses the current comment for BERT sequence classification and outputs an intent `label_id`.
- The multi-turn model uses the current product, dialogue history, and comment as input to an LLM and directly generates the intent label.

### Building the training data

1. Run the single-turn model and DeepSeek-V3 on approximately 20k cleaned examples. Keep only disagreements; the existing single-turn data can cover examples where they agree.
2. Manually remove unsuitable comments, including traffic from conversations with real hosts mistakenly collected during avatar streams and repetitive spam.
3. Send the remaining examples to annotators.
4. Algorithm engineers review annotations individually and remove examples humans cannot reliably interpret. The final dataset contains over 3000 multi-turn intent examples.

### Scores and boundary cases

| Method | Description | Accuracy |
| --- | --- | --- |
| DeepSeek-V3 | Prompt engineering | 0.66 |
| DeepSeek-R1 | Prompt engineering | 0.71 |
| Qwen2.5 7B, multi-turn SFT | 3000 multi-turn examples, direct answers without CoT | 0.77 |
| Qwen2.5 7B, multi-turn + single-turn SFT | 3000 multi-turn + 16000 single-turn examples, direct answers without CoT | 0.80 |
| BERT, multi-turn + single-turn fine-tuning | Same 3000 + 16000 examples as Qwen | 0.69 |

- Multi-turn labeling is much harder: determining the true intent may take 30–60 seconds per example.
- The current product, viewer-specific dialogue history, and current comment provide sufficient information to identify intent.
- Context does not remove every ambiguity. A question can support a link ID or product keywords, and a previously discussed item may now be the current presentation. Several routes can retrieve enough evidence. We therefore inspect intent accuracy and the final reply separately: a routing error need not become an answer error.

#### Cases where context changes the route

| Comment | Current product | Dialogue history | Single-turn intent | Multi-turn intent | Explanation |
| --- | --- | --- | --- | --- | --- |
| Smart toilet | — | User: Can you recommend a toilet? Assistant: Consider link 17, a smart toilet with power-outage flushing, automatic temperature control, and foot-sensor flushing, suitable for a small home. | Product presentation | Product question | In isolation the product name looks like a presentation request; context shows that the user wants a recommendation. |
| Drying hair | — | User: Which one is suitable for drying hair? Assistant: Consider link 2, a cotton hair towel with good absorbency and several designs. | Refusal | Product question | The fragment is unclear alone; history identifies a requested product for drying hair. |
| Host, does this tracker need charging? | In-car GPS anti-loss/anti-theft tracker with recording | User: Does it need charging? Assistant: I am not sure; please ask customer service. | Product question | Question without an explicit product subject | The comment alone could trigger product search, while the current presentation makes the intended product clear. |

#### Comparison with DeepSeek-R1

- DeepSeek-R1 makes intent errors on broadly distributed, long-tail boundary cases that prompt tuning alone cannot resolve.
- Data-driven SFT handles these cases and can improve further with more annotated production examples.

### More reasoning did not help this classifier

We also tried giving the intent model a reasoning trace. R1 generated a chain of thought conditioned on each known label, and we used those examples for fine-tuning. The question was whether this extra supervision would help the model make the same classification decision more reliably.

| Method | Description | Accuracy |
| --- | --- | --- |
| Qwen2.5 7B, multi-turn SFT | 3000 examples, direct label without CoT | 0.77 |
| Qwen2.5 7B, multi-turn CoT SFT | 3000 examples with CoT, reasoning before the label | 0.68 |

- Generated CoT diluted supervision on the true labels, performing worse than directly predicting the labels.
- R1 annotation can work well in an open label space, but generating reasoning for examples with existing ground-truth labels did not meet expectations here.

## Finding the product the viewer means

The multi-turn product-entity parser extracts product names, attributes, and link numbers from dialogue history and recognized intent.

The core challenges include history dependence, numerical interference, and generalization from specific products to broader categories.

- Input: current comment, dialogue history, and multi-turn intent.
- Output: three types of structured entities:

- Product entities, such as Telunsu pure milk.
- Product attributes, such as 2 HP, size 39, or iPhone15.
- Item-link numbers, such as 107 or 39.

<!-- image:llm-barrage-interaction:images/figure-fa5ffaedbb15.png | Entity-parser inputs and structured outputs. -->

### Training data

For entity parsing, we kept product questions, presentation requests, and their link-ID variants from the intent data. DeepSeek-R1 generated parses, followed by manual filtering, leaving 2100 examples. Even with the strongest parser in this comparison, we checked whether historical products were still relevant.

| Data component | Description |
| --- | --- |
| Base examples | Retain product questions (840), presentation requests (210), and link-number examples (770). |
| Augmentation | Add 1000 adversarial examples covering pronunciation, spelling, dialect, and other interference. |
| Quality assurance | Multi-stage DeepSeek-R1 generation followed by human verification. |

### Data augmentation

#### Numerical ambiguity

Numbers elsewhere in the conversation can be mistaken for item links. We improve sensitivity to their roles using three kinds of interference:

| Interference | Example | Error |
| --- | --- | --- |
| Power rating | 2-HP air conditioner → extract 2 | Confusing a specification with a link number |
| Size or dimensions | Size-39 trainers → extract 39 | Failing to distinguish an attribute from a link identifier |
| Product generation | iPhone15 → extract 15 | Mistaking digits in a product name for a link |

We use two-stage DeepSeek-R1 generation: first generate the interference type, then generate a dialogue exhibiting it. This improves diversity.

<!-- image:llm-barrage-interaction:images/figure-16373a291666.png | Numerical-ambiguity examples separate product specifications from link IDs. -->

#### Product generalization

When history names a specific product, the model may extract it even when the current request is generic. For example:

User: Which milk has a promotion? → Incorrect extraction: Telunsu pure milk.

We generate three kinds of generalization:

| Generalization | Specific product | Broader category |
| --- | --- | --- |
| Product | Zespri kiwifruit | Fruit |
| Brand | Telunsu pure milk | Milk |
| Specification | Nongfu Spring 5L | Large bottled water |

We manually annotate an initial product set, expand the pool with DeepSeek-R1, and generate dialogues using product categories.

<!-- image:llm-barrage-interaction:images/figure-4e025b93aef7.png | Generalization examples cover brands, categories, and specifications. -->

#### Historical noise

A clearly named historical product can override the item in the current comment. We built adversarial product pairs around the naming noise below, then generated conversations to test whether the parser could resist that pull.

| Issue | Generation strategy | Example |
| --- | --- | --- |
| Abbreviation | Initial letters plus digits | i12 → iPhone12 |
| Misspelling | Adjacent-key substitution or omitted letters | iQO10 → iQOO10 |
| Series confusion | Mix product generations | Xiaomi13 → Xiaomi14 |
| Dialect/homophone | Vary the pronunciation or pinyin | Aiku11 → iQOO11 |

DeepSeek-R1 first generates product pairs exhibiting these issues, then generates corresponding dialogues.

<!-- image:llm-barrage-interaction:images/figure-ff72febd7e73.png | Constructing examples with historical noise and perturbed product names. -->

### How we score a parse and inspect its errors

Training: LoRA fine-tuning of a 7B base model.

Evaluation: compute Jaccard similarity between the predicted and true product strings' character 2-gram sets. A similarity of at least 0.7 counts as correct; report accuracy.

<!-- image:llm-barrage-interaction:images/figure-45a61484792f.png | Entity parsing is evaluated using string 2-gram Jaccard similarity. -->

- <img alt="Jaccard 2-gram notation" class="inline-equation" decoding="async" height="23" loading="lazy" src="../llm-barrage-interaction/images/figure-9cc4c1a4bc85.png" width="47"/> denotes the set of 2-grams of string S.

| model | acc |
| --- | --- |
| gpt4-fewshot-cot | 0.77 |
| deepseek-r1 | 0.87 |
| ours | 0.92 |

| Current comment | Dialogue history | Multi-turn intent | Parsed product |
| --- | --- | --- | --- |
| The warm version | Viewer: Shoes. Host: You can inspect link 154's product page; I will present it later, after finishing link 107. | Product question | Warm shoes |
| Don't they look similar? | Viewer: Is 12 or 13 better value? Host: iQOO 12 costs 3999 before coupons and 3118.3 after; iQOO 13 costs 3999 before coupons and 3928.3 after. iQOO 12 is better value. Viewer: Which performs better? Host: iQOO 13 has Snapdragon 8 Elite, versus the third-generation Snapdragon 8 in iQOO 12. Viewer: Which takes better pictures? Host: Look at link 39, with 50MP main, 16MP front, and 50MP ultrawide cameras. | Product question | iQOO 12, iQOO 13 |
| What differs between links one and seven? | Viewer: Can 7 record audio? Host: The high-end tracker at link 7 can; ask customer service for details. Viewer: Does link seven need Wi-Fi? Host: A Wi-Fi version is available; customer service can explain setup. | Link-number product question | 1, 7 |
| Difference | Viewer: Promotions for links 30 and 27. Host: Before ordering, open the product list at the bottom right and claim the shop coupon after entering the product page. | Link-number product question | 30, 27 |

## Keeping retrieval tied to the live catalog

<!-- image:llm-barrage-interaction:images/figure-a6c40beabfaa.png | Live catalog synchronization, semantic retrieval, and lexical ranking. -->

- Before searching, synchronize with the live product list. Compute BERT context embeddings, add missing vectors, and remove vectors for products no longer available. Each vector corresponds to an `itemId`.
- After catalog synchronization, BERT retrieves semantic candidates and BM25 adds a lexical check against product text and the comment. We combine both signals in the final filter. This helps short queries, where a category word or specification can matter more than overall embedding similarity.
- Lexical reranking improves retrieval for short queries.

## Turning evidence into a reply

### Different questions need different replies

- Casual chat: respond using the conversation history and current comment.

| Dialogue history | Current comment | Host response |
| --- | --- | --- |
| User: Ordered. Assistant: Great, thanks for your support! User: What if I forgot to enter my phone number? Assistant: Contact customer service; they can help you check. | I contacted customer service. | Okay, they will help you as soon as possible. Don't worry. |

- Product questions: answer from product information, including recommendations and searches.

| Viewer comment | Host response | Retrieved products, with unrelated details omitted |
| --- | --- | --- |
| Do you have a 3-HP wall-mounted air conditioner? | The Gree air conditioner at link 209 is a 3-HP wall-mounted model. Its post-coupon price is 6399. | Link 208: Gree inverter heating/cooling, 2-HP wall unit, Qingxuanfeng. Link 209: Gree inverter heating/cooling, 3-HP wall unit, Qingxuanfeng. Link 288: Gree first-level-efficiency inverter heating/cooling, small 2-HP wall unit, Fengjiyuan. |

- Livestream promotion questions:

- When the merchant configures promotions, answer questions, searches, and recommendations using that information.
- If no promotion is configured or the information cannot answer the question, use general guidance about coupons, red packets, and government subsidies.

| Viewer comment | Host response | Promotion information |
| --- | --- | --- |
| How can I get the best price? | Before ordering, open the product list at the bottom right and claim the fan red packet after entering the product page. | Type: pre-purchase coupon; name: fan red packet; no minimum spend; discount: 4.0 yuan; fans only; claim by entering the product page. |
| Are government subsidies still available? | Check the product list for a government-subsidy label and open the product to claim it. Policies vary by region. | — |

### Where the response data comes from

<!-- image:llm-barrage-interaction:images/figure-8b5a4b0b6530.png | Context differences between single-turn and multi-turn interaction. -->

| Intent | Data type | Examples |
| --- | --- | --- |
| Casual chat | Single-turn | 1509 |
| Casual chat | Multi-turn | 181 |
| Promotions | Configured promotion | 278 |
| Promotions | No configured promotion | 121 |
| Product questions | Single product, answerable | 1678 |
| Product questions | Single product, refusal | 1249 |
| Product questions | Multiple products, multi-turn | 400 |
| Product questions | Multiple products, single-turn | 399 |
| Product recommendations | Initial recommendation dataset | 400 |
| Product recommendations | Multiple products, single-turn | 400 |
| Product recommendations | Multiple products, multi-turn | 249 |
| Product searches | Multiple products, single-turn | 400 |
| Product searches | Multiple products, multi-turn | 354 |
| Questions without an explicit subject | Single-turn | 400 |
| Questions without an explicit subject | Multi-turn | 398 |
| Total | All data | 8416 |

### Saying the same thing in text and speech

| Viewer comment | Text response | Spoken/TTS response |
| --- | --- | --- |
| Any deals on smart toilets? | Link 17 was 9999 and is now 2199 after coupons. Links 45 and 31 are 2799 and 2599. These are strong offers. | I see a viewer asking about smart-toilet deals. Link seventeen was nine thousand nine hundred and ninety-nine; now it is two thousand one hundred and ninety-nine after coupons. Link forty-five is two thousand seven hundred and ninety-nine, and link thirty-one is two thousand five hundred and ninety-nine. The offer may end, so take a look. Now I will continue the presentation. |

- Text: answer directly, without normalizing numbers or English, and limit the response to 60 Chinese characters to fit the comment box.
- TTS: briefly restate the viewer's question so they know the host is responding to them, normalize numbers and English for speech synthesis, and apply no character limit.
- Implementation:

- Text: use an LLM to remove the question-restatement portion from original examples.
- TTS: normalize the original data for speech.
- Distinguish the two data variants through system instructions.

A problem introduced by the two modes:

The same underlying example may be seen twice during training, increasing the risk of overfitting.

Our solution:

- Split original conversations before making text and TTS variants. Otherwise, rewrites can leak across the split. We saw evaluation accuracy above 95% in this situation, versus roughly 70–80% when this generation task converged. Those are observations from this setup; unexpectedly good numbers should trigger a split audit first.
- Adjust the learning rate from the learning curves and select the checkpoint with the lowest validation loss.

## Checks that matter in deployment

We pay particular attention to module handoffs. A correct intent can still produce a wrong entity, or the right entity can retrieve an unavailable item. Full-request replays sit alongside component scores so we can trace the reply back to its product and evidence.

Augmented versions of one conversation should stay together too: paraphrases, numerical perturbations, and noisy-history variants. When validation looks unexpectedly strong, we check construction and splitting before tuning again. Otherwise, an apparent model improvement may simply sit on top of a leaked baseline.

The reported intent and entity accuracies describe these business datasets and scoring rules. They are not universal model rankings. Continually labeling real boundary cases remains a practical way to improve a deployed classifier.
