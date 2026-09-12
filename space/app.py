"""Restraint-7B — ZeroGPU Space.

Gradio UI + OpenAI-compatible /v1/chat/completions shim over the real
agentic loop (simulated tool executor, same as eval).

Space repo layout (copy from github.com/harneet2512/Codetune):
    app.py
    requirements.txt
    tooltune/            # contracts, io
    tools/               # ToolRegistry + simulated executors
    train/__init__.py
    train/agentic_loop.py
"""

import os
import sys
import threading

import spaces
import torch
import gradio as gr
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tooltune.contracts import TaskRecord
from tools.registry import ToolRegistry
from train.agentic_loop import generate_agentic_completion

MODEL_ID = os.environ.get("MODEL_ID", "aravindpersona/restraint-7b")

_model = None
_tok = None
_lock = threading.Lock()


def _load():
    global _model, _tok
    if _model is not None:
        return
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    _tok = AutoTokenizer.from_pretrained(MODEL_ID)
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        device_map="auto",
    )
    _model.eval()


class HFGenerator:
    def __init__(self, model, tok):
        self.model, self.tok = model, tok

    @spaces.GPU(duration=120)
    def generate(self, prompt, max_new_tokens=256, temperature=0.0):
        inputs = self.tok(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens,
                do_sample=temperature > 0, temperature=max(temperature, 0.01),
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
                stop_strings=["</tool_call>", "<observation>", "</answer>", "\nUser:"],
                tokenizer=self.tok,
            )
        # stop_strings excludes the terminator; re-emit tags the parser needs
        text = self.tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        if "<tool_call>" in text and "</tool_call>" not in text:
            text += "</tool_call>"
        if "<answer>" in text and "</answer>" not in text:
            text += "</answer>"
        return text


def run_task(prompt_text: str, expected_tools=None):
    with _lock:
        _load()
        gen = HFGenerator(_model, _tok)
        task = TaskRecord(
            id="demo", tier="demo", prompt=prompt_text,
            ground_truth="", expected_tools=expected_tools or [],
            metadata={}, error_injection_policy={},
        )
        return generate_agentic_completion(
            generator=gen, task=task, registry=ToolRegistry(),
            max_steps=5, temperature=0.0,
        )


def ui_run(message):
    trace = run_task(message)
    calls = len(trace.tool_calls)
    verdict = "answered directly (no tool calls)" if calls == 0 else f"{calls} tool call(s)"
    return f"```\n{trace.transcript.strip()}\n```\n\n**Answer:** {trace.final_answer or '(none)'} — *{verdict}*"


# ---------- OpenAI-compatible shim ----------

api = FastAPI(title="Restraint-7B")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "restraint-7b"
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int = 512


@api.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    trace = run_task(user)
    return {
        "id": "chatcmpl-restraint",
        "object": "chat.completion",
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": trace.final_answer or ""},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "tool_calls_made": len(trace.tool_calls),
        },
    }


@api.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID}


demo = gr.Interface(
    fn=ui_run,
    inputs=gr.Textbox(label="Task", lines=3,
                      placeholder="What is 6 squared?  |  Weather in NYC?"),
    outputs=gr.Markdown(label="Agent trace"),
    title="Restraint-7B",
    description=(
        "7B tool-use model post-trained (SFT + corrective SFT) for restraint: answers "
        "knowledge questions directly instead of burning tool calls. "
        "Simulated 5-tool executor — same harness as the eval suite. "
        f"[Weights](https://huggingface.co/{MODEL_ID}) · "
        "[Code](https://github.com/harneet2512/Codetune)"
    ),
    examples=[
        ["What is 6 squared?"],
        ["What is 37 multiplied by 576?"],
        ["What's the weather in Tokyo right now?"],
        ["What HTTP status code means 'created'?"],
    ],
)

app = gr.mount_gradio_app(api, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
