import copy
import json
import subprocess
import sys
from pathlib import Path

from ai_drama_runtime.registry import SkillRegistry
from ai_drama_runtime.shot_prompt_canonical import SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_REF = "ai-drama-shot-prompt-skill@v0.1.0"
VALIDATOR_RELATIVE = Path("validators/validate_shot_prompt_set.py")


def _valid_shot_prompt_set():
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "project-001",
        "chapter_id": "chapter-001",
        "source_storyboard_revision_id": "storyboard-rev-001",
        "shots": [
            {
                "shot_id": "SHOT_001",
                "shot_order": 1,
                "duration_seconds": 8,
                "scene_id": "SCENE_001",
                "character_ids": ["CHAR_MING"],
                "prop_ids": ["PROP_RING"],
                "asset_refs": ["asset-character-ming", "asset-scene-hall"],
                "camera": {"shot_size": "medium", "movement": "slow push in"},
                "action": "Ming closes the ring box before anyone notices.",
                "emotion": "contained panic",
                "dialogue": [{"speaker_character_id": "CHAR_MING", "text": "Not now."}],
                "positive_prompt": "Live action medium shot of Ming hiding a ring box in a bright hall.",
                "negative_prompt": "cartoon, face drift, costume change",
                "continuity_notes": ["Preserve Ming's blue jacket and left-to-right screen direction."],
                "agnes_video_params": {"duration_seconds": 8, "aspect_ratio": "16:9"},
            }
        ],
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _run_validator(validator_path, revision_path, report_path):
    return subprocess.run(
        [
            sys.executable,
            str(validator_path),
            "--revision",
            str(revision_path),
            "--report",
            str(report_path),
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_shot_prompt_skill_package_resolves_and_declares_metadata():
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)

    assert package.skill_ref == SKILL_REF
    assert package.output_types == ["shot_prompt_set"]
    profile = package.metadata["execution_profiles"][0]
    assert profile["profile_id"] == "shot-prompt-canonical-v1"
    assert profile["output_type"] == "shot_prompt_set"
    assert profile["parser_version"] == "shot-prompt-canonical-json-v1"
    assert profile["unsupported_outputs"] == ["libtv_execution_package", "post_production_package"]

    validators = {item.validator_id: item for item in package.validators}
    assert list(validators) == ["shot_prompt_set_structure"]
    assert validators["shot_prompt_set_structure"].entrypoint == package.root / VALIDATOR_RELATIVE


def test_shot_prompt_skill_validator_accepts_valid_canonical_json(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, _valid_shot_prompt_set())

    result = _run_validator(validator, revision, report)

    assert result.returncode == 0, result.stderr + result.stdout
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["validator_id"] == "shot_prompt_set_structure"
    assert report_data["status"] == "PASS"
    assert report_data["canonical_hash"]


def test_shot_prompt_skill_validator_rejects_missing_asset_refs(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    invalid = _valid_shot_prompt_set()
    del invalid["shots"][0]["asset_refs"]
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, invalid)

    result = _run_validator(validator, revision, report)

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "CANONICAL_SCHEMA_INVALID"
    assert "asset_refs" in report_data["message"]


def test_shot_prompt_skill_validator_rejects_invalid_canonical_content(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    invalid = copy.deepcopy(_valid_shot_prompt_set())
    invalid["shots"][0]["duration_seconds"] = 30
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, invalid)

    result = _run_validator(validator, revision, report)

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "SHOT_PROMPT_DURATION_INVALID"


def test_shot_prompt_skill_validator_writes_report_for_invalid_json(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    revision.write_text("{not-json", encoding="utf-8")

    result = _run_validator(validator, revision, report)

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "CANONICAL_SCHEMA_INVALID"


def test_shot_prompt_skill_validator_rejects_duplicate_asset_refs(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    invalid = _valid_shot_prompt_set()
    invalid["shots"][0]["asset_refs"] = ["asset-character-ming", "asset-character-ming"]
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, invalid)

    result = _run_validator(validator, revision, report)

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "SHOT_PROMPT_ASSET_REFS_INVALID"


def test_shot_prompt_skill_validator_rejects_agnes_duration_mismatch(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    invalid = _valid_shot_prompt_set()
    invalid["shots"][0]["agnes_video_params"]["duration_seconds"] = 9
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, invalid)

    result = _run_validator(validator, revision, report)

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "SHOT_PROMPT_DURATION_INVALID"


def test_shot_prompt_skill_validator_writes_report_for_bad_repo_root(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, _valid_shot_prompt_set())

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--revision",
            str(revision),
            "--report",
            str(report),
            "--repo-root",
            str(tmp_path / "not-repo"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "SHOT_PROMPT_VALIDATOR_IMPORT_FAILED"


def test_shot_prompt_skill_validator_writes_report_for_repo_root_import_error(tmp_path):
    package = SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SKILL_REF)
    validator = package.root / VALIDATOR_RELATIVE
    fake_repo = tmp_path / "fake-repo"
    runtime_dir = fake_repo / "ai_drama_runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "shot_prompt_canonical.py").write_text(
        "raise ImportError('simulated import failure')\n",
        encoding="utf-8",
    )
    revision = tmp_path / "shot-prompt-set.json"
    report = tmp_path / "report.json"
    _write_json(revision, _valid_shot_prompt_set())

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--revision",
            str(revision),
            "--report",
            str(report),
            "--repo-root",
            str(fake_repo),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["status"] == "FAIL"
    assert report_data["error_code"] == "SHOT_PROMPT_VALIDATOR_IMPORT_FAILED"
