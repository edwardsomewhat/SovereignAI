# CrewAI 1.14 API Field Reference

Source: docs.crewai.com (verified against crewai-core 1.14.5)

## Agent Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `role` | `str` | *Required* | Agent's function and expertise |
| `goal` | `str` | *Required* | Individual objective guiding decisions |
| `backstory` | `str` | *Required* | Context and personality |
| `llm` | `Union[str, LLM]` | `"gpt-4"` | Model string or LLM object |
| `tools` | `List[BaseTool]` | `[]` | Tool capabilities |
| `function_calling_llm` | `Optional[Any]` | `None` | Separate LLM for tool calls |
| `max_iter` | `int` | `20` | Max iterations before forced answer |
| `max_rpm` | `Optional[int]` | `None` | API rate limit |
| `max_execution_time` | `Optional[int]` | `None` | Timeout in seconds |
| `verbose` | `bool` | `False` | Detailed execution logs |
| `allow_delegation` | `bool` | `False` | Allow delegating to other agents |
| `allow_code_execution` | `Optional[bool]` | `False` | **Deprecated** |
| `max_retry_limit` | `int` | `2` | Max retries on error |
| `respect_context_window` | `bool` | `True` | Auto-summarize at context limit |
| `use_system_prompt` | `Optional[bool]` | `True` | False for older models |

## Task Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `description` | `str` | *Required* | Clear statement of the task |
| `expected_output` | `str` | *Required* | Desired outcome description |
| `name` | `Optional[str]` | `None` | Name identifier |
| `agent` | `Optional[BaseAgent]` | `None` | Responsible agent |
| `context` | `Optional[List[Task]]` | `None` | Upstream task outputs as context |
| `async_execution` | `Optional[bool]` | `False` | Run asynchronously |
| `human_input` | `Optional[bool]` | `False` | Human review before final answer |
| `output_file` | `Optional[str]` | `None` | Save output to file |
| `output_json` | `Optional[BaseModel]` | `None` | Pydantic model for structured output |
| `output_pydantic` | `Optional[BaseModel]` | `None` | Same as output_json |
| `callback` | `Optional[Any]` | `None` | Post-completion hook |
| `guardrail` | `Optional[Callable]` | `None` | Output validation function |
| `guardrail_max_retries` | `Optional[int]` | `3` | Retries when guardrail fails |

## Crew Fields (hierarchical mode)

| Field | Type | Notes |
|-------|------|-------|
| `agents` | `List[BaseAgent]` | Workers only — NOT the manager |
| `tasks` | `List[Task]` | All tasks the crew can handle |
| `process` | `Process` | `Process.hierarchical` |
| `manager_agent` | `BaseAgent` | The coordinator agent |
| `manager_llm` | `Union[str, LLM]` | Separate model for the manager |
| `verbose` | `bool` | Detailed logs |
| `planning` | `bool` | Enable planning phase before execution |
| `memory` | `bool` | Enable cross-run memory |

## Process Values

```python
from crewai import Process
Process.sequential    # 'sequential' — tasks run in defined order
Process.hierarchical  # 'hierarchical' — manager assigns dynamically
```

## OpenRouter Setup

```python
# Option A: LLM object
from crewai import LLM
llm = LLM(
    model="openrouter/deepseek/deepseek-chat",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# Option B: String (CrewAI resolves creds from env vars)
llm_str = "openrouter/deepseek/deepseek-chat"
# Requires OPENROUTER_API_KEY and OPENROUTER_BASE_URL in environment
```

Model name format: `openrouter/<provider>/<model>` (e.g., `openrouter/anthropic/claude-sonnet-4`).

## Two-Tier Model Strategy

- Workers: cheaper/faster model (e.g., `deepseek/deepseek-chat`)
- Manager: stronger reasoning model (e.g., `anthropic/claude-sonnet-4`)
- Set worker LLM on each Agent's `llm=` param
- Set manager LLM on Crew's `manager_llm=` param
