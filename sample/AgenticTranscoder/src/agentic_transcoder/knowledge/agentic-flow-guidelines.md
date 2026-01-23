# Agentic Flow Coding Guidelines

This document defines the **mandatory** code patterns for generated Agentic Flow projects.

---

## Reference Materials

Documentation and source code to reference when generating code.

### Documentation (docs/en/)

| Path | Why to Read |
|------|-------------|
| `getting-started/first-flow.md` | Understand Flow basics, phase() usage, Runner's role |
| `concepts/phase.md` | Check phase() options (persist, label), nesting rules, event firing |
| `concepts/flow-runner.md` | Understand Runner API details, handler injection, session management |

### Source Code (src/agentic_flow/)

| File | Why to Read |
|------|-------------|
| `__init__.py` | Verify public API (Agent, Runner, phase, reasoning) definitions |
| `agent.py` | Understand Agent class implementation, model_settings, tools types |
| `phase.py` | Understand phase() context manager implementation, event firing timing |

### Intent

- **docs/**: Learn features and recommended patterns provided by Agentic Flow
- **src/**: Resolve ambiguities in documentation from implementation
- Reference both for accurate code generation

---

## Required Imports

All generated code MUST use Agentic Flow imports:

```python
from agentic_flow import Agent, Runner, phase
```

NEVER use:
- `from openai import OpenAI` (direct SDK)
- `from agents import Agent, Runner` (AgentBuilder)

---

## Agent Definition

```python
# agent_specs.py
from agentic_flow import Agent

assistant = Agent(
    name="assistant",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
)
```

Rules:
- Use `Agent` from `agentic_flow`
- Model MUST be `"gpt-5.2"` (see Model Normalization below)
- No manual OpenAI client creation

### Model Normalization

**All models in source code are normalized to `gpt-5.2`.**

This is an intentional transformation, not a bug:

| Source Model | Transformed To |
|--------------|----------------|
| `gpt-4.1` | `gpt-5.2` |
| `gpt-4.1-mini` | `gpt-5.2` |
| `gpt-4o` | `gpt-5.2` |
| `gpt-4o-mini` | `gpt-5.2` |
| Any other model | `gpt-5.2` |

Reflector: Do NOT flag model changes as issues. This is project standard.

---

## Flow Definition

```python
# flow.py
from agentic_flow import Runner, phase
from .agents import assistant

async def conversation(message: str) -> str:
    """Main conversation flow."""
    async with phase("Response", persist=True):
        return await assistant(message).stream()

runner = Runner(flow=conversation)
```

Rules:
- Use `async with phase("Name", persist=True)` for the outermost phase
- Use `await agent(message).stream()` for agent calls
- Export `runner = Runner(flow=...)`

---

## Server Definition

Generated projects use ChatKitServer for frontend integration. See `chatkit-integration.md` for the full pattern.

```python
# server.py - Simplified structure
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from agentic_flow import Runner
from agentic_flow.chatkit import run_with_chatkit_context
from chatkit.server import ChatKitServer

from flow import chat_flow
from store import SQLiteStore

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AppServer(ChatKitServer):
    async def respond(self, thread, item, context):
        # Extract user message, create session, run flow
        ...

server = AppServer()

@app.post("/chatkit")
async def chatkit_endpoint(request: Request):
    # Process ChatKit protocol
    ...

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Rules:
- Use FastAPI with CORS middleware
- Inherit from `ChatKitServer`
- Provide `/chatkit` and `/health` endpoints
- Use `run_with_chatkit_context` for streaming

---

## Project Structure

```
project_name/
├── __init__.py
├── agent_specs.py     # Agent definitions (NOT agents.py)
├── flow.py            # Flow with phase() and Runner
├── server.py          # FastAPI server (ChatKitServer)
├── store.py           # SQLiteStore for thread persistence
├── pyproject.toml     # Dependencies
├── frontend/          # React + ChatKit UI
└── tests/
    ├── test_flow.py
    └── test_server.py
```

### CRITICAL: File Naming

**NEVER name the agent file `agents.py`.**

The OpenAI Agents SDK uses `agents` as its module name. If you create `agents.py` in your project, Python will import your file instead of the SDK, causing circular import errors:

```python
# WRONG: agents.py conflicts with SDK
# File: agents.py
from agentic_flow import Agent  # ImportError: circular import

# CORRECT: Use agent_specs.py
# File: agent_specs.py
from agentic_flow import Agent  # Works correctly
```

**Why `agent_specs.py`?**
- Clear that it contains agent specifications
- Avoids collision with `agents.py` SDK module
- Shorter and cleaner than `builder_agents.py`

---

## pyproject.toml

Generated projects are placed in `workspace/{project}_af/` under `sample/AgenticTranscoder/`.
The relative path to Agentic Flow root from there is `../../../..` (4 levels up).

```toml
[project]
name = "chat-agent"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "agentic-flow",
    "openai-agents>=0.3.2",
    "fastapi>=0.115",
    "uvicorn>=0.32",
    "python-dotenv>=1.0",
    "chatkit",
    "httpx>=0.27",
]

# Path: workspace/{project}_af → workspace → agentic_transcoder → sample → Agentic Flow
[tool.uv.sources]
agentic-flow = { path = "../../../..", editable = true }

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = [".", "../../../../src"]
testpaths = ["tests"]
```

Key points:
- `agentic-flow` path is relative to workspace location
- `pythonpath` includes Agentic Flow src for imports
- All ChatKit dependencies included

---

## Frontend Setup

### CRITICAL: Clean Install Required

When copying frontend/ from template, **always do a clean npm install**:

```bash
cd workspace/frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

**Why?**

Copying `node_modules/` from another location causes path resolution errors:

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../node_modules/dist/node/cli.js'
```

This happens because:
1. node_modules contains hardcoded paths from the original location
2. Symlinks in `.bin/` point to wrong locations
3. Some packages cache absolute paths

**Template Rule**: Never include `node_modules/` in template. Only include:
- `package.json`
- `src/`
- `vite.config.ts`
- Other source files

### Frontend Directory Structure

```
frontend/
├── package.json        # Dependencies (no lock file in template)
├── vite.config.ts      # Vite configuration
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx        # Entry point
    ├── index.css
    └── components/
        └── ChatKitPanel.tsx
```

---

## Forbidden Patterns

NEVER generate:

```python
# WRONG: Direct OpenAI SDK
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)

# WRONG: AgentBuilder imports
from agents import Agent, Runner, trace

# WRONG: Manual tracing
with trace_span("..."):
    ...

# WRONG: Synchronous flow
def run_workflow(...):  # Must be async
    ...
```

---

## Allowed Transformations

These differences between source and output are **intentional and correct**:

| Transformation | Reason |
|----------------|--------|
| Model → `gpt-5.2` | Project standard model |
| `store=True` removed | Session handles persistence |
| `trace()` removed | Not needed in Agentic Flow |
| `conversation_history` removed | Session handles automatically |
| Defensive fallbacks added | Coder may add safety patterns |

**Reflector**: These are NOT bugs. Do not create todos for these differences.

---

## User Guidelines

If a `guidelines.md` file exists in the workspace, its contents should also be followed.
User guidelines supplement (but do not override) these Agentic Flow guidelines.

---

# Coding Standards

These standards apply to ALL generated code. Violations are detected by `/refactoring`.

## Naming Rules

| Rule | Wrong | Correct |
|------|-------|---------|
| No private prefix | `_run_spinner()` | `run_spinner()` |
| No private variables | `self._state` | `self.state` |
| No private parameters | `_handler=handler` | `handler=handler` |
| Consistent verbs | `get_` vs `fetch_` | Pick one, use everywhere |

## Structural Rules

| Rule | What to Avoid |
|------|---------------|
| No dead code | Unused functions, unreachable branches |
| No unused imports | Remove after refactoring |
| No premature abstraction | ABC with single implementation |
| No future reservations | `pass`-only methods, TODO stubs |
| No duplicate logic | Extract common patterns |
| No decorative comments | Code should be self-explanatory |

## Comment Rules

```python
# ❌ Wrong: Decorative separators (code already shows structure)
# ═══════════════════════════════════════════════════════════════
# SECTION: Configuration
# ═══════════════════════════════════════════════════════════════

# ❌ Wrong: Obvious comments
i += 1  # Increment i

# ✅ Correct: Intent comments (explain WHY, not WHAT)
# Retry limit prevents infinite loops on transient failures
MAX_RETRIES = 3
```

## Type Annotations

All functions MUST have type annotations:

```python
# ❌ Wrong
def run_pytest(output_dir):
    ...

# ✅ Correct
async def run_pytest(output_dir: str) -> RunResult:
    ...
```

## Pydantic for LLM Output

Never parse LLM text manually. Use `.output_type()`:

```python
# ❌ Wrong
result = await critic(prompt).stream()
verdict = parse_verdict(result)  # Fragile

# ✅ Correct
verdict = await critic(prompt).output_type(Verdict).stream()
```

## Prompt Templates

Templates at module level, not inline:

```python
# ❌ Wrong: Inline templates make flow unreadable
await coder(f"""GENERATE {output_dir}
frontend={frontend}
{plan}
""").stream()

# ✅ Correct: Templates in prompts.py
prompt = GENERATE_PROMPT.format(output_dir=output_dir, frontend=frontend, plan=plan)
await coder(prompt).stream()
```

## Detection Categories

Run `/refactoring` to audit:

| ID | Category |
|----|----------|
| D1 | Dead Code |
| D2 | Unused Imports |
| D3 | Premature Abstraction |
| D4 | Future Reservations |
| D5 | Duplicate Logic |
| D6 | Contradictory Implementation |
| D7 | Inconsistent Naming |
| D8 | Private Prefix |

---

# Intent-First Writing

State intent before implementation in all code and documentation.

## Where to Apply

| Context | How |
|---------|-----|
| Flow/Phase | Docstring explaining purpose |
| Agent instructions | Lead with purpose, then details |
| Prompt templates | Comment stating expected outcome |
| Function docstrings | Intent first, then parameters |

## Example

```python
async def transcode(source_code: str, output_dir: str) -> Verdict:
    """Transform AgentBuilder code to Agentic Flow project.

    Intent: Take legacy AgentBuilder code and produce a modern,
    well-tested Agentic Flow project with identical behavior.
    """
    async with phase("Plan"):
        analysis = await analyzer(source_code).stream()
        plan = await planner(prompt).stream()
```

## Why It Matters

- **Maintainability**: Future readers understand purpose
- **Debugging**: Intent reveals what should happen
- **Review**: Verify implementation matches intent
- **AI Agents**: LLMs work better with clear intent context
