from __future__ import annotations

from typing_extensions import TypedDict

from .base import build_registration


class RCAState(TypedDict):
    incident_summary: str
    hypothesis: str


def _summarize_incident(state: RCAState) -> dict:
    return {
        "incident_summary": state["incident_summary"],
        "hypothesis": "Likely deploy-induced regression in payment service",
    }


def build_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(RCAState)
    graph.add_node("summarize_incident", _summarize_incident)
    graph.add_edge(START, "summarize_incident")
    graph.add_edge("summarize_incident", END)
    return graph.compile()


def registration(
    *,
    owner_principal: str | None = None,
    self_identified_owner: str | None = None,
    framework: str | None = None,
    target_application: str | None = None,
    prompt_for_identity: bool = False,
) -> dict:
    return build_registration(
        agent_id="sre-rca-langgraph",
        framework=framework or "langgraph",
        owner_principal=owner_principal,
        self_identified_owner=self_identified_owner,
        target_application=target_application,
        prompt_for_identity=prompt_for_identity,
        service_account="rca-langgraph-sa",
    ).to_payload()
