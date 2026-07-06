import json
import uuid

from ai_drama_runtime.services import NotFound
from ai_drama_runtime.store import RuntimeStore, now_iso

from .models import ChapterRecord, ChapterSourceRevisionRecord, ProductionProfileRecord, ProjectRecord


class ProductStore:
    def __init__(self, runtime_store: RuntimeStore):
        self.runtime = runtime_store
        self.conn = runtime_store.conn
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(
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
              updated_at TEXT NOT NULL,
              UNIQUE(project_id, position)
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
            CREATE TABLE IF NOT EXISTS production_profiles (
              profile_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              chapter_id TEXT NOT NULL DEFAULT '',
              profile_type TEXT NOT NULL CHECK (profile_type IN ('character','scene','prop','style')),
              name TEXT NOT NULL,
              payload_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS production_profiles_scope_idx
              ON production_profiles(project_id, chapter_id, profile_type, name);
            """
        )
        self.conn.commit()

    def create_project(
        self,
        *,
        name,
        description="",
        series_canon="",
        characters_context="",
        production_brief="",
    ):
        created_at = now_iso()
        project_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO projects
            (project_id, name, description, series_canon, characters_context,
             production_brief, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                name,
                description,
                series_canon,
                characters_context,
                production_brief,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_project(project_id)

    def create_chapter(self, project_id, title, position):
        created_at = now_iso()
        chapter_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO chapters
            (chapter_id, project_id, title, position, current_source_revision_id,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, '', ?, ?)
            """,
            (chapter_id, project_id, title, position, created_at, created_at),
        )
        self.conn.commit()
        return self.get_chapter(chapter_id)

    def create_source_revision(self, chapter_id, content):
        object_id = self.runtime.write_text_object(content)
        created_at = now_iso()
        source_revision_id = uuid.uuid4().hex
        with self.conn:
            row = self.conn.execute(
                """
                SELECT COALESCE(MAX(number), 0) + 1 AS n
                FROM chapter_source_revisions
                WHERE chapter_id = ?
                """,
                (chapter_id,),
            ).fetchone()
            self.conn.execute(
                """
                INSERT INTO chapter_source_revisions
                (source_revision_id, chapter_id, number, object_id, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_revision_id, chapter_id, int(row["n"]), object_id, object_id, created_at),
            )
            self.conn.execute(
                """
                UPDATE chapters
                SET current_source_revision_id = ?, updated_at = ?
                WHERE chapter_id = ?
                """,
                (source_revision_id, created_at, chapter_id),
            )
        return self.get_source_revision(source_revision_id)

    def get_project(self, project_id):
        row = self.conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return None if row is None else ProjectRecord(**dict(row))

    def get_chapter(self, chapter_id):
        row = self.conn.execute("SELECT * FROM chapters WHERE chapter_id = ?", (chapter_id,)).fetchone()
        return None if row is None else ChapterRecord(**dict(row))

    def list_chapters(self, project_id):
        if self.get_project(project_id) is None:
            raise NotFound("project not found: %s" % project_id)
        rows = self.conn.execute(
            """
            SELECT *
            FROM chapters
            WHERE project_id = ?
            ORDER BY position ASC, created_at ASC, chapter_id ASC
            """,
            (project_id,),
        ).fetchall()
        return [ChapterRecord(**dict(row)) for row in rows]

    def get_source_revision(self, source_revision_id):
        row = self.conn.execute(
            "SELECT * FROM chapter_source_revisions WHERE source_revision_id = ?",
            (source_revision_id,),
        ).fetchone()
        return None if row is None else ChapterSourceRevisionRecord(**dict(row))

    def create_production_profile(self, *, project_id, chapter_id, profile_type, name, payload):
        created_at = now_iso()
        profile_id = uuid.uuid4().hex
        payload_object_id = self.runtime.write_text_object(_normalized_json(payload))
        self.conn.execute(
            """
            INSERT INTO production_profiles
            (profile_id, project_id, chapter_id, profile_type, name,
             payload_object_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                project_id,
                chapter_id,
                profile_type,
                name,
                payload_object_id,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_production_profile(profile_id)

    def get_production_profile(self, profile_id):
        row = self.conn.execute(
            "SELECT * FROM production_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return None if row is None else ProductionProfileRecord(**dict(row))

    def list_production_profiles(self, project_id, *, chapter_id=None, profile_type=None):
        conditions = ["project_id = ?"]
        params = [project_id]
        if chapter_id is not None:
            conditions.append("chapter_id = ?")
            params.append(chapter_id)
        if profile_type is not None:
            conditions.append("profile_type = ?")
            params.append(profile_type)
        rows = self.conn.execute(
            """
            SELECT *
            FROM production_profiles
            WHERE %s
            ORDER BY chapter_id ASC, profile_type ASC, name ASC, created_at ASC, profile_id ASC
            """
            % " AND ".join(conditions),
            params,
        ).fetchall()
        return [ProductionProfileRecord(**dict(row)) for row in rows]

    def update_production_profile_payload(self, profile_id, *, name, payload):
        updated_at = now_iso()
        payload_object_id = self.runtime.write_text_object(_normalized_json(payload))
        cursor = self.conn.execute(
            """
            UPDATE production_profiles
            SET name = ?, payload_object_id = ?, updated_at = ?
            WHERE profile_id = ?
            """,
            (name, payload_object_id, updated_at, profile_id),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_production_profile(profile_id)

    def delete_production_profile(self, profile_id):
        cursor = self.conn.execute(
            "DELETE FROM production_profiles WHERE profile_id = ?",
            (profile_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0


def _normalized_json(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
