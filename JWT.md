The following should be the capability JWT: 

Header:

{
  "alg": "EdDSA",
  "kid": "cap-key-2026-01",
  "typ": "JWT"
}
Payload:

{
  "iss": "https://idp.yourdomain.com",
  "sub": "agent:operator-prod",
  "aud": "tool-gateway",
  "jti": "c1b2c3d4-....",                  // unique token id for replay defense
  "iat": 1739630000,
  "nbf": 1739630000,
  "exp": 1739630300,                       // 5 minutes

  "azp": "agent-runtime:k8s:cluster-1:ns/sre:sa/operator",  // authorized presenter (attested runtime)

  "tenant": "org:democorp",
  "env": "prod",
  "session": {
    "session_id": "sess-9f...",
    "trace_id": "trace-7a...",
    "purpose": "incident_response",
    "reason": "Elevated 5xx after deploy",
    "ticket": "INC-1234"
  },

  "delegation": {
    "grant_id": "grant-55...",
    "grant_type": "human_approval",        // or "policy_auto"
    "granted_by": "user:raj@company.com",  // or "policy:sev1-rollback"
    "granted_at": 1739629900,
    "expires_at": 1739630500,
    "mfa": true
  },

  "cap": {
    "action": "github.actions.rollback",    // example action
    "resource": "github:repo:org/app",      // example domain
    "constraints": {...}                    // depends on the 
  },

  "risk": {
    "level": "high",
    "step_up_required": false
  },

  "limits": {
    "rate": "3/5m",
    "cost_budget": 100
  }
}
