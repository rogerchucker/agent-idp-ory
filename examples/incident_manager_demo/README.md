# Incident Manager Registration Demo

This demo now uses a shared, framework-agnostic Agent IdP SDK and shows how an incident manager platform can register SRE RCA agents across frameworks using the same IdP contract:

1. `sre-rca-openai` (OpenAI Agents SDK)
2. `sre-rca-langgraph` (LangGraph)
3. `sre-rca-claude` (Claude Agent SDK)
4. `sre-rca-google-adk` (Google ADK adapter shape)
5. `sre-rca-crewai` (CrewAI adapter shape)

## SDK layout

- Standalone package: `/Users/raj/ai/agents/agent-idp/sdk/python/agent-idp-sdk`
- `src/agent_idp_sdk/core.py`: shared `IdpClient` and config
- `src/agent_idp_sdk/types.py`: typed registration models
- `src/agent_idp_sdk/adapters/*`: framework adapters that map to common registration payloads

Backward compatibility is preserved:

- Existing modules (`openai_rca_agent.py`, `langgraph_rca_agent.py`, `claude_rca_agent.py`, `idp_client.py`) remain as wrappers.

## Registration process (incident-manager perspective)

1. Incident manager picks framework-specific agent implementation.
2. Adapter maps framework metadata to canonical IdP registration payload.
3. Incident manager calls `POST /agents` via shared SDK client.
4. IdP persists and returns canonical agent record.
5. Later at runtime, each agent signs in via attestation (`/attest/exchange`) and mints capabilities.

## Prerequisites

1. Agent IdP running on `http://localhost:7001`
2. Admin API key if enabled in your config

## Run

```bash
cd /Users/raj/ai/agents/agent-idp/examples/incident_manager_demo
uv sync
IDP_BASE_URL=http://localhost:7001 \
IDP_ADMIN_API_KEY=<your-admin-key-if-required> \
uv run python register_all_agents.py
```

## Expected output

You should see:

1. Each framework adapter object/spec initialized
2. Five successful registration confirmations

## Context7-backed SDK notes used for this demo

1. OpenAI Agents SDK: `Agent` + `Runner.run_sync/run`
2. LangGraph: `StateGraph`, `START/END`, `compile().invoke(...)`
3. Claude Agent SDK: `ClaudeAgentOptions` / `query(...)`
4. Google ADK and CrewAI support currently demonstrates adapter payload normalization for IdP registration.
