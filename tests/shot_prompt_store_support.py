def table_columns(conn, table_name):
    return {
        row["name"]: dict(row)
        for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
    }


def table_sql(conn, table_name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return "" if row is None else row["sql"]


def index_sql(conn, table_name):
    return {
        row["name"]: {
            "unique": bool(row["unique"]),
            "origin": row["origin"],
            "partial": bool(row["partial"]),
            "columns": [
                column["name"]
                for column in conn.execute("PRAGMA index_info(%s)" % row["name"]).fetchall()
            ],
            "predicate_tokens": _normalized_partial_index_predicate(conn, row["name"]),
        }
        for row in conn.execute("PRAGMA index_list(%s)" % table_name).fetchall()
    }


def check_constraints(conn, table_name):
    sql = table_sql(conn, table_name)
    return [
        _normalized_sql_tokens(match)
        for match in sql.split("CHECK")
        if "(" in match
    ]


def normalized_schema_snapshot(conn):
    result = {}
    for name in _table_names(conn):
        result[name] = {
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"].upper(),
                    "notnull": row["notnull"],
                    "default": row["dflt_value"],
                    "pk": row["pk"],
                }
                for row in conn.execute("PRAGMA table_info(%s)" % name).fetchall()
            ],
            "foreign_keys": [
                dict(row)
                for row in conn.execute("PRAGMA foreign_key_list(%s)" % name).fetchall()
            ],
            "indexes": index_sql(conn, name),
            "check_constraints": check_constraints(conn, name),
        }
    return result


def snapshot_database(conn):
    tables = {}
    for name in _table_names(conn):
        tables[name] = {
            "columns": list(table_columns(conn, name)),
            "schema": normalized_schema_snapshot(conn).get(name, {}),
            "indexes": index_sql(conn, name),
            "row_count": conn.execute("SELECT COUNT(*) AS count FROM %s" % name).fetchone()[
                "count"
            ],
        }
    return {
        "tables": tables,
        "foreign_key_check": [
            dict(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()
        ],
        "transient_tables": [
            name for name in _table_names(conn) if name.endswith("_old") or name.endswith("_new")
        ],
        "legacy_revision": dict(
            conn.execute("SELECT * FROM revisions WHERE revision_id = 'legacy-revision'").fetchone()
        ),
    }


def create_phase2_legacy_db(db_path):
    from tests.test_storyboard_legacy_migration import _create_planning_baseline_legacy_db

    _create_planning_baseline_legacy_db(db_path)


def seed_phase3_store(
    store,
    *,
    revision_id="legacy-revision",
    artifact_id="artifact-1",
    artifact_type="storyboard",
):
    content_object_id = store.write_text_object("{}")
    store.ensure_artifact(artifact_id, artifact_type, "project-1", "chapter-1")
    run = store.create_run(
        run_id="run-1",
        artifact_id=artifact_id,
        project_id="project-1",
        chapter_id="chapter-1",
        skill_id="ai-drama-storyboard-design-skill",
        skill_version="v0.2.0",
        skill_hash="skill-hash",
        runtime="test-runtime",
        provider="mock",
        model="mock",
        status="COMPLETED",
        request_object_id=content_object_id,
        response_object_id=content_object_id,
        input_hash=content_object_id,
    )
    return store.insert_revision(
        revision_id=revision_id,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id="project-1",
        chapter_id="chapter-1",
        run_id=run.run_id,
        skill_id="ai-drama-storyboard-design-skill",
        skill_version="v0.2.0",
        skill_package_hash="skill-hash",
        runtime_provider="mock",
        runtime_model="mock",
        content_object_id=content_object_id,
        content_hash=content_object_id,
        raw_response_object_id=content_object_id,
        parser_version="storyboard-canonical-json-v1",
        content_profile="storyboard-canonical-v1",
    )


def _table_names(conn):
    return [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]


def _normalized_sql_tokens(sql):
    return sorted(
        set(
            sql.replace("\n", " ")
            .replace("(", " ( ")
            .replace(")", " ) ")
            .replace(",", " , ")
            .split()
        )
    )


def _normalized_partial_index_predicate(conn, index_name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    ).fetchone()
    sql = "" if row is None or row["sql"] is None else row["sql"]
    marker = " WHERE "
    upper_sql = sql.upper()
    predicate = sql[upper_sql.find(marker) + len(marker) :] if marker in upper_sql else ""
    return _normalized_sql_tokens(predicate)
