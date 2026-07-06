import hashlib
import json
import sqlite3

from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app
from ai_drama_web.store import ProductStore


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _create_project_and_chapter(client, *, project_name="生死", chapter_title="第一章", position=1):
    project = client.post("/api/projects", json={"name": project_name}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": chapter_title, "position": position},
    ).json()
    return project, chapter


def _character_profile_payload(name):
    return {
        "name": name,
        "continuity_notes": f"{name} 资产绑定连续性",
        "identity_notes": "沈家嫡女，克制坚韧",
        "appearance_notes": "清冷端正，二十岁出头",
        "costume_notes": "素青色袄裙，银簪",
    }


def _create_character_profile(client, project_id, chapter_id, *, name="沈清荷"):
    response = client.post(
        f"/api/projects/{project_id}/profiles",
        json={
            "chapter_id": chapter_id,
            "profile_type": "character",
            "payload": _character_profile_payload(name),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_scene_profile(client, project_id, chapter_id, *, name="沈府正厅"):
    response = client.post(
        f"/api/projects/{project_id}/profiles",
        json={
            "chapter_id": chapter_id,
            "profile_type": "scene",
            "payload": {
                "name": name,
                "continuity_notes": f"{name} 布局连续性",
                "scene_layout_notes": "主座在北，屏风在东侧",
                "lighting_notes": "日间冷光，门外逆光",
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_prop_profile(client, project_id, chapter_id, *, name="传家玉佩"):
    response = client.post(
        f"/api/projects/{project_id}/profiles",
        json={
            "chapter_id": chapter_id,
            "profile_type": "prop",
            "payload": {
                "name": name,
                "continuity_notes": f"{name} 状态连续性",
                "prop_handling_notes": "始终由沈清荷贴身握持",
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _upload_png(client, chapter_id, *, name="沈清荷定妆照", metadata=None):
    data = {
        "asset_type": "character_reference",
        "name": name,
    }
    if metadata is not None:
        data["metadata"] = json.dumps(metadata)
    return client.post(
        f"/api/chapters/{chapter_id}/assets",
        data=data,
        files={"file": ("reference.png", PNG_BYTES, "image/png")},
    )


def test_png_upload_stores_exact_hash_metadata_and_lists_only_that_chapter(tmp_path):
    data_root = tmp_path / "runtime-data"
    app = create_app(data_root=data_root, skills_root="skills")

    with TestClient(app) as client:
        project, chapter = _create_project_and_chapter(client)
        second_chapter = client.post(
            f"/api/projects/{project['project_id']}/chapters",
            json={"title": "第二章", "position": 2},
        ).json()

        metadata = {"z": 2, "camera": {"lens": "50mm"}}
        upload = _upload_png(client, chapter["chapter_id"], metadata=metadata)
        assert upload.status_code == 200, upload.text
        asset = upload.json()

        assert asset["project_id"] == project["project_id"]
        assert asset["chapter_id"] == chapter["chapter_id"]
        assert asset["asset_type"] == "character_reference"
        assert asset["name"] == "沈清荷定妆照"
        assert asset["object_id"] == hashlib.sha256(PNG_BYTES).hexdigest()
        assert asset["media_type"] == "image/png"
        assert asset["width"] == 0
        assert asset["height"] == 0
        assert asset["status"] == "draft"
        assert asset["source_type"] == "upload"
        assert asset["source_job_id"] == ""
        assert asset["metadata"] == metadata

        other_upload = _upload_png(client, second_chapter["chapter_id"], name="第二章定妆照")
        assert other_upload.status_code == 200, other_upload.text

        list_response = client.get(f"/api/chapters/{chapter['chapter_id']}/assets")
        assert list_response.status_code == 200, list_response.text
        assert [item["asset_id"] for item in list_response.json()] == [asset["asset_id"]]

        empty_second_project = client.post("/api/projects", json={"name": "旁支"}).json()
        empty_second_chapter = client.post(
            f"/api/projects/{empty_second_project['project_id']}/chapters",
            json={"title": "旁支第一章", "position": 1},
        ).json()
        assert client.get(f"/api/chapters/{empty_second_chapter['chapter_id']}/assets").json() == []

    conn = sqlite3.connect(data_root / "runtime.db")
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT object_id, metadata_object_id FROM assets WHERE asset_id = ?",
            (asset["asset_id"],),
        ).fetchone()
    finally:
        conn.close()

    with RuntimeStore(data_root / "runtime.db", data_root / "objects") as runtime_store:
        assert row["object_id"] == hashlib.sha256(PNG_BYTES).hexdigest()
        assert runtime_store.read_bytes_object(row["object_id"]) == PNG_BYTES
        assert runtime_store.read_text(row["metadata_object_id"]) == json.dumps(
            metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )


def test_bind_to_character_profile_is_idempotent_and_state_transitions_work(client):
    project, chapter = _create_project_and_chapter(client)
    profile = _create_character_profile(client, project["project_id"], chapter["chapter_id"])
    asset = _upload_png(client, chapter["chapter_id"]).json()

    payload = {"target_type": "character", "target_id": profile["profile_id"], "role": "primary_reference"}
    first_bind = client.post(f"/api/assets/{asset['asset_id']}/bindings", json=payload)
    assert first_bind.status_code == 200, first_bind.text
    binding = first_bind.json()
    assert binding["asset_id"] == asset["asset_id"]
    assert binding["target_type"] == "character"
    assert binding["target_id"] == profile["profile_id"]
    assert binding["role"] == "primary_reference"

    duplicate_bind = client.post(f"/api/assets/{asset['asset_id']}/bindings", json=payload)
    assert duplicate_bind.status_code == 200, duplicate_bind.text
    assert duplicate_bind.json()["binding_id"] == binding["binding_id"]

    usable = client.post(f"/api/assets/{asset['asset_id']}/mark-usable")
    assert usable.status_code == 200, usable.text
    assert usable.json()["status"] == "usable"

    missing_reason = client.post(f"/api/assets/{asset['asset_id']}/reject")
    assert missing_reason.status_code == 422

    rejected = client.post(f"/api/assets/{asset['asset_id']}/reject", json={"reason": "服装细节漂移"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["metadata"]["rejection_reason"] == "服装细节漂移"


def test_scene_and_prop_bindings_are_scoped_and_shot_binding_requires_known_target(client):
    project, chapter = _create_project_and_chapter(client)
    scene = _create_scene_profile(client, project["project_id"], chapter["chapter_id"])
    prop = _create_prop_profile(client, project["project_id"], chapter["chapter_id"])
    asset = _upload_png(client, chapter["chapter_id"]).json()

    scene_bind = client.post(
        f"/api/assets/{asset['asset_id']}/bindings",
        json={"target_type": "scene", "target_id": scene["profile_id"], "role": "layout_reference"},
    )
    assert scene_bind.status_code == 200, scene_bind.text

    prop_bind = client.post(
        f"/api/assets/{asset['asset_id']}/bindings",
        json={"target_type": "prop", "target_id": prop["profile_id"], "role": "handling_reference"},
    )
    assert prop_bind.status_code == 200, prop_bind.text

    missing_shot = client.post(
        f"/api/assets/{asset['asset_id']}/bindings",
        json={"target_type": "shot", "target_id": "missing-shot", "role": "keyframe"},
    )
    assert missing_shot.status_code == 404


def test_current_adopted_binding_is_explicit_and_unique_per_target_role(client):
    project, chapter = _create_project_and_chapter(client)
    profile = _create_character_profile(client, project["project_id"], chapter["chapter_id"])
    first_asset = _upload_png(client, chapter["chapter_id"], name="版本一").json()
    second_asset = _upload_png(client, chapter["chapter_id"], name="版本二").json()

    draft_current = client.post(
        f"/api/assets/{first_asset['asset_id']}/bindings",
        json={
            "target_type": "character",
            "target_id": profile["profile_id"],
            "role": "primary_reference",
            "is_current": True,
        },
    )
    assert draft_current.status_code == 409

    client.post(f"/api/assets/{first_asset['asset_id']}/mark-usable")
    client.post(f"/api/assets/{second_asset['asset_id']}/mark-usable")

    first_bind = client.post(
        f"/api/assets/{first_asset['asset_id']}/bindings",
        json={
            "target_type": "character",
            "target_id": profile["profile_id"],
            "role": "primary_reference",
            "is_current": True,
        },
    )
    assert first_bind.status_code == 200, first_bind.text
    assert first_bind.json()["is_current"] is True

    second_bind = client.post(
        f"/api/assets/{second_asset['asset_id']}/bindings",
        json={
            "target_type": "character",
            "target_id": profile["profile_id"],
            "role": "primary_reference",
            "is_current": True,
        },
    )
    assert second_bind.status_code == 200, second_bind.text
    assert second_bind.json()["is_current"] is True

    duplicate_first = client.post(
        f"/api/assets/{first_asset['asset_id']}/bindings",
        json={
            "target_type": "character",
            "target_id": profile["profile_id"],
            "role": "primary_reference",
            "is_current": False,
        },
    )
    assert duplicate_first.status_code == 200, duplicate_first.text
    assert duplicate_first.json()["binding_id"] == first_bind.json()["binding_id"]
    assert duplicate_first.json()["is_current"] is False

    current_reject_without_reason = client.post(f"/api/assets/{second_asset['asset_id']}/reject")
    assert current_reject_without_reason.status_code == 422

    rejected = client.post(f"/api/assets/{first_asset['asset_id']}/reject", json={"reason": "脸部漂移"}).json()
    rejected_current = client.post(
        f"/api/assets/{rejected['asset_id']}/bindings",
        json={
            "target_type": "character",
            "target_id": profile["profile_id"],
            "role": "primary_reference",
            "is_current": True,
        },
    )
    assert rejected_current.status_code == 409


def test_get_asset_content_returns_original_bytes_and_media_type(client):
    _, chapter = _create_project_and_chapter(client)
    asset = _upload_png(client, chapter["chapter_id"]).json()

    response = client.get(f"/api/assets/{asset['asset_id']}/content")

    assert response.status_code == 200, response.text
    assert response.content == PNG_BYTES
    assert response.headers["content-type"] == "image/png"


def test_upload_rejects_unsupported_media_type(client):
    _, chapter = _create_project_and_chapter(client)

    response = client.post(
        f"/api/chapters/{chapter['chapter_id']}/assets",
        data={"asset_type": "character_reference", "name": "错误素材"},
        files={"file": ("reference.gif", b"GIF89a", "image/gif")},
    )

    assert response.status_code == 415


def test_upload_rejects_files_over_configured_size_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_MAX_ASSET_UPLOAD_BYTES", str(len(PNG_BYTES) - 1))
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app) as client:
        _, chapter = _create_project_and_chapter(client)
        response = _upload_png(client, chapter["chapter_id"])

    assert response.status_code == 413


def test_upload_reads_only_one_byte_past_configured_size_limit(tmp_path, monkeypatch):
    oversized_payload = PNG_BYTES + b"x" * 128
    monkeypatch.setenv("AI_DRAMA_MAX_ASSET_UPLOAD_BYTES", str(len(PNG_BYTES)))
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app) as client:
        _, chapter = _create_project_and_chapter(client)
        response = client.post(
            f"/api/chapters/{chapter['chapter_id']}/assets",
            data={"asset_type": "character_reference", "name": "超限素材"},
            files={"file": ("reference.png", oversized_payload, "image/png")},
        )

    assert response.status_code == 413


def test_missing_chapter_and_asset_operations_return_404(client):
    assert client.get("/api/chapters/missing/assets").status_code == 404

    missing_upload = client.post(
        "/api/chapters/missing/assets",
        data={"asset_type": "character_reference", "name": "不存在章节素材"},
        files={"file": ("reference.png", PNG_BYTES, "image/png")},
    )
    assert missing_upload.status_code == 404

    assert client.post("/api/assets/missing/bindings", json={"target_type": "character", "target_id": "x", "role": "r"}).status_code == 404
    assert client.post("/api/assets/missing/mark-usable").status_code == 404
    assert client.post("/api/assets/missing/reject").status_code == 404
    assert client.get("/api/assets/missing/content").status_code == 404


def test_asset_schemas_reject_extra_fields(client):
    _, chapter = _create_project_and_chapter(client)
    asset = _upload_png(client, chapter["chapter_id"]).json()

    extra_binding = client.post(
        f"/api/assets/{asset['asset_id']}/bindings",
        json={"target_type": "character", "target_id": "x", "role": "r", "unexpected": True},
    )

    assert extra_binding.status_code == 422


def test_asset_binding_schema_adds_current_column_to_existing_tables(tmp_path):
    data_root = tmp_path / "runtime-data"
    with RuntimeStore(data_root / "runtime.db", data_root / "objects"):
        pass

    conn = sqlite3.connect(data_root / "runtime.db")
    try:
        conn.executescript(
            """
            CREATE TABLE asset_bindings (
              binding_id TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL REFERENCES assets(asset_id) ON DELETE RESTRICT,
              target_type TEXT NOT NULL CHECK (target_type IN ('character','scene','prop','shot')),
              target_id TEXT NOT NULL,
              role TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(asset_id, target_type, target_id, role)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    app = create_app(data_root=data_root, skills_root="skills")
    with TestClient(app):
        pass

    conn = sqlite3.connect(data_root / "runtime.db")
    conn.row_factory = sqlite3.Row
    try:
        columns = conn.execute("PRAGMA table_info(asset_bindings)").fetchall()
        index = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'asset_bindings_current_role_idx'"
        ).fetchone()
    finally:
        conn.close()

    assert "is_current" in {column["name"] for column in columns}
    assert index is not None


def test_asset_binding_schema_normalizes_duplicate_current_rows_before_index(tmp_path):
    data_root = tmp_path / "runtime-data"
    with RuntimeStore(data_root / "runtime.db", data_root / "objects") as runtime_store:
        ProductStore(runtime_store)

    conn = sqlite3.connect(data_root / "runtime.db")
    try:
        conn.executescript(
            """
            DROP INDEX IF EXISTS asset_bindings_current_role_idx;
            DROP TABLE asset_bindings;
            INSERT INTO projects
              (project_id, name, description, series_canon, characters_context, production_brief, created_at, updated_at)
            VALUES
              ('p', '项目', '', '', '', '', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z');
            INSERT INTO chapters
              (chapter_id, project_id, title, position, current_source_revision_id, created_at, updated_at)
            VALUES
              ('c', 'p', '第一章', 1, '', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z');
            INSERT INTO assets
              (asset_id, project_id, chapter_id, asset_type, name, object_id, media_type,
               width, height, status, source_type, source_job_id, metadata_object_id, created_at, updated_at)
            VALUES
              ('a1', 'p', 'c', 'character_reference', '旧版本', 'o1', 'image/png', 0, 0, 'usable', 'upload', '', 'm1', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z'),
              ('a2', 'p', 'c', 'character_reference', '新版本', 'o2', 'image/png', 0, 0, 'usable', 'upload', '', 'm2', '2026-07-02T00:00:00Z', '2026-07-02T00:00:00Z');
            CREATE TABLE asset_bindings (
              binding_id TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL REFERENCES assets(asset_id) ON DELETE RESTRICT,
              target_type TEXT NOT NULL CHECK (target_type IN ('character','scene','prop','shot')),
              target_id TEXT NOT NULL,
              role TEXT NOT NULL,
              is_current INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              UNIQUE(asset_id, target_type, target_id, role)
            );
            INSERT INTO asset_bindings
              (binding_id, asset_id, target_type, target_id, role, is_current, created_at)
            VALUES
              ('older', 'a1', 'character', 'p1', 'primary_reference', 1, '2026-07-01T00:00:00Z'),
              ('newer', 'a2', 'character', 'p1', 'primary_reference', 1, '2026-07-02T00:00:00Z');
            """
        )
        conn.commit()
    finally:
        conn.close()

    app = create_app(data_root=data_root, skills_root="skills")
    with TestClient(app):
        pass

    conn = sqlite3.connect(data_root / "runtime.db")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT binding_id, is_current
            FROM asset_bindings
            ORDER BY binding_id
            """
        ).fetchall()
        index = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'asset_bindings_current_role_idx'"
        ).fetchone()
    finally:
        conn.close()

    assert {row["binding_id"]: row["is_current"] for row in rows} == {"newer": 1, "older": 0}
    assert index is not None
