"""
BDD-inspired DSL for defining eval scenarios.

Provides a lightweight Given/When/Then framework for expressing
evaluation criteria in a readable, composable way. Each assertion
produces a 0.0–1.0 score; pass/fail is determined by thresholds.

Usage:
    from evaluation.dsl import scenario

    @scenario("AI legislation search", category="legislation")
    def test_ai_legislation(s):
        s.given("a query", "What actions has Congress taken on AI policy?")
        s.when("the agent researches this query")
        s.then("the answer should mention", "artificial intelligence")
        s.then("there should be at least {n} citations", 3)
        s.then("the answer should be", "comprehensive")  # LLM-judged
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any


# ── Metric categories ────────────────────────────────────────────────

METRIC_CATEGORIES = {
    "latency": "⏱️",
    "coverage": "📚",
    "relevance": "🎯",
    "groundedness": "📎",
    "quality": "✨",
}


# ── Result types ──────────────────────────────────────────────────────

@dataclass
class StepResult:
    """Result of a single Then assertion with a 0.0–1.0 score."""
    step_text: str
    score: float  # 0.0 to 1.0
    metric: str = ""  # metric category (latency, coverage, relevance, etc.)
    detail: str = ""
    is_llm_judged: bool = False
    stage: str = ""  # which when-stage this grader belongs to

    @property
    def passed(self) -> bool:
        """A step passes if its score is > 0.5 (default threshold)."""
        return self.score > 0.5


@dataclass
class ScenarioResult:
    """Result of running a single scenario against an architecture."""
    scenario_id: str
    scenario_name: str
    category: str
    architecture: str
    steps: List[StepResult] = field(default_factory=list)
    completion_time: float = 0.0
    documents_retrieved: int = 0
    citations_count: int = 0
    sources_used: List[str] = field(default_factory=list)
    answer: str = ""
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        """Scenario passes if overall score meets threshold (0.7)."""
        return self.overall_score >= 0.7

    @property
    def overall_score(self) -> float:
        if not self.steps:
            return 0.0
        return sum(s.score for s in self.steps) / len(self.steps)

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.steps if s.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.steps if not s.passed)

    def scores_by_metric(self) -> dict:
        """Average scores grouped by metric category."""
        groups: dict = {}
        for s in self.steps:
            cat = s.metric or "other"
            groups.setdefault(cat, []).append(s.score)
        return {k: sum(v) / len(v) for k, v in groups.items()}


# ── Scenario builder ─────────────────────────────────────────────────

class ScenarioBuilder:
    """Collects Given/When/Then steps during scenario definition.

    Supports multi-stage cases: each when() starts a new stage,
    and subsequent then() calls bind to that stage.
    """

    def __init__(self, scenario_id: str, name: str, category: str):
        self.scenario_id = scenario_id
        self.name = name
        self.category = category
        self.query: Optional[str] = None
        self._stages: List[tuple] = []  # [(action_text, [(assertion_text, args)])]
        self._current_stage: Optional[int] = None

    def given(self, context: str, value: Any = None):
        """Define a Given step (precondition)."""
        if context == "a query":
            self.query = value
        return self

    def when(self, action: str):
        """Define a When step (action). Starts a new stage."""
        self._stages.append((action, []))
        self._current_stage = len(self._stages) - 1
        return self

    def then(self, assertion: str, *args):
        """Define a Then step (assertion).

        The assertion string is matched against registered step definitions.
        Extra args are passed to the step function.
        Binds to the most recent when() stage.
        """
        if self._current_stage is None:
            # No when() called yet — create an implicit stage
            self._stages.append(("", []))
            self._current_stage = 0
        self._stages[self._current_stage][1].append((assertion, args))
        return self

    @property
    def stages(self) -> List[tuple]:
        """Return list of (action_text, thens) stage tuples."""
        return self._stages

    @property
    def _thens(self) -> List[tuple]:
        """Backward-compatible flat list of all thens across stages."""
        return [(a, args) for _, thens in self._stages for a, args in thens]


# ── Scenario registry ────────────────────────────────────────────────

_SCENARIOS: List[ScenarioBuilder] = []


def scenario(name: str, category: str = "general") -> Callable:
    """Decorator to register an eval scenario.

    The decorated function receives a ScenarioBuilder and should call
    given/when/then to define the scenario's steps.

    The function name (minus 'test_' prefix) becomes the scenario id.
    """
    def decorator(fn: Callable) -> Callable:
        sid = fn.__name__
        if sid.startswith("test_"):
            sid = sid[5:]
        builder = ScenarioBuilder(scenario_id=sid, name=name, category=category)
        fn(builder)
        _SCENARIOS.append(builder)
        return fn
    return decorator


def template(name: str, category: str = "general") -> Callable:
    """Decorator to register a case template.

    A template defines the grader behavior once. Call .cases() on the
    returned object to generate scenarios from a dataset.

    The decorated function receives (ScenarioBuilder, data_dict) and should
    use data_dict to parameterize given/when/then clauses.

    Usage:
        @template("legislation research", category="legislation")
        def legislation(s, data):
            s.given("a query", data["query"])
            s.when("the agent researches this query")
            s.then("documents retrieved should be at least", 3)
            s.when("the agent synthesizes the results")
            for term in data["expected_terms"]:
                s.then("the answer should mention", term)
            s.then("the answer should be", data["quality_criteria"])

        legislation.cases([
            {"query": "AI policy actions", "expected_terms": ["AI"], "quality_criteria": "comprehensive"},
            {"query": "Climate legislation", "expected_terms": ["climate"], "quality_criteria": "well-sourced"},
        ])
    """
    def decorator(fn: Callable) -> Callable:
        fn._template_name = name
        fn._template_category = category

        def cases(dataset: List[dict], id_field: str = "query") -> None:
            """Generate a scenario for each entry in the dataset."""
            for i, data in enumerate(dataset):
                # Build a readable case name from the data
                case_label = str(data.get(id_field, f"case_{i}"))
                if len(case_label) > 60:
                    case_label = case_label[:57] + "..."
                case_name = f"{name}: {case_label}"
                sid = re.sub(r'[^a-z0-9]+', '_', case_label.lower()).strip('_')

                builder = ScenarioBuilder(
                    scenario_id=f"{fn.__name__}_{sid}",
                    name=case_name,
                    category=category,
                )
                fn(builder, data)
                _SCENARIOS.append(builder)

        fn.cases = cases
        return fn
    return decorator


def get_all_scenarios() -> List[ScenarioBuilder]:
    """Return all registered scenarios."""
    return list(_SCENARIOS)


def get_scenarios_by_category(category: str) -> List[ScenarioBuilder]:
    """Return scenarios matching a category."""
    return [s for s in _SCENARIOS if s.category == category]
