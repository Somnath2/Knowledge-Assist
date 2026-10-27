"""ADK orchestration for the code review agents."""

from google.adk.agents import ParallelAgent, SequentialAgent

from review_agent.agents.code_validator import root_agent as code_validator
from review_agent.agents.security_checker import root_agent as security_checker
from review_agent.agents.synthesizer import root_agent as synthesizer

review_specialists = ParallelAgent(
    name="review_specialists",
    description="Runs correctness and security reviewers in parallel.",
    sub_agents=[code_validator, security_checker],
)

root_agent = SequentialAgent(
    name="github_code_review",
    description="Read-only multi-agent GitHub repository code review.",
    sub_agents=[review_specialists, synthesizer],
)