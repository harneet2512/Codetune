"""Restraint-7B demo endpoint on Modal.

Serves the real agentic loop over the published GGUF on a T4.
Scales to zero when idle — only request time bills.

Deploy:  modal deploy scripts/modal_demo.py
Then:    POST {url}/v1/chat/completions  {"messages":[{"role":"user","content":"..."}]}
         GET  {url}/                     tiny HTML demo
         POST {url}/run                 {"prompt": "..."} -> full trace JSON
"""

import modal

app = modal.App("restraint-7b-demo")

GGUF_REPO = "aravindpersona/restraint-7b"
GGUF_FILE = "restraint-7b-v2-q4km.gguf"


def _download_gguf():
    from huggingface_hub import hf_hub_download
    hf_hub_download(GGUF_REPO, GGUF_FILE, local_dir="/root/model")


image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("libgomp1")
    .pip_install(
        "llama-cpp-python==0.3.16",
        extra_index_url="https://abetlen.github.io/llama-cpp-python/whl/cu124",
    )
    .pip_install("huggingface_hub", "fastapi[standard]")
    .run_function(_download_gguf)
    .add_local_dir("tooltune", remote_path="/root/tooltune", copy=True)
    .add_local_dir("tools", remote_path="/root/tools", copy=True)
    .add_local_dir("tooltune_data", remote_path="/root/tooltune_data", copy=True)
    .add_local_file("train/__init__.py", remote_path="/root/train/__init__.py", copy=True)
    .add_local_file("train/agentic_loop.py", remote_path="/root/train/agentic_loop.py", copy=True)
)

STOPS = ["<|im_end|>", "\nUser:", "</answer>", "</tool_call>", "<observation>"]


@app.cls(gpu="T4", image=image, scaledown_window=300)
class Model:
    @modal.enter()
    def load(self):
        import sys

        sys.path.insert(0, "/root")
        from llama_cpp import Llama
        from tools.registry import ToolRegistry

        self.llm = Llama(
            "/root/model/" + GGUF_FILE,
            n_gpu_layers=-1,
            n_ctx=4096,
            verbose=False,
        )
        self.registry = ToolRegistry()

    def _generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0) -> str:
        out = self.llm(
            prompt,
            max_tokens=max_new_tokens,
            temperature=temperature,
            stop=STOPS,
        )
        text = out["choices"][0]["text"]
        # stop excludes the terminator; re-emit tags the transcript parser needs
        if "<tool_call>" in text and "</tool_call>" not in text:
            text += "</tool_call>"
        if "<answer>" in text and "</answer>" not in text:
            text += "</answer>"
        return text

    @modal.method()
    def run(self, prompt_text: str) -> dict:
        from tooltune.contracts import TaskRecord
        from train.agentic_loop import generate_agentic_completion

        task = TaskRecord(
            id="demo",
            tier="demo",
            prompt=prompt_text,
            ground_truth="",
            expected_tools=[],
            metadata={},
            error_injection_policy={},
        )
        gen = _Gen(self)
        trace = generate_agentic_completion(
            generator=gen, task=task, registry=self.registry, max_steps=5, temperature=0.0
        )
        return {
            "transcript": trace.transcript,
            "answer": trace.final_answer,
            "tool_calls": [c.to_dict() for c in trace.tool_calls],
        }


class _Gen:
    def __init__(self, model):
        self.model = model

    def generate(self, prompt, max_new_tokens=256, temperature=0.0):
        return self.model._generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)


HTML = """<!doctype html><html><body style="font-family:monospace;max-width:720px;margin:40px auto">
<h2>Restraint-7B</h2>
<p>7B tool-use model trained to answer knowledge questions <b>without</b> calling tools.
Try <i>"What is 6 squared?"</i> (direct answer) vs <i>"What's the weather in Tokyo?"</i> (tool call).</p>
<input id=q size=60 value="What is 6 squared?"><button onclick="go()">Run</button>
<pre id=o style="white-space:pre-wrap;background:#f4f4f4;padding:12px"></pre>
<script>
async function go(){
  document.getElementById('o').textContent='running (cold start ~60s first time)...';
  const r = await fetch('run',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({prompt:document.getElementById('q').value})});
  const d = await r.json();
  document.getElementById('o').textContent = d.transcript + '\\n\\nANSWER: ' + d.answer;
}
</script>
<p style="color:#888">weights: huggingface.co/aravindpersona/restraint-7b · code: github.com/harneet2512/Codetune</p>
</body></html>"""


@app.function(image=image)
@modal.asgi_app()
def api():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel

    web = FastAPI(title="Restraint-7B")

    class RunReq(BaseModel):
        prompt: str

    class ChatReq(BaseModel):
        messages: list[dict]
        model: str = "restraint-7b"

    @web.get("/", response_class=HTMLResponse)
    def index():
        return HTML

    @web.get("/health")
    def health():
        return {"status": "ok", "model": GGUF_REPO}

    @web.post("/run")
    def run(req: RunReq):
        return Model().run.remote(req.prompt)

    @web.post("/v1/chat/completions")
    def chat(req: ChatReq):
        prompt = req.messages[-1]["content"] if req.messages else ""
        r = Model().run.remote(prompt)
        return {
            "id": "chatcmpl-restraint",
            "object": "chat.completion",
            "model": req.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": r["answer"] or r["transcript"]},
                "finish_reason": "stop",
            }],
        }

    return web
