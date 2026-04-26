"""Planner sub-agent: builds the pharmacy workflow plan."""

from google.adk.agents import LlmAgent

from scriptflow_agent.prompts import PLANNER_AGENT_PROMPT
from scriptflow_agent.config import MODEL_NAME


planner_agent = LlmAgent(
    name="planner_agent",
    model=MODEL_NAME,
    description="Converts the triage and evidence outputs into a step-by-step pharmacy workflow plan.",
    instruction=PLANNER_AGENT_PROMPT,
)
