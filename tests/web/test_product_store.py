from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.services import NotFound
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


def test_list_chapters_returns_project_chapters_in_stable_position_order(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    runtime.conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
          project_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          series_canon TEXT NOT NULL,
          characters_context TEXT NOT NULL,
          production_brief TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chapters (
          chapter_id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
          title TEXT NOT NULL,
          position INTEGER NOT NULL,
          current_source_revision_id TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chapter_source_revisions (
          source_revision_id TEXT PRIMARY KEY,
          chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
          number INTEGER NOT NULL,
          object_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(chapter_id, number)
        );
        """
    )
    runtime.conn.commit()
    store = ProductStore(runtime)
    project = store.create_project(name="生死")
    other_project = store.create_project(name="旁支")

    second = store.create_chapter(project.project_id, "第二章", 2)
    first = store.create_chapter(project.project_id, "第一章", 1)
    tie = store.create_chapter(project.project_id, "第一章补充", 1)
    other = store.create_chapter(other_project.project_id, "不应出现", 1)

    chapters = store.list_chapters(project.project_id)

    assert [chapter.chapter_id for chapter in chapters] == [first.chapter_id, tie.chapter_id, second.chapter_id]
    assert other.chapter_id not in {chapter.chapter_id for chapter in chapters}


def test_list_chapters_raises_not_found_for_missing_project(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)

    try:
        store.list_chapters("missing")
    except NotFound as exc:
        assert "project not found" in str(exc)
    else:
        raise AssertionError("expected NotFound")
