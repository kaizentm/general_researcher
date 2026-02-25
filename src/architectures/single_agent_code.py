"""
Single Agent + Code Execution Architecture.

Same as single_agent but the Researcher has access to execute_python
for data analysis, aggregation, and computation over retrieved documents.
"""
from datetime import datetime

from architectures.common import ResearchResult, extract_citations
from agents.client import FoundryAgentManager
from agents.researcher import create_researcher_with_code
from utils import normalize_query, log_query_corrections

__all__ = ["SingleAgentCodeOrchestrator"]


class SingleAgentCodeOrchestrator:
    """Single Researcher agent with search tools + code execution."""

    def __init__(self, manager: FoundryAgentManager, data_sources=None):
        self.manager = manager
        self.agent, self.tools, self.stats = create_researcher_with_code(manager)

    def research(self, query: str, max_results_per_source: int = 5) -> ResearchResult:
        """Run the Foundry researcher agent with code execution and return a ResearchResult."""
        start_time = datetime.now()

        query, corrections = normalize_query(query)
        log_query_corrections(corrections)

        self.stats.reset()
        result = self.manager.run_agent(self.agent.id, query, tool_set=self.tools)
        docs_retrieved, sources_called = self.stats.reset()
        citations = extract_citations(result.text)

        elapsed = (datetime.now() - start_time).total_seconds()

        return ResearchResult(
            query=query,
            answer=result.text,
            sources_checked=sources_called,
            documents_retrieved=docs_retrieved,
            documents_used=len(citations),
            citations=citations,
            time_elapsed=elapsed,
            metadata={"architecture": "single_agent_code"},
        )
