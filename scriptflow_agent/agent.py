"""
ScriptFlow root orchestrator agent.
This is the agent ADK discovers when you run `adk web` from the project root.
It is also what `to_a2a()` will wrap as the public A2A server.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from scriptflow_agent.prompts import ROOT_ORCHESTRATOR_PROMPT
from scriptflow_agent.config import MODEL_NAME
from scriptflow_agent.sub_agents import (
    triage_agent,
    evidence_agent,
    planner_agent,
    form_filler_agent,
)

# ADK convention: the variable MUST be named `root_agent` for `adk web` to discover it.
root_agent = LlmAgent(
    name="scriptflow",
    model=MODEL_NAME,
    description=(
        "ScriptFlow is a clinically-aware pharmacy prior authorization orchestrator. "
        "Given a rejected pharmacy claim, it classifies the issue, scores patient-safety urgency, "
        "extracts FHIR evidence, drafts the PA form (or appeal letter), and produces a complete "
        "5T deliverable: Talk, Table, Template, Transaction, and Task."
    ),
    instruction=ROOT_ORCHESTRATOR_PROMPT,
    tools=[
        AgentTool(agent=triage_agent),
        AgentTool(agent=evidence_agent),
        AgentTool(agent=planner_agent),
        AgentTool(agent=form_filler_agent),
    ],
)
