# Installation

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- OpenAI API key

## Install with uv (recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that handles dependencies and virtual environments automatically.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add AF to your project
uv add git+https://github.com/daiichisankyo/AgenticFlow.git
```

## Install with pip (alternative)

```bash
pip install git+https://github.com/daiichisankyo/AgenticFlow.git
```

This installs AF and its dependencies, including the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/).

## Set up your API key

AF uses the OpenAI Agents SDK, which requires an API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

Or create a `.env` file:

```
OPENAI_API_KEY=your-api-key
```

And load it in your code:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Development Setup

To contribute or run samples locally:

```bash
# Clone the repository
git clone https://github.com/daiichisankyo/AgenticFlow.git
cd AgenticFlow

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run linter
uv run ruff check src/

# Build documentation
uv sync --group docs
uv run mkdocs serve
```

### Project Structure

```
AgenticFlow/
├── pyproject.toml      # Package config + dependency groups
├── uv.lock             # Lock file
├── src/agentic_flow/   # Library source
├── tests/              # Test suite
└── sample/             # Sample applications
```

### Dependency Groups

| Group | Purpose | Command |
|-------|---------|---------|
| `dev` | Testing, linting | `uv sync --group dev` |
| `docs` | Documentation | `uv sync --group docs` |
| `sample` | Sample apps | `uv sync --group sample` |

Run sample applications:

```bash
uv sync --group sample
uv run python -m sample.guide.cli
```

## Verify installation

```python
import agentic_flow as af

assistant = af.Agent(
    name="assistant",
    instructions="Say hello.",
    model="gpt-5.2",
)

async def greet(message: str) -> str:
    return await assistant(message)

runner = af.Runner(flow=greet)
result = runner.run_sync("Hi!")
print(result)
```

If you see a greeting, you're ready to go.

---

Next: [Quickstart](quickstart.md) :material-arrow-right:
