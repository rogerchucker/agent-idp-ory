from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

IDP_BASE_URL = os.getenv("IDP_BASE_URL", "http://localhost:7001").rstrip("/")
IDP_ADMIN_API_KEY = os.getenv("IDP_ADMIN_API_KEY", "")
IDP_INTERNAL_API_KEY = os.getenv("IDP_INTERNAL_API_KEY", "")

app = FastAPI(title="Incident Manager Demo UI", version="0.1.0")

SCENARIOS = [
    {
        "id": "happy_path",
        "title": "Happy Path",
        "expect": "Success",
        "description": "Agent is registered, attested, authorized, and executes successfully.",
    },
    {
        "id": "failure_unregistered",
        "title": "Failure: Agent Not Registered",
        "expect": "Fail at authN",
        "description": "Attestation is attempted for an unknown agent_id.",
    },
    {
        "id": "failure_authn",
        "title": "Failure: Authentication (attestation invalid)",
        "expect": "Fail at authN",
        "description": "Agent exists, but runtime binding does not match the attestation.",
    },
    {
        "id": "failure_authz",
        "title": "Failure: Authorization (policy denied)",
        "expect": "Fail at authZ",
        "description": "Grant exists, but requested capability action does not match the approved grant.",
    },
]


def _headers(kind: str) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if kind == "admin" and IDP_ADMIN_API_KEY:
        headers["x-admin-api-key"] = IDP_ADMIN_API_KEY
    if kind == "internal" and IDP_INTERNAL_API_KEY:
        headers["x-internal-api-key"] = IDP_INTERNAL_API_KEY
    return headers


async def _post(client: httpx.AsyncClient, path: str, payload: dict[str, Any], kind: str) -> dict[str, Any]:
    url = f"{IDP_BASE_URL}{path}"
    started = time.time()
    try:
        resp = await client.post(url, json=payload, headers=_headers(kind))
    except httpx.HTTPError as exc:
        return {
            "status_code": 0,
            "ok": False,
            "response": {"detail": f"request_failed:{exc.__class__.__name__}"},
            "duration_ms": int((time.time() - started) * 1000),
        }

    body: Any
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text}

    return {
        "status_code": resp.status_code,
        "ok": resp.is_success,
        "response": body,
        "duration_ms": int((time.time() - started) * 1000),
    }


async def run_scenario(name: str) -> dict[str, Any]:
    run_id = uuid.uuid4().hex[:8]
    trace_id = f"trace-{name}-{run_id}"
    session_id = f"session-{name}-{run_id}"
    agent_id = f"demo-{name}-{run_id}"

    agent_payload = {
        "agent_id": agent_id,
        "tenant": "org:democorp",
        "owner_principal": "user:raj@example.com",
        "trust_level": "high",
        "allowed_envs": ["prod"],
        "runtime_bindings": [
            {
                "kind": "k8s",
                "cluster": "cluster-1",
                "namespace": "sre",
                "service_account": "operator",
            }
        ],
        "status": "active",
    }

    attest_good = {
        "kind": "k8s",
        "cluster": "cluster-1",
        "namespace": "sre",
        "service_account": "operator",
        "agent_id": agent_id,
        "env": "prod",
        "session_id": session_id,
        "trace_id": trace_id,
    }

    attest_bad_binding = {
        **attest_good,
        "service_account": "wrong-service-account",
    }

    grant_payload = {
        "grant_type": "human_approval",
        "granted_by": "user:raj@example.com",
        "agent_id": agent_id,
        "env": "prod",
        "action": "github.actions.rollback",
        "resource": "github:repo:org/app",
        "purpose": "incident_response",
        "reason": "Elevated 5xx after deploy",
        "ticket": "INC-4242",
        "mfa": True,
        "ttl_seconds": 900,
    }

    steps: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        if name == "happy_path":
            register = await _post(client, "/agents", agent_payload, "admin")
            steps.append({"step": "register_agent", "phase": "registration", **register})
            if not register["ok"]:
                return _finalize(name, run_id, steps)

            attest = await _post(client, "/attest/exchange", attest_good, "internal")
            steps.append({"step": "attest_exchange", "phase": "authN", **attest})
            if not attest["ok"]:
                return _finalize(name, run_id, steps)
            access_token = attest["response"]["access_token"]

            grant = await _post(client, "/grants", grant_payload, "admin")
            steps.append({"step": "create_grant", "phase": "authorization", **grant})
            if not grant["ok"]:
                return _finalize(name, run_id, steps)
            grant_id = grant["response"]["grant_id"]

            mint_payload = {
                "agent_access_token": access_token,
                "grant_id": grant_id,
                "session_id": session_id,
                "trace_id": trace_id,
                "purpose": "incident_response",
                "reason": "Elevated 5xx after deploy",
                "ticket": "INC-4242",
                "cap_action": "github.actions.rollback",
                "cap_resource": "github:repo:org/app",
                "constraints": {"branch": "main"},
                "risk_level": "high",
                "limits": {"rate": "3/5m", "cost_budget": 100},
            }
            mint = await _post(client, "/capabilities/mint", mint_payload, "internal")
            steps.append({"step": "mint_capability", "phase": "authZ", **mint})
            if not mint["ok"]:
                return _finalize(name, run_id, steps)
            capability_token = mint["response"]["capability_token"]

            execute_payload = {
                "capability_token": capability_token,
                "tool": "github",
                "action": "github.actions.rollback",
                "resource": "github:repo:org/app",
                "params": {"sha": "abc123"},
                "presenter": "agent-runtime:k8s:cluster-1:ns/sre:sa/operator",
            }
            execute = await _post(client, "/gateway/execute", execute_payload, "internal")
            steps.append({"step": "gateway_execute", "phase": "execution", **execute})
            return _finalize(name, run_id, steps)

        if name == "failure_unregistered":
            missing_attest = {
                **attest_good,
                "agent_id": f"missing-agent-{run_id}",
            }
            attest = await _post(client, "/attest/exchange", missing_attest, "internal")
            steps.append({"step": "attest_exchange", "phase": "authN", **attest})
            return _finalize(name, run_id, steps)

        if name == "failure_authn":
            register = await _post(client, "/agents", agent_payload, "admin")
            steps.append({"step": "register_agent", "phase": "registration", **register})
            if not register["ok"]:
                return _finalize(name, run_id, steps)

            attest = await _post(client, "/attest/exchange", attest_bad_binding, "internal")
            steps.append({"step": "attest_exchange", "phase": "authN", **attest})
            return _finalize(name, run_id, steps)

        if name == "failure_authz":
            register = await _post(client, "/agents", agent_payload, "admin")
            steps.append({"step": "register_agent", "phase": "registration", **register})
            if not register["ok"]:
                return _finalize(name, run_id, steps)

            attest = await _post(client, "/attest/exchange", attest_good, "internal")
            steps.append({"step": "attest_exchange", "phase": "authN", **attest})
            if not attest["ok"]:
                return _finalize(name, run_id, steps)
            access_token = attest["response"]["access_token"]

            grant = await _post(client, "/grants", grant_payload, "admin")
            steps.append({"step": "create_grant", "phase": "authorization", **grant})
            if not grant["ok"]:
                return _finalize(name, run_id, steps)
            grant_id = grant["response"]["grant_id"]

            mint_payload_denied = {
                "agent_access_token": access_token,
                "grant_id": grant_id,
                "session_id": session_id,
                "trace_id": trace_id,
                "purpose": "incident_response",
                "reason": "Trying an unapproved operation",
                "ticket": "INC-4242",
                "cap_action": "github.actions.delete_repo",
                "cap_resource": "github:repo:org/app",
                "constraints": {"branch": "main"},
                "risk_level": "medium",
                "limits": {"rate": "3/5m", "cost_budget": 100},
            }
            mint = await _post(client, "/capabilities/mint", mint_payload_denied, "internal")
            steps.append({"step": "mint_capability", "phase": "authZ", **mint})
            return _finalize(name, run_id, steps)

    raise HTTPException(status_code=400, detail="unknown_scenario")


def _finalize(name: str, run_id: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    success = bool(steps) and steps[-1]["ok"] and name == "happy_path"
    first_failure = next((step for step in steps if not step["ok"]), None)
    return {
        "scenario": name,
        "run_id": run_id,
        "success": success,
        "failure": first_failure,
        "steps": steps,
    }


@app.get("/api/scenarios")
def list_scenarios() -> dict[str, Any]:
    return {
        "idp_base_url": IDP_BASE_URL,
        "scenarios": SCENARIOS,
        "keys_configured": {
            "admin": bool(IDP_ADMIN_API_KEY),
            "internal": bool(IDP_INTERNAL_API_KEY),
        },
    }


@app.post("/api/scenarios/{scenario}/run")
async def run_scenario_api(scenario: str) -> dict[str, Any]:
    valid = {item["id"] for item in SCENARIOS}
    if scenario not in valid:
        raise HTTPException(status_code=404, detail="unknown_scenario")
    return await run_scenario(scenario)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Agent IdP Demo UI</title>
  <style>
    :root {
      --bg: #f6f4ef;
      --card: #fffefb;
      --ink: #202429;
      --muted: #5f6670;
      --line: #d8d5cc;
      --ok: #1f7a3a;
      --bad: #b22518;
      --accent: #0c5c7a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: radial-gradient(circle at 20% 0%, #efe7d0 0%, var(--bg) 45%);
      color: var(--ink);
    }
    main { max-width: 1100px; margin: 0 auto; padding: 28px 16px 40px; }
    h1 { margin: 0 0 10px; font-size: 2rem; letter-spacing: 0.01em; }
    .meta { color: var(--muted); margin-bottom: 20px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.04);
    }
    .card h3 { margin: 0 0 8px; font-size: 1rem; }
    .card p { margin: 0 0 8px; color: var(--muted); }
    button {
      border: none;
      background: var(--accent);
      color: white;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
    }
    button:disabled { opacity: 0.65; cursor: progress; }
    .small { font-size: 0.85rem; color: var(--muted); }
    #results { display: grid; gap: 10px; }
    .result {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
    }
    .pill {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      margin-right: 8px;
    }
    .ok { background: #d6f4df; color: var(--ok); }
    .bad { background: #fadad6; color: var(--bad); }
    pre {
      white-space: pre-wrap;
      background: #f2f0ea;
      border-radius: 8px;
      padding: 10px;
      border: 1px solid var(--line);
      font-size: 0.78rem;
      overflow-x: auto;
    }
  </style>
</head>
<body>
<main>
  <h1>Agent Identity Flow Demo</h1>
  <div class=\"meta\" id=\"meta\">Loading scenario metadata...</div>
  <div style=\"margin-bottom:14px\"><button id=\"runAll\">Run All Scenarios</button></div>
  <section class=\"grid\" id=\"scenarios\"></section>
  <section id=\"results\"></section>
</main>
<script>
const scenariosEl = document.getElementById('scenarios');
const resultsEl = document.getElementById('results');
const metaEl = document.getElementById('meta');
const runAllBtn = document.getElementById('runAll');

function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function renderResult(data) {
  const outcomeClass = data.success ? 'ok' : 'bad';
  const outcomeText = data.success ? 'SUCCESS' : 'FAILURE';

  const stepsHtml = data.steps.map((step) => {
    const stepClass = step.ok ? 'ok' : 'bad';
    return `<div style=\"margin-bottom:10px\">\n      <span class=\"pill ${stepClass}\">${step.ok ? 'OK' : 'ERROR'}</span>\n      <strong>${escapeHtml(step.step)}</strong>\n      <span class=\"small\">phase=${escapeHtml(step.phase)} status=${step.status_code} (${step.duration_ms}ms)</span>\n      <pre>${escapeHtml(JSON.stringify(step.response, null, 2))}</pre>\n    </div>`;
  }).join('');

  const failureLine = data.failure
    ? `<p><strong>Failure cause:</strong> ${escapeHtml(data.failure.step)} -> ${escapeHtml((data.failure.response && data.failure.response.detail) || 'unknown')}</p>`
    : '';

  return `<article class=\"result\">\n    <span class=\"pill ${outcomeClass}\">${outcomeText}</span>\n    <strong>${escapeHtml(data.scenario)}</strong>\n    <span class=\"small\">run_id=${escapeHtml(data.run_id)}</span>\n    ${failureLine}\n    ${stepsHtml}\n  </article>`;
}

async function runScenario(id, button) {
  button.disabled = true;
  try {
    const response = await fetch(`/api/scenarios/${id}/run`, { method: 'POST' });
    const data = await response.json();
    resultsEl.insertAdjacentHTML('afterbegin', renderResult(data));
  } catch (error) {
    resultsEl.insertAdjacentHTML('afterbegin', `<article class=\"result\"><span class=\"pill bad\">FAILURE</span><strong>${escapeHtml(id)}</strong><p>${escapeHtml(error.message)}</p></article>`);
  } finally {
    button.disabled = false;
  }
}

async function loadScenarios() {
  const response = await fetch('/api/scenarios');
  const data = await response.json();

  metaEl.textContent = `Agent IdP: ${data.idp_base_url} | admin key configured: ${data.keys_configured.admin} | internal key configured: ${data.keys_configured.internal}`;

  scenariosEl.innerHTML = data.scenarios.map((scenario) => `
    <article class=\"card\">
      <h3>${escapeHtml(scenario.title)}</h3>
      <p>${escapeHtml(scenario.description)}</p>
      <div class=\"small\">Expected: ${escapeHtml(scenario.expect)}</div>
      <div style=\"margin-top:10px\"><button data-scenario=\"${escapeHtml(scenario.id)}\">Run Scenario</button></div>
    </article>
  `).join('');

  for (const button of scenariosEl.querySelectorAll('button[data-scenario]')) {
    button.addEventListener('click', () => runScenario(button.dataset.scenario, button));
  }

  runAllBtn.addEventListener('click', async () => {
    runAllBtn.disabled = true;
    const buttons = [...scenariosEl.querySelectorAll('button[data-scenario]')];
    for (const button of buttons) {
      await runScenario(button.dataset.scenario, button);
    }
    runAllBtn.disabled = false;
  });
}

loadScenarios();
</script>
</body>
</html>"""
