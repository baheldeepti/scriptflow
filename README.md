# ScriptFlow

> Clinically-aware AI orchestrator for pharmacy prior authorization.
> Built for the **Agents Assemble: Healthcare AI Endgame Challenge** (Prompt Opinion, May 2026).

## What it does

ScriptFlow is an **A2A agent** that consumes a custom **MCP server** and Prompt Opinion's hosted FHIR MCP to convert pharmacy claim rejections into ready-to-submit PA packages — in minutes instead of days.

The novel angle: ScriptFlow scores **clinical urgency** for every case (1=Critical, 2=High, 3=Standard) so patient-safety-critical delays (insulin, anticoagulants, oncology, antibiotics) jump the queue and trigger bridge-supply recommendations.

## Architecture

```
┌──────────────────────────────────────────────────┐
│        Prompt Opinion workspace (clinician)      │
└────────────────────┬─────────────────────────────┘
                     │ A2A
                     ▼
┌──────────────────────────────────────────────────┐
│      ScriptFlow Orchestrator (Google ADK)        │
│   triage → evidence → planner → form_filler      │
└──┬──────────────────────┬────────────────────────┘
   │ MCP                  │ MCP
   ▼                      ▼
PA Analyzer MCP    PO-hosted FHIR MCP
(this repo)        (ts.fhir-mcp.promptopinion.ai/mcp)
```

## Quickstart

```bash
# 1. Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env  # fill in your GOOGLE_API_KEY

# 2. Run the MCP server (terminal 1)
python -m pa_analyzer_mcp.server

# 3. Run the agent locally with the ADK web UI (terminal 2)
adk web

# 4. Or expose the agent as A2A (terminal 2)
python -m scriptflow_agent.a2a_server
```

## Project layout

```
scriptflow/
├── pa_analyzer_mcp/        ← The MCP "Superpower" (5 tools)
│   ├── server.py             FastAPI MCP wrapper, SHARP-compliant
│   └── tools.py              classify, doc-list, urgency, FHIR pull, appeal
├── scriptflow_agent/       ← The A2A "Superhero"
│   ├── agent.py              root orchestrator
│   ├── prompts.py            ALL LLM instructions, single source of truth
│   ├── config.py             env-driven settings
│   ├── a2a_server.py         exposes the agent over A2A
│   └── sub_agents/
│       ├── triage_agent.py
│       ├── evidence_agent.py
│       ├── planner_agent.py
│       └── form_filler_agent.py
├── sample_data/            ← synthetic patient + rejection + SOP
└── demo_scripts/           ← demo prompts & video script
```

## Standards used

- **MCP** — for tools (PA Analyzer)
- **A2A** — for agent invocation (Google ADK `to_a2a`)
- **FHIR R4** — for clinical evidence retrieval
- **SHARP-on-MCP** — for context propagation (X-FHIR-Server-URL, X-FHIR-Access-Token, X-Patient-ID)

## Synthetic data only

Every example in `sample_data/` is fabricated for demonstration. ScriptFlow contains no real PHI.
