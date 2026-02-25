"""
Code execution tool for Foundry Agents.

Allows agents to write and execute Python code for data analysis,
aggregation, and computation over retrieved documents. Runs in-process
since the project already runs inside a container.
"""
import io
import json
import logging
import sys
import traceback
import threading
from contextlib import redirect_stdout, redirect_stderr

from azure.ai.agents.models import FunctionTool

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30

# Pre-imported modules available to executed code
_ALLOWED_GLOBALS = {
    "__builtins__": __builtins__,
}

# Lazily populated on first execution
_PRELOADED_MODULES = {
    "json": "json",
    "math": "math",
    "statistics": "statistics",
    "collections": "collections",
    "re": "re",
    "datetime": "datetime",
    "pandas": "pandas",
}


def _get_exec_globals() -> dict:
    """Build a globals dict with pre-imported common modules."""
    g = dict(_ALLOWED_GLOBALS)
    for alias, module_name in _PRELOADED_MODULES.items():
        try:
            g[alias] = __import__(module_name)
        except ImportError:
            pass
    return g


def execute_python(code: str) -> str:
    """Execute Python code and return its stdout output.

    The code runs with common data analysis libraries pre-imported
    (json, pandas, math, statistics, collections, re, datetime).
    Use print() to produce output. The last expression's value is
    also captured if it is not None.

    Args:
        code: Python source code to execute.

    Returns:
        A JSON object with 'output' (stdout) and optionally 'error'.
    """
    logger.info("execute_python called: %d chars of code", len(code))
    logger.debug("Code:\n%s", code)

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    result = {"output": "", "error": None}
    exec_globals = _get_exec_globals()

    def _run():
        nonlocal result
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compile(code, "<agent_code>", "exec"), exec_globals)
        except Exception:
            result["error"] = traceback.format_exc()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_SECONDS)

    if thread.is_alive():
        result["error"] = f"Execution timed out after {TIMEOUT_SECONDS}s"
        result["output"] = stdout_buf.getvalue()
        logger.warning("Code execution timed out")
    else:
        result["output"] = stdout_buf.getvalue()
        stderr_output = stderr_buf.getvalue()
        if stderr_output and not result["error"]:
            result["error"] = stderr_output

    if result["error"]:
        logger.warning("Code execution error: %s", result["error"][:500])
    else:
        logger.info("Code execution succeeded: %d chars output", len(result["output"]))

    # Drop null error for cleaner output
    if result["error"] is None:
        del result["error"]

    return json.dumps(result)


execute_python.__annotations__ = {"code": str, "return": str}


def get_code_exec_tool() -> FunctionTool:
    """Create a FunctionTool for Python code execution."""
    tool = FunctionTool(functions={execute_python})
    logger.info("Created code execution FunctionTool")
    return tool
