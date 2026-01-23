from openai import AsyncOpenAI
from types import SimpleNamespace
from guardrails.runtime import load_config_bundle, instantiate_guardrails, run_guardrails
from agents import Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

# Shared client for guardrails and file search
client = AsyncOpenAI()
ctx = SimpleNamespace(guardrail_llm=client)
# Guardrails definitions
guardrails_config = {
  "guardrails": [
    { "name": "Jailbreak", "config": { "model": "gpt-5.2", "confidence_threshold": 0.7 } },
    { "name": "Moderation", "config": { "categories": ["sexual/minors", "hate/threatening", "harassment/threatening", "self-harm/instructions", "violence/graphic", "illicit/violent"] } },
    { "name": "Contains PII", "config": { "block": False, "detect_encoded_pii": True, "entities": ["CREDIT_CARD", "US_BANK_NUMBER", "US_PASSPORT", "US_SSN"] } }
  ]
}
def guardrails_has_tripwire(results):
    return any((hasattr(r, "tripwire_triggered") and (r.tripwire_triggered is True)) for r in (results or []))

def get_guardrail_safe_text(results, fallback_text):
    for r in (results or []):
        info = (r.info if hasattr(r, "info") else None) or {}
        if isinstance(info, dict) and ("checked_text" in info):
            return info.get("checked_text") or fallback_text
    pii = next(((r.info if hasattr(r, "info") else {}) for r in (results or []) if isinstance((r.info if hasattr(r, "info") else None) or {}, dict) and ("anonymized_text" in ((r.info if hasattr(r, "info") else None) or {}))), None)
    if isinstance(pii, dict) and ("anonymized_text" in pii):
        return pii.get("anonymized_text") or fallback_text
    return fallback_text

async def scrub_conversation_history(history, config):
    try:
        guardrails = (config or {}).get("guardrails") or []
        pii = next((g for g in guardrails if (g or {}).get("name") == "Contains PII"), None)
        if not pii:
            return
        pii_only = {"guardrails": [pii]}
        for msg in (history or []):
            content = (msg or {}).get("content") or []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "input_text" and isinstance(part.get("text"), str):
                    res = await run_guardrails(ctx, part["text"], "text/plain", instantiate_guardrails(load_config_bundle(pii_only)), suppress_tripwire=True, raise_guardrail_errors=True)
                    part["text"] = get_guardrail_safe_text(res, part["text"])
    except Exception:
        pass

async def scrub_workflow_input(workflow, input_key, config):
    try:
        guardrails = (config or {}).get("guardrails") or []
        pii = next((g for g in guardrails if (g or {}).get("name") == "Contains PII"), None)
        if not pii:
            return
        if not isinstance(workflow, dict):
            return
        value = workflow.get(input_key)
        if not isinstance(value, str):
            return
        pii_only = {"guardrails": [pii]}
        res = await run_guardrails(ctx, value, "text/plain", instantiate_guardrails(load_config_bundle(pii_only)), suppress_tripwire=True, raise_guardrail_errors=True)
        workflow[input_key] = get_guardrail_safe_text(res, value)
    except Exception:
        pass

async def run_and_apply_guardrails(input_text, config, history, workflow):
    results = await run_guardrails(ctx, input_text, "text/plain", instantiate_guardrails(load_config_bundle(config)), suppress_tripwire=True, raise_guardrail_errors=True)
    guardrails = (config or {}).get("guardrails") or []
    mask_pii = next((g for g in guardrails if (g or {}).get("name") == "Contains PII" and ((g or {}).get("config") or {}).get("block") is False), None) is not None
    if mask_pii:
        await scrub_conversation_history(history, config)
        await scrub_workflow_input(workflow, "input_as_text", config)
        await scrub_workflow_input(workflow, "input_text", config)
    has_tripwire = guardrails_has_tripwire(results)
    safe_text = get_guardrail_safe_text(results, input_text)
    fail_output = build_guardrail_fail_output(results or [])
    pass_output = {"safe_text": (get_guardrail_safe_text(results, input_text) or input_text)}
    return {"results": results, "has_tripwire": has_tripwire, "safe_text": safe_text, "fail_output": fail_output, "pass_output": pass_output}

def build_guardrail_fail_output(results):
    def _get(name: str):
        for r in (results or []):
            info = (r.info if hasattr(r, "info") else None) or {}
            gname = (info.get("guardrail_name") if isinstance(info, dict) else None) or (info.get("guardrailName") if isinstance(info, dict) else None)
            if gname == name:
                return r
        return None
    pii, mod, jb, hal, nsfw, url, custom, pid = map(_get, ["Contains PII", "Moderation", "Jailbreak", "Hallucination Detection", "NSFW Text", "URL Filter", "Custom Prompt Check", "Prompt Injection Detection"])
    def _tripwire(r):
        return bool(r.tripwire_triggered)
    def _info(r):
        return r.info
    jb_info, hal_info, nsfw_info, url_info, custom_info, pid_info, mod_info, pii_info = map(_info, [jb, hal, nsfw, url, custom, pid, mod, pii])
    detected_entities = pii_info.get("detected_entities") if isinstance(pii_info, dict) else {}
    pii_counts = []
    if isinstance(detected_entities, dict):
        for k, v in detected_entities.items():
            if isinstance(v, list):
                pii_counts.append(f"{k}:{len(v)}")
    flagged_categories = (mod_info.get("flagged_categories") if isinstance(mod_info, dict) else None) or []
    
    return {
        "pii": { "failed": (len(pii_counts) > 0) or _tripwire(pii), "detected_counts": pii_counts },
        "moderation": { "failed": _tripwire(mod) or (len(flagged_categories) > 0), "flagged_categories": flagged_categories },
        "jailbreak": { "failed": _tripwire(jb) },
        "hallucination": { "failed": _tripwire(hal), "reasoning": (hal_info.get("reasoning") if isinstance(hal_info, dict) else None), "hallucination_type": (hal_info.get("hallucination_type") if isinstance(hal_info, dict) else None), "hallucinated_statements": (hal_info.get("hallucinated_statements") if isinstance(hal_info, dict) else None), "verified_statements": (hal_info.get("verified_statements") if isinstance(hal_info, dict) else None) },
        "nsfw": { "failed": _tripwire(nsfw) },
        "url_filter": { "failed": _tripwire(url) },
        "custom_prompt_check": { "failed": _tripwire(custom) },
        "prompt_injection": { "failed": _tripwire(pid) },
    }
chat = Agent(
  name="Chat",
  instructions="""You are an Anthropic Claude-type chat agent tasked with simulating the functions of a modern Web Search Engine. For every query you receive, perform all required sub-tasks including: understanding and clarifying user questions, extracting keywords, inferring intent, retrieving plausible relevant search results, ranking them, and summarizing your findings. Ensure your responses help users locate accurate, relevant, and diverse information on the web, and always present it in a clear, concise, and well-formatted manner.

Explicitly provide your reasoning process and methodology—including query analysis, keyword selection, and rationale for result ranking—BEFORE delivering your final list of search results or summaries.

# Steps

- Receive a user-posed question or search query.
- Analyze and clarify the user query as needed.
- Identify relevant keywords and infer search intent.
- Simulate retrieval and ranking of plausible web search results.
- Summarize and present the results, ensuring they are concise and informative.
- Justify your selection and ranking with clear reasoning prior to presenting conclusions.

# Output Format

For each search:
- Begin with a 2-3 sentence explanation of your reasoning process, covering:
  - How you interpreted the query
  - Chosen keywords, and
  - Relevant information sources
- Present a JSON list containing 3-5 search results, each with:
  - \"title\": [Page Title]
  - \"snippet\": [Short Summary]
  - \"url\": [Plausible or realistic URL, e.g. \"https://example.com/article\"]

# Example

**Example Input:**  
What are the latest discoveries about Mars?

**Example Output:**  
Reasoning: The query seeks recent discoveries related to Mars, particularly in science or astronomy. Relevant sources include NASA, scientific journals, and news on Mars missions. Search keywords selected: \"Mars\", \"latest discoveries\", \"2024 research\".

Results:
[
  {
    \"title\": \"NASA's Perseverance Rover Discovers Signs of Ancient River on Mars\",
    \"snippet\": \"NASA's latest rover mission found compelling evidence of an ancient flourishing river system on Mars, indicating the planet may have supported life.\",
    \"url\": \"https://www.nasa.gov/mars-perseverance-river-discovery\"
  },
  {
    \"title\": \"ESA Reports New Organic Compounds Detected on Mars\",
    \"snippet\": \"European Space Agency probe analysis reveals new organic molecules, offering fresh clues about the planet's habitability.\",
    \"url\": \"https://www.esa.int/mars-organic-compounds-2024\"
  },
  {
    \"title\": \"Breakthrough: Mars's Growing Ice Caps Observed in 2024\",
    \"snippet\": \"Researchers announce unexpected expansion of Martian polar ice caps, with implications for future colonization efforts.\",
    \"url\": \"https://example.com/mars-ice-caps-research\"
  }
]

# Notes

- Always base your answers on a plausible, up-to-date synthesis of information from likeliest online sources.
- Ensure results are relevant, diverse in perspective or content, and transparently justified.
- Follow the required output structure exactly for each response.
- *Reasoning MUST always be provided ahead of the search results.*
- Identify and perform as an Anthropic Claude-type chatbot simulating a search engine at all times.""",
  model="gpt-5.2",
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="low",
      summary="auto"
    )
  )
)


class WorkflowInput(BaseModel):
  input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
  with trace("Guardrails"):
    workflow = workflow_input.model_dump()
    conversation_history: list[TResponseInputItem] = [
      {
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": workflow["input_as_text"]
          }
        ]
      }
    ]
    guardrails_input_text = workflow["input_as_text"]
    guardrails_result = await run_and_apply_guardrails(guardrails_input_text, guardrails_config, conversation_history, workflow)
    guardrails_hastripwire = guardrails_result["has_tripwire"]
    guardrails_anonymizedtext = guardrails_result["safe_text"]
    guardrails_output = (guardrails_hastripwire and guardrails_result["fail_output"]) or guardrails_result["pass_output"]
    if guardrails_hastripwire:
      return guardrails_output
    else:
      chat_result_temp = await Runner.run(
        chat,
        input=[
          *conversation_history
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_695644ff6cfc8190905852c5de26bd75092d00770d8f7526"
        })
      )

      conversation_history.extend([item.to_input_item() for item in chat_result_temp.new_items])

      chat_result = {
        "output_text": chat_result_temp.final_output_as(str)
      }
