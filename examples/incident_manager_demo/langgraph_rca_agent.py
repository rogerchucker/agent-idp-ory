from __future__ import annotations

from typing_extensions import TypedDict
from langgraph.graph import START, END, StateGraph


class RCAState(TypedDict):
    incident_summary: str
    hypothesis: str


def _summarize_incident(state: RCAState) -> dict:
    return {
        "incident_summary": state["incident_summary"],
        "hypothesis": "Likely deploy-induced regression in payment service",
    }


def build_graph():
    graph = StateGraph(RCAState)
    graph.add_node("summarize_incident", _summarize_incident)
    graph.add_edge(START, "summarize_incident")
    graph.add_edge("summarize_incident", END)
    return graph.compile()


def registration_payload() -> dict:
    return {
        "agent_id": "sre-rca-langgraph",
        "tenant": "org:democorp",
        "owner_principal": "user:incident-manager@company.com",
        "trust_level": "high",
        "allowed_envs": ["prod", "stage"],
        "runtime_bindings": [
            {
                "kind": "k8s",
                "cluster": "cluster-1",
                "namespace": "sre",
                "service_account": "rca-langgraph-sa",
            }
        ],
        "status": "active",
    }
