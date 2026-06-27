from pathlib import Path

from ai_drama_runtime.manifest import discover_skill_packages, load_skill_package


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = (
    REPO_ROOT
    / "skills"
    / "ai-drama-script-adaptation-skill"
    / "v0.6.1-rc2.4"
)


def test_discovers_active_script_skill_version():
    packages = discover_skill_packages(REPO_ROOT / "skills")

    matching = [
        pkg
        for pkg in packages
        if pkg.skill_id == "ai-drama-script-adaptation-skill"
        and pkg.version == "v0.6.1-rc2.4"
    ]
    assert len(matching) == 1
    assert matching[0].root == SKILL_ROOT


def test_loads_skill_metadata_and_declared_validators():
    package = load_skill_package(SKILL_ROOT)

    assert package.skill_id == "ai-drama-script-adaptation-skill"
    assert package.version == "v0.6.1-rc2.4"
    assert package.instructions_entry.name == "SKILL.md"
    assert package.content_hash
    assert package.validators
    assert all(validator.entrypoint.exists() for validator in package.validators)
