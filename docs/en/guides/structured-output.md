# Structured Output

AF supports typed outputs using Pydantic models, enabling IDE completion and type checking.

## Basic Typed Output

Define a Pydantic model and pass it to `output_type`:

```python
from pydantic import BaseModel
import agentic_flow as af

class Analysis(BaseModel):
    sentiment: str
    confidence: float
    keywords: list[str]

analyzer = af.Agent(
    name="analyzer",
    instructions="Analyze the sentiment of the given text.",
    model="gpt-5.2",
    output_type=Analysis,  # Typed output
)

result: Analysis = await analyzer("I love this product!")
print(result.sentiment)     # "positive"
print(result.confidence)    # 0.95
print(result.keywords)      # ["love", "product"]
```

## Type Parameter

`af.Agent[T]` is generic. `T` is determined by `output_type`:

```python
# T = str (default)
assistant: af.Agent[str] = af.Agent(name="assistant", instructions="...", model="gpt-5.2")

# T = Analysis
analyzer: af.Agent[Analysis] = af.Agent(
    name="analyzer",
    instructions="...",
    output_type=Analysis,
    model="gpt-5.2",
)
```

`ExecutionSpec[T]` carries the same type:

```python
spec: ExecutionSpec[Analysis] = analyzer("text")
result: Analysis = await spec
```

## Nested Models

Complex structures work as expected:

```python
class Citation(BaseModel):
    source: str
    url: str
    relevance: float

class ResearchResult(BaseModel):
    summary: str
    key_findings: list[str]
    citations: list[Citation]
    confidence: float

researcher = af.Agent(
    name="researcher",
    instructions="Research the topic and provide structured findings.",
    output_type=ResearchResult,
    model="gpt-5.2",
)

result: ResearchResult = await researcher("quantum computing").stream()
for citation in result.citations:
    print(f"{citation.source}: {citation.url}")
```

## Enum Fields

Use enums for constrained values:

```python
from enum import Enum

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class SentimentAnalysis(BaseModel):
    sentiment: Sentiment
    confidence: float

analyzer = af.Agent(
    name="analyzer",
    instructions="Classify sentiment.",
    output_type=SentimentAnalysis,
    model="gpt-5.2",
)

result = await analyzer("Great product!")
if result.sentiment == Sentiment.POSITIVE:
    print("User is happy!")
```

## Optional Fields

Handle optional data:

```python
class UserProfile(BaseModel):
    name: str
    email: str | None = None
    age: int | None = None

extractor = af.Agent(
    name="extractor",
    instructions="Extract user information from text.",
    output_type=UserProfile,
    model="gpt-5.2",
)

result = await extractor("My name is Alice, I'm 30.")
print(result.name)   # "Alice"
print(result.email)  # None
print(result.age)    # 30
```

## Chaining Typed Agents

Pass structured output between agents:

```python
class Triage(BaseModel):
    category: str
    priority: int
    reason: str

class Response(BaseModel):
    message: str
    action_items: list[str]

triager = af.Agent(
    name="triager",
    instructions="Categorize and prioritize the request.",
    output_type=Triage,
    model="gpt-5.2",
)

responder = af.Agent(
    name="responder",
    instructions="Respond based on the triage.",
    output_type=Response,
    model="gpt-5.2",
)

async def support_flow(message: str) -> str:
    async with af.phase("Triage"):
        triage: Triage = await triager(message).stream()

    async with af.phase("Response", persist=True):
        response: Response = await responder(
            f"Category: {triage.category}\n"
            f"Priority: {triage.priority}\n"
            f"Reason: {triage.reason}\n"
            f"Original: {message}"
        ).stream()

    return response.message
```

## Validation

Pydantic validates output automatically:

```python
class StrictAnalysis(BaseModel):
    score: int  # Must be integer
    category: str  # Required

# If the model returns invalid data, Pydantic raises ValidationError
```

## Streaming with Typed Output

Streaming works with typed output — you get the final parsed result:

```python
result: Analysis = await analyzer("text").stream()
# result is Analysis, not str
```

## SDK Pass-Through

`output_type` is passed directly to the SDK:

```python
# AF
af.Agent(name="...", instructions="...", output_type=MyModel, model="gpt-5.2")

# Equivalent SDK call
agents.Agent(name="...", instructions="...", output_type=MyModel)
```

AF doesn't modify or wrap the SDK's structured output handling.

---

Next: [Testing](testing.md) :material-arrow-right:
