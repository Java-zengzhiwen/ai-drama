from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


def test_project_chapter_and_source_revision_are_persisted(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)

    project = store.create_project(
        name="生死",
        description="古装重生短剧",
        series_canon="明代商贾世界",
        characters_context="沈清荷、沈清莲",
        production_brief="真人写实，16:9，低饱和",
    )
    chapter = store.create_chapter(project.project_id, "第一章", 1)
    source = store.create_source_revision(chapter.chapter_id, "第一章正文")

    assert store.get_project(project.project_id).name == "生死"
    assert store.get_chapter(chapter.chapter_id).current_source_revision_id == source.source_revision_id
    assert runtime.read_text(source.object_id) == "第一章正文"


def test_list_chapters_returns_persisted_project_chapters_in_stable_position_order(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="生死")
    other_project = store.create_project(name="旁支")
    third = store.create_chapter(project.project_id, "第三章", 3)
    first = store.create_chapter(project.project_id, "第一章", 1)
    second = store.create_chapter(project.project_id, "第二章", 2)
    store.create_chapter(other_project.project_id, "其他项目第一章", 1)

    chapters = store.list_chapters(project.project_id)

    assert [chapter.chapter_id for chapter in chapters] == [
        first.chapter_id,
        second.chapter_id,
        third.chapter_id,
    ]
    assert {chapter.project_id for chapter in chapters} == {project.project_id}


def test_list_chapters_rejects_missing_project(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)

    try:
        store.list_chapters("missing-project")
    except KeyError as exc:
        assert "missing-project" in str(exc)
    else:
        raise AssertionError("missing project did not raise KeyError")
