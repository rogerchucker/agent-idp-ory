# Incident Manager Registration Demo

This demo shows how an incident manager platform registers 3 SRE RCA agents in the Agent IdP:

1. `sre-rca-openai` (OpenAI Agents SDK)
2. `sre-rca-langgraph` (LangGraph)
3. `sre-rca-claude` (Claude Agent SDK)

## Registration process (incident-manager perspective)

1. Incident manager picks framework-specific agent implementation.
2. Agent metadata and runtime identity binding are prepared (`agent_id`, owner, envs, k8s SA binding).
3. Incident manager calls `POST /agents` on IdP (admin API).
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
1. Each SDK agent object/graph/options initialized
2. Three successful registration confirmations

## Context7-backed SDK notes used for this demo

1. OpenAI Agents SDK: `Agent` + `Runner.run_sync/run`
2. LangGraph: `StateGraph`, `START/END`, `compile().invoke(...)`
3. Claude Agent SDK: `ClaudeAgentOptions` / `query(...)`
