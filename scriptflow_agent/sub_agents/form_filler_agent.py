"""Form Filler sub-agent: drafts the PA form OR an appeal letter."""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPServerParams

from scriptflow_agent.prompts import FORM_FILLER_AGENT_PROMPT
from scriptflow_agent.config import PA_ANALYZER_MCP_URL, MODEL_NAME


pa_analyzer_toolset = MCPToolset(
    connection_params=StreamableHTTPServerParams(url=PA_ANALYZER_MCP_URL),
)

form_filler_agent = LlmAgent(
    name="form_filler_agent",
    model=MODEL_NAME,
    description="Drafts a pre-filled PA form or, for denials, an appeal letter ready for prescriber signature.",
    instruction=FORM_FILLER_AGENT_PROMPT,
    tools=[pa_analyzer_toolset],
)
