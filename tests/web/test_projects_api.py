def test_create_project_chapter_and_source(client):
    project_response = client.post(
        "/api/projects",
        json={
            "name": "生死",
            "description": "古装重生短剧",
            "series_canon": "明代商贾世界",
            "characters_context": "沈清荷、沈清莲",
            "production_brief": "真人写实，16:9",
        },
    )
    assert project_response.status_code == 200
    project = project_response.json()

    projects = client.get("/api/projects")
    assert projects.status_code == 200
    assert [item["project_id"] for item in projects.json()] == [project["project_id"]]

    fetched_project = client.get(f"/api/projects/{project['project_id']}")
    assert fetched_project.status_code == 200
    assert fetched_project.json()["name"] == "生死"

    chapter_response = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    )
    assert chapter_response.status_code == 200
    chapter = chapter_response.json()

    source_response = client.post(
        f"/api/chapters/{chapter['chapter_id']}/source-revisions",
        json={"content": "第一章正文"},
    )
    assert source_response.status_code == 200
    source = source_response.json()
    assert source["chapter_id"] == chapter["chapter_id"]

    fetched_chapter = client.get(f"/api/chapters/{chapter['chapter_id']}")
    assert fetched_chapter.status_code == 200
    assert fetched_chapter.json()["source_text"] == "第一章正文"


def test_project_chapter_source_validation_rejects_blank_values(client):
    assert client.post("/api/projects", json={"name": " "}).status_code == 422

    project = client.post("/api/projects", json={"name": "生死"}).json()
    assert (
        client.post(
            f"/api/projects/{project['project_id']}/chapters",
            json={"title": "", "position": 1},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/projects/{project['project_id']}/chapters",
            json={"title": "第一章", "position": 0},
        ).status_code
        == 422
    )

    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    assert (
        client.post(
            f"/api/chapters/{chapter['chapter_id']}/source-revisions",
            json={"content": " "},
        ).status_code
        == 422
    )


def test_missing_records_return_404(client):
    assert client.get("/api/projects/missing").status_code == 404
    assert (
        client.post(
            "/api/projects/missing/chapters",
            json={"title": "第一章", "position": 1},
        ).status_code
        == 404
    )
    assert client.get("/api/chapters/missing").status_code == 404
    assert (
        client.post(
            "/api/chapters/missing/source-revisions",
            json={"content": "第一章正文"},
        ).status_code
        == 404
    )


def test_duplicate_chapter_position_returns_409(client):
    project = client.post("/api/projects", json={"name": "生死"}).json()
    payload = {"title": "第一章", "position": 1}
    assert client.post(f"/api/projects/{project['project_id']}/chapters", json=payload).status_code == 200
    assert client.post(f"/api/projects/{project['project_id']}/chapters", json=payload).status_code == 409
