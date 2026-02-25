"""
Action registry for When clause dispatch.

Each action maps a When clause pattern to a handler that invokes
the SUT and returns a raw result. The runner normalizes the result
into a Subject for graders to evaluate.

Action handlers receive:
  - context: dict with given data (e.g. {"query": "..."})
  - previous: the Subject from the prior stage (None for first stage)
  - architecture: the SUT instance

Returning `previous` signals a pass-through (no new SUT invocation).

Usage:
    from evaluation.actions import action

    @action("the agent researches")
    def research(context, previous, architecture):
        return architecture.research(context["query"])
"""
from __future__ import annotations

from typing import Any, Callable, Optional


_ACTION_DEFS: list = []  # [(pattern, fn)]


def action(pattern: str):
    """Register an action handler for a When clause pattern."""
    def decorator(fn: Callable) -> Callable:
        _ACTION_DEFS.append((pattern, fn))
        return fn
    return decorator


def match_action(action_text: str) -> Optional[Callable]:
    """Find a matching action handler by prefix match."""
    if not action_text:
        return None
    for pattern, fn in _ACTION_DEFS:
        if action_text.lower().startswith(pattern.lower()):
            return fn
    return None


# ── Built-in actions for the research agent ──────────────────────────

@action("the agent researches")
def _research(context: dict, previous: Any, architecture: Any) -> Any:
    """Invoke the research pipeline on the SUT."""
    return architecture.research(context["query"], max_results_per_source=5)


@action("the agent synthesizes")
def _synthesize(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade synthesis output. In this POC, synthesis is part of the
    research pipeline, so pass through the previous subject."""
    return previous


@action("the agent executes code")
def _execute_code(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade code execution. Pass through — code runs during research."""
    return previous


@action("the critic evaluates")
def _critic_evaluates(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade critic behavior. Pass through — critic runs during research."""
    return previous


@action("the agent plans")
def _plan(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade planning behavior. Pass through — planning runs during research."""
    return previous


@action("the agent executes the plan")
def _execute_plan(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade plan execution. Pass through — execution runs during research."""
    return previous


@action("the supervisor plans")
def _supervisor_plans(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade supervisor planning. Pass through — planning runs during research."""
    return previous


@action("the source workers execute")
def _workers_execute(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade worker execution. Pass through — workers run during research."""
    return previous


@action("the workers research with peer sharing")
def _workers_peer(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade P2P worker behavior. Pass through — workers run during research."""
    return previous


@action("the synthesizer produces")
def _synthesizer_produces(context: dict, previous: Any, architecture: Any) -> Any:
    """Grade synthesizer output. Pass through — synthesizer runs during research."""
    return previous
