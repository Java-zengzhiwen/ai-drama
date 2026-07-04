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
