from pathlib import Path
import os
import shutil
import subprocess
import sys

from ai_drama_runtime.manifest import SkillValidator, load_skill_package
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.validators import run_declared_validators


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def test_latest_approval_order_is_deterministic_after_restart(tmp_path):
    with RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")) as service:
        result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock")
        service.approve_revision(result.revision.revision_id, "tester")
        service.reject_revision(result.revision.revision_id, "tester")
        assert service.store.latest_approval(result.revision.revision_id).action == "script_rejected"
        service.approve_revision(result.revision.revision_id, "tester")
        assert service.store.latest_approval(result.revision.revision_id).action == "script_approved"

    reopened = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    assert reopened.latest_approval(result.revision.revision_id).action == "script_approved"
    reopened.close()


def test_validator_uses_current_python_placeholder_and_stable_timeout(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        store.ensure_artifact("a", "drama_script", "p", "c")
        run = store.create_run(
            artifact_id="a",
            project_id="p",
            chapter_id="c",
            skill_id="s",
            skill_version="v1",
            skill_hash="h",
            runtime="mock",
            provider="mock",
            model="m",
            status="SUCCEEDED",
            request_object_id=store.write_text_object("{}"),
            response_object_id=store.write_text_object("{}"),
            input_hash="h",
        )
        revision = store.insert_revision(
            artifact_id="a",
            artifact_type="drama_script",
            project_id="p",
            chapter_id="c",
            run_id=run.run_id,
            skill_id="s",
            skill_version="v1",
            skill_package_hash="h",
            runtime_provider="mock",
            runtime_model="m",
            content_object_id=store.write_text_object("# Script\n\n## Scene\nBody"),
            content_hash="h",
            raw_response_object_id=store.write_text_object("{}"),
            parser_version="p",
        )
        check = tmp_path / "check.py"
        check.write_text("import sys; print(sys.executable)\n", encoding="utf-8")
        sleepy = tmp_path / "sleepy.py"
        sleepy.write_text("import time; time.sleep(3)\n", encoding="utf-8")
        package = type(
            "Pkg",
            (),
            {
                "root": tmp_path,
                "validators": [
                    SkillValidator("py", "py", check, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 5, "zero_is_pass", "runtime_policy", [], "APPLICABLE", ""),
                    SkillValidator("sleep", "sleep", sleepy, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass", "runtime_policy", [], "APPLICABLE", ""),
                ],
            },
        )()
        results = run_declared_validators(store, package, revision, tmp_path, repo_root=tmp_path)
        by_id = {item.validator_id: item for item in results}
        assert store.read_text(by_id["py"].stdout_object_id).strip() == sys.executable
        assert by_id["sleep"].error_code == "VALIDATOR_TIMEOUT"


def test_store_closes_database_so_file_can_be_removed(tmp_path):
    db = tmp_path / "runtime.db"
    objects = tmp_path / "objects"
    with RuntimeStore(db, objects) as store:
        store.write_text_object("x")
    os.remove(db)
    assert not db.exists()


def test_service_context_closes_database_so_directory_can_be_deleted(tmp_path):
    data = tmp_path / "data"
    with RuntimeService(RuntimeStore(data / "runtime.db", data / "objects")) as service:
        service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock")

    shutil.rmtree(data)
    assert not data.exists()


def test_repeated_service_open_close_leaves_no_database_lock(tmp_path):
    for index in range(5):
        with RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")) as service:
            service.store.write_text_object("value-%s" % index)

    os.remove(tmp_path / "runtime.db")
    assert not (tmp_path / "runtime.db").exists()


def test_timeout_validator_releases_temporary_directory(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        store.ensure_artifact("a", "drama_script", "p", "c")
        run = store.create_run(
            artifact_id="a",
            project_id="p",
            chapter_id="c",
            skill_id="s",
            skill_version="v1",
            skill_hash="h",
            runtime="mock",
            provider="mock",
            model="m",
            status="SUCCEEDED",
            request_object_id=store.write_text_object("{}"),
            response_object_id=store.write_text_object("{}"),
            input_hash="h",
        )
        revision = store.insert_revision(
            artifact_id="a",
            artifact_type="drama_script",
            project_id="p",
            chapter_id="c",
            run_id=run.run_id,
            skill_id="s",
            skill_version="v1",
            skill_package_hash="h",
            runtime_provider="mock",
            runtime_model="m",
            content_object_id=store.write_text_object("# Script\n\n## Scene\nBody"),
            content_hash="h",
            raw_response_object_id=store.write_text_object("{}"),
            parser_version="p",
        )
        sleepy = tmp_path / "sleepy.py"
        sleepy.write_text("import time; time.sleep(3)\n", encoding="utf-8")
        package = type(
            "Pkg",
            (),
            {
                "root": tmp_path,
                "validators": [
                    SkillValidator("sleep", "sleep", sleepy, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass", "runtime_policy", [], "APPLICABLE", "")
                ],
            },
        )()
        results = run_declared_validators(store, package, revision, tmp_path, repo_root=tmp_path)
        assert results[0].error_code == "VALIDATOR_TIMEOUT"

    shutil.rmtree(tmp_path)
    assert not tmp_path.exists()


def test_multiple_cli_calls_release_data_root(tmp_path):
    data = tmp_path / "runtime-data"
    commands = [
        [sys.executable, "-m", "ai_drama_runtime.cli", "--data-root", str(data), "--skills-root", "skills", "skills", "list"],
        [
            sys.executable,
            "-m",
            "ai_drama_runtime.cli",
            "--data-root",
            str(data),
            "--skills-root",
            "skills",
            "skills",
            "validate",
            "ai-drama-script-adaptation-skill@v0.6.1-rc2.4",
        ],
        [
            sys.executable,
            "-m",
            "ai_drama_runtime.cli",
            "--data-root",
            str(data),
            "--skills-root",
            "skills",
            "run",
            "create",
            "--skill",
            "ai-drama-script-adaptation-skill@v0.6.1-rc2.4",
            "--input",
            "acceptance/shengsi-chapter-001",
            "--runtime",
            "mock",
            "--model",
            "mock",
        ],
    ]
    for command in commands:
        subprocess.run(command, cwd=str(REPO_ROOT), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)

    shutil.rmtree(data)
    assert not data.exists()
