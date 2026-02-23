from __future__ import annotations

import os

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
    owner_principal = os.getenv("IDP_OWNER_PRINCIPAL")
    self_identified_owner = os.getenv("IDP_SELF_IDENTIFIED_OWNER")
    target_application = os.getenv("IDP_TARGET_APPLICATION")
    prompt_for_identity = os.getenv("IDP_PROMPT_IDENTITY", "").lower() in {"1", "true", "yes"}

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
        openai_registration(
            owner_principal=owner_principal,
            self_identified_owner=self_identified_owner,
            target_application=target_application,
            prompt_for_identity=prompt_for_identity,
        ),
        langgraph_registration(
            owner_principal=owner_principal,
            self_identified_owner=self_identified_owner,
            target_application=target_application,
            prompt_for_identity=prompt_for_identity,
        ),
        claude_registration(
            owner_principal=owner_principal,
            self_identified_owner=self_identified_owner,
            target_application=target_application,
            prompt_for_identity=prompt_for_identity,
        ),
        google_adk_registration(
            owner_principal=owner_principal,
            self_identified_owner=self_identified_owner,
            target_application=target_application,
            prompt_for_identity=prompt_for_identity,
        ),
        crewai_registration(
            owner_principal=owner_principal,
            self_identified_owner=self_identified_owner,
            target_application=target_application,
            prompt_for_identity=prompt_for_identity,
        ),
    ]

    for payload in payloads:
        print(
            "Registering payload metadata:",
            {
                "agent_id": payload.get("agent_id"),
                "framework": payload.get("framework"),
                "self_identified_owner": payload.get("self_identified_owner"),
                "target_application": payload.get("target_application"),
            },
        )
        result = client.register_agent(payload)
        print(f"Registered {result['agent_id']} (owner={result['owner_principal']})")


if __name__ == "__main__":
    main()
