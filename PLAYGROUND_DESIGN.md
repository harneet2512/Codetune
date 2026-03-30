# ToolTune Playground — Design & Build Prompt

## What This Is
A developer-facing diagnostic playground that shows **how a fine-tuned model thinks through real engineering tasks**. Not a chat UI — a **reasoning debugger**. The viewer watches the agent's decision-making process unfold step by step, with visual traces comparing Base (broken) → SFT (format-correct but clumsy) → GRPO (surgical and restrained).

No GPU needed. All traces are hardcoded in demo mode. The UI is the product.

---

## Core Design Principle
**Show the WHY, not just the WHAT.**

Every tool call should be preceded by visible reasoning. Every decision should be traceable. The viewer should be able to look at a GRPO trace and say: "I see exactly why it chose to read the spec before patching, and why it skipped the calculator on a trivial question."

---

## Page Layout

### Single Page App — 3 Panels

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: ToolTune Playground                    [v2]    │
│  Subtitle: "Watch an agent think through real tasks"    │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  TASK PANEL  │         TRACE VIEWER                     │
│  (left rail) │         (center — main stage)            │
│              │                                          │
│  ┌────────┐  │  ┌────────────────────────────────────┐  │
│  │Incident│  │  │     REASONING FLOWCHART            │  │
│  │Triage  │  │  │                                    │  │
│  ├────────┤  │  │  [Think] → [Tool] → [Observe]     │  │
│  │Spec    │  │  │     ↓                              │  │
│  │Audit   │  │  │  [Think] → [Tool] → [Observe]     │  │
│  ├────────┤  │  │     ↓                              │  │
│  │Bug     │  │  │  [Think] → [Answer]                │  │
│  │Repro   │  │  │                                    │  │
│  ├────────┤  │  └────────────────────────────────────┘  │
│  │Data    │  │                                          │
│  │Discrep.│  │  ┌────────────────────────────────────┐  │
│  ├────────┤  │  │     RAW TRACE (collapsible)        │  │
│  │CI Fix  │  │  │  <think>...</think>                │  │
│  ├────────┤  │  │  <tool_call>...</tool_call>        │  │
│  │Schema  │  │  │  <observation>...</observation>    │  │
│  │Migrate │  │  └────────────────────────────────────┘  │
│  ├────────┤  │                                          │
│  │Conflict│  │  ┌────────────────────────────────────┐  │
│  │Evidence│  │  │     VERDICT BAR                    │  │
│  ├────────┤  │  │  ✓ Correct  │ 4 tools │ 5 steps   │  │
│  │2+2     │  │  │  Restraint: ✓  Recovery: ✓         │  │
│  │(simple)│  │  └────────────────────────────────────┘  │
│  └────────┘  │                                          │
│              │                                          │
│  MODEL TABS  │                                          │
│  [BASE][SFT] │                                          │
│  [GRPO]      │                                          │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
```

---

## The Reasoning Flowchart (The Star Feature)

This is what makes jaws drop. For each trace, render a **vertical flowchart** showing the agent's reasoning process:

### Node Types

```
┌─────────────────────────────────────────┐
│ 🧠 THINK (blue node)                    │
│                                         │
│ "I need to check the error logs first   │
│  to identify the pattern before I can   │
│  determine if this is a rollback or     │
│  hotfix situation."                     │
│                                         │
│ Decision: Search logs for 500 errors    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 🔧 TOOL CALL (orange node)              │
│                                         │
│ log_search(query="500", level="ERROR",  │
│            service="checkout")          │
│                                         │
│ Status: ✓ Executed                      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 👁 OBSERVATION (green node)              │
│                                         │
│ Found 5 ERROR entries. All from orgs    │
│ with custom pricing. Error: "NoneType   │
│ has no attribute price"                 │
│                                         │
│ [Expand full JSON ▼]                    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 🧠 THINK (blue node)                    │
│                                         │
│ "The errors are isolated to orgs with   │
│  custom pricing tiers, not all users.   │
│  Per the runbook, this means hotfix     │
│  not rollback. Let me check the deploy  │
│  history to confirm timing."            │
│                                         │
│ Decision: Check deploy history          │
└──────────────────┬──────────────────────┘
                   │
                   ▼
                  ...
                   │
                   ▼
┌─────────────────────────────────────────┐
│ ✅ ANSWER (green success node)           │
│                                         │
│ "Recommend HOTFIX, not rollback.        │
│  Root cause: v2.14.1 enabled            │
│  new_checkout_flow without handling     │
│  org discount for custom pricing tiers. │
│  Immediate action: disable              │
│  new_checkout_flow feature flag."       │
│                                         │
│ Confidence: HIGH                        │
│ Evidence: 4 sources cited               │
└─────────────────────────────────────────┘
```

### For BASE model (broken):

```
┌─────────────────────────────────────────┐
│ 🧠 THINK (red/dim node)                 │
│                                         │
│ "I'll check the checkout logs."         │
│                                         │
│ (No structured reasoning)               │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ ❌ RAW OUTPUT (red node)                 │
│                                         │
│ {"tool": "log_search",                  │
│  "tool_params": {"query": "500"}}       │
│                                         │
│ Status: ✗ Wrong format — not executed   │
│ Model output raw JSON instead of using  │
│ <tool_call> tags                        │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ ❌ NO ANSWER (red node)                  │
│                                         │
│ Model continued generating JSON blobs   │
│ without ever producing an answer.       │
│ Loop terminated at max steps.           │
│                                         │
│ Verdict: COMPLETE FAILURE               │
└─────────────────────────────────────────┘
```

### For SFT model (over-tools):

```
┌─────────────────────────────────────────┐
│ 🧠 THINK (yellow/warning node)           │
│                                         │
│ "Let me search for information about    │
│  this error."                           │
│                                         │
│ (Generic reasoning, not task-specific)  │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 🔧 TOOL CALL (orange node)              │
│ log_search(query="checkout")            │
│ Status: ✓ Executed                      │
│ ⚠ Overly broad query                   │
└──────────────────┬──────────────────────┘
                   │
                   ▼
        ... (calls 6+ tools when 4 suffice)
                   │
                   ▼
┌─────────────────────────────────────────┐
│ ✅ ANSWER (yellow/partial node)          │
│                                         │
│ "There are errors in checkout. The      │
│  deploy changed something. Consider     │
│  rolling back."                         │
│                                         │
│ Verdict: PARTIALLY CORRECT              │
│ ⚠ Recommends rollback (runbook says    │
│   hotfix for org-specific errors)       │
│ ⚠ Used 6 tools (optimal: 4)           │
└─────────────────────────────────────────┘
```

---

## The 7 Killer Demo Tasks (Hardcoded Traces)

For each task, write 3 complete traces (base/sft/grpo) showing these behavioral contrasts:

### 1. Production Incident Triage
**Prompt:** "500 errors spiked on /api/checkout after the 14:05 deploy..."
- **BASE:** Outputs raw JSON, never executes tools, no answer
- **SFT:** Searches logs (broad query), checks deploys, reads code, reads runbook, reads feature flags, searches docs again (6 tools). Recommends rollback (wrong — runbook says hotfix for org-specific issues)
- **GRPO:** Searches error logs (targeted: level=ERROR, service=checkout), checks deploy history, reads runbook rollback criteria, reads checkout code (4 tools). Recommends hotfix + disable feature flag (correct). Cites runbook criteria.

### 2. Spec Compliance Audit
**Prompt:** "Audit the auth middleware against the API Security Spec..."
- **BASE:** Outputs something about security but no structured analysis
- **SFT:** Reads spec, reads code, finds 2 of 4 violations (misses token-in-memory and expiry issues)
- **GRPO:** Reads spec first, then reads code, systematically checks each AUTH-00X rule. Finds all 4 violations with exact citations: AUTH-001 (HS256+"none"), AUTH-002 (hardcoded key), AUTH-003 (720hr expiry), AUTH-004 (token stored in g.session_token)

### 3. Customer Bug Reproduction
**Prompt:** "Exports fail for orgs with custom roles like 'billing-admin'..."
- **BASE:** Rambles about exports
- **SFT:** Searches for "export", reads export.py, finds the bug, but also unnecessarily calls sql_query and log_search (5 tools)
- **GRPO:** Runs test suite first (targeted: test_export.py), reads failing test, reads export.py, identifies hardcoded role list (3 tools). Also notes feature_flags.yaml has same issue.

### 4. Data Discrepancy Investigation
**Prompt:** "Dashboard says $12,450.49, warehouse says $11,705.48..."
- **BASE:** Guesses about rounding errors
- **SFT:** Queries both numbers, reads docs, but concludes "there's a discrepancy" without determining cause (unhelpful)
- **GRPO:** Queries dashboard revenue definition from docs, queries warehouse definition, identifies delta is taxes+shipping ($745.01 = 3-5% expected range per data dictionary), recommends warehouse number for board report with reasoning

### 5. CI Failure → Fix
**Prompt:** "Checkout test suite has a failing test after latest deploy..."
- **BASE:** No useful output
- **SFT:** Runs all tests, reads failing test, reads checkout.py, but also reads unrelated files (5 tools)
- **GRPO:** Runs test_checkout.py, reads failing test (test_checkout_org_discount), reads checkout.py line where total is computed, identifies missing org discount logic (3 tools)

### 6. Schema Migration Planning
**Prompt:** "Rename customer_id to account_id across the service..."
- **BASE:** Generic advice about ALTER TABLE
- **SFT:** Searches customer_id, finds references, but misses migration guide and produces incomplete plan
- **GRPO:** Searches customer_id (finds all references), reads migration guide from docs (3-phase rename), reads existing migration file (003), reads affected models, produces phased plan citing the guide

### 7. Conflicting Evidence Resolution
**Prompt:** "Spec says 1hr expiry, code says 720hr..."
- **BASE:** No structured analysis
- **SFT:** Reads spec, reads code, says "they conflict" (no resolution)
- **GRPO:** Reads spec (authoritative: AUTH-003), reads code (non-compliant: 720hr), runs auth tests (3 tests fail including expiry), determines spec is authoritative, recommends changing create_token to expires_hours=1

### 8-10. Restraint Tasks
**Prompt:** "What HTTP status for business logic conflict?" / "JWT sub vs iss?" / "Hash table lookup complexity?"
- **BASE:** Answers correctly (from pretrained knowledge) but with no structure
- **SFT:** Calls search_docs or codebase_search unnecessarily before answering
- **GRPO:** Answers directly: "409 Conflict" / "sub=subject, iss=issuer" / "O(1)" — zero tool calls

---

## Visual Design System

### Colors
```
Background:     #0D1117 (GitHub dark)
Surface:        #161B22
Border:         #30363D
Text primary:   #E6EDF3
Text secondary: #8B949E

Think nodes:    #1F6FEB (blue) border, #0D1117 bg
Tool nodes:     #D29922 (amber) border
Observe nodes:  #238636 (green) border
Answer nodes:   #238636 (green) bg, white text
Error nodes:    #DA3633 (red) border
Warning nodes:  #D29922 (amber) bg, dark text

Base model:     #DA3633 (red accent)
SFT model:      #D29922 (amber accent)
GRPO model:     #238636 (green accent)
```

### Typography
```
Headers:        Inter/SF Pro, 600 weight
Body:           Inter/SF Pro, 400 weight
Code/traces:    JetBrains Mono / Fira Code, 400 weight
Node labels:    12px uppercase, letter-spacing 0.05em
```

### Animations
- Nodes appear one at a time with a fade-in + slide-down (200ms each)
- Connection lines draw themselves between nodes (CSS animation)
- Tool call nodes pulse briefly when "executing"
- Observation nodes expand with a typewriter effect
- "Autoplay" button plays the entire trace like a presentation
- User can click any node to jump to that step

---

## Component Breakdown

### 1. TaskSelector (left rail)
- List of 10 tasks with icons and difficulty badges
- Category labels: "Incident Triage", "Spec Audit", etc.
- Click to load task
- Active task highlighted

### 2. ModelTabs (below task selector or above trace)
- Three tabs: BASE | SFT | GRPO
- Color-coded with model accent colors
- Badge showing verdict: ❌ FAIL | ⚠️ PARTIAL | ✅ CORRECT
- Click to switch trace

### 3. ReasoningFlowchart (center stage — the star)
- Vertical flow of nodes connected by lines
- Each node type has distinct visual treatment
- Nodes are expandable (click to show full content)
- Collapsed view shows just the decision/action summary
- Step counter on the left margin: Step 1, Step 2, ...
- Time indicator (simulated): "+0.8s", "+2.1s" between steps

### 4. TracePanel (below flowchart, collapsible)
- Raw XML trace in syntax-highlighted code view
- `<think>` blocks in blue
- `<tool_call>` blocks in amber
- `<observation>` blocks in green
- `<answer>` block in bright green
- Line numbers

### 5. VerdictBar (bottom of trace area)
- Horizontal bar showing metrics:
  - Correct/Incorrect (with icon)
  - Tool calls used vs optimal
  - Steps taken
  - Restraint score
  - Key behaviors detected: "Cited spec rule", "Verified before answering", "Recovered from error"

### 6. ComparisonView (optional toggle)
- Side-by-side 3-column view showing BASE | SFT | GRPO for the same task
- Flowcharts rendered smaller but synchronized
- Differences highlighted (red for base failures, amber for SFT issues, green for GRPO wins)

---

## Tech Stack
- **Frontend:** Vanilla JS + CSS (no framework — keep it simple and fast)
- **Backend:** FastAPI (already built in playground/app.py)
- **Data:** Hardcoded traces in JSON (tooltune/simulators.py or JSON files)
- **Deployment:** `uvicorn playground.app:app --port 8000`
- **No GPU, no model, no external dependencies**

---

## File Structure
```
playground/
├── app.py                  # FastAPI app
├── routes.py               # API endpoints
├── agent.py                # Agent runner (demo mode)
├── models.py               # Pydantic models
├── data.py                 # Data loading
├── static/
│   ├── index.html          # Main SPA
│   ├── css/
│   │   └── style.css       # Full design system
│   └── js/
│       ├── app.js          # Main controller
│       ├── flowchart.js    # Reasoning flowchart renderer
│       ├── trace.js        # Raw trace viewer
│       └── verdict.js      # Verdict bar logic
└── data/
    └── v2_traces.json      # All hardcoded traces (3 models × 10 tasks)
```

---

## API Endpoints

```
GET  /api/tasks              → list of 10 tasks with metadata
GET  /api/traces/:task/:model → full trace for a task+model combo
GET  /api/showcase           → all tasks with all 3 model traces
GET  /api/health             → {"mode": "demo", "version": "2.0"}
```

---

## What Makes This Demo Land

1. **The flowchart is the hero.** Not the chat. Not the code. The visual reasoning chain.
2. **Base model traces are viscerally broken.** Raw JSON output, no tools executed, no answer. It's obvious the model can't do the task.
3. **SFT traces show competence with waste.** Correct format, tools execute, but too many calls, generic reasoning, sometimes wrong conclusions.
4. **GRPO traces look like a senior engineer.** Targeted queries, cites evidence, follows runbook criteria, knows when to stop. Uses 3-4 tools when SFT uses 5-6.
5. **Restraint tasks are the mic drop.** "What is O(1) lookup?" — Base rambles, SFT searches docs, GRPO says "O(1)" with zero tools. That single comparison tells the whole story.
6. **The autoplay feature** lets you present this like a slide deck. Click play, watch the agent think step by step, narrate over it.

---

## Build Order
1. Create v2_traces.json with all 30 hardcoded traces (10 tasks × 3 models)
2. Build the flowchart renderer (flowchart.js)
3. Build the layout (index.html + style.css)
4. Wire up task selection + model tabs
5. Add the verdict bar
6. Add autoplay animation
7. Polish: comparison view, responsive, dark mode
