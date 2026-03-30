"""File reader tool — reads full file content from the mock codebase."""
import json

# Reuse codebase from codebase_search
from .codebase_search import CODEBASE


def run(filepath: str) -> str:
    """Read the full content of a file."""
    if filepath in CODEBASE:
        data = CODEBASE[filepath]
        return json.dumps({
            "filepath": filepath,
            "content": data["content"],
            "author": data["author"],
            "last_modified": data["last_modified"],
        })

    return json.dumps({"error": f"File not found: {filepath}"})
