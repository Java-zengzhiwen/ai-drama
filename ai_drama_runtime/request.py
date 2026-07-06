from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .acceptance import load_acceptance_bundle
from .parser import PARSER_VERSION, STORYBOARD_PARSER_VERSION


REQUEST_FORMAT_VERSION = "runtime-request-v1"
SYSTEM_INSTRUCTION = "Follow the skill package and return only the requested Markdown DramaScript revision."
STORYBOARD_SYSTEM_INSTRUCTION = "Follow the skill package and return only the requested Markdown Storyboard revision."
STORYBOARD_CANONICAL_SYSTEM_INSTRUCTION = "Follow the skill package and return only Storyboard Canonical JSON."
SHOT_PROMPT_CANONICAL_SYSTEM_INSTRUCTION = "Follow the skill package and return only Shot Prompt Canonical JSON."


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_item(root, path, logical_type):
    text = path.read_text(encoding="utf-8")
    return {
        "logical_type": logical_type,
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": _sha(text),
        "content": text,
    }


def _unique_file_items(root, paths):
    seen = set()
    items = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        items.append(_file_item(root, path, "context"))
    return items


@dataclass(frozen=True)
class RuntimeRequest:
    payload: dict

    def to_dict(self):
        return self.payload

    def to_json(self):
        return json.dumps(self.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self):
        return _sha(self.to_json())

    def model_messages(self):
        return [
            {"role": "system", "content": self.payload["system_instruction"]},
            {"role": "user", "content": self.to_json()},
        ]


def build_runtime_request(skill, acceptance_root, provider, model, timeout_seconds=60):
    bundle = load_acceptance_bundle(acceptance_root)
    instruction_text = skill.instructions_entry.read_text(encoding="utf-8")
    profile = (skill.metadata.get("execution_profiles") or [{}])[0]
    context_files = _unique_file_items(skill.root, skill.context_files + skill.schemas + skill.contracts)
    inputs = [
        {
            "logical_type": key,
            "relative_path": item.relative_path,
            "sha256": _sha(item.text),
            "content": item.text,
        }
        for key, item in bundle.input_files.items()
    ]
    payload = {
        "request_format_version": REQUEST_FORMAT_VERSION,
        "skill": {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "package_hash": skill.content_hash,
            "execution_profile": profile.get("profile_id", "markdown-script-mvp-v1"),
        },
        "system_instruction": SYSTEM_INSTRUCTION,
        "skill_instruction": {
            "relative_path": skill.instructions_entry.relative_to(skill.root).as_posix(),
            "sha256": _sha(instruction_text),
            "content": instruction_text,
        },
        "context_files": context_files,
        "inputs": inputs,
        "output_contract": {
            "profile": profile.get("profile_id", "markdown-script-mvp-v1"),
            "format": profile.get("output_format", "markdown"),
            "parser_version": PARSER_VERSION,
            "supported_artifacts": profile.get("supported_artifacts", ["creator_facing_markdown_script"]),
            "unsupported_bundle_artifacts": profile.get("unsupported_bundle_artifacts", []),
        },
        "runtime_config": {
            "provider": provider,
            "model": model or "",
            "timeout_seconds": timeout_seconds,
        },
    }
    return RuntimeRequest(payload)


def build_runtime_request_from_inputs(skill, inputs, provider, model, timeout_seconds=60):
    instruction_text = skill.instructions_entry.read_text(encoding="utf-8")
    profile = (skill.metadata.get("execution_profiles") or [{}])[0]
    context_files = _unique_file_items(skill.root, skill.context_files + skill.schemas + skill.contracts)
    normalized_inputs = [
        {
            "logical_type": logical_type,
            "relative_path": "web-inputs/%s.md" % logical_type,
            "sha256": _sha(content),
            "content": content,
        }
        for logical_type, content in sorted(inputs.items())
    ]
    payload = {
        "request_format_version": REQUEST_FORMAT_VERSION,
        "skill": {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "package_hash": skill.content_hash,
            "execution_profile": profile.get("profile_id", "markdown-script-mvp-v1"),
        },
        "system_instruction": SYSTEM_INSTRUCTION,
        "skill_instruction": {
            "relative_path": skill.instructions_entry.relative_to(skill.root).as_posix(),
            "sha256": _sha(instruction_text),
            "content": instruction_text,
        },
        "context_files": context_files,
        "inputs": normalized_inputs,
        "output_contract": {
            "profile": profile.get("profile_id", "markdown-script-mvp-v1"),
            "format": profile.get("output_format", "markdown"),
            "parser_version": PARSER_VERSION,
            "supported_artifacts": profile.get("supported_artifacts", ["creator_facing_markdown_script"]),
            "unsupported_bundle_artifacts": profile.get("unsupported_bundle_artifacts", []),
        },
        "runtime_config": {
            "provider": provider,
            "model": model or "",
            "timeout_seconds": timeout_seconds,
        },
    }
    return RuntimeRequest(payload)


def _storyboard_inputs_from_source_revision(store, source_revision):
    run = store.get_run(source_revision.run_id)
    snapshots = {item.logical_type: item for item in store.input_snapshots(source_revision.run_id)}
    required = ("series_canon", "characters", "production_brief")
    missing = [name for name in required if name not in snapshots]
    if missing:
        raise ValueError("SOURCE_CONTEXT_MISSING: %s" % ",".join(missing))
    approval = store.latest_approval(source_revision.revision_id)
    def _snapshot_text(name):
        item = snapshots.get(name)
        return store.read_text(item.object_id)
    return {
        "source_script_revision_id": source_revision.revision_id,
        "source_script_artifact_id": source_revision.artifact_id,
        "source_script_content_hash": source_revision.content_hash,
        "source_script_approval_record_id": approval.record_id if approval else "",
        "source_script_approval_record": approval.__dict__ if approval else {},
        "source_script_markdown": store.read_text(source_revision.content_object_id),
        "series_canon": _snapshot_text("series_canon"),
        "characters": _snapshot_text("characters"),
        "production_brief": _snapshot_text("production_brief"),
        "source_run_id": run.run_id,
    }


def build_storyboard_runtime_request(skill, store, source_revision, provider, model, timeout_seconds=60):
    instruction_text = skill.instructions_entry.read_text(encoding="utf-8")
    profile = (skill.metadata.get("execution_profiles") or [{}])[0]
    context_files = _unique_file_items(skill.root, skill.context_files + skill.schemas + skill.contracts)
    inputs = _storyboard_inputs_from_source_revision(store, source_revision)
    profile_id = profile.get("profile_id", "storyboard-markdown-mvp-v1")
    output_format = profile.get("output_format", "markdown")
    parser_version = profile.get("parser_version", STORYBOARD_PARSER_VERSION)
    payload = {
        "request_format_version": REQUEST_FORMAT_VERSION,
        "skill": {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "package_hash": skill.content_hash,
            "execution_profile": profile_id,
        },
        "system_instruction": STORYBOARD_CANONICAL_SYSTEM_INSTRUCTION if profile_id == "storyboard-canonical-v1" else STORYBOARD_SYSTEM_INSTRUCTION,
        "skill_instruction": {
            "relative_path": skill.instructions_entry.relative_to(skill.root).as_posix(),
            "sha256": _sha(instruction_text),
            "content": instruction_text,
        },
        "context_files": context_files,
        "inputs": inputs,
        "output_contract": {
            "profile": profile_id,
            "format": output_format,
            "parser_version": parser_version,
            "required_schema_version": profile.get("required_schema_version", ""),
            "renderer_id": profile.get("renderer_id", ""),
            "renderer_version": profile.get("renderer_version", ""),
            "supported_artifacts": profile.get("supported_artifacts", ["storyboard_markdown"]),
            "unsupported_bundle_artifacts": profile.get("unsupported_bundle_artifacts", []),
        },
        "runtime_config": {
            "provider": provider,
            "model": model or "",
            "timeout_seconds": timeout_seconds,
        },
    }
    return RuntimeRequest(payload)


def _shot_prompt_inputs_from_source_revision(store, source_revision, requirement_set):
    from ai_drama_web.store import ProductStore

    product_store = ProductStore(store)
    storyboard_text = store.read_text(source_revision.content_object_id)
    storyboard_canonical = json.loads(storyboard_text)
    profiles = []
    for record in product_store.list_production_profiles(source_revision.project_id):
        if record.chapter_id not in {"", source_revision.chapter_id}:
            continue
        profiles.append(
            {
                "profile_id": record.profile_id,
                "project_id": record.project_id,
                "chapter_id": record.chapter_id,
                "profile_type": record.profile_type,
                "name": record.name,
                "payload": json.loads(store.read_text(record.payload_object_id)),
            }
        )
    asset_requirements = {} if requirement_set is None else {
        key: value
        for key, value in requirement_set.items()
        if key != "content_object_id"
    }
    ready_items = []
    for row in asset_requirements.get("payload", {}).get("shot_rows", []):
        for item in row.get("ready", []):
            ready = dict(item)
            ready.setdefault("shot_id", row.get("shot_id", ""))
            ready_items.append(ready)
    approval = store.latest_approval(source_revision.revision_id)
    return {
        "source_storyboard_revision_id": source_revision.revision_id,
        "source_storyboard_artifact_id": source_revision.artifact_id,
        "source_storyboard_content_hash": source_revision.content_hash,
        "source_storyboard_approval_record_id": approval.record_id if approval else "",
        "storyboard_canonical": storyboard_canonical,
        "production_profiles": profiles,
        "asset_requirements": asset_requirements,
        "asset_bindings": ready_items,
    }


def build_shot_prompt_runtime_request(
    skill,
    store,
    source_storyboard_revision,
    asset_requirement_set,
    provider,
    model,
    timeout_seconds=60,
):
    instruction_text = skill.instructions_entry.read_text(encoding="utf-8")
    profile = (skill.metadata.get("execution_profiles") or [{}])[0]
    context_files = _unique_file_items(skill.root, skill.context_files + skill.schemas + skill.contracts)
    inputs = _shot_prompt_inputs_from_source_revision(store, source_storyboard_revision, asset_requirement_set)
    profile_id = profile.get("profile_id", "shot-prompt-canonical-v1")
    payload = {
        "request_format_version": REQUEST_FORMAT_VERSION,
        "skill": {
            "skill_id": skill.skill_id,
            "version": skill.version,
            "package_hash": skill.content_hash,
            "execution_profile": profile_id,
        },
        "system_instruction": SHOT_PROMPT_CANONICAL_SYSTEM_INSTRUCTION,
        "skill_instruction": {
            "relative_path": skill.instructions_entry.relative_to(skill.root).as_posix(),
            "sha256": _sha(instruction_text),
            "content": instruction_text,
        },
        "context_files": context_files,
        "inputs": inputs,
        "output_contract": {
            "profile": profile_id,
            "format": profile.get("output_format", "json"),
            "parser_version": profile.get("parser_version", "shot-prompt-canonical-json-v1"),
            "required_schema_version": profile.get("required_schema_version", "shot-prompt-canonical-v1"),
            "supported_outputs": profile.get("supported_outputs", ["shot_prompt_set"]),
            "unsupported_outputs": profile.get("unsupported_outputs", []),
        },
        "runtime_config": {
            "provider": provider,
            "model": model or "",
            "timeout_seconds": timeout_seconds,
        },
    }
    return RuntimeRequest(payload)
