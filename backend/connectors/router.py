"""Tool call router — dispatches tool calls to the correct API connector."""

from connectors.github import call_github
from connectors.gmail import call_gmail
from connectors.drive import call_drive


async def execute_tool(tool_name: str, args: dict) -> dict:
    """Execute a tool call against the real API and return the result."""
    service, _, method = tool_name.partition(".")

    if service == "github":
        return await call_github(method, args)
    elif service == "gmail":
        return await call_gmail(method, args)
    elif service == "drive":
        return await call_drive(method, args)
    else:
        return {"error": f"Unknown service: {service}", "tool": tool_name}
