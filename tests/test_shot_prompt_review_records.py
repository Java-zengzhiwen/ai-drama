import sqlite3

import pytest

from ai_drama_runtime.shot_prompt_migration import REVIEW_EVENT_TYPES
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import index_sql, seed_phase3_store, table_sql


def test_review_tables_enforce_scope_events_and_indexes(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)
        set_review_id = "review-set"
        shot_review_id = "review-shot"
        store.conn.execute(
            """
            INSERT INTO review_records
            (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
            VALUES (?, 'artifact-1', 'legacy-revision', 'set', NULL, 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
            """,
            (set_review_id,),
        )
        store.conn.execute(
            """
            INSERT INTO review_records
            (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
            VALUES (?, 'artifact-1', 'legacy-revision', 'shot', 'SHOT_001', 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
            """,
            (shot_review_id,),
        )
        for event_type in REVIEW_EVENT_TYPES:
            store.conn.execute(
                """
                INSERT INTO review_record_events
                (event_id, review_id, event_type, actor, note, created_at)
                VALUES (?, ?, ?, 'tester', '', '2026-07-03T00:00:00Z')
                """,
                ("event-" + event_type, shot_review_id, event_type),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO review_records
                (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
                VALUES ('bad-set', 'artifact-1', 'legacy-revision', 'set', 'SHOT_001', 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO review_records
                (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
                VALUES ('bad-shot', 'artifact-1', 'legacy-revision', 'shot', NULL, 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO review_record_events
                (event_id, review_id, event_type, actor, note, created_at)
                VALUES ('bad-event', 'review-shot', 'note_added', 'tester', '', '2026-07-03T00:00:00Z')
                """
            )
        assert "scope = 'set' AND shot_id IS NULL" in table_sql(store.conn, "review_records")
        indexes = index_sql(store.conn, "review_records")
        assert "review_records_revision_shot_idx" in indexes
        assert "review_records_artifact_revision_idx" in indexes
        event_indexes = index_sql(store.conn, "review_record_events")
        assert "review_record_events_review_id_created_event_idx" in event_indexes


def test_review_record_creation_always_creates_opened_event_atomically(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)
        review = store.insert_review_record_with_opened_event(
            artifact_id="artifact-1",
            revision_id="legacy-revision",
            scope="set",
            shot_id=None,
            body="Set-level issue",
            blocking=True,
            created_by="reviewer-a",
            note="opened",
        )
        assert review.body_hash
        assert store.review_status(review.review_id) == "opened"
        assert store.open_blocking_review_count("legacy-revision") == 1
        store.insert_review_event(
            review_id=review.review_id,
            event_type="voided",
            actor="reviewer-a",
            note="",
        )
        assert store.open_blocking_review_count("legacy-revision") == 0
        store.insert_review_event(
            review_id=review.review_id,
            event_type="reopened",
            actor="reviewer-a",
            note="",
        )
        assert store.open_blocking_review_count("legacy-revision") == 1
        store.insert_review_event(
            review_id=review.review_id,
            event_type="resolved",
            actor="reviewer-b",
            note="",
        )
        assert store.open_blocking_review_count("legacy-revision") == 0


def test_review_record_creation_rolls_back_when_opened_event_fails(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)

        def fail_event_insert(**_values):
            raise RuntimeError("forced opened event insert failure")

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(store, "_insert_review_event_row", fail_event_insert)
        with pytest.raises(RuntimeError):
            store.insert_review_record_with_opened_event(
                artifact_id="artifact-1",
                revision_id="legacy-revision",
                scope="set",
                shot_id=None,
                body="Set-level issue",
                blocking=True,
                created_by="reviewer-a",
                note="opened",
            )
        monkeypatch.undo()
        assert store.conn.execute("SELECT COUNT(*) AS count FROM review_records").fetchone()["count"] == 0
        assert store.conn.execute("SELECT COUNT(*) AS count FROM review_record_events").fetchone()["count"] == 0


def test_review_status_uses_event_id_as_same_timestamp_tie_breaker(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)
        review = store.insert_review_record_with_opened_event(
            artifact_id="artifact-1",
            revision_id="legacy-revision",
            scope="shot",
            shot_id="SHOT_001",
            body="Shot-level issue",
            blocking=True,
            created_by="reviewer-a",
            note="opened",
        )
        with store.conn:
            store._insert_review_event_row(
                review_id=review.review_id,
                event_type="resolved",
                actor="reviewer-a",
                note="",
                event_id="event-a",
                created_at="9999-01-01T00:00:00.000000Z",
            )
            store._insert_review_event_row(
                review_id=review.review_id,
                event_type="reopened",
                actor="reviewer-b",
                note="",
                event_id="event-b",
                created_at="9999-01-01T00:00:00.000000Z",
            )
        assert store.review_status(review.review_id) == "reopened"
        assert store.open_blocking_review_count("legacy-revision") == 1
