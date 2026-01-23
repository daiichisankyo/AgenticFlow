# AF - Agentic Flow Framework

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-online-green.svg)](https://daiichisankyo.github.io/AgenticFlow/)

**Write agent workflows like regular Python code.**

```python
async def research_flow(query: str) -> str:
    # Internal thinking - not saved to session
    async with af.phase("Research"):
        findings = await researcher(query).stream()

    # persist=True saves the final response to session
    async with af.phase("Analysis", persist=True):
        return await analyst(findings).stream()
```

No graphs. No YAML. No state machines. Just Python.

---

## ✨ Why the agentic flow approach?

OpenAI Agents SDK is powerful, but multi-agent workflows get verbose fast:

<table>
<tr>
<th>Pure SDK (~50 lines)</th>
<th>AF (~15 lines)</th>
</tr>
<tr>
<td>

```python
# Manual orchestration
result1 = await Runner.run(
    researcher, messages
)
research = result1.final_output

result2 = await Runner.run(
    analyst,
    [{"role": "user", "content": research}]
)
# No streaming, no phases,
# no session management...
```

</td>
<td>

```python
async def my_flow(query: str) -> str:
    # Internal thinking - not saved to session
    async with af.phase("Research"):
        research = await researcher(query).stream()

    # persist=True saves the final response to session
    async with af.phase("Analysis", persist=True):
        return await analyst(research).stream()

runner = af.Runner(flow=my_flow)
result = await runner(query)
```

</td>
</tr>
</table>

**The agentic flow approach gives you:**

- **Callable agents** - `agent(prompt).stream()` like PyTorch modules
- **Workflow phases** - Structure and visibility for multi-step processes
- **Automatic streaming** - Real-time output with zero configuration
- **Session injection** - Conversation persistence without global state
- **ChatKit integration** - Production-ready UI streaming

---

## 📋 Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- OpenAI API key

---

## 📦 Installation

### With uv (recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add AF to your project
uv add git+https://github.com/daiichisankyo/AgenticFlow.git
```

### With pip (alternative)

```bash
pip install git+https://github.com/daiichisankyo/AgenticFlow.git
```

### Set your API key

Create a `.env.local` file from the example:

```bash
cp .env.example .env.local
# Edit .env.local and add your OpenAI API key
```

Or set it directly in your environment:

```bash
export OPENAI_API_KEY="your-api-key"
```

---

## 🚀 Quickstart Code

```python
import agentic_flow as af

# Define agents
researcher = af.Agent(
    name="researcher",
    instructions="Research the topic thoroughly.",
    model="gpt-5.2",
)

writer = af.Agent(
    name="writer",
    instructions="Write clear, engaging content.",
    model="gpt-5.2",
)

# Define workflow as a regular async function
async def blog_flow(topic: str) -> str:
    # Internal thinking - not saved to session
    async with af.phase("Research"):
        research = await researcher(topic).stream()

    # persist=True saves the final response to session
    async with af.phase("Writing", persist=True):
        return await writer(f"Write about: {research}").stream()

# Run
runner = af.Runner(flow=blog_flow)
article = await runner("quantum computing")
```

---

## 💡 Core Concepts

AF is built on three primitives:

- **Agent** - Callable wrapper around SDK Agent. Returns `ExecutionSpec` for deferred execution.
- **ExecutionSpec** - Lazy specification configured with modifiers (`.stream()`, `.isolated()`, `.silent()`, `.max_turns()`)
- **phase** - Context manager for workflow boundaries. Controls session persistence with `persist=True`.

For details, see [Concepts](https://daiichisankyo.github.io/AgenticFlow/concepts/).

---

## 🔄 Patterns

### Sequential Pipeline

```python
async def pipeline(input: str) -> str:
    # Internal processing - not saved to session
    async with af.phase("Extract"):
        entities = await extractor(input).stream()

    async with af.phase("Enrich"):
        enriched = await enricher(entities).stream()

    # persist=True saves the final response to session
    async with af.phase("Format", persist=True):
        return await formatter(enriched).stream()
```

### Conditional Branching

```python
async def smart_process(data: str) -> str:
    # Internal classification - not saved to session
    async with af.phase("Classify"):
        category = await classifier(data).stream()

    # persist=True on whichever branch returns the final response
    if "technical" in category:
        async with af.phase("Technical Analysis", persist=True):
            return await tech_analyst(data).stream()
    else:
        async with af.phase("General Summary", persist=True):
            return await summarizer(data).stream()
```

### Iterative Refinement

```python
async def refine(draft: str) -> str:
    for i in range(3):
        # Internal review - not saved to session
        async with af.phase(f"Review #{i+1}"):
            feedback = await critic(draft).stream()

        if "APPROVED" in feedback:
            return draft

        # Internal revision - not saved to session
        async with af.phase(f"Revise #{i+1}"):
            draft = await reviser(f"{draft}\n\nFeedback: {feedback}").stream()

    # Note: This pattern returns the draft directly without session save.
    # Add a final phase with persist=True if you need to save the result.
    return draft
```

### Parallel Execution

```python
import asyncio

async def parallel_analysis(data: str) -> dict:
    # persist=True saves the final response to session
    # isolated() runs each agent without shared context
    async with af.phase("Parallel Analysis", persist=True):
        results = await asyncio.gather(
            sentiment_agent(data).isolated(),
            entity_agent(data).isolated(),
            summary_agent(data).isolated(),
        )

    return {
        "sentiment": results[0],
        "entities": results[1],
        "summary": results[2],
    }
```

---

## 🔌 ChatKit Integration

```python
from pathlib import Path
import agentic_flow as af
from agents import SQLiteSession
from chatkit.server import ChatKitServer
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# Persist data in a known location
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI()


class MyServer(ChatKitServer):
    async def respond(self, thread, item, context):
        user_message = item.content[0].text if item else ""
        session = SQLiteSession(
            session_id=thread.id,
            db_path=str(DATA_DIR / "chat.db"),
        )
        runner = af.Runner(flow=my_flow, session=session)
        async for event in af.chatkit.run_with_chatkit_context(
            runner, thread, self.store, context, user_message
        ):
            yield event


server = MyServer(store)


@app.post("/chatkit")
async def chatkit_endpoint(request: Request):
    result = await server.process(await request.body(), {})
    return StreamingResponse(result, media_type="text/event-stream")
```

Each `af.phase()` automatically creates workflow boundaries for proper reasoning display.

---

## 🎮 Try the Demos

First, install sample dependencies:

```bash
uv sync --group sample
```

### CLI Quickstart

Experience the core concepts interactively:

```bash
uv run --group sample python sample/quickstart.py
```

Demonstrates:
1. Flow & Runner separation
2. Declaration vs execution (`agent(prompt)` returns spec, `await` executes)
3. Modifiers (`.stream()`, `.isolated()`, `.silent()`, `.max_turns()`)
4. Typed output with Pydantic

### Guide TUI

Interactive Textual UI that answers questions about AF:

```bash
uv run --group sample python -m sample.guide.cli
```

### Guide Web Server (FastAPI + ChatKit)

Start the backend API:

```bash
uv run --group sample uvicorn sample.guide.server:app --reload --port 8000
```

### Guide Frontend (Next.js + ChatKit)

In a separate terminal:

```bash
cd sample/guide/frontend
npm install
npm run dev
```

Visit http://localhost:3000

---

## 📚 Documentation

- **[Concepts](https://daiichisankyo.github.io/AgenticFlow/concepts/)** - Call-Spec Discipline, ExecutionSpec, Phase, Modifiers
- **[API Reference](https://daiichisankyo.github.io/AgenticFlow/reference/api/)** - Complete API documentation
- **[Context Resolution](https://daiichisankyo.github.io/AgenticFlow/context-resolution/)** - Advanced context management

For the complete documentation site, visit [https://daiichisankyo.github.io/AgenticFlow/](https://daiichisankyo.github.io/AgenticFlow/)

---

## Contributing

```bash
# Clone and setup
git clone https://github.com/daiichisankyo/AgenticFlow.git
cd AgenticFlow
uv sync --group dev

# Run tests
uv run pytest

# Run linter
uv run ruff check src/
```

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linter
5. Submit a pull request

---

## 📄 License

MIT - see [LICENSE](LICENSE) for details.
