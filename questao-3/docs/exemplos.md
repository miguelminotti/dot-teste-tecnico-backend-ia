# Exemplos de consultas e resultados

Buscas reais, geradas pela CLI em 2026-10-28 na configuração padrão: o `BAAI/bge-m3` e a busca só com embeddings ([ADR 0001](adr/0001-modelo-de-embeddings-bge-m3.md)). Dois exemplos trocam o modelo ou o método, para mostrar o que os [experimentos](experimentos.md) mediram. As saídas estão como a CLI as imprimiu, sem edição. A busca é determinística: o mesmo índice dá a mesma saída.

As consultas 1 a 4 vêm do [conjunto de avaliação](avaliacao.md), e cada resultado foi conferido com os artigos que o juiz rotulou como relevantes. A 5 é livre, fora do conjunto.

Cada resultado traz a posição, a nota (o cosseno entre a consulta e o melhor pedaço do artigo), o título, o link do arXiv e o trecho, com a seção de onde ele veio. O trecho é cortado em 300 caracteres.

## 1. Pelo nome do método

A consulta `q004` usa o nome do método, que só existe neste artigo. O artigo certo vem em 1º, com o parágrafo da discussão que o resume. Os outros dois são vizinhos fracos, com notas bem abaixo (0,57 e 0,56, contra 0,72): o 2º direciona o comportamento de LLMs entre línguas, e o 3º é um corpus de fala que tem o sotaque entre os atributos.

```bash
uv run semantic-search "AccentCL class-incremental accent classification" --k 3
```

```text
1. [0.715] AccentCL: Robust Accent Classification with Incremental Expansion
   https://arxiv.org/abs/2610.07426
   Discussion: We proposed AccentCL, a framework for English accent classification that supports
   class-incremental expansion. By combining data from new accents with replay memory stratified by
   dataset, AccentCL adds Spanish- and Chinese-accented English without retraining on the full old
   dataset. In our [...]

2. [0.571] Compositional Activation Steering Across Languages and Behaviors with Contextual Gates
   https://arxiv.org/abs/2610.24906
   CLAS.: We build on the contextual steering method of Hsu et al. (2026), referred to as CLAS,
   keeping d_{\ell}^{(a)} fixed while learning a per-layer, per-attribute affine gate:
   \alpha_{\ell}^{(a)}=w_{\ell}^{(a)\top}h_{\ell}+b_{\ell}^{(a)},\qquad h_{\ell}\leftarrow [...]

3. [0.561] SPARC: Spoken Profile Authorship Recognition Corpus
   https://arxiv.org/abs/2610.25265
   Accent/Dialect: Accent yields the clearest two-tier separation of all attributes. Embedding-based
   models sit at chance in the different-topic setting (0.494 EER for SentenceBERT; 0.494–0.534 AUC
   across the embedding baselines) and gain little in the within-episode condition. LLMs, by
   contrast, extract a [...]
```

## 2. Por paráfrase, em português, e o viés de língua do e5

A mesma consulta em português, sobre o artigo em inglês. Com o bge-m3, o artigo certo vem em 1º, com o mesmo trecho da consulta em inglês.

```bash
uv run semantic-search "Como continuar adicionando novas categorias de sotaque na fala sem retreinar do zero" --k 3
```

```text
1. [0.555] AccentCL: Robust Accent Classification with Incremental Expansion
   https://arxiv.org/abs/2610.07426
   Class-incremental accent expansion: We next evaluate whether the regional accent inventory can be
   expanded without retraining the full model from scratch. Starting from the five-class base model,
   we incrementally add two accent classes: first Spanish-accented English, and then Chinese-
   accented English, yielding a class- [...]

2. [0.522] ReAnchor: Reusing Rejected Verifier States for Diffusion Drafting
   https://arxiv.org/abs/2610.26531
   Introduction: Building on this finding, we introduce ReAnchor, a training-free method that reuses
   verifier hidden states from the discarded post-rejection suffix to reanchor the same pretrained
   drafter at those later positions. The reanchored blocks are generated in parallel with the
   baseline draft, each [...]

3. [0.510] Mixture of Phonetic Experts Based Low-Rank Adaptation of Conformer Models for Accented English Speech Recognition
   https://arxiv.org/abs/2610.26888
   Hybrid Phonetic Routing Mechanism: Crucially, the expert set is shared across all accents. No
   accent-specific modules are introduced and no accent labels are required at test time; the model
   adapts to a given utterance purely through its frame-level phonetic routing decisions.
```

Com o `intfloat/multilingual-e5-base`, o modelo de partida, um artigo sobre um LLM em português brasileiro passa à frente. Nada nele trata de sotaque: o trecho é uma tabela com nomes em português ("comecar_com", "min_maiusculas"). O e5 casava a língua da consulta com o assunto "português", em 10 das 99 buscas em português; o bge-m3, em 1. Foi esse erro que decidiu a troca de modelo.

```bash
uv run semantic-search "Como continuar adicionando novas categorias de sotaque na fala sem retreinar do zero" --k 3 --model intfloat/multilingual-e5-base
```

```text
1. [0.829] Manacá-1B-Instruct-2: Reproducible Safety Alignment for a Native Brazilian-Portuguese LLM. Negative DPO Results, a Controlled Composition Scan, and a Silent Failure Mode of the LLM Judge
   https://arxiv.org/abs/2610.20570
   Mandatory Core: Validated Comparison Against 4 Baselines: Table 9 goes one level deeper, into the
   21 individual instruction types (instr-loose metric). The most striking pattern: on at least six
   types, comecar_com, min_maiusculas, num_itens_numerados, num_marcadores, num_paragrafos,
   terminar_com, all five models that do not inherit Qwen pre-training [...]

2. [0.818] AccentCL: Robust Accent Classification with Incremental Expansion
   https://arxiv.org/abs/2610.07426
   Problem formulation: We study accent classification as a robust class-incremental learning
   problem. Given an accent classifier trained on a set of “old” accent classes
   \mathcal{Y}_{\mathrm{old}}, the goal is to add a “new” accent class y_{\mathrm{new}} while
   preserving performance on the old classes. Before each [...]

3. [0.816] SPARC: Spoken Profile Authorship Recognition Corpus
   https://arxiv.org/abs/2610.25265
   Spoken Language Data Filtering: We apply a unified multi-stage data cleaning pipeline to both
   corpora. First, utterances with an SNR \geq 15 dB are kept for the remaining processing to ensure
   the quality of transcription. Specifically, we estimated SNR via WADA-SNR Kim and Stern (2008)
   for NaturalVoices and Brouhaha Lavechin [...]
```

## 3. Por tema, o caso mais difícil

A consulta `q091` tem 3 artigos relevantes. O 1º resultado é um deles, e o trecho descreve exatamente o tema ("leverage interaction trajectories to construct and transfer reusable procedural knowledge"). Os outros dois relevantes ficam em 8º e 9º, fora dos 5 primeiros. Os resultados 2 a 5 tratam de memória de agentes, compressão de contexto, agentes na borda e pós-treino: vizinhos do tema, que o juiz não rotulou como relevantes. Temas largos são o ponto fraco medido da busca: os 10 primeiros resultados trazem, em média, cerca de metade dos relevantes.

```bash
uv run semantic-search "How can LLM agents learn reusable procedural guidance from their own trajectories?" --k 5
```

```text
1. [0.642] AtomSD: Procedural Atom-Guided Self-Distillation for LLM Agents
   https://arxiv.org/abs/2610.26926
   Introduction: Toward this goal, existing approaches leverage interaction trajectories to
   construct and transfer reusable procedural knowledge, broadly following two directions. (1)
   Organizing trajectories into reusable guidance. Prior work transforms previous interactions into
   reflections, workflows, [...]

2. [0.600] MemPilot: Orchestrating On-Demand Multimodal Memory Curation for LLM Agents
   https://arxiv.org/abs/2610.06830
   Abstract: MemPilot: Orchestrating On-Demand Multimodal Memory Curation for LLM Agents. Memory has
   become integral to the LLM agent ecosystem, supporting information retention and reuse across
   interactions. However, most existing agent memory systems construct memory in a query-agnostic
   manner, which can [...]

3. [0.590] From Long Context to Selective Memory:A Survey of Memory-Centric Compression for Large Language Models
   https://arxiv.org/abs/2610.21165
   Agent-Side Activation Control: In long-horizon agent tasks, activation control also applies to
   the agent’s own trajectory: as tool calls, observations, and intermediate reasoning accumulate,
   the agent must decide which history stays in active context and which is summarized, folded, or
   externalized. ACON (Kang et al., [...]

4. [0.584] EdgeWise: Bringing Long-Horizon Agents to the Edge via Selective Cloud Delegation
   https://arxiv.org/abs/2610.17560
   Introduction: In particular, our step-level RL method with fine-grained credit assignment enables
   the local SLM to jointly learn task solving and when to leverage the cloud LLM, without an
   additional decision model at inference time. Extensive experiments on long-horizon coding-agent
   benchmarks demonstrate [...]

5. [0.583] What Should SFT Learn? Conditional Information Gain for Generalizable Post-Training
   https://arxiv.org/abs/2610.12995
   Introduction: However, such adaptation introduces a fundamental tension between acquiring target
   behaviors and preserving the capabilities that LLMs already support. It is especially evident in
   post-training methods that learn from fixed, externally provided data, including SFT, offline
   preference [...]
```

## 4. Busca padrão e busca híbrida

A consulta `q051`, de detalhe, pergunta por que os pesos de um conjunto de modelos podem ser negativos. Na busca padrão, o artigo certo fica em 2º. Em 1º vem um artigo sobre a avaliação de novidade de ideias, cujo pedaço fala de "weak labels": perto da consulta no sentido, mas sobre outro assunto.

```bash
uv run semantic-search "Why allow negative weights for weak experts when weighting LLM ensemble votes without labels?" --k 3
```

```text
1. [0.610] Old Ideas, Novel Problems: The Instability of LLM-Based Novelty Evaluation
   https://arxiv.org/abs/2610.02022
   Weak labels for generated ideas.: The lower-novelty side of Human+Generated carries no observed
   novelty label. Its labels rest instead on a weak-labeling assumption: a top-decile ICLR
   submission whose reviewers agree is original is more novel than an idea produced in a single
   scaffold-free, tool-free pass of a deliberately [...]

2. [0.597] A Jury, Not an Electorate: Label-Free Reliability Estimation for Ensembles of Language Models
   https://arxiv.org/abs/2610.21085
   Abstract: A Jury, Not an Electorate: Label-Free Reliability Estimation for Ensembles of Language
   Models. An ensemble of language models is a jury, not an electorate. The answers are testimony
   from witnesses of unknown reliability, and the question is not what the majority said but who is
   credible. Most [...]

3. [0.575] ANCHOR: Assessing Naturalistic Constraint Hierarchies and Ordering in Repository-Grounded Agentic Coding
   https://arxiv.org/abs/2610.16859
   Judge Validation: Evaluators were given the checklist question, the explicit pass condition, and
   the same evidence excerpt provided to the LLM judge, but no access to the judge’s output, in
   order to avoid anchoring. The majority label across the five evaluators was used as the human
   consensus, and inter- [...]
```

Na busca híbrida, o BM25 casa os termos da pergunta ("negative", "weights", "experts", "ensemble", "votes") e põe o artigo certo em 1º na lista dele, e o RRF o leva ao 1º lugar. A nota passa a ser a do RRF, que chega no máximo a 2/61, cerca de 0,033, para um pedaço em 1º nas duas listas. A híbrida não é o padrão porque, em português, o BM25 traz mais ruído que acerto ([experimentos](experimentos.md#bm25-e-busca-híbrida)).

```bash
uv run semantic-search "Why allow negative weights for weak experts when weighting LLM ensemble votes without labels?" --k 3 --method hybrid
```

```text
1. [0.032] A Jury, Not an Electorate: Label-Free Reliability Estimation for Ensembles of Language Models
   https://arxiv.org/abs/2610.21085
   Abstract: A Jury, Not an Electorate: Label-Free Reliability Estimation for Ensembles of Language
   Models. An ensemble of language models is a jury, not an electorate. The answers are testimony
   from witnesses of unknown reliability, and the question is not what the majority said but who is
   credible. Most [...]

2. [0.021] Old Ideas, Novel Problems: The Instability of LLM-Based Novelty Evaluation
   https://arxiv.org/abs/2610.02022
   Weak labels for generated ideas.: The lower-novelty side of Human+Generated carries no observed
   novelty label. Its labels rest instead on a weak-labeling assumption: a top-decile ICLR
   submission whose reviewers agree is original is more novel than an idea produced in a single
   scaffold-free, tool-free pass of a deliberately [...]

3. [0.020] Residual Advantage: Student-Relative Teacher Guidance for RL with Verifiable Rewards
   https://arxiv.org/abs/2610.11519
   Combining with verifier feedback: Let c_{t}\geq 0 be the actor’s relative weights on the
   response’s positions, summing to one (c_{t}=1/M for token-mean reduction over M positions), and
   let \overline{A}^{d}=\sum_{t}c_{t}A_{t}^{d} be the response mean of the local advantages. RA adds
   the centered local advantage, scaled by the [...]
```

## 5. Uma consulta livre, em português

Fora do conjunto de avaliação, sem rótulo. Três dos cinco artigos tratam de agentes de programação: ANCHOR e SpecGuardBench são benchmarks para eles, e o trecho do OPRD resume como esses agentes são avaliados. O Epi (um agente de pesquisa autônomo) e o LatentRiskBench (riscos de agentes corporativos) tratam de avaliar agentes em geral, e não de programação.

```bash
uv run semantic-search "como avaliar agentes de programação" --k 5
```

```text
1. [0.589] ANCHOR: Assessing Naturalistic Constraint Hierarchies and Ordering in Repository-Grounded Agentic Coding
   https://arxiv.org/abs/2610.16859
   Abstract: ANCHOR: Assessing Naturalistic Constraint Hierarchies and Ordering in Repository-
   Grounded Agentic Coding. For repository-grounded coding agents, a functionally correct patch is
   not necessarily an acceptable one: developers also constrain how the task must be carried out-
   modification scope, [...]

2. [0.589] Epi: Towards a Persistent, Self-Improving Agent for Autonomous Research
   https://arxiv.org/abs/2610.24944
   6.2 Benchmark and Protocol: The evaluator first runs each program on two development instances.
   The agent sees these results during the campaign. After the campaign, the best development
   program runs once on four held-out instances. Each held-out run has a time limit of one hour. The
   benchmark score has a quality term [...]

3. [0.577] SpecGuardBench: Can Coding Agents Construct Reliable Validation Harnesses from Natural Language Specifications?
   https://arxiv.org/abs/2610.16870
   Conclusion and Discussion: We have introduced SpecGuardBench, a benchmark of 291 validation tasks
   drawn from 30 features of 13 real-world Python repositories, each providing an atomic natural
   language specification, a reference implementation, a violating implementation that the original
   test suite cannot catch, and [...]

4. [0.556] LatentRiskBench: Measuring State-Dependent Risks in Enterprise Agents
   https://arxiv.org/abs/2610.17685
   Related Works: Recent agent benchmarks evaluate increasingly realistic forms of web navigation,
   tool use, computer use, prompt-injection robustness, and policy compliance (Zhou et al., 2023;
   Koh et al., 2024; Xie et al., 2024; Mialon et al., 2024; OpenAI, 2025; Schick et al., 2023;
   Debenedetti et al., 2024; [...]

5. [0.544] OPRD: On-Policy Reminder Distillation for Long-Horizon Coding Agents
   https://arxiv.org/abs/2610.21496
   Repository-Level Software Engineering Agents.: Repository-level evaluation covers code completion
   (Deng et al. 2024; Yang et al. 2024b), executable issue resolution (Jimenez et al. 2024), broad
   agent capabilities (Xu et al. 2025), and multimodal web coding (Lei et al. 2026). SWE-agent,
   AutoCodeRover, and Agentless provide tool-based issue- [...]
```
