"""
ScriptFlow PA Analyzer — MCP Server.

Exposes the tools defined in tools.py over the MCP protocol via JSON-RPC over HTTP.
Implements the SHARP-on-MCP spec:
  - Advertises capabilities.experimental.fhir_context_required.value = True
  - Reads X-FHIR-Server-URL, X-FHIR-Access-Token, X-Patient-ID request headers
  - Returns 403 when FHIR-dependent tools are called without context

Run locally:
    python -m pa_analyzer_mcp.server
"""

from __future__ import annotations
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from pa_analyzer_mcp.tools import (
    classify_rejection,
    identify_missing_documentation,
    extract_pa_evidence,
    assess_clinical_urgency,
    draft_appeal_letter,
)

app = FastAPI(title="ScriptFlow PA Analyzer MCP")


def _sharp_context(request: Request) -> dict:
    """Extract the SHARP context headers from an incoming HTTP request."""
    return {
        "fhir_server_url": request.headers.get("X-FHIR-Server-URL", ""),
        "fhir_access_token": request.headers.get("X-FHIR-Access-Token", ""),
        "patient_id": request.headers.get("X-Patient-ID", ""),
    }


def _ok(request_id, payload: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def _error(request_id, code: int, message: str, status: int = 200):
    body = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    return JSONResponse(status_code=status, content=body)


def _tool_text(payload: Any) -> dict:  # type: ignore[name-defined]
    """Wrap a tool result in MCP's content-block format."""
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return _error(None, -32700, "Parse error", status=400)

    method = body.get("method")
    request_id = body.get("id", 1)

    # ---------------- initialize ----------------
    if method == "initialize":
        return _ok(request_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "scriptflow-pa-analyzer", "version": "1.0.0"},
            "capabilities": {
                "tools": {},
                # Prompt Opinion FHIR context extension declaration
                # https://docs.promptopinion.ai/fhir-context/mcp-fhir-context
                "extensions": {
                    "ai.promptopinion/fhir-context": {
                        "scopes": [
                            {"name": "patient/Patient.rs", "required": True},
                            {"name": "patient/Condition.rs"},
                            {"name": "patient/MedicationRequest.rs"},
                            {"name": "patient/Observation.rs"},
                        ]
                    }
                },
            },
        })

    # ---------------- tools/list ----------------
    if method == "tools/list":
        return _ok(request_id, {
            "tools": [
                {
                    "name": "classify_rejection",
                    "description": (
                        "Classify a pharmacy claim rejection into a category "
                        "(PA_REQUIRED, STEP_THERAPY, FORMULARY_EXCLUSION, QUANTITY_LIMIT, "
                        "DIAGNOSIS_MISMATCH, MISSING_PRIOR_TX, AGE_RESTRICTION, DENIAL, UNKNOWN)."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "rejection_text": {"type": "string"},
                            "medication": {"type": "string"},
                        },
                        "required": ["rejection_text"],
                    },
                },
                {
                    "name": "identify_missing_documentation",
                    "description": "Given a rejection category, return the documents typically required.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "rejection_category": {"type": "string"},
                            "medication": {"type": "string"},
                        },
                        "required": ["rejection_category"],
                    },
                },
                {
                    "name": "assess_clinical_urgency",
                    "description": (
                        "Score the patient-safety urgency of a delayed medication. Returns a tier "
                        "(1=CRITICAL, 2=HIGH, 3=STANDARD), an SLA in hours, and a recommended action."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "medication": {"type": "string"},
                            "has_ascvd": {"type": "boolean"},
                            "has_active_infection": {"type": "boolean"},
                        },
                        "required": ["medication"],
                    },
                },
                {
                    "name": "extract_pa_evidence",
                    "description": (
                        "Pull conditions, prior medications, and recent labs from the patient's FHIR chart. "
                        "Requires SHARP context headers."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {"medication": {"type": "string"}},
                        "required": ["medication"],
                    },
                },
                {
                    "name": "draft_appeal_letter",
                    "description": "Draft a payer-agnostic appeal letter for a denied prior authorization.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "medication": {"type": "string"},
                            "diagnosis": {"type": "string"},
                            "denial_reason": {"type": "string"},
                            "clinical_justification": {"type": "string"},
                            "prior_therapies": {"type": "string"},
                            "prescriber_name": {"type": "string"},
                            "patient_id": {"type": "string"},
                        },
                        "required": ["medication", "diagnosis", "denial_reason", "clinical_justification"],
                    },
                },
            ]
        })

    # ---------------- tools/call ----------------
    if method == "tools/call":
        params = body.get("params", {}) or {}
        tool_name = params.get("name")
        args = params.get("arguments", {}) or {}
        ctx = _sharp_context(request)

        if tool_name == "classify_rejection":
            result = classify_rejection(
                rejection_text=args.get("rejection_text", ""),
                medication=args.get("medication", ""),
            )
        elif tool_name == "identify_missing_documentation":
            result = identify_missing_documentation(
                rejection_category=args.get("rejection_category", "UNKNOWN"),
                medication=args.get("medication", ""),
            )
        elif tool_name == "assess_clinical_urgency":
            result = assess_clinical_urgency(
                medication=args.get("medication", ""),
                has_ascvd=bool(args.get("has_ascvd", False)),
                has_active_infection=bool(args.get("has_active_infection", False)),
            )
        elif tool_name == "extract_pa_evidence":
            if not ctx["fhir_server_url"] or not ctx["patient_id"]:
                return _error(
                    request_id, -32000,
                    "Missing SHARP context headers. X-FHIR-Server-URL and X-Patient-ID are required.",
                    status=403,
                )
            result = extract_pa_evidence(
                fhir_base_url=ctx["fhir_server_url"],
                fhir_access_token=ctx["fhir_access_token"],
                patient_id=ctx["patient_id"],
                medication=args.get("medication", ""),
            )
        elif tool_name == "draft_appeal_letter":
            result = draft_appeal_letter(
                medication=args.get("medication", ""),
                diagnosis=args.get("diagnosis", ""),
                denial_reason=args.get("denial_reason", ""),
                clinical_justification=args.get("clinical_justification", ""),
                prior_therapies=args.get("prior_therapies", ""),
                prescriber_name=args.get("prescriber_name", "[Prescriber Name]"),
                patient_id=args.get("patient_id", ctx["patient_id"] or "[Patient ID]"),
            )
        else:
            return _error(request_id, -32601, f"Unknown tool: {tool_name}")

        return _ok(request_id, _tool_text(result))

    # ---------------- unknown method ----------------
    return _error(request_id, -32601, f"Unknown method: {method}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "scriptflow-pa-analyzer", "tools": 5}


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
