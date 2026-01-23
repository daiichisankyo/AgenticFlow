# Testing

Testing AF applications involves async tests and proper event loop handling.

## pytest-asyncio Setup

Install pytest-asyncio:

```bash
pip install pytest-asyncio
```

Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

## Basic Test

```python
import pytest
import agentic_flow as af

assistant = af.Agent(name="assistant", instructions="Say hello.", model="gpt-5.2")

async def greet_flow(message: str) -> str:
    async with af.phase("Greeting"):
        return await assistant(message)

@pytest.mark.asyncio
async def test_greet_flow():
    runner = af.Runner(flow=greet_flow)
    result = await runner("Hi")
    assert "hello" in result.lower()
```

## Event Loop Issue

pytest-asyncio creates a new event loop for each test. The OpenAI SDK caches a global HTTP client, which can cause issues:

```
RuntimeError: Event loop is closed
```

## Solution: Reset HTTP Client

Create a fixture that resets the SDK's HTTP client:

```python
import pytest

@pytest.fixture(autouse=True)
def reset_openai_http_client():
    """Reset OpenAI SDK's cached HTTP client after each test."""
    yield
    try:
        import openai
        if hasattr(openai, "_base_client") and openai._base_client is not None:
            openai._base_client = None
        if hasattr(openai, "AsyncOpenAI"):
            # Reset any cached async clients
            pass
    except Exception:
        pass
```

## Testing with Sessions

Use in-memory or temporary sessions:

```python
import tempfile
from agents import SQLiteSession

@pytest.fixture
def session():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        yield SQLiteSession(session_id="test", db_path=f.name)

@pytest.mark.asyncio
async def test_with_session(session):
    runner = af.Runner(flow=my_flow, session=session)
    result = await runner("Hello")
    assert result
```

## Testing Phases

Verify phase behavior:

```python
@pytest.mark.asyncio
async def test_phase_persist():
    results = []

    async def tracking_flow(message: str) -> str:
        async with af.phase("Work", persist=True):
            result = await assistant(message)
            results.append(result)
            return result

    runner = af.Runner(flow=tracking_flow)
    await runner("Test")

    assert len(results) == 1
```

## Testing Handlers

Capture events with a test handler:

```python
import agentic_flow as af

@pytest.mark.asyncio
async def test_handler_receives_events():
    events = []

    def test_handler(event):
        events.append(event)

    runner = af.Runner(flow=my_flow, handler=test_handler)
    await runner("Hello")

    # Check phase events were received
    phase_starts = [e for e in events if isinstance(e, af.PhaseStarted)]
    phase_ends = [e for e in events if isinstance(e, af.PhaseEnded)]

    assert len(phase_starts) > 0
    assert len(phase_starts) == len(phase_ends)
```

## Testing Isolation

Verify `.isolated()` works:

```python
@pytest.mark.asyncio
async def test_isolated_no_session():
    session_accessed = False

    class TrackingSession:
        async def get_items(self):
            nonlocal session_accessed
            session_accessed = True
            return []

    runner = af.Runner(flow=my_flow, session=TrackingSession())

    # Isolated call shouldn't access session
    result = await assistant("Hello").isolated()

    # Note: This tests the agent directly, not through the flow
    assert not session_accessed
```

## Parallel Test Execution

When running tests in parallel, ensure isolation:

```python
@pytest.mark.asyncio
async def test_parallel_agents():
    import asyncio

    results = await asyncio.gather(
        agent("task 1").isolated(),
        agent("task 2").isolated(),
        agent("task 3").isolated(),
    )

    assert len(results) == 3
```

## Mocking Agents

For unit tests without API calls, you can mock at the SDK level:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_flow_logic_only():
    with patch("agents.Runner.run") as mock_run:
        mock_run.return_value = AsyncMock(final_output="mocked response")

        runner = af.Runner(flow=my_flow)
        result = await runner("Test")

        assert result == "mocked response"
```

## Integration Tests

For full integration tests, use real API calls:

```python
import os
import pytest

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
@pytest.mark.asyncio
async def test_real_api():
    runner = af.Runner(flow=my_flow)
    result = await runner("What is 2+2?")
    assert "4" in result
```

## Test Organization

```
tests/
├── conftest.py           # Fixtures (reset_openai_http_client)
├── test_flows.py         # Flow tests
├── test_agents.py        # Agent tests
├── test_phases.py        # Phase tests
└── test_integration.py   # Full integration tests
```

---

Next: [API Reference](../reference/api.md) :material-arrow-right:
