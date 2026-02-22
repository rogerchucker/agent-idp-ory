from __future__ import annotations

from agent_idp_sdk import IdpClient, IdpConfig
from agent_idp_sdk.adapters import (
    build_agent,
    build_claude_options,
    build_crewai_agent_spec,
    build_google_adk_agent_spec,
    build_graph,
    claude_registration,
    crewai_registration,
    google_adk_registration,
    langgraph_registration,
    openai_registration,
)


def main() -> None:
    client = IdpClient(IdpConfig())

    # Instantiate each framework-specific definition once.
    openai_agent = build_agent()
    langgraph_graph = build_graph()
    claude_options = build_claude_options()
    google_adk_spec = build_google_adk_agent_spec()
    crewai_spec = build_crewai_agent_spec()

    print(f"Prepared OpenAI agent: {openai_agent.name}")
    print(f"Prepared LangGraph graph object: {type(langgraph_graph).__name__}")
    print(f"Prepared Claude options max_turns: {claude_options.max_turns}")
    print(f"Prepared Google ADK spec: {google_adk_spec.name}")
    print(f"Prepared CrewAI spec role: {crewai_spec.role}")

    payloads = [
        openai_registration(),
        langgraph_registration(),
        claude_registration(),
        google_adk_registration(),
        crewai_registration(),
    ]

    for payload in payloads:
        result = client.register_agent(payload)
        print(f"Registered {result['agent_id']} (owner={result['owner_principal']})")


if __name__ == "__main__":
    main()
