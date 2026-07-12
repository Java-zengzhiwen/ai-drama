from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"


def test_agents_md_contains_autonomous_execution_policy_without_weakening_m5_gate() -> None:
    text = AGENTS.read_text(encoding="utf-8")

    assert "## Codex Autonomous Execution Policy" in text
    assert "Default Codex can execute directly" in text
    assert "USER_ACTION_REQUIRED" in text
    assert "ACTION=<one action for the user>" in text
    assert "RESUME_WITH=<exact phrase to resume>" in text

    for pause_condition in (
        "real paid provider requests",
        "passwords, 2FA, CAPTCHA, OAuth, or system permission prompts",
        "destructive actions such as data deletion, database reset, overwriting user files, or Mac restart",
        "new, replaced, or exposed credentials",
        "repository governance requires human approval",
    ):
        assert pause_condition in text

    m5_gate = text.index("## M5 Authorization Gate")
    autonomous_policy = text.index("## Codex Autonomous Execution Policy")
    assert autonomous_policy > m5_gate
    assert "No real Agnes request may be made without this exact user-provided token." in text
