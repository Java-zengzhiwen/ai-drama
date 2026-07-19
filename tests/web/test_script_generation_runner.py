from pathlib import Path

from ai_drama_runtime.registry import SkillRegistry
from ai_drama_runtime.runtime import _mock_script
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.services.script_generation_stream import (
    ScriptGenerationRunner,
    _DisplayableScriptText,
)
from ai_drama_web.services.script_workflow import SCRIPT_SKILL_REF
from ai_drama_web.store import ProductStore


class FakeStreamingGateway:
    def __init__(self, before_invoke=None):
        self.submit_count = 0
        self.before_invoke = before_invoke or (lambda: None)

    def invoke_stream(self, snapshot_hash, operation, request):
        self.before_invoke()
        self.submit_count += 1
        assert snapshot_hash == "snapshot-1"
        assert operation == "textStream"
        assert request["messages"]
        script = _mock_script("fake-stream")
        split_at = len(script) // 2
        yield {"type": "started", "sequence": 0}
        yield {"type": "text_delta", "sequence": 1, "text": script[:split_at]}
        yield {"type": "text_delta", "sequence": 2, "text": script[split_at:]}
        yield {"type": "usage", "sequence": 3, "usage": {"total_tokens": 3}}
        yield {
            "type": "completed",
            "sequence": 4,
            "evidence": {"schema": "provider-stream-shape-v1"},
        }


def _runner_fixture(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Streaming")
    chapter = store.create_chapter(project.project_id, "第一章", 1)
    source = store.create_source_revision(chapter.chapter_id, "沈清荷醒来，决定重新查账。")
    skill = SkillRegistry.scan([repo_root / "skills"]).get_ref(SCRIPT_SKILL_REF)
    runtime_service = RuntimeService(runtime, repo_root=repo_root)
    prepared = runtime_service.prepare_script_inputs(
        skill,
        artifact_id=f"{chapter.chapter_id}:script",
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        inputs={
            "source_chapter": "沈清荷醒来，决定重新查账。",
            "series_canon": "古装商贾世界",
            "characters": "沈清荷",
            "production_brief": "本次改编目标时长：4 分钟。",
        },
        runtime="supplier",
        model="resolved-by-snapshot",
    )
    session = store.create_script_generation_run(
        run_id="session-1",
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        source_revision_id=source.source_revision_id,
        runtime_run_id=prepared.run_id,
        idempotency_key="click-1",
    )
    store.bind_script_generation_snapshot(
        session["run_id"],
        supplier_text_run_id="text-run-1",
        snapshot_hash="snapshot-1",
    )
    return repo_root, runtime, store, prepared


def test_runner_persists_before_provider_and_creates_one_validated_revision(tmp_path):
    repo_root, runtime, store, prepared = _runner_fixture(tmp_path)

    def assert_prepared_rows():
        assert store.get_script_generation_run("session-1")["status"] == "submitting"
        assert runtime.get_run(prepared.run_id).status == "RUNNING"

    gateway = FakeStreamingGateway(before_invoke=assert_prepared_rows)
    runner = ScriptGenerationRunner(store, runtime, repo_root=repo_root, gateway=gateway)

    result = runner.run_cycle()

    assert result.started == 1
    assert gateway.submit_count == 1
    session = store.get_script_generation_run("session-1")
    assert session["status"] == "completed"
    assert session["revision_id"]
    revision = runtime.get_revision(session["revision_id"])
    assert runtime.read_text(revision.content_object_id).startswith("# Mock Drama Script")
    required = [row for row in runtime.validation_results(revision.revision_id) if row.required]
    assert required and all(row.status == "PASS" for row in required)
    assert [event["event_type"] for event in store.list_script_generation_events(
        "session-1", after_sequence=0
    )][-3:] == ["stage", "stage", "revision_completed"]

    assert runner.run_cycle().started == 0
    assert gateway.submit_count == 1


def test_streaming_request_keeps_skill_inputs_and_target_duration(tmp_path):
    _repo_root, runtime, _store, prepared = _runner_fixture(tmp_path)
    request = prepared.runtime_request.to_dict()
    inputs = {item["logical_type"]: item["content"] for item in request["inputs"]}

    assert request["skill"]["version"] == "v0.6.1-rc2.4"
    assert "本次改编目标时长：4 分钟" in inputs["production_brief"]
    assert {"source_chapter", "series_canon", "characters", "production_brief"} <= set(inputs)
    assert runtime.get_run(prepared.run_id).status == "RUNNING"


def test_stream_display_waits_for_a_markdown_heading_and_hides_wrappers():
    text = _DisplayableScriptText()

    assert text.push('{"script":"') == ""
    assert text.push('# 第一场\\n半截 JSON"}') == ""
    assert text.final_output().startswith('{"script"')

    markdown = _DisplayableScriptText()
    assert markdown.push("这里是说明，不应展示\n") == ""
    assert markdown.push("# 第一场\n正文") == "# 第一场\n正文"
    assert markdown.final_output() == "# 第一场\n正文"


def test_recovery_completes_a_finalized_revision_without_resubmitting(tmp_path):
    repo_root, runtime, store, _prepared = _runner_fixture(tmp_path)
    gateway = FakeStreamingGateway()
    runner = ScriptGenerationRunner(store, runtime, repo_root=repo_root, gateway=gateway)
    assert runner.run_cycle().completed == 1
    revision_id = store.get_script_generation_run("session-1")["revision_id"]
    with store.conn:
        store.conn.execute(
            "DELETE FROM script_generation_events WHERE run_id=? AND event_type='revision_completed'",
            ("session-1",),
        )
        last = store.conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS n FROM script_generation_events WHERE run_id=?",
            ("session-1",),
        ).fetchone()["n"]
        store.conn.execute(
            "UPDATE script_generation_runs SET status='finalizing', revision_id='', last_sequence=? WHERE run_id=?",
            (last, "session-1"),
        )

    report = store.recover_script_generation_runs()

    assert report == {"unknown_outcome": 0}
    recovered = store.get_script_generation_run("session-1")
    assert recovered["status"] == "completed"
    assert recovered["revision_id"] == revision_id
    assert gateway.submit_count == 1
