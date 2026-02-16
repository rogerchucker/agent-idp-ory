This document captures all the requirements for building an IdP that represents AI Agents the correct way. This would help us achieve the following identity model:

## Identity Model

Human identities: use SSO/IdP (Okta/Azure AD/Google).
Agent identities: workload identities issued by the org's platform (like SPIFFE/SPIRE style), or IdP as “service accounts”.
Tool identities: each external system you call (GitHub, Grafana, PagerDuty, AWS, etc.) is a resource server with its own trust boundary.

The core auth material will be short-lived, attested credentials instead of API keys, subject to the following constraints:
- Agent runs in a controlled runtime (k8s, VM, serverless).
- Runtime will provide attestation (k8s SA + OIDC, cloud workload identity, or SPIFFE SVID).

Agent will exchange attestation for a platform access token (JWT) with:
- agent_id
- environment (prod/stage)
- session_id / trace_id
- issued_at / expiry (5–15 min)
- allowed audiences (i.e. which internal services it can call)

## Authorization Model

AuthZ will be enforced in 3 layers:
1. Global guardrails (org policy)
    - Non-negotiable constraints: prod change windows, forbidden actions, data boundaries, geo constraints, etc.

2. Delegation / intent grants (who allowed this?)
    - A human or system grants permission for this mission (incident, ticket, request).

3. Execution-time capability (what exactly can be done now?)
    - sMint a capability token scoped to specific actions/resources for a short TTL.

## Background:
We must treat agents like first-class workloads (not “users with API keys”), and makes every tool call an authorization decision with tight scoping + auditability.

## Core principles
1. Agents are identities (service principals), not people.
2. AuthZ is per-action, per-resource, per-context (time, env, risk, purpose), not “agent can use tool X”.
3. Delegation is explicit: the only way an agent gains power is via a signed grant from a human, org policy, or another trusted agent with the right to delegate.
4. Capabilities over static roles for execution (short-lived, least-privilege tokens).
5. Every action is attributable: “who/what/why” is mandatory (trace IDs + reason codes + link to ticket/alert).


Let's build an Agent IdP based on the following architecture:      
      
                 ┌────────────────────────────────────────────────┐
                 │                     Humans                      │
                 │   (SSO / IdP: Okta/AAD/Google) + MFA/Approvals │
                 └───────────────┬────────────────────────────────┘
                                 │ OAuth/OIDC (human auth)
                                 v
┌─────────────────────────────────────────────────────────────────────────┐
│                           Agent Identity Plane                           │
│                                                                         │
│  ┌───────────────┐     ┌─────────────────────┐     ┌─────────────────┐ │
│  │ Agent Registry │<--->│ Policy Decision Pt  │<--->│ Delegation/Grants│ │
│  │ (agents, trust │     │ (ABAC/OPA/Cedar)    │     │ (approvals, HITL │ │
│  │ levels, owners)│     └─────────────────────┘     │ and revocation)  │ │
│  └───────┬───────┘                │                 └────────┬────────┘ │
│          │                         │                          │          │
│          │                 decision/constraints               │          │
│          v                         v                          v          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                Capability Minting / Token Service                  │  │
│  │  - exchanges agent runtime identity for short-lived JWTs           │  │
│  │  - mints *capability tokens* scoped to action+resource+constraints │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                  │                                        │
└──────────────────────────────────┼────────────────────────────────────────┘
                                   │ capability JWT (aud=tool-gateway)
                                   v
                     ┌─────────────────────────────────┐
                     │           Tool Gateway           │
                     │ (Policy Enforcement Point / PEP) │
                     │ - verify JWT + constraints        │
                     │ - schema validate requests        │
                     │ - rate-limit / replay protect     │
                     │ - redact + audit log              │
                     └───────────────┬─────────────────┘
                                     │ tool-native auth (stored here)
                                     v
          ┌──────────────┬──────────────┬──────────────┬──────────────┐
          │ GitHub        │ Kubernetes   │ Grafana/Loki │ Cloud/DB/etc  │
          │ (App/Token)   │ (RBAC)       │ (API keys)   │ (vendor creds)│
          └──────────────┴──────────────┴──────────────┴──────────────┘

Runtime identity / attestation path:
  Agent Runtime (K8s SA OIDC / SPIFFE / Cloud workload identity) ──> Minting Service

This Agent IdP should achieve the following:
1. Authenticate workloads (agents) via attestation.
2. Authorize via delegation + capability minting, not static roles.
3. Enforce at a Tool Gateway so agents never hold broad vendor credentials.

There will be two types of tokens:
1. Agent Access Token (authenticate the agent to the minting service / platform APIs)
2. Capability Token (authorizes a specific action against a tool gateway)

The Capability JWT claims should follow the JSON structure in JWT.md.

We will build this as an extension to Ory. We will use Ory for human + baseline OAuth, then build the agent-specific pieces:
- Ory: Human SSO, MFA, org onboarding, SCIM, standard tokens

The following will coinstitute the MVP solution:
1. Agent Registry (agents, trust levels, owners)
2. Delegation/Grants (approvals, revocation)
3. Capability Minting (short-lived constraint JWTs)
4. Tool Gateway (enforcement + auditing)
5. Policy Engine (OPA/Cedar) for decisions

