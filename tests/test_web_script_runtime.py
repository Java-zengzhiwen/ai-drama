from pathlib import Path

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.request import build_runtime_request_from_inputs
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"


@pytest.fixture
def skill_package():
    return load_skill_package(SKILL_ROOT)


def test_direct_input_request_is_canonical(skill_package):
    request = build_runtime_request_from_inputs(
        skill_package,
        inputs={
            "source_chapter": "正文",
            "series_canon": "世界观",
            "characters": "人物",
            "production_brief": "制作要求",
        },
        provider="mock",
        model="mock-script-v1",
    )

    assert [item["logical_type"] for item in request.payload["inputs"]] == [
        "characters",
        "production_brief",
        "series_canon",
        "source_chapter",
    ]


def test_run_script_inputs_persists_input_snapshots(skill_package, tmp_path):
    inputs = {
        "source_chapter": "正文",
        "series_canon": "世界观",
        "characters": "人物",
        "production_brief": "制作要求",
    }
    with RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")) as service:
        result = service.run_script_inputs(
            skill_package,
            artifact_id="chapter-1:script",
            project_id="project-1",
            chapter_id="chapter-1",
            inputs=inputs,
            runtime="mock",
            model="mock-script-v1",
        )

        snapshots = service.store.input_snapshots(result.run.run_id)

        assert result.revision.artifact_id == "chapter-1:script"
        assert {item.logical_type: service.store.read_text(item.object_id) for item in snapshots} == inputs
