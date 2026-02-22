# agent-idp-sdk

Framework-agnostic Python SDK for integrating agents with the Agent IdP.

## Includes

- Shared `IdpClient` for IdP HTTP API interactions
- Typed registration models (`AgentRegistration`, `RuntimeBinding`)
- Framework adapters for:
  - OpenAI Agents SDK
  - LangGraph
  - Claude Agent SDK
  - Google ADK (registration normalization stub)
  - CrewAI (registration normalization stub)

## Install

```bash
uv add agent-idp-sdk
```

For framework extras:

```bash
uv add "agent-idp-sdk[all]"
```

## Quick usage

```python
from agent_idp_sdk import IdpClient, IdpConfig
from agent_idp_sdk.adapters import openai_registration

client = IdpClient(IdpConfig(base_url="https://idp.example.com", admin_api_key="..."))
result = client.register_agent(openai_registration())
print(result["agent_id"])
```
