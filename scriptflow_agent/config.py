"""
ScriptFlow configuration. Edit values here as needed.
Reads from environment variables when they exist so deployment overrides are easy.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---- LLM model ----
# gemini-2.5-flash is fast & cheap and works well for the sub-agents.
# You can switch the orchestrator to gemini-2.5-pro if you want stronger reasoning.
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

# ---- MCP server URL ----
# Local default: the PA Analyzer running on port 8080.
# When deployed (or via ngrok) override with PA_ANALYZER_MCP_URL.
PA_ANALYZER_MCP_URL = os.getenv("PA_ANALYZER_MCP_URL", "http://localhost:8080/mcp")

# ---- Default SHARP context for LOCAL TESTING only ----
# When ScriptFlow runs inside Prompt Opinion these are injected by the platform.
# For running `adk web` standalone, point at a public synthetic FHIR sandbox.
DEFAULT_FHIR_BASE_URL = os.getenv("DEFAULT_FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
DEFAULT_FHIR_TOKEN = os.getenv("DEFAULT_FHIR_TOKEN", "")
DEFAULT_PATIENT_ID = os.getenv("DEFAULT_PATIENT_ID", "demo-patient-001")

# ---- Public URL of THIS A2A agent (used in agent card) ----
# Set to your ngrok URL when exposing publicly.
A2A_PUBLIC_URL = os.getenv("A2A_PUBLIC_URL", "http://localhost:8000")
