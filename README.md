# General Researcher - A Playground

Disclaimer: this is for funsies.

A personal playground for exploring agent architecture patterns and evaluation approaches. Uses government research as the problem domain — querying public APIs (GovInfo, Federal Register, Data.gov) through different agent compositions built on [Microsoft Foundry Agents](https://learn.microsoft.com/en-us/azure/ai-services/agents/).

## What's in here

**5 agent roles** composed by **6 architecture patterns**, plus a **behavior-driven eval framework** for comparing them.

```
Agents:        Researcher · Critic · Synthesizer · Planner · Source Worker
Architectures: single_agent · researcher_critic · multi_agent
               supervisor_worker · plan_and_execute · hybrid_p2p
Eval:          Multi-stage behavioral eval with scored metrics (latency/coverage/relevance/groundedness/quality)
```

## Agents

| Agent | What it does | Tools | Model |
|-------|-------------|-------|-------|
| **Researcher** | Searches sources, synthesizes findings | `search_govinfo`, `search_federal_register`, `search_datagov` | gpt-4o |
| **Critic** | Scores quality, identifies gaps | — | gpt-4o-mini |
| **Synthesizer** | Produces cited final answers | — | gpt-4o |
| **Planner** | Creates step-by-step research plans | — | gpt-4o-mini |
| **Source Worker** | Searches one source, summarizes | 1 tool | gpt-4o-mini |

## Architectures

Each is a thin orchestration layer (~50–130 LOC) over the shared agents:

| Pattern | Flow | Agents used |
|---------|------|-------------|
| **Single Agent** | Researcher does everything in one tool-calling loop | R |
| **Researcher-Critic** | Researcher → Critic feedback loop (max 3 rounds) | R, C |
| **Multi-Agent** | Researcher → Critic gate → Synthesizer | R, C, S |
| **Plan-and-Execute** | Planner → Researcher → Critic → Synthesizer | P, R, C, S |
| **Supervisor-Worker** | Planner → parallel Source Workers → Critic → Synthesizer | P, W×3, C, S |
| **Hybrid P2P** | Source Workers share discoveries across rounds → Synthesizer | W×3, S |

## Behavioral evaluation framework

Most eval frameworks treat evaluation as verification — you build an agent, then check if it works. This project treats eval as a **design tool**. The same eval cases run across all 6 architectures.

### Multi-stage Given / When / Then

Cases are split into **stages**: each `when` invokes a registered action handler and produces a subject for that stage's graders to evaluate. This tells you not just *whether* the agent failed, but *which stage* broke down.

```python
@template("legislation research", category="legislation")
def legislation(s, data):
    s.given("a query", data["query"])

    # Stage 1: Retrieval — did the agent search the right sources?
    s.when("the agent researches this query")
    s.then("the agent should have called", "search_govinfo")
    s.then("no tool calls should have failed")
    s.then("documents retrieved should be at least", 3)
    s.then("sources should include", "GovInfo")
    s.then("unique sources used should be at least", 1)

    # Stage 2: Synthesis — is the answer correct and well-formed?
    s.when("the agent synthesizes the results")
    s.then("completion time should be under", 20)
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", 2)
    s.then("azure relevance score")
    s.then("the answer should be", data["quality_criteria"])

# Generate cases from a dataset — same behavior, many queries
legislation.cases([
    {"query": "AI policy actions by Congress",
     "expected_terms": ["AI", "Congress"],
     "quality_criteria": "comprehensive and well-sourced"},
    {"query": "Climate change legislation",
     "expected_terms": ["climate", "energy"],
     "quality_criteria": "factual and grounded"},
    # ... add 100 more queries, same grader behavior
])
```

Templates define the grader behavior once. `@template` + `.cases()` separates the *what to evaluate* from the *what to evaluate it with* — add queries without touching grader logic.

For one-off cases, `@scenario` still works:

```python
@scenario("edge case: empty query", category="robustness")
def test_empty_query(s):
    s.given("a query", "")
    s.when("the agent researches this query")
    s.then("no tool calls should have failed")
```

### Action registry

Each `when` clause dispatches to a registered action handler via prefix match:

```python
from evaluation.actions import action

@action("the agent researches")
def _research(context, previous, architecture):
    return architecture.research(context["query"], max_results_per_source=5)

@action("the agent summarizes")
def _summarize(context, previous, architecture):
    return previous  # pass-through: grade the same output
```

Actions receive the given context, the previous stage's subject, and the SUT. Returning `previous` signals a pass-through (no new SUT invocation). New actions are added without modifying the runner.

### Three layers of graders

| Layer | What it checks | Examples | Cost |
|-------|---------------|----------|------|
| **Deterministic** | Measurable outcomes | Keyword presence, citation count, latency, source diversity | Free, fast |
| **Process (traces)** | Intermediate agent behavior | Tool calls made, tool failures, agent run count | Free, requires OTel |
| **AI-judged** | Subjective quality | Relevance, coherence, groundedness, fluency | LLM call per check |

The process layer is the key differentiator. An agent can produce a correct-looking answer that's entirely hallucinated because it never called the right tool. Outcome-only eval misses this entirely. By instrumenting the agent's tool-call loop with OpenTelemetry spans and grading against them in the same case, you evaluate **how** the agent arrived at its answer, not just **what** it said.

### Scored metrics, not pass/fail

Every grader produces a **0.0–1.0 score** mapped to one of 5 metric categories. Pass/fail is derived (graders pass at > 0.5, cases at ≥ 0.7), but the scores are the signal:

```
  Metric          Score        Steps
  ────────────────────────────────
  ⏱️ latency       0.85 [████████░░]  (2)
  📚 coverage      0.67 [██████░░░░]  (4)
  🎯 relevance     0.92 [█████████░]  (3)
  📎 groundedness  0.50 [█████░░░░░]  (2)
  ✨ quality        0.78 [███████░░░]  (3)
```

A binary pass/fail says "failed." Scores say "failed because groundedness is weak — the agent finds the right stuff but doesn't cite it, so add a citation-formatting step, not better retrieval."

### Dual-mode tracing

OpenTelemetry runs with two exporters simultaneously:
- **In-memory** — always active, used by the eval runner to capture and grade against spans per case
- **Cloud (App Insights)** — opt-in via `APPLICATIONINSIGHTS_CONNECTION_STRING`, for persisting traces from production runs

Same instrumentation serves dev-time eval and production observability.

## Usage

```bash
cp .env.example .env   # set AZURE_AI_PROJECT_ENDPOINT + model deployments
make build
make run QUERY='AI safety federal actions'
make eval              # eval (single_agent, deterministic only)
make eval-all          # all 6 architectures
make compare QUERY='AI legislation'  # parallel comparison
```

Direct CLI with filters:
```bash
uv run src/eval.py -a single_agent researcher_critic    # compare two architectures
uv run src/eval.py -a single_agent -c legislation       # filter by category
uv run src/eval.py -a single_agent --no-llm-judge --no-azure-eval  # fast dev mode
```

## Project layout

```
src/
├── agents/          # Foundry Agent definitions + client lifecycle
├── architectures/   # 6 orchestration patterns
├── data_sources/    # GovInfo, Federal Register, Data.gov API clients
├── evaluation/
│   ├── dsl.py       # @scenario, @template, ScenarioBuilder, StepResult
│   ├── actions.py   # @action registry for When clause dispatch
│   ├── steps.py     # Grader registry (@step) + all built-in graders
│   ├── scenarios.py # Templates + datasets (generates eval cases)
│   ├── runner.py    # EvalRunner: multi-stage dispatch, results, reporting
│   ├── llm_judge.py # LLM-based quality judge
│   └── azure_evaluators.py  # Azure AI Evaluation SDK wrapper
├── tools/           # FunctionTool wrappers
├── utils/           # Tracing (OTel dual-mode)
├── main.py          # CLI
├── eval.py          # Eval CLI
└── run_architecture.py
```

## Environment

```bash
AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api
MODEL_DEPLOYMENT_NAME=gpt-4o
MODEL_DEPLOYMENT_NAME_FAST=gpt-4o-mini
```

Requires Python 3.10+, an Azure AI Foundry project with model deployments, and `az login`.
