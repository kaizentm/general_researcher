"""
Researcher agent definition.

The Researcher is equipped with search tools and autonomously decides
which sources to query, how to refine searches, and evaluates relevance.
Used by: ReAct, Single Agent, Multi-Agent, Plan-and-Execute.
"""
from agents.client import FoundryAgentManager
from tools.search_tools import get_all_search_tools
from tools.exec_tools import get_code_exec_tool


RESEARCHER_INSTRUCTIONS = """You are a government policy research agent with access to three search tools:
- search_govinfo: Congressional bills and legislation
- search_federal_register: Federal regulations, rules, and agency notices
- search_datagov: Government datasets and data catalogs

When given a research query:
1. Search ALL three sources with queries tailored to each source's content type
2. Review results for relevance — mentally discard documents that don't address the query
3. If results are insufficient or too narrow, refine your search terms and try again
4. Synthesize a comprehensive answer using ONLY information from retrieved documents
5. Cite every claim with inline citations [1], [2], etc.
6. Include a numbered reference list at the end with source, title, URL, and date

Be thorough but efficient. Do not fabricate information not found in the documents."""


RESEARCHER_WITH_CODE_INSTRUCTIONS = RESEARCHER_INSTRUCTIONS + """

You also have access to a code execution tool:
- execute_python: Run Python code for data analysis, aggregation, filtering, or computation.
  Pre-imported: json, pandas, math, statistics, collections, re, datetime.
  Use print() to produce output.

Use execute_python when a query requires:
- Statistical analysis (rates, trends, counts, comparisons)
- Aggregating or filtering large result sets
- Data transformations that are easier in code than natural language
- Any computation where precision matters

Workflow for analytical queries:
1. Search sources to gather raw data
2. Write Python code to process/analyze the data
3. Execute the code and interpret results
4. Present findings with both the analysis and source citations"""


def create_researcher(manager: FoundryAgentManager, model_override: str = None):
    """Create a Researcher agent with all search tools.
    
    Returns (agent, tools, stats) tuple.
    """
    tools, stats = get_all_search_tools(govinfo_api_key=manager.govinfo_api_key)
    return manager.create_agent(
        name="researcher",
        instructions=RESEARCHER_INSTRUCTIONS,
        tools=tools.definitions,
        model_override=model_override or manager.model,
    ), tools, stats


def create_researcher_with_code(manager: FoundryAgentManager, model_override: str = None):
    """Create a Researcher agent with search tools and code execution.
    
    Returns (agent, tools, stats) tuple.
    """
    search_tools, stats = get_all_search_tools(govinfo_api_key=manager.govinfo_api_key)
    code_tool = get_code_exec_tool()
    search_tools.add_functions(set(code_tool._functions.values()))
    return manager.create_agent(
        name="researcher",
        instructions=RESEARCHER_WITH_CODE_INSTRUCTIONS,
        tools=search_tools.definitions,
        model_override=model_override or manager.model,
    ), search_tools, stats
