"""Draft skills live in both .claude/skills (Claude Code) and .agents/skills (Codex).

The two copies must stay identical so a fix made in one reaches both agents.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
AGENT_SKILLS = ROOT / ".agents" / "skills"


def test_claude_skills_are_mirrored_in_agents_skills():
    claude_files = sorted(CLAUDE_SKILLS.glob("*/SKILL.md"))
    assert claude_files, "no skills found under .claude/skills"
    for path in claude_files:
        mirror = AGENT_SKILLS / path.parent.name / "SKILL.md"
        assert mirror.exists(), f"missing mirror {mirror.relative_to(ROOT)}"
        assert mirror.read_bytes() == path.read_bytes(), (
            f"{path.relative_to(ROOT)} and {mirror.relative_to(ROOT)} differ"
        )
