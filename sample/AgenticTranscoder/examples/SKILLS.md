# Agentic Flow Skills Catalog

## Purpose

Transformation patterns (SKILLs) for AgentBuilder→Agentic Flow conversion.

Coder workflow:
1. Analyze input code - identify ALL features (tools, guardrails, routing, etc.)
2. Load ALL matching skills using `load_skill(directory_name)`
3. Compose patterns from multiple skills if needed
4. Transform using combined BEFORE/AFTER examples

Skills are composable - complex inputs may require multiple skills combined.

---

## Available Skills

| Skill | Location | When to Use |
|-------|----------|-------------|
| single-agent-chat | `examples/basic/` | Single Agent, no tools, simple request-response |
| single-agent-with-tools | `examples/websearch/` | Single Agent with WebSearchTool or other SDK tools |
| single-agent-with-guardrails | `examples/guardrail/` | Single Agent with openai-guardrails integration |
| classify-and-route | `examples/router/` | Multiple Agents with conditional routing |

---

## SKILL Structure

Each SKILL directory contains:

| File | Role |
|------|------|
| `source.py` | BEFORE: AgentBuilder format (input example) |
| `agent_specs.py` | AFTER: Agentic Flow agents (output example) |
| `flow.py` | AFTER: Agentic Flow flow (output example) |
| `server.py` | ChatKit server (standard, no edit needed) |
| `store.py` | SQLite store (standard, no edit needed) |
| `tests/` | Test files |

---

## Selection Algorithm

```
ANALYZE input source code:

1. Check for guardrails FIRST (independent of agent count)
   - Has guardrails_config or run_guardrails?
   - Has Jailbreak, Moderation, Contains PII?
   - Uses guardrails.runtime imports?
   → YES: load_skill("guardrail") - ALWAYS load if present

2. Count Agent() definitions
   - 1 agent → step 3
   - 2+ agents → step 4

3. Check for tools (single agent)
   - Has WebSearchTool or SDK tools? → load_skill("websearch")
   - No tools? → load_skill("basic")

4. Check for classification pattern (multiple agents)
   - Has output_type with category field?
   - Has if/elif branching on category?
   → YES: load_skill("router")
   → NO: Consider custom pattern

5. Compose loaded skills (see Composition Rules below)
```

**Important**: Guardrails check happens FIRST and independently.
An input with guardrails + routing requires BOTH skills loaded.

---

## Composition Rules

When multiple features are detected, load ALL matching skills and compose them.

### Composition Priority

Apply patterns in this order:

| Priority | Feature | Where to Apply |
|----------|---------|----------------|
| 1 | Guardrails | `guardrails_config.json` + `@input_guardrail` in agent_specs.py |
| 2 | Guardrails | Attach to FIRST agent receiving user input |
| 3 | Routing | Classify phase → Response phase in flow.py |
| 4 | Tools | `tools=[...]` on appropriate agents |
| 5 | Model settings | `reasoning("low"\|"medium"\|"high")` |

### Example: Guardrails + Router

Input has: `guardrails_config` + `classify` agent + `cook`/`meteorologist` agents

**Step 1**: Load both skills
```
load_skill("guardrail")  → Learn openai-guardrails pattern
load_skill("router")      → Learn Classify/Response phase pattern
```

**Step 2**: Compose in agent_specs.py
```python
# From guardrails skill: single @input_guardrail with openai-guardrails
from guardrails.runtime import run_guardrails, load_config_bundle, instantiate_guardrails

@input_guardrail
async def guardrails_check(ctx, agent, input):
    config = load_config_bundle(CONFIG_PATH)
    results = await run_guardrails(
        ctx={"guardrail_llm": AsyncOpenAI()},
        data=text,
        media_type="text/plain",
        guardrails=instantiate_guardrails(config),
    )
    return GuardrailFunctionOutput(tripwire_triggered=any(r.tripwire_triggered for r in results))

# From router skill: multiple agents
# Attach guardrails to classify (first to receive input)
classify = Agent(
    name="classify",
    input_guardrails=[guardrails_check],  # ← Composed
    output_type=ClassifyResult,
    ...
)

cook = Agent(name="cook", ...)
meteorologist = Agent(name="meteorologist", ...)
```

**Step 3**: Compose in flow.py
```python
# From router skill: phase structure
# Guardrails run automatically via classify's input_guardrails
async def router_flow(user_message: str) -> str:
    async with phase("Classify"):
        classification = await classify(user_message).stream()

    if classification.category == "cook":
        async with phase("Response", persist=True):
            return await cook(user_message).stream()
    ...
```

### Example: Guardrails + Tools

Input has: `guardrails_config` + `WebSearchTool`

```python
# Composed agent_specs.py
from guardrails.runtime import run_guardrails, load_config_bundle, instantiate_guardrails

@input_guardrail
async def guardrails_check(ctx, agent, input): ...

chat_agent = Agent(
    name="chat",
    tools=[WebSearchTool(...)],  # From websearch skill
    input_guardrails=[guardrails_check],  # From guardrails skill
    ...
)
```

### Key Principle

**Skills are patterns to understand, not code to copy.**

When composing:
1. Understand the INTENT of each skill's pattern
2. Merge the patterns logically
3. Guardrails always attach to the first agent receiving user input
4. Flow structure follows the most complex pattern (router > single agent)

---

## Key Transformations (All SKILLs)

| AgentBuilder | Agentic Flow |
|--------------|-------------|
| `Runner.run(agent, input=[...])` | `await agent(message).stream()` |
| `ModelSettings(store=True)` | Remove (auto-managed by Session) |
| `conversation_history` | Remove (auto-managed by Session) |
| `trace()`, `RunConfig` | Remove |
| `from agents import Agent` | `from agentic_flow import Agent, reasoning` |

---

## Adding New Skills

1. Create `examples/{skill-name}/` directory
2. Add `source.py` - AgentBuilder format input
3. Add `agent_specs.py` - Agentic Flow agents
4. Add `flow.py` - Agentic Flow flow
5. Add standard files (server.py, store.py, tests/)
6. Add entry to table above

---

## Reference

For detailed transformation rules, see `knowledge/transformation-rules.md`.
