"""ConnectorRegistry — dispatches tool calls to real API backends.

Provides a unified interface for the agentic loop to discover and execute
connector tools against GitHub, Google Drive, and Gmail.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from tooltune.contracts import ToolCall, ToolObservation

from tools.connectors import github_tools, google_drive_tools, gmail_tools
from tools.connectors.schemas import CONNECTOR_TOOL_SCHEMAS


# Type alias for a connector function
ConnectorFn = Callable[..., dict[str, Any]]


class ConnectorRegistry:
    """Registry for ToolTune connector tools (GitHub, Drive, Gmail).

    Usage::

        registry = ConnectorRegistry()
        result = registry.execute(
            "github_list_issues",
            {"repo": "octocat/Hello-World", "state": "open"},
            credentials={"github_token": "ghp_..."},
        )
    """

    def __init__(self) -> None:
        self._tools: dict[str, ConnectorFn] = {
            # GitHub
            "github_search_code": github_tools.github_search_code,
            "github_read_file": github_tools.github_read_file,
            "github_list_issues": github_tools.github_list_issues,
            "github_list_prs": github_tools.github_list_prs,
            "github_read_pr": github_tools.github_read_pr,
            "github_create_branch": github_tools.github_create_branch,
            "github_commit_file": github_tools.github_commit_file,
            "github_create_pr": github_tools.github_create_pr,
            "github_create_issue": github_tools.github_create_issue,
            # Google Drive
            "drive_search": google_drive_tools.drive_search,
            "drive_read_file": google_drive_tools.drive_read_file,
            "drive_list_recent": google_drive_tools.drive_list_recent,
            "drive_get_file_info": google_drive_tools.drive_get_file_info,
            # Gmail
            "gmail_search": gmail_tools.gmail_search,
            "gmail_read_email": gmail_tools.gmail_read_email,
            "gmail_send_email": gmail_tools.gmail_send_email,
            "gmail_list_labels": gmail_tools.gmail_list_labels,
        }

        # Build a name -> schema lookup
        self._schemas: dict[str, dict[str, Any]] = {
            s["name"]: s for s in CONNECTOR_TOOL_SCHEMAS
        }

    def get_tool(self, name: str) -> ConnectorFn | None:
        """Return the callable for a tool by name, or None if unknown."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions (name, description, parameters) for the model.

        This is what gets injected into the system prompt during training
        and inference.
        """
        return [self._schemas[name] for name in self._tools if name in self._schemas]

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        credentials: dict[str, Any] | None = None,
    ) -> ToolObservation:
        """Execute a connector tool and return a ToolObservation.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool arguments as a dict.
            credentials: Optional credentials dict. Supported keys:
                - ``github_token``: GitHub personal access token
                - ``google_credentials``: google.oauth2 credentials object
                - ``google_access_token``: OAuth access token string

        Returns:
            A ``ToolObservation`` with the JSON-serialized result.
        """
        if tool_name not in self._tools:
            return ToolObservation(
                tool_name=tool_name,
                content=json.dumps({"error": f"Unknown tool: {tool_name}"}),
                is_error=True,
            )

        fn = self._tools[tool_name]
        credentials = credentials or {}

        # Inject credentials into arguments based on tool type
        call_args = dict(arguments)
        if tool_name.startswith("github_"):
            call_args.setdefault("token", credentials.get("github_token"))
        elif tool_name.startswith("drive_") or tool_name.startswith("gmail_"):
            google_creds = credentials.get("google_credentials")
            if google_creds is None and credentials.get("google_access_token"):
                # Lazy-build credentials from access token
                try:
                    from google.oauth2.credentials import Credentials
                    google_creds = Credentials(token=credentials["google_access_token"])
                except ImportError:
                    pass
            if google_creds is not None:
                call_args.setdefault("credentials", google_creds)

        try:
            result = fn(**call_args)
            is_error = "error" in result
            return ToolObservation(
                tool_name=tool_name,
                content=json.dumps(result, default=str),
                is_error=is_error,
            )
        except Exception as exc:
            return ToolObservation(
                tool_name=tool_name,
                content=json.dumps({"error": f"Tool execution failed: {exc}"}),
                is_error=True,
            )

    def execute_tool_call(
        self,
        tool_call: ToolCall,
        credentials: dict[str, Any] | None = None,
    ) -> ToolObservation:
        """Execute from a ``ToolCall`` contract object (for agentic loop compatibility).

        Args:
            tool_call: A ``ToolCall`` from the agentic loop parser.
            credentials: Optional credentials dict.

        Returns:
            A ``ToolObservation``.
        """
        if not tool_call.valid:
            return ToolObservation(
                tool_name=tool_call.name,
                content=json.dumps({"error": tool_call.error or "Invalid tool call"}),
                is_error=True,
            )
        return self.execute(tool_call.name, tool_call.arguments, credentials)
