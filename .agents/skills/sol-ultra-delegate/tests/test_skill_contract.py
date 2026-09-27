from __future__ import annotations

import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]


class SkillContractTests(unittest.TestCase):
    def test_openai_metadata_is_explicit_only(self):
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn('display_name: "Sol Ultra Delegate"', metadata)
        self.assertIn("$sol-ultra-delegate", metadata)
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_skill_pins_supervisor_and_fallback_without_recursion(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        lowered = skill.lower()

        self.assertIn('model="gpt-5.6-sol"', skill)
        self.assertIn('reasoning_effort="ultra"', skill)
        self.assertIn('fork_turns="none"', skill)
        self.assertIn("never exceed four", skill)
        self.assertIn("at most one DeepMimo chat-completion request", skill)
        self.assertIn("must automatically spawn exactly one native fallback", skill)
        self.assertIn("Trigger exactly one native fallback automatically if and only if", skill)
        self.assertIn('handoff_reason="providers-exhausted"', skill)
        self.assertIn("fails the lane's predefined local acceptance check", skill)
        self.assertIn("There is no discretionary decline after either eligible trigger", skill)
        self.assertIn("spawn exactly one agent", lowered)
        self.assertIn("must not call DeepMimo", skill)
        self.assertIn("must not spawn another agent", skill)
        self.assertIn("must not spawn another agent, recurse", skill)
        self.assertIn("A failed or blocked fallback ends the lane as `BLOCKED`; do not retry", skill)
        self.assertIn("Helper status `BLOCKED` never authorizes fallback", skill)
        self.assertIn("quota or policy rejection", skill)
        self.assertIn("Sol Ultra is a task-level original-model handoff", skill)
        self.assertNotIn("The decision is discretionary", skill)
        self.assertIn("Wait for every lane to finish", skill)
        self.assertIn("The root Codex task remains head engineer and final acceptor", skill)

    def test_project_authority_boundary_is_persisted(self):
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("## `$sol-ultra-delegate` authority boundary", agents)
        self.assertIn("does not select or launch a native fallback", agents)
        self.assertIn("perfume-chem-sol-ultra", agents)
        self.assertIn("X-DeepMimo-Original-Model-Handoff", agents)
        self.assertIn("automatically creates exactly one native GPT-5.6 Sol Ultra fallback", agents)
        self.assertIn("Sol Ultra is a task-level original-model handoff", agents)
        self.assertIn("quota or policy rejection", agents)
        self.assertIn("must not call DeepMimo, spawn another agent, or recurse", agents)
        self.assertIn("global `$delegate`/OpenRouter path remains unused and unchanged", agents)


if __name__ == "__main__":
    unittest.main()
