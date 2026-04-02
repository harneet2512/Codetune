"""HuggingFace Space inference client."""

import httpx
from config import HF_SPACE_URL, HF_TOKEN


async def call_model(messages: list[dict], tool_schemas: list[dict]) -> dict:
    """Call the HuggingFace Space endpoint for model inference.

    Returns: {"output": str, "tokens_used": int, "inference_time_ms": int}
    """
    if not HF_SPACE_URL:
        raise RuntimeError(
            "HF_SPACE_URL not configured. Set it in .env to enable live inference."
        )

    # Build the system prompt with tool schemas
    tool_desc = "\n".join(
        f"- {t['name']}: {t['description']}" for t in tool_schemas
    )
    system_prompt = (
        "You are a tool-using agent. Available tools:\n"
        f"{tool_desc}\n\n"
        "Use the following format:\n"
        "<think>your reasoning</think>\n"
        '<tool_call>{"name": "tool.method", "args": {...}}</tool_call>\n'
        "<observation>tool result</observation>\n"
        "<answer>your final answer</answer>\n\n"
        "Always think before acting. Only call tools when needed."
    )

    payload = {
        "system_prompt": system_prompt,
        "messages": messages,
        "max_new_tokens": 512,
        "temperature": 0.3,
    }

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            HF_SPACE_URL,
            json=payload,
            headers=headers,
            timeout=120,  # model inference can take 30-60s on cold start
        )
        resp.raise_for_status()
        return resp.json()


async def check_model_status() -> dict:
    """Check if the HuggingFace Space is available and warm."""
    if not HF_SPACE_URL:
        return {"status": "not_configured", "url": ""}

    try:
        async with httpx.AsyncClient() as client:
            # Hit a lightweight endpoint to check if the Space is up
            resp = await client.get(
                HF_SPACE_URL.replace("/api/predict", "/api/status"),
                timeout=10,
            )
            if resp.status_code == 200:
                return {"status": "warm", "url": HF_SPACE_URL}
            return {"status": "cold", "url": HF_SPACE_URL}
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"status": "offline", "url": HF_SPACE_URL}
