"""
Eval scenarios for the government research agent.

Architecture-specific templates define grader behavior for each pipeline pattern.
Datasets provide the queries. Each dataset entry generates a case per template.

Templates model the actual pipeline stages of each architecture:
  - single_agent: research → synthesize
  - single_agent_code: research → execute code → synthesize
  - researcher_critic: research → critic feedback → synthesize
  - multi_agent: research → critic gate → synthesize
  - plan_and_execute: plan → execute → critic → synthesize
  - supervisor_worker: plan → parallel workers → critic → synthesize
  - hybrid_p2p: parallel workers with peer sharing → synthesize

Import this module to register all scenarios before running evals.
"""
from .dsl import scenario, template

MAX_COMPLETION_TIME = 20  # seconds


# ═══════════════════════════════════════════════════════════════════════
# Architecture-specific templates
# ═══════════════════════════════════════════════════════════════════════

# ── Single Agent ──────────────────────────────────────────────────────

@template("single agent", category="single_agent")
def single_agent(s, data):
    """Baseline: one researcher agent does everything."""
    s.given("a query", data["query"])

    s.when("the agent researches this query")
    if data.get("expected_source"):
        s.then("the agent should have called", data["expected_source"])
        s.then("sources should include", data["source_label"])
    s.then("no tool calls should have failed")
    s.then("total tool calls should be at least", 1)
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", 1)

    s.when("the agent synthesizes the results")
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be at least 150 characters", data.get("min_length", 150))
    s.then("the answer should be", data["quality_criteria"])


# ── Single Agent + Code Execution ────────────────────────────────────

@template("single agent code", category="single_agent_code")
def single_agent_code(s, data):
    """Researcher with code execution for quantitative analysis."""
    s.given("a query", data["query"])

    s.when("the agent researches this query")
    if data.get("expected_source"):
        s.then("the agent should have called", data["expected_source"])
        s.then("sources should include", data["source_label"])
    s.then("no tool calls should have failed")
    s.then("total tool calls should be at least", 1)
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", 1)

    s.when("the agent executes code")
    s.then("code should have been executed")
    s.then("no code execution errors")

    s.when("the agent synthesizes the results")
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME * 2))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("the answer should contain a number")
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be", data["quality_criteria"])


# ── Researcher-Critic ────────────────────────────────────────────────

@template("researcher critic", category="researcher_critic")
def researcher_critic(s, data):
    """Researcher → Critic feedback loop (max 3 rounds)."""
    s.given("a query", data["query"])

    s.when("the agent researches this query")
    if data.get("expected_source"):
        s.then("the agent should have called", data["expected_source"])
        s.then("sources should include", data["source_label"])
    s.then("no tool calls should have failed")
    s.then("total tool calls should be at least", 1)
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", 1)

    s.when("the critic evaluates the research")
    s.then("the critic should have run")
    s.then("critic iterations should be at most", 3)

    s.when("the agent synthesizes the results")
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME * 2))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be at least 150 characters", data.get("min_length", 150))
    s.then("the answer should be", data["quality_criteria"])


# ── Multi-Agent (R → C → S) ─────────────────────────────────────────

@template("multi agent", category="multi_agent")
def multi_agent(s, data):
    """Researcher → Critic gate → Synthesizer."""
    s.given("a query", data["query"])

    s.when("the agent researches this query")
    if data.get("expected_source"):
        s.then("the agent should have called", data["expected_source"])
        s.then("sources should include", data["source_label"])
    s.then("no tool calls should have failed")
    s.then("total tool calls should be at least", 1)
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", 1)

    s.when("the critic evaluates the research")
    s.then("the critic should have run")
    s.then("critic iterations should be at most", 3)
    s.then("distinct agents should have run at least", 3)

    s.when("the synthesizer produces the answer")
    s.then("the synthesizer should have run")
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME * 2))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be at least 150 characters", data.get("min_length", 150))
    s.then("the answer should be", data["quality_criteria"])


# ── Plan-and-Execute ─────────────────────────────────────────────────

@template("plan and execute", category="plan_execute")
def plan_execute(s, data):
    """Planner → Researcher → Critic → Synthesizer with replanning."""
    s.given("a query", data["query"])

    s.when("the agent plans the research")
    s.then("the planner should have run")

    s.when("the agent executes the plan")
    if data.get("expected_source"):
        s.then("the agent should have called", data["expected_source"])
        s.then("sources should include", data["source_label"])
    s.then("no tool calls should have failed")
    s.then("total tool calls should be at least", 1)
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", 1)

    s.when("the critic evaluates the research")
    s.then("the critic should have run")
    s.then("critic iterations should be at most", 3)

    s.when("the synthesizer produces the answer")
    s.then("the synthesizer should have run")
    s.then("distinct agents should have run at least", 4)
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME * 3))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be at least 150 characters", data.get("min_length", 150))
    s.then("the answer should be", data["quality_criteria"])


# ── Supervisor-Worker ────────────────────────────────────────────────

@template("supervisor worker", category="supervisor_worker")
def supervisor_worker(s, data):
    """Planner → parallel Source Workers → Critic → Synthesizer."""
    s.given("a query", data["query"])

    s.when("the supervisor plans the research")
    s.then("the planner should have run")

    s.when("the source workers execute")
    s.then("source workers should have run at least", data.get("min_workers", 2))
    s.then("no tool calls should have failed")
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", data.get("min_sources", 2))

    s.when("the critic evaluates the research")
    s.then("the critic should have run")

    s.when("the synthesizer produces the answer")
    s.then("the synthesizer should have run")
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME * 3))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be at least 150 characters", data.get("min_length", 150))
    s.then("the answer should be", data["quality_criteria"])


# ── Hybrid P2P ───────────────────────────────────────────────────────

@template("hybrid p2p", category="hybrid_p2p")
def hybrid_p2p(s, data):
    """Source Workers share discoveries across rounds → Synthesizer."""
    s.given("a query", data["query"])

    s.when("the workers research with peer sharing")
    s.then("source workers should have run at least", data.get("min_workers", 2))
    s.then("no tool calls should have failed")
    s.then("documents retrieved should be at least", data.get("min_docs", 3))
    s.then("unique sources used should be at least", data.get("min_sources", 2))

    s.when("the synthesizer produces the answer")
    s.then("the synthesizer should have run")
    s.then("completion time should be under", data.get("max_time", MAX_COMPLETION_TIME * 3))
    for term in data["expected_terms"]:
        s.then("the answer should mention", term)
    s.then("there should be at least 2 citations", data.get("min_citations", 2))
    s.then("the answer should be at least 150 characters", data.get("min_length", 150))
    s.then("the answer should be", data["quality_criteria"])


# ═══════════════════════════════════════════════════════════════════════
# Shared dataset — same queries, architecture-specific behavior
# ═══════════════════════════════════════════════════════════════════════

LEGISLATION_CASES = [
    {
        "query": "What actions has Congress taken on artificial intelligence policy?",
        "expected_terms": ["artificial intelligence", "Congress"],
        "quality_criteria": "comprehensive and well-sourced",
        "expected_source": "search_govinfo",
        "source_label": "GovInfo",
        "min_citations": 3,
        "min_length": 200,
    },
    {
        "query": "Legislation related to climate change and renewable energy",
        "expected_terms": ["climate", "energy"],
        "quality_criteria": "factual and grounded in cited sources",
    },
]

REGULATION_CASES = [
    {
        "query": "EPA regulations on clean water standards",
        "expected_terms": ["water", "EPA"],
        "quality_criteria": "specific about regulatory details",
        "expected_source": "search_federal_register",
        "source_label": "Federal Register",
        "min_docs": 3,
    },
    {
        "query": "What federal regulations were issued regarding cybersecurity?",
        "expected_terms": ["cybersecurity"],
        "quality_criteria": "comprehensive about federal cybersecurity requirements",
    },
]

DATASET_CASES = [
    {
        "query": "What government datasets are available about public health?",
        "expected_terms": ["health", "data"],
        "quality_criteria": "informative about available data resources",
        "expected_source_label": "Data.gov",
    },
]

POLICY_CASES = [
    {
        "query": "Recent immigration policy changes and border security",
        "expected_terms": ["immigration", "border"],
        "quality_criteria": "balanced and evidence-based",
    },
]

ANALYTICAL_CASES = [
    {
        "query": "Compare the number of bills introduced related to AI versus cybersecurity in the most recent Congress. Which topic had more legislative activity?",
        "expected_terms": ["bill"],
        "quality_criteria": "a quantitative comparison with specific counts, not just qualitative statements",
        "expected_source": "search_govinfo",
        "source_label": "GovInfo",
        "min_docs": 4,
    },
    {
        "query": "How many final rules has the EPA published related to air quality in the past year? Summarize the trend.",
        "expected_terms": ["EPA"],
        "quality_criteria": "data-driven with specific counts or percentages, not vague generalizations",
        "expected_source": "search_federal_register",
        "source_label": "Federal Register",
        "min_docs": 2,
    },
    {
        "query": "What government datasets exist for tracking federal spending, and how many legislative actions reference budget transparency? Provide a breakdown.",
        "expected_terms": ["budget"],
        "quality_criteria": "a structured breakdown combining dataset availability with legislative context",
        "min_citations": 3,
        "min_sources": 2,
    },
]

# Merge all cases into one dataset
ALL_CASES = LEGISLATION_CASES + REGULATION_CASES + DATASET_CASES + POLICY_CASES

# ═══════════════════════════════════════════════════════════════════════
# Generate cases: each architecture × each query
# ═══════════════════════════════════════════════════════════════════════

# Every architecture gets the standard cases
single_agent.cases(ALL_CASES)
researcher_critic.cases(ALL_CASES)
multi_agent.cases(ALL_CASES)
plan_execute.cases(ALL_CASES)
supervisor_worker.cases(ALL_CASES)
hybrid_p2p.cases(ALL_CASES)

# Code execution architecture gets analytical cases (quantitative queries)
single_agent_code.cases(ANALYTICAL_CASES)
