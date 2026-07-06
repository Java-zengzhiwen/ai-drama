import json
import uuid

from ai_drama_runtime.services import NotFound
from ai_drama_runtime.store import RuntimeStore, now_iso

from .models import (
    AssetBindingRecord,
    AssetRecord,
    ChapterRecord,
    ChapterSourceRevisionRecord,
    ProductionProfileRecord,
    ProjectRecord,
)


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
            CREATE TABLE IF NOT EXISTS assets (
              asset_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              chapter_id TEXT NOT NULL DEFAULT '',
              asset_type TEXT NOT NULL CHECK (asset_type IN ('character_reference','character_outfit','scene_reference','scene_angle','prop_reference','shot_keyframe')),
              name TEXT NOT NULL,
              object_id TEXT NOT NULL,
              media_type TEXT NOT NULL,
              width INTEGER NOT NULL DEFAULT 0,
              height INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL CHECK (status IN ('draft','generating','usable','rejected','failed')),
              source_type TEXT NOT NULL CHECK (source_type IN ('upload','agnes','derived')),
              source_job_id TEXT NOT NULL DEFAULT '',
              metadata_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS asset_bindings (
              binding_id TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL REFERENCES assets(asset_id) ON DELETE RESTRICT,
              project_id TEXT NOT NULL DEFAULT '',
              chapter_id TEXT NOT NULL DEFAULT '',
              target_type TEXT NOT NULL CHECK (target_type IN ('character','scene','prop','shot')),
              target_id TEXT NOT NULL,
              role TEXT NOT NULL,
              is_current INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              UNIQUE(asset_id, target_type, target_id, role)
            );
            CREATE TABLE IF NOT EXISTS asset_requirement_sets (
              requirement_set_id TEXT PRIMARY KEY,
              chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
              storyboard_revision_id TEXT NOT NULL,
              content_object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        self._ensure_column("asset_bindings", "is_current", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("asset_bindings", "project_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("asset_bindings", "chapter_id", "TEXT NOT NULL DEFAULT ''")
        self._backfill_asset_binding_scope()
        self._normalize_current_asset_bindings()
        self.conn.execute("DROP INDEX IF EXISTS asset_bindings_current_role_idx")
        self.conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS asset_bindings_current_role_idx
              ON asset_bindings(project_id, chapter_id, target_type, target_id, role)
              WHERE is_current = 1
            """
        )
        self.conn.commit()

    def _ensure_column(self, table_name, column_name, definition):
        rows = self.conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
        if any(row["name"] == column_name for row in rows):
            return
        self.conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table_name, column_name, definition))

    def _normalize_current_asset_bindings(self):
        self.conn.execute(
            """
            WITH ranked AS (
              SELECT
                binding_id,
                ROW_NUMBER() OVER (
                  PARTITION BY project_id, chapter_id, target_type, target_id, role
                  ORDER BY created_at DESC, binding_id DESC
                ) AS current_rank
              FROM asset_bindings
              WHERE is_current = 1
            )
            UPDATE asset_bindings
            SET is_current = 0
            WHERE binding_id IN (
              SELECT binding_id FROM ranked WHERE current_rank > 1
            )
            """
        )

    def _backfill_asset_binding_scope(self):
        self.conn.execute(
            """
            UPDATE asset_bindings
            SET
              project_id = (
                SELECT assets.project_id FROM assets WHERE assets.asset_id = asset_bindings.asset_id
              ),
              chapter_id = (
                SELECT assets.chapter_id FROM assets WHERE assets.asset_id = asset_bindings.asset_id
              )
            WHERE project_id = '' OR chapter_id = ''
            """
        )

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

    def create_uploaded_asset(self, *, project_id, chapter_id, asset_type, name, data, media_type, metadata):
        created_at = now_iso()
        asset_id = uuid.uuid4().hex
        object_id = self.runtime.write_bytes_object(data)
        metadata_object_id = self.runtime.write_text_object(_normalized_json(metadata))
        self.conn.execute(
            """
            INSERT INTO assets
            (asset_id, project_id, chapter_id, asset_type, name, object_id,
             media_type, width, height, status, source_type, source_job_id,
             metadata_object_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'draft', 'upload', '', ?, ?, ?)
            """,
            (
                asset_id,
                project_id,
                chapter_id,
                asset_type,
                name,
                object_id,
                media_type,
                metadata_object_id,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_asset(asset_id)

    def create_generated_asset(
        self,
        *,
        project_id,
        chapter_id,
        asset_type,
        name,
        data,
        media_type,
        source_job_id,
        metadata,
    ):
        created_at = now_iso()
        asset_id = uuid.uuid4().hex
        object_id = self.runtime.write_bytes_object(data)
        metadata_object_id = self.runtime.write_text_object(_normalized_json(metadata))
        self.conn.execute(
            """
            INSERT INTO assets
            (asset_id, project_id, chapter_id, asset_type, name, object_id,
             media_type, width, height, status, source_type, source_job_id,
             metadata_object_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'draft', 'agnes', ?, ?, ?, ?)
            """,
            (
                asset_id,
                project_id,
                chapter_id,
                asset_type,
                name,
                object_id,
                media_type,
                source_job_id,
                metadata_object_id,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_asset(asset_id)

    def get_asset(self, asset_id):
        row = self.conn.execute(
            "SELECT * FROM assets WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()
        return None if row is None else AssetRecord(**dict(row))

    def list_assets_for_chapter(self, chapter_id):
        rows = self.conn.execute(
            """
            SELECT *
            FROM assets
            WHERE chapter_id = ?
            ORDER BY created_at ASC, asset_id ASC
            """,
            (chapter_id,),
        ).fetchall()
        return [AssetRecord(**dict(row)) for row in rows]

    def update_asset_status(self, asset_id, status, *, metadata=None):
        updated_at = now_iso()
        metadata_object_id = None if metadata is None else self.runtime.write_text_object(_normalized_json(metadata))
        if metadata_object_id is not None:
            cursor = self.conn.execute(
                """
                UPDATE assets
                SET status = ?, metadata_object_id = ?, updated_at = ?
                WHERE asset_id = ?
                """,
                (status, metadata_object_id, updated_at, asset_id),
            )
        else:
            cursor = self.conn.execute(
                """
                UPDATE assets
                SET status = ?, updated_at = ?
                WHERE asset_id = ?
                """,
                (status, updated_at, asset_id),
            )
        self.conn.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_asset(asset_id)

    def create_asset_binding(self, *, asset_id, target_type, target_id, role, is_current=False):
        asset = self.get_asset(asset_id)
        if asset is None:
            return None
        created_at = now_iso()
        binding_id = uuid.uuid4().hex
        current_value = 1 if is_current else 0
        with self.conn:
            if current_value:
                self.conn.execute(
                    """
                    UPDATE asset_bindings
                    SET is_current = 0
                    WHERE project_id = ? AND chapter_id = ?
                      AND target_type = ? AND target_id = ? AND role = ? AND is_current = 1
                    """,
                    (asset.project_id, asset.chapter_id, target_type, target_id, role),
                )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO asset_bindings
                (binding_id, asset_id, project_id, chapter_id, target_type, target_id, role, is_current, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding_id,
                    asset_id,
                    asset.project_id,
                    asset.chapter_id,
                    target_type,
                    target_id,
                    role,
                    current_value,
                    created_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE asset_bindings
                SET is_current = ?, project_id = ?, chapter_id = ?
                WHERE asset_id = ? AND target_type = ? AND target_id = ? AND role = ?
                """,
                (current_value, asset.project_id, asset.chapter_id, asset_id, target_type, target_id, role),
            )
        row = self.conn.execute(
            """
            SELECT *
            FROM asset_bindings
            WHERE asset_id = ? AND target_type = ? AND target_id = ? AND role = ?
            """,
            (asset_id, target_type, target_id, role),
        ).fetchone()
        return AssetBindingRecord(**dict(row))

    def asset_has_current_binding(self, asset_id):
        row = self.conn.execute(
            """
            SELECT 1
            FROM asset_bindings
            WHERE asset_id = ? AND is_current = 1
            LIMIT 1
            """,
            (asset_id,),
        ).fetchone()
        return row is not None

    def clear_current_asset_bindings(self, asset_id):
        self.conn.execute(
            """
            UPDATE asset_bindings
            SET is_current = 0
            WHERE asset_id = ? AND is_current = 1
            """,
            (asset_id,),
        )
        self.conn.commit()

    def asset_bindings_for_requirement(self, *, project_id, chapter_id, target_type, target_id, role, asset_type):
        rows = self.conn.execute(
            """
            SELECT
              assets.asset_id,
              assets.asset_type,
              assets.status,
              assets.chapter_id,
              asset_bindings.binding_id,
              asset_bindings.target_type,
              asset_bindings.target_id,
              asset_bindings.role,
              asset_bindings.is_current,
              asset_bindings.created_at
            FROM asset_bindings
            JOIN assets ON assets.asset_id = asset_bindings.asset_id
            WHERE assets.project_id = ?
              AND asset_bindings.target_type = ?
              AND asset_bindings.target_id = ?
              AND asset_bindings.role = ?
              AND assets.asset_type = ?
              AND assets.chapter_id IN ('', ?)
            ORDER BY asset_bindings.is_current DESC, assets.updated_at DESC, asset_bindings.created_at DESC, assets.asset_id ASC
            """,
            (project_id, target_type, target_id, role, asset_type, chapter_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_asset_requirement_set(self, *, chapter_id, storyboard_revision_id, payload):
        created_at = now_iso()
        requirement_set_id = uuid.uuid4().hex
        content_text = _normalized_json(payload)
        content_object_id = self.runtime.write_text_object(content_text)
        content_hash = content_object_id
        self.conn.execute(
            """
            INSERT INTO asset_requirement_sets
            (requirement_set_id, chapter_id, storyboard_revision_id, content_object_id, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (requirement_set_id, chapter_id, storyboard_revision_id, content_object_id, content_hash, created_at),
        )
        self.conn.commit()
        return {
            "requirement_set_id": requirement_set_id,
            "chapter_id": chapter_id,
            "storyboard_revision_id": storyboard_revision_id,
            "content_object_id": content_object_id,
            "content_hash": content_hash,
            "created_at": created_at,
            "payload": payload,
        }

    def latest_asset_requirement_set(self, chapter_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM asset_requirement_sets
            WHERE chapter_id = ?
            ORDER BY created_at DESC, requirement_set_id DESC
            LIMIT 1
            """,
            (chapter_id,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["payload"] = json.loads(self.runtime.read_text(data["content_object_id"]))
        return data

def _normalized_json(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
