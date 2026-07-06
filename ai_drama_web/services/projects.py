import sqlite3

from ai_drama_runtime.store import RuntimeStore

from ai_drama_web.models import ChapterRecord, ProjectRecord
from ai_drama_web.store import ProductStore


class MissingRecord(Exception):
    pass


class DuplicateChapterPosition(Exception):
    pass


class ProjectService:
    def __init__(self, product_store: ProductStore, runtime_store: RuntimeStore):
        self.product_store = product_store
        self.runtime_store = runtime_store

    def create_project(self, data):
        return self.product_store.create_project(**data.model_dump())

    def list_projects(self):
        rows = self.product_store.conn.execute("SELECT * FROM projects ORDER BY created_at, project_id").fetchall()
        return [ProjectRecord(**dict(row)) for row in rows]

    def get_project(self, project_id):
        project = self.product_store.get_project(project_id)
        if project is None:
            raise MissingRecord
        return project

    def create_chapter(self, project_id, data):
        if self.product_store.get_project(project_id) is None:
            raise MissingRecord
        try:
            return self.product_store.create_chapter(project_id, data.title, data.position)
        except sqlite3.IntegrityError as exc:
            raise DuplicateChapterPosition from exc

    def list_chapters(self, project_id):
        try:
            return self.product_store.list_chapters(project_id)
        except KeyError as exc:
            raise MissingRecord from exc

    def get_chapter(self, chapter_id) -> tuple[ChapterRecord, str]:
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord
        source_text = ""
        if chapter.current_source_revision_id:
            source = self.product_store.get_source_revision(chapter.current_source_revision_id)
            if source is not None:
                source_text = self.runtime_store.read_text(source.object_id)
        return chapter, source_text

    def create_source_revision(self, chapter_id, data):
        if self.product_store.get_chapter(chapter_id) is None:
            raise MissingRecord
        return self.product_store.create_source_revision(chapter_id, data.content)
