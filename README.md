# CodeTune

A post-training lab that turns Qwen 2.5 7B into a tool-using agent through reinforcement learning. The model learns to read files from GitHub, search emails in Gmail, find specs in Google Drive, and know when not to call tools at all. 8% to 62% task accuracy. Full-stack playground included.

![CodeTune Demo](codetune-demo.gif)

## Results

```
                        Base        SFT         GRPO
Task Accuracy           8%          60%         62%         +54pp
Tool Precision          12%         85%         94%         +82pp
Restraint Score         15%         60%         85%         +70pp
Evidence Quality        0.4/5       3.2/5       4.2/5       +3.8
```

### By Category (250 tasks)

```
                        Tasks       Base        SFT         GRPO
Single-tool             100         12%         78%         80%
Multi-step              80          4%          55%         58%
Cross-service           50          2%          42%         45%
Restraint               20          15%         60%         85%
```

## What It Does

**Training.** Supervised fine-tuning on 250 expert tool-use traces, then GRPO with a composite reward signal (correctness + tool precision + restraint + planning). QLoRA on a single T4 GPU.

**Evaluation.** 250 tasks modeled on real engineering workflows: spec compliance audits, production incident triage, cross-service investigations, and restraint scenarios. Four tiers from single-tool lookups to multi-hop cross-service reasoning.

**17 tool schemas across 5 services.** GitHub (search repos, read files, list PRs, commit history, create issues), Gmail (search, read, send, list threads), Google Drive (search, read documents, list folders, metadata), Confluence, Jira.

**Full-stack playground.** React frontend with three-column model comparison, block-based trace visualization, eval dashboard, connectors workbench with live tool testing, and a FastAPI backend with real API integrations.

**Live inference.** The trained GRPO model runs on HuggingFace ZeroGPU, executes real tool calls against real APIs (GitHub, Gmail, Google Drive via OAuth), and streams the reasoning trace to the frontend in real time via SSE.

## Architecture

```
Frontend (React/Vite)         Backend (FastAPI)           Model (HuggingFace)
+-----------------+    HTTP   +-----------------+  POST   +-----------------+
| Playground      |---/api-->| ReAct Loop      |-------->| Qwen 2.5 7B     |
| Eval Dashboard  |<--SSE---| Tool Router     |         | GRPO checkpoint  |
| Connectors      |          | Trace Builder   |         | ZeroGPU (T4)    |
| Models          |          | Demo Cache      |         +-----------------+
+-----------------+          +-------+---------+
                                     |
                         +-----------+-----------+
                         v           v           v
                    GitHub API   Gmail API   Drive API
```

## Demo Tasks

**Spec Compliance Audit.** Read the API Security Spec from Google Drive, then audit the auth middleware on GitHub against it. GRPO finds all 4 violations with line numbers. SFT finds 2. Base guesses.

**Production Incident Triage.** Search Gmail for deployment alerts, trace to the failing commit on GitHub, read the diff, identify root cause. GRPO cross-references 3 sources and names the exact commit.

**Restraint: HTTP 409.** "What HTTP status code for a resource that already exists?" GRPO answers directly. Zero tool calls. SFT calls `search_pages` unnecessarily.

**Cross-Service Investigation.** Search emails for deployment failures, then check the related repo for recent commits. Tests multi-hop reasoning across GitHub and Gmail.

## Training Pipeline

```
Qwen 2.5 7B Instruct
        |
        v  SFT (250 traces, QLoRA r=64, 2 epochs)
        |
  + SFT --- 60% accuracy, learns format but over-tools
        |
        v  LoRA merge, then GRPO (300 steps, 8 gen/prompt)
        |
  + GRPO --- 62% accuracy, 94% tool precision, 85% restraint
```

### Reward Signal

```
Signal              Weight      What It Measures
Task correctness    1.0         Did the model get the right answer?
Tool precision      0.3         Were tool calls well-targeted with correct args?
Restraint           0.1         Did it avoid tools on knowledge questions?
Planning            0.1         Did it plan before acting?
Loop penalty        -0.1        Penalize excess tool calls per step
```

### What Changes at Each Stage

**Base** outputs raw JSON blobs. No structured reasoning. Hallucinates tool names. 0% tool usage.

**SFT** learns the ReAct format (think, tool_call, observation, answer) but over-tools on questions that don't need tools. 74% tool call rate on knowledge questions. Finds 2 of 4 violations in spec audits.

**GRPO** learns when NOT to call tools (100% restraint on knowledge questions), targets queries precisely, cross-references multiple sources, and cites evidence with line numbers. Finds all 4 violations in spec audits.

## Failure Modes (Latest GRPO Eval)

```
Mode                    Count       Example
Hallucinated tool       3 (1.2%)    Called analyze_security() which doesn't exist
Malformed arguments     5 (2.0%)    Passed integer for query expecting string
Wrong tool selection    8 (3.2%)    Used search_emails when task required search_files
Premature termination   12 (4.8%)   Answered before reading all sources
Over-planning           4 (1.6%)    Called 6 tools for a single-step lookup
Missed restraint        6 (2.4%)    Called search_pages for "What is HTTP 409?"
```

## Quick Start

### Demo Mode (no credentials needed)

```bash
cd playground/client
npm install
npm run dev
```

Open http://localhost:3000. All views work with pre-computed traces.

### Full Stack (live inference + real APIs)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env    # fill in your credentials
python main.py

# Frontend (separate terminal)
cd playground/client
npm run dev
```

### Credentials

GitHub: personal access token with `public_repo` scope.
Gmail and Drive: Google Cloud OAuth 2.0 client with `gmail.readonly` and `drive.readonly` scopes.
HuggingFace: Space with your GRPO model deployed on ZeroGPU.

All credentials go in `backend/.env`. See `.env.example` for the full template.

## Project Structure

```
codetune/
  train/                    SFT + GRPO training scripts
  tooltune/eval/            Tool-use evaluation suite
  eval/                     Code generation evals (HumanEval, MBPP)
  tasks/                    250 engineering workflow tasks (4 tiers)
  tools/connectors/         GitHub, Gmail, Drive tool schemas + mock executors
  playground/client/        React frontend (Vite + TypeScript)
  backend/                  FastAPI orchestrator
    connectors/             Real API connectors (GitHub, Gmail, Drive)
    inference/              HuggingFace Space client
    auth/                   Google OAuth 2.0
    traces/                 Raw output to block parser
  results/                  Training logs, eval results, checkpoints
  serve/                    Quantization + deployment (vLLM, SGLang, llama.cpp)
  bench/                    Async benchmark runner
  configs/                  YAML configs for training, eval, serving
```

## Technical Details

- **Base model**: Qwen/Qwen2.5-7B-Instruct (7B params, ChatML format)
- **Fine-tuning**: QLoRA (r=16, alpha=32, NF4 quantization, ~87M trainable params)
- **GRPO**: TRL library, num_generations=8, beta=0, lr=5e-6
- **Frontend**: React 19, TypeScript, Vite 8, lucide-react
- **Backend**: FastAPI, httpx, sse-starlette, google-auth-oauthlib
- **Serving**: vLLM, SGLang, llama.cpp with GPTQ INT8 / AWQ INT4
