"""AgentBuilder source code for WebSearch Agent.

This is the BEFORE format that Transcoder transforms into Agentic Flow.
Pattern: single-agent-with-tools (WebSearchTool)
"""

from agents import WebSearchTool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

# Tool definitions
web_search_preview = WebSearchTool(
    user_location={
        "type": "approximate",
        "country": None,
        "region": None,
        "city": None,
        "timezone": None,
    },
    search_context_size="medium",
)

websearch = Agent(
    name="WebSearch",
    instructions="""You are a helpful assistant designed to generate a Web Search Engine. Construct all required components, including search query understanding, result retrieval, ranking, and summarization of results. Ensure your outputs allow a user to search for information on the web, retrieve accurate and relevant results, and present those results in a clear, concise, and informative manner. Provide explanations of your reasoning process before delivering the final list of search results or summaries.

# Steps

- Receive a user-posed question or search query.
- Analyze and clarify the user query as needed.
- Identify keywords and search intent.
- Retrieve and rank relevant search results as if searching the web.
- Summarize results and provide concise, informative responses.
- Justify your choices and ranking of results with reasoning prior to showing conclusions.

# Output Format

Output each search with:
- A brief explanation (2-3 sentences) of your reasoning and keyword extraction.
- A JSON list of 3-5 results, each with:
  - "title": [Page Title]
  - "snippet": [Short Summary]
  - "url": [Placeholder or realistic, e.g. "https://example.com/article"]
""",
    model="gpt-5.2",
    tools=[web_search_preview],
    model_settings=ModelSettings(
        store=True,
        reasoning=Reasoning(effort="low", summary="auto"),
    ),
)


class WorkflowInput(BaseModel):
    input_as_text: str


async def run_workflow(workflow_input: WorkflowInput):
    with trace("WebSearch workflow"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": workflow["input_as_text"]}],
            }
        ]
        result = await Runner.run(
            websearch,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={"__trace_source__": "agent-builder"}
            ),
        )
        conversation_history.extend(
            [item.to_input_item() for item in result.new_items]
        )
