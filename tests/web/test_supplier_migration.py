from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


def test_supplier_core_migration_is_replayable_and_preserves_legacy_rows(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    runtime.conn.execute(
        "INSERT INTO artifacts (artifact_id, artifact_type, project_id, chapter_id, created_at) "
        "VALUES ('legacy-artifact', 'script', 'project-1', 'chapter-1', '2026-07-12T00:00:00Z')"
    )
    runtime.conn.commit()

    ProductStore(runtime)
    first_counts = {
        table: runtime.conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in (
            "schema_migrations",
            "suppliers",
            "supplier_versions",
            "supplier_config_revisions",
            "credential_versions",
            "credential_migration_journal",
            "script_generation_runs",
            "script_generation_events",
        )
    }
    ProductStore(runtime)
    second_counts = {
        table: runtime.conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in first_counts
    }

    assert first_counts == second_counts
    assert runtime.conn.execute(
        "SELECT artifact_id FROM artifacts WHERE artifact_id = 'legacy-artifact'"
    ).fetchone()["artifact_id"] == "legacy-artifact"
    assert runtime.conn.execute(
        "SELECT migration_id FROM schema_migrations WHERE migration_id = 'm6a_supplier_core_v1'"
    ).fetchone()["migration_id"] == "m6a_supplier_core_v1"
    assert runtime.conn.execute(
        "SELECT migration_id FROM schema_migrations WHERE migration_id = 'streaming_script_generation_v1'"
    ).fetchone()["migration_id"] == "streaming_script_generation_v1"
