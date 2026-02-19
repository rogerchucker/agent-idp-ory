from __future__ import annotations

from idp_client import IdpConfig, register_agent

import claude_rca_agent
import langgraph_rca_agent
import openai_rca_agent


def main() -> None:
    config = IdpConfig()

    # Instantiate each framework-specific agent definition once.
    openai_agent = openai_rca_agent.build_agent()
    langgraph_graph = langgraph_rca_agent.build_graph()
    claude_options = claude_rca_agent.build_agent_options()

    print(f"Prepared OpenAI agent: {openai_agent.name}")
    print(f"Prepared LangGraph graph object: {type(langgraph_graph).__name__}")
    print(f"Prepared Claude options max_turns: {claude_options.max_turns}")

    payloads = [
        openai_rca_agent.registration_payload(),
        langgraph_rca_agent.registration_payload(),
        claude_rca_agent.registration_payload(),
    ]

    for payload in payloads:
        result = register_agent(config, payload)
        print(f"Registered {result['agent_id']} (owner={result['owner_principal']})")


if __name__ == "__main__":
    main()
