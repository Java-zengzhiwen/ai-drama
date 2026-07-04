from pathlib import Path
import json
import shutil

import pytest

from ai_drama_runtime.manifest import SkillManifestError, load_skill_package
from ai_drama_runtime.registry import DuplicateSkillError, SkillRegistry


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_CANONICAL_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.2.0"


def _write_skill(root, **overrides):
    (root / "validators").mkdir(parents=True, exist_ok=True)
    (root / "schemas").mkdir(exist_ok=True)
    (root / "contracts").mkdir(exist_ok=True)
    (root / "references").mkdir(exist_ok=True)
    (root / "SKILL.md").write_text("instructions", encoding="utf-8")
    (root / "references" / "a.md").write_text("context", encoding="utf-8")
    (root / "schemas" / "a.json").write_text("{}", encoding="utf-8")
    (root / "contracts" / "a.md").write_text("contract", encoding="utf-8")
    (root / "validators" / "ok.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "validators" / "common.py").write_text("HELPER = 'ok'\n", encoding="utf-8")
    data = {
        "package_format_version": "1",
        "skill_id": "skill-a",
        "version": "v1",
        "display_name": "Skill A",
        "description": "test skill",
        "package_status": "active",
        "instructions_entry": "SKILL.md",
        "context_files": ["references/a.md"],
        "input_types": ["source_chapter"],
        "output_types": ["drama_script"],
        "schemas": ["schemas/a.json"],
        "contracts": ["contracts/a.md"],
        "validator_support_files": ["validators/common.py"],
        "validators": [
            {
                "validator_id": "ok",
                "entrypoint": "validators/ok.py",
                "required": True,
                "applies_to": ["drama_script_revision"],
                "command": ["python3", "{entrypoint}"],
                "dependencies": [],
                "timeout_seconds": 5,
                "expected_exit_behavior": "zero_is_pass",
                "validator_origin": "migrated_skill",
                "required_artifacts": ["creator_facing_markdown_script"],
                "current_profile_status": "APPLICABLE",
                "current_profile_reason": "test",
            }
        ],
        "runtime_requirements": {"python": ">=3.9"},
        "dependency_requirements": [],
        "provenance": {"source": "test"},
        "execution_profiles": [
            {
                "profile_id": "markdown-script-mvp-v1",
                "output_artifact_type": "drama_script_markdown",
                "output_format": "markdown",
                "parser_version": "drama-script-markdown-v1",
                "supported_artifacts": ["creator_facing_markdown_script"],
                "unsupported_bundle_artifacts": [],
            }
        ],
    }
    data.update(overrides)
    import json

    (root / "skill.json").write_text(json.dumps(data), encoding="utf-8")


def test_manifest_rejects_missing_required_field(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root)
    import json

    data = json.loads((root / "skill.json").read_text())
    data.pop("display_name")
    (root / "skill.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SkillManifestError, match="display_name"):
        load_skill_package(root)


def test_manifest_rejects_bad_types_and_path_escape(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root, context_files="not-a-list")
    with pytest.raises(SkillManifestError, match="context_files"):
        load_skill_package(root)

    _write_skill(root, instructions_entry="../outside.md")
    with pytest.raises(SkillManifestError, match="escapes"):
        load_skill_package(root)


def test_manifest_rejects_symlink_escape(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("print('bad')", encoding="utf-8")
    _write_skill(root)
    (root / "validators" / "ok.py").unlink()
    (root / "validators" / "ok.py").symlink_to(outside)

    with pytest.raises(SkillManifestError, match="escapes"):
        load_skill_package(root)


def test_package_hash_uses_declared_active_files_only(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root)
    first = load_skill_package(root).content_hash
    (root / "ignored.pyc").write_bytes(b"junk")
    assert load_skill_package(root).content_hash == first
    (root / "references" / "a.md").write_text("changed", encoding="utf-8")
    assert load_skill_package(root).content_hash != first


def test_package_hash_includes_declared_validator_support_files(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root)
    first = load_skill_package(root).content_hash

    (root / "validators" / "common.py").write_text("HELPER = 'changed'\n", encoding="utf-8")

    assert load_skill_package(root).content_hash != first


def test_package_hash_ignores_undeclared_validator_files(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root)
    first = load_skill_package(root).content_hash

    (root / "validators" / "scratch.py").write_text("print('ignored')\n", encoding="utf-8")

    assert load_skill_package(root).content_hash == first


def test_manifest_rejects_missing_validator_support_file(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root)
    (root / "validators" / "common.py").unlink()

    with pytest.raises(SkillManifestError, match="validator_support_files"):
        load_skill_package(root)


def test_manifest_rejects_validator_support_file_escape(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    _write_skill(root, validator_support_files=["/tmp/outside.py"])

    with pytest.raises(SkillManifestError, match="escapes"):
        load_skill_package(root)

    _write_skill(root, validator_support_files=["../outside.py"])
    with pytest.raises(SkillManifestError, match="escapes"):
        load_skill_package(root)

    outside = tmp_path / "outside.py"
    outside.write_text("print('bad')\n", encoding="utf-8")
    _write_skill(root)
    (root / "validators" / "common.py").unlink()
    (root / "validators" / "common.py").symlink_to(outside)
    with pytest.raises(SkillManifestError, match="escapes"):
        load_skill_package(root)


def test_registry_indexes_gets_and_isolates_invalid_packages(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    _write_skill(good)
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "skill.json").write_text("{}", encoding="utf-8")

    registry = SkillRegistry.scan([tmp_path])

    assert registry.get("skill-a", "v1").root == good.resolve()
    assert registry.show("skill-a@v1")["skill_id"] == "skill-a"
    assert registry.list()[0]["version"] == "v1"
    assert registry.invalid_packages


def test_registry_rejects_duplicate_skill_version(tmp_path):
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    _write_skill(one)
    _write_skill(two)

    with pytest.raises(DuplicateSkillError):
        SkillRegistry.scan([tmp_path])


def test_real_skill_package_is_valid_and_paths_are_inside_root():
    package = load_skill_package(SKILL_ROOT)

    assert package.skill_id == "ai-drama-script-adaptation-skill"
    assert package.version == "v0.6.1-rc2.4"
    assert package.context_files
    assert package.schemas
    assert package.contracts
    assert all(SKILL_ROOT.resolve() in path.parents for path in [v.entrypoint for v in package.validators])
    genericity = [v for v in package.validators if v.validator_id == "genericity"][0]
    assert not any("{repo_root}" in part for part in genericity.command)


def test_canonical_storyboard_execution_profile_metadata_is_valid():
    package = load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT)

    profile = package.execution_profiles[0]
    assert profile["profile_id"] == "storyboard-canonical-v1"
    assert profile["output_format"] == "json"
    assert profile["parser_version"] == "storyboard-canonical-json-v1"
    assert profile["required_schema_version"] == "storyboard-canonical-v1"
    assert profile["renderer_id"] == "storyboard-canonical-markdown-renderer"
    assert profile["renderer_version"] == "1.0.0"


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda profile: profile.pop("renderer_id"), "renderer_id"),
        (lambda profile: profile.__setitem__("output_format", "markdown"), "output_format"),
        (lambda profile: profile.__setitem__("required_schema_version", "other"), "required_schema_version"),
        (lambda profile: profile.__setitem__("renderer_version", ""), "renderer_version"),
    ],
)
def test_canonical_storyboard_execution_profile_metadata_is_required(tmp_path, mutate, match):
    root = tmp_path / "storyboard-canonical"
    shutil.copytree(STORYBOARD_CANONICAL_SKILL_ROOT, root)
    data = json.loads((root / "skill.json").read_text(encoding="utf-8"))
    mutate(data["execution_profiles"][0])
    (root / "skill.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SkillManifestError, match=match):
        load_skill_package(root)
