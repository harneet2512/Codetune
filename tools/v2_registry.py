"""V2 Tool Registry — engineering-grade tools for killer demos."""
from tooltune.contracts import ToolCall, ToolObservation, ToolSpec
from . import codebase_search, file_reader, run_tests, log_search, search_docs, sql_query


class ToolRegistryV2:
    """Registry for engineering workflow tools."""

    def __init__(self) -> None:
        self._tools = {
            "codebase_search": (
                ToolSpec(
                    name="codebase_search",
                    description="Search the codebase for symbols, patterns, or references. Returns matching lines with file paths and line numbers.",
                    parameters={
                        "query": {"type": "string", "description": "Search pattern (regex supported)"},
                        "file_filter": {"type": "string", "description": "Optional path filter (e.g., 'tests/' or 'src/api')"},
                    },
                ),
                lambda args: codebase_search.run(args["query"], args.get("file_filter", "")),
            ),
            "file_reader": (
                ToolSpec(
                    name="file_reader",
                    description="Read the full content of a source file. Use after codebase_search to inspect files in detail.",
                    parameters={
                        "filepath": {"type": "string", "description": "Path to file (e.g., 'src/api/checkout.py')"},
                    },
                ),
                lambda args: file_reader.run(args["filepath"]),
            ),
            "run_tests": (
                ToolSpec(
                    name="run_tests",
                    description="Run the test suite or a specific test file/test case. Returns pass/fail status with error details for failures.",
                    parameters={
                        "test_path": {"type": "string", "description": "Test file path (e.g., 'tests/test_checkout.py'). Empty = run all."},
                        "test_name": {"type": "string", "description": "Specific test name (e.g., 'test_checkout_org_discount')"},
                    },
                ),
                lambda args: run_tests.run(args.get("test_path", ""), args.get("test_name", "")),
            ),
            "log_search": (
                ToolSpec(
                    name="log_search",
                    description="Search application logs and deploy history. Filter by log level, service, or keyword. Use source='deploys' for deploy history.",
                    parameters={
                        "query": {"type": "string", "description": "Search keyword (e.g., '500', 'checkout', 'error')"},
                        "level": {"type": "string", "description": "Log level filter: INFO, WARN, ERROR"},
                        "service": {"type": "string", "description": "Service filter: checkout, payment, monitoring"},
                        "source": {"type": "string", "description": "'logs' (default) or 'deploys' for deploy history"},
                    },
                ),
                lambda args: log_search.run(
                    args.get("query", ""),
                    args.get("level", ""),
                    args.get("service", ""),
                    args.get("source", "logs"),
                ),
            ),
            "search_docs": (
                ToolSpec(
                    name="search_docs",
                    description="Search internal documentation, API specs, runbooks, and data dictionaries. Returns matching sections with citations.",
                    parameters={
                        "query": {"type": "string", "description": "Search topic (e.g., 'token expiry', 'rollback criteria', 'revenue')"},
                        "doc_id": {"type": "string", "description": "Specific doc ID to retrieve in full (e.g., 'api_security_spec', 'incident_runbook')"},
                    },
                ),
                lambda args: search_docs.run(args.get("query", ""), args.get("doc_id", "")),
            ),
            "sql_query": (
                ToolSpec(
                    name="sql_query",
                    description="Execute a SQL query against the database. Available tables: orders, payment_events, customers. Supports SELECT, COUNT, SUM, WHERE, LIMIT.",
                    parameters={
                        "query": {"type": "string", "description": "SQL query to execute"},
                    },
                ),
                lambda args: sql_query.run(args["query"]),
            ),
        }

    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-format tool definitions for system prompt."""
        defs = []
        for spec, _ in self._tools.values():
            defs.append({
                "name": spec.name,
                "description": spec.description,
                "parameters": {
                    k: {"type": v["type"], "description": v["description"]}
                    for k, v in spec.parameters.items()
                },
            })
        return defs

    def validate_call(self, call: ToolCall) -> ToolCall:
        if call.name not in self._tools:
            call.valid = False
            call.error = f"Unknown tool: {call.name}"
        return call

    def execute(self, call: ToolCall) -> ToolObservation:
        if call.name not in self._tools:
            return ToolObservation(call.name, f'{{"error": "Unknown tool: {call.name}"}}', is_error=True)
        _, runner = self._tools[call.name]
        try:
            result = runner(call.arguments)
            is_err = "error" in result.lower() if isinstance(result, str) else False
            return ToolObservation(call.name, result, is_error=is_err)
        except Exception as e:
            return ToolObservation(call.name, f'{{"error": "{str(e)}"}}', is_error=True)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
