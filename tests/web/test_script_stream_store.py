import json

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore, ScriptGenerationConflict


def _store(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Streaming")
    chapter = store.create_chapter(project.project_id, "第一章", 1)
    source = store.create_source_revision(chapter.chapter_id, "原文")
    run = store.create_script_generation_run(
        run_id="stream-run-1",
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        source_revision_id=source.source_revision_id,
        runtime_run_id="runtime-run-1",
        idempotency_key="click-1",
    )
    return runtime, store, run


def test_script_stream_migration_is_additive_and_replay_safe(tmp_path):
    runtime, store, _run = _store(tmp_path)
    expected_run_columns = {
        "run_id",
        "runtime_run_id",
        "supplier_text_run_id",
        "snapshot_hash",
        "status",
        "last_sequence",
        "revision_id",
        "error_code",
    }
    first_columns = {
        row["name"]
        for row in store.conn.execute("PRAGMA table_info(script_generation_runs)")
    }
    assert expected_run_columns <= first_columns
    assert store.conn.execute(
        "SELECT COUNT(*) AS n FROM schema_migrations WHERE migration_id = ?",
        ("streaming_script_generation_v1",),
    ).fetchone()["n"] == 1

    ProductStore(runtime)

    assert store.conn.execute(
        "SELECT COUNT(*) AS n FROM schema_migrations WHERE migration_id = ?",
        ("streaming_script_generation_v1",),
    ).fetchone()["n"] == 1
    assert store.get_script_generation_run("stream-run-1")["status"] == "prepared"


def test_duplicate_event_must_have_same_hash(tmp_path):
    _runtime, store, _run = _store(tmp_path)
    first = store.append_script_generation_event(
        "stream-run-1",
        sequence=1,
        event_type="text_delta",
        payload={"text": "# 第一场"},
    )
    replay = store.append_script_generation_event(
        "stream-run-1",
        sequence=1,
        event_type="text_delta",
        payload={"text": "# 第一场"},
    )

    assert replay == first
    with pytest.raises(ScriptGenerationConflict, match="STREAM_SEQUENCE_CONFLICT"):
        store.append_script_generation_event(
            "stream-run-1",
            sequence=1,
            event_type="text_delta",
            payload={"text": "different"},
        )


def test_events_are_ordered_replayable_objects_and_update_character_count(tmp_path):
    runtime, store, _run = _store(tmp_path)
    store.append_script_generation_event(
        "stream-run-1", sequence=1, event_type="text_delta", payload={"text": "第一"}
    )
    store.append_script_generation_event(
        "stream-run-1", sequence=2, event_type="text_delta", payload={"text": "场"}
    )

    events = store.list_script_generation_events("stream-run-1", after_sequence=1)

    assert [event["sequence"] for event in events] == [2]
    assert json.loads(runtime.read_text(events[0]["payload_object_id"])) == {
        "text": "场"
    }
    current = store.get_script_generation_run("stream-run-1")
    assert current["last_sequence"] == 2
    assert current["character_count"] == 3


def test_claim_is_compare_and_set_and_recovery_marks_active_unknown(tmp_path):
    _runtime, store, _run = _store(tmp_path)

    claimed = store.claim_script_generation_run("stream-run-1")

    assert claimed["status"] == "submitting"
    assert store.claim_script_generation_run("stream-run-1") is None
    report = store.recover_script_generation_runs()
    assert report == {"unknown_outcome": 1}
    recovered = store.get_script_generation_run("stream-run-1")
    assert recovered["status"] == "unknown_outcome"
    assert recovered["error_code"] == "SUBMISSION_OUTCOME_UNKNOWN"

