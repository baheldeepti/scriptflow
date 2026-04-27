"""Triage sub-agent: classifies rejections and scores clinical urgency."""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

from scriptflow_agent.prompts import TRIAGE_AGENT_PROMPT
from scriptflow_agent.config import PA_ANALYZER_MCP_URL, MODEL_NAME


pa_analyzer_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url=PA_ANALYZER_MCP_URL),
)

triage_agent = LlmAgent(
    name="triage_agent",
    model=MODEL_NAME,
    description=(
        "Classifies a pharmacy rejection AND scores the clinical urgency of the medication delay "
        "so the orchestrator can prioritize patient-safety-critical cases."
    ),
    instruction=TRIAGE_AGENT_PROMPT,
    tools=[pa_analyzer_toolset],
)
