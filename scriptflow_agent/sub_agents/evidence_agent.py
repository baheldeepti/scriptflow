"""Evidence sub-agent: pulls FHIR clinical evidence to support a PA."""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPServerParams

from scriptflow_agent.prompts import EVIDENCE_AGENT_PROMPT
from scriptflow_agent.config import (
    PA_ANALYZER_MCP_URL,
    MODEL_NAME,
    DEFAULT_FHIR_BASE_URL,
    DEFAULT_FHIR_TOKEN,
    DEFAULT_PATIENT_ID,
)


# When the agent is invoked from the Prompt Opinion platform, the platform
# auto-injects SHARP context headers. For local testing without the platform,
# we pass them manually via the MCPToolset headers below.
pa_analyzer_toolset = MCPToolset(
    connection_params=StreamableHTTPServerParams(
        url=PA_ANALYZER_MCP_URL,
        headers={
            "X-FHIR-Server-URL": DEFAULT_FHIR_BASE_URL,
            "X-FHIR-Access-Token": DEFAULT_FHIR_TOKEN,
            "X-Patient-ID": DEFAULT_PATIENT_ID,
        },
    ),
)

evidence_agent = LlmAgent(
    name="evidence_agent",
    model=MODEL_NAME,
    description="Pulls clinical evidence (conditions, prior medications, labs) from the patient FHIR chart.",
    instruction=EVIDENCE_AGENT_PROMPT,
    tools=[pa_analyzer_toolset],
)
