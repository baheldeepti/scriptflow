"""
A small FastAPI proxy that fixes ADK's agent card to be A2A v0.3 spec-compliant
(adds the `supportedInterfaces` field that Prompt Opinion requires).

Routes:
- GET /a2a/scriptflow_agent/.well-known/agent-card.json  -> serves spec-compliant card
- everything else                                         -> forwards to ADK on port 8001
"""
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

ADK_BACKEND = os.getenv("ADK_BACKEND", "http://127.0.0.1:8001")
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://scriptflow-agent.ngrok.app")
AGENT_PATH = "/a2a/scriptflow_agent"

app = FastAPI()

AGENT_CARD = {
    "name": "ScriptFlow",
    "description": (
        "ScriptFlow is a clinically-aware pharmacy prior authorization orchestrator. "
        "Given a rejected pharmacy claim, it classifies the issue, scores patient-safety "
        "urgency (Tier 1 Critical / Tier 2 High / Tier 3 Standard), extracts FHIR clinical "
        "evidence, drafts a pre-filled PA form or appeal letter, and produces a complete 5T "
        "deliverable: Talk, Table, Template, Transaction, Task. Built for the Agents Assemble "
        "hackathon, May 2026."
    ),
    "url": f"{PUBLIC_URL}{AGENT_PATH}",
    "version": "1.0.0",
    "protocolVersion": "0.3.0",
    "preferredTransport": "JSONRPC",
    "supportedInterfaces": [
        {
            "transport": "JSONRPC",
            "url": f"{PUBLIC_URL}{AGENT_PATH}",
            "protocolBinding": "JSONRPC",
            "protocolVersion": "0.3.0"
        }
    ],
    "additionalInterfaces": [
        {
            "transport": "JSONRPC",
            "url": f"{PUBLIC_URL}{AGENT_PATH}",
            "protocolBinding": "JSONRPC",
            "protocolVersion": "0.3.0"
        }
    ],
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "capabilities": {"streaming": True},
    "skills": [
        {
            "id": "resolve_prior_authorization",
            "name": "Resolve Prior Authorization Case",
            "description": (
                "Takes a pharmacy rejection or denial and produces a complete PA workflow plan: "
                "classification, urgency triage, evidence gathering, pre-filled PA form, "
                "simulated submission, and follow-up task."
            ),
            "tags": ["healthcare", "pharmacy", "prior authorization", "FHIR", "MCP", "A2A"],
            "examples": [
                "Patient was prescribed Ozempic. Aetna rejected it for step therapy. Patient has T2DM and ASCVD. Please resolve.",
                "PA for adalimumab was denied. Patient failed methotrexate. Draft an appeal.",
                "Apixaban claim rejected as not covered. Patient on chronic anticoagulation for AFib. What now?",
            ],
        }
    ],
}


@app.get(f"{AGENT_PATH}/.well-known/agent-card.json")
async def agent_card():
    return JSONResponse(content=AGENT_CARD)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scriptflow-a2a-proxy"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(path: str, request: Request):
    """Forward every other request to ADK. Translate message/stream -> message/send."""
    url = f"{ADK_BACKEND}/{path}"
    # Preserve query string
    if request.url.query:
        url = f"{url}?{request.url.query}"

    body = await request.body()
    # Translate message/stream -> message/send (ADK doesnt support streaming)
    if request.method == "POST" and body:
        try:
            import json as _json
            payload = _json.loads(body)
            if isinstance(payload, dict) and payload.get("method") == "message/stream":
                payload["method"] = "message/send"
                body = _json.dumps(payload).encode("utf-8")
        except Exception:
            pass
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            r = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
            )
            response_headers = {k: v for k, v in r.headers.items() if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")}
            return Response(content=r.content, status_code=r.status_code, headers=response_headers)
        except Exception as e:
            return JSONResponse(status_code=502, content={"error": f"backend unreachable: {e}"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
