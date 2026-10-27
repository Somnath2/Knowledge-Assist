import unittest

from google.adk.agents import ParallelAgent, SequentialAgent

from review_agent.agent import root_agent


class AgentWorkflowTest(unittest.TestCase):
    def test_root_agent_runs_specialists_then_synthesizer(self):
        self.assertIsInstance(root_agent, SequentialAgent)
        specialists, synthesizer = root_agent.sub_agents

        self.assertIsInstance(specialists, ParallelAgent)
        self.assertEqual([agent.name for agent in specialists.sub_agents], ["code_validator", "security_checker"])
        self.assertEqual(synthesizer.name, "review_synthesizer")


if __name__ == "__main__":
    unittest.main()