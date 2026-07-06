import json
import sqlite3

from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app


def _create_project_and_chapter(client):
    project = client.post("/api/projects", json={"name": "生死"}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    return project, chapter


def _profile_payload(profile_type, name):
    base = {"name": name, "continuity_notes": f"{name} 连续性锁定"}
    if profile_type == "character":
        return {
            **base,
            "identity_notes": "沈家嫡女，克制坚韧",
            "appearance_notes": "清冷端正，二十岁出头",
            "costume_notes": "素青色袄裙，银簪",
        }
    if profile_type == "scene":
        return {
            **base,
            "scene_layout_notes": "沈府正厅，主座在北，屏风在东侧",
            "lighting_notes": "日间冷光，门外逆光",
        }
    if profile_type == "prop":
        return {
            **base,
            "prop_handling_notes": "玉佩始终由沈清荷贴身握持",
        }
    if profile_type == "style":
        return {
            **base,
            "style_rules": "真人写实，克制表演",
            "cinematography_rules": "中近景优先，缓慢推镜",
            "color_rules": "低饱和青灰色调",
            "negative_rules": "禁止卡通化、过度磨皮、现代服饰",
        }
    raise AssertionError(f"unexpected profile type: {profile_type}")


def test_create_update_and_list_profiles_by_chapter_and_type(client):
    project, chapter = _create_project_and_chapter(client)
    second_chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第二章", "position": 2},
    ).json()

    created = {}
    for profile_type, name in [
        ("character", "沈清荷"),
        ("scene", "沈府正厅"),
        ("prop", "传家玉佩"),
        ("style", "冷调写实"),
    ]:
        response = client.post(
            f"/api/projects/{project['project_id']}/profiles",
            json={
                "chapter_id": chapter["chapter_id"],
                "profile_type": profile_type,
                "payload": _profile_payload(profile_type, name),
            },
        )
        assert response.status_code == 200, response.text
        created[profile_type] = response.json()
        assert created[profile_type]["project_id"] == project["project_id"]
        assert created[profile_type]["chapter_id"] == chapter["chapter_id"]
        assert created[profile_type]["profile_type"] == profile_type
        assert created[profile_type]["name"] == name
        assert created[profile_type]["payload"]["name"] == name

    client.post(
        f"/api/projects/{project['project_id']}/profiles",
        json={
            "chapter_id": second_chapter["chapter_id"],
            "profile_type": "character",
            "payload": _profile_payload("character", "第二章人物"),
        },
    )

    updated_payload = {
        **_profile_payload("character", "沈清荷新版"),
        "costume_notes": "月白色披风，银簪保持不变",
    }
    update_response = client.put(
        f"/api/profiles/{created['character']['profile_id']}",
        json={"payload": updated_payload},
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["profile_id"] == created["character"]["profile_id"]
    assert updated["name"] == "沈清荷新版"
    assert updated["payload"]["costume_notes"] == "月白色披风，银簪保持不变"
    assert updated["created_at"] == created["character"]["created_at"]
    assert updated["updated_at"] >= created["character"]["updated_at"]

    list_response = client.get(
        f"/api/projects/{project['project_id']}/profiles",
        params={"chapter_id": chapter["chapter_id"], "profile_type": "character"},
    )
    assert list_response.status_code == 200, list_response.text
    profiles = list_response.json()
    assert [profile["profile_id"] for profile in profiles] == [created["character"]["profile_id"]]
    assert profiles[0]["name"] == "沈清荷新版"
    assert profiles[0]["payload"] == updated_payload


def test_profile_payload_validation_rejects_extra_and_blank_fields(client):
    project, chapter = _create_project_and_chapter(client)

    extra_response = client.post(
        f"/api/projects/{project['project_id']}/profiles",
        json={
            "chapter_id": chapter["chapter_id"],
            "profile_type": "prop",
            "payload": {
                **_profile_payload("prop", "传家玉佩"),
                "unexpected": "not allowed",
            },
        },
    )
    assert extra_response.status_code == 422

    blank_response = client.post(
        f"/api/projects/{project['project_id']}/profiles",
        json={
            "chapter_id": chapter["chapter_id"],
            "profile_type": "scene",
            "payload": {
                **_profile_payload("scene", "沈府正厅"),
                "lighting_notes": " ",
            },
        },
    )
    assert blank_response.status_code == 422


def test_profile_project_and_chapter_scope_is_enforced(client):
    project, chapter = _create_project_and_chapter(client)
    other_project = client.post("/api/projects", json={"name": "旁支"}).json()
    other_chapter = client.post(
        f"/api/projects/{other_project['project_id']}/chapters",
        json={"title": "外部章节", "position": 1},
    ).json()

    cross_project_create = client.post(
        f"/api/projects/{project['project_id']}/profiles",
        json={
            "chapter_id": other_chapter["chapter_id"],
            "profile_type": "character",
            "payload": _profile_payload("character", "错误人物"),
        },
    )
    assert cross_project_create.status_code == 404

    created = client.post(
        f"/api/projects/{project['project_id']}/profiles",
        json={
            "chapter_id": chapter["chapter_id"],
            "profile_type": "character",
            "payload": _profile_payload("character", "沈清荷"),
        },
    ).json()

    cross_project_list = client.get(
        f"/api/projects/{project['project_id']}/profiles",
        params={"chapter_id": other_chapter["chapter_id"]},
    )
    assert cross_project_list.status_code == 404

    own_list = client.get(
        f"/api/projects/{project['project_id']}/profiles",
        params={"chapter_id": chapter["chapter_id"]},
    )
    assert [profile["profile_id"] for profile in own_list.json()] == [created["profile_id"]]
    assert client.get("/api/projects/missing/profiles").status_code == 404
    assert client.put("/api/profiles/missing", json={"payload": _profile_payload("prop", "玉佩")}).status_code == 404


def test_delete_profile_removes_it_from_project_lists(client):
    project, chapter = _create_project_and_chapter(client)
    created = client.post(
        f"/api/projects/{project['project_id']}/profiles",
        json={
            "chapter_id": chapter["chapter_id"],
            "profile_type": "prop",
            "payload": _profile_payload("prop", "传家玉佩"),
        },
    ).json()

    delete_response = client.delete(f"/api/profiles/{created['profile_id']}")
    assert delete_response.status_code == 204

    list_response = client.get(
        f"/api/projects/{project['project_id']}/profiles",
        params={"chapter_id": chapter["chapter_id"]},
    )
    assert list_response.status_code == 200
    assert list_response.json() == []
    assert client.delete("/api/profiles/missing").status_code == 404


def test_profile_payload_is_stored_as_normalized_json(tmp_path):
    data_root = tmp_path / "runtime-data"
    app = create_app(data_root=data_root, skills_root="skills")
    payload = _profile_payload("style", "冷调写实")

    with TestClient(app) as client:
        project, chapter = _create_project_and_chapter(client)
        response = client.post(
            f"/api/projects/{project['project_id']}/profiles",
            json={
                "chapter_id": chapter["chapter_id"],
                "profile_type": "style",
                "payload": payload,
            },
        )
        assert response.status_code == 200, response.text
        profile = response.json()

    conn = sqlite3.connect(data_root / "runtime.db")
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT payload_object_id FROM production_profiles WHERE profile_id = ?",
            (profile["profile_id"],),
        ).fetchone()
    finally:
        conn.close()

    with RuntimeStore(data_root / "runtime.db", data_root / "objects") as runtime_store:
        stored = runtime_store.read_text(row["payload_object_id"])

    assert stored == json.dumps(profile["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
