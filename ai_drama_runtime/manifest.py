from dataclasses import dataclass
from pathlib import Path
import hashlib
import json


class SkillManifestError(ValueError):
    pass


REQUIRED_FIELDS = {
    "package_format_version": str,
    "skill_id": str,
    "version": str,
    "display_name": str,
    "description": str,
    "package_status": str,
    "instructions_entry": str,
    "context_files": list,
    "input_types": list,
    "output_types": list,
    "schemas": list,
    "contracts": list,
    "validator_support_files": list,
    "validators": list,
    "runtime_requirements": dict,
    "dependency_requirements": list,
    "provenance": dict,
    "execution_profiles": list,
}

VALIDATOR_FIELDS = {
    "validator_id": str,
    "entrypoint": str,
    "required": bool,
    "applies_to": list,
    "command": list,
    "dependencies": list,
    "timeout_seconds": int,
    "expected_exit_behavior": str,
    "validator_origin": str,
    "required_artifacts": list,
    "current_profile_status": str,
    "current_profile_reason": str,
}


CANONICAL_STORYBOARD_PROFILE_ID = "storyboard-canonical-v1"
CANONICAL_STORYBOARD_PROFILE_FIELDS = {
    "profile_id",
    "output_format",
    "parser_version",
    "required_schema_version",
    "renderer_id",
    "renderer_version",
}


@dataclass(frozen=True)
class SkillValidator:
    validator_id: str
    name: str
    entrypoint: Path
    required: bool
    applies_to: list
    command: list
    dependencies: list
    timeout_seconds: int
    expected_exit_behavior: str
    validator_origin: str = "migrated_skill"
    required_artifacts: list = None
    current_profile_status: str = "APPLICABLE"
    current_profile_reason: str = ""


@dataclass(frozen=True)
class SkillPackage:
    root: Path
    skill_id: str
    version: str
    display_name: str
    description: str
    package_status: str
    instructions_entry: Path
    context_files: list
    input_types: list
    output_types: list
    schemas: list
    contracts: list
    validator_support_files: list
    validators: list
    content_hash: str
    metadata: dict
    execution_profiles: list

    @property
    def skill_ref(self):
        return "%s@%s" % (self.skill_id, self.version)


def _load_metadata(root):
    meta_path = root / "skill.json"
    if not meta_path.is_file():
        raise SkillManifestError("missing skill.json in %s" % root)
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillManifestError("invalid skill.json: %s" % exc) from exc
    if not isinstance(data, dict):
        raise SkillManifestError("skill.json must be an object")
    return data


def _check_type(data, field, expected):
    if field not in data:
        raise SkillManifestError("missing required field: %s" % field)
    if not isinstance(data[field], expected):
        raise SkillManifestError("%s must be %s" % (field, expected.__name__))


def _safe_path(root, value, field):
    if not isinstance(value, str) or not value:
        raise SkillManifestError("%s must be a relative path" % field)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SkillManifestError("%s escapes skill package: %s" % (field, value))
    resolved = (root / path).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise SkillManifestError("%s escapes skill package: %s" % (field, value))
    if not resolved.is_file():
        raise SkillManifestError("%s does not exist: %s" % (field, value))
    return resolved


def _safe_path_list(root, values, field):
    return [_safe_path(root, value, "%s[]" % field) for value in values]


def _hash_files(root, files):
    hasher = hashlib.sha256()
    for path in sorted({Path(item).resolve() for item in files}):
        rel = path.relative_to(root.resolve()).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _validate_execution_profiles(profiles):
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            raise SkillManifestError("execution_profiles[%d] must be an object" % index)
        if profile.get("profile_id") != CANONICAL_STORYBOARD_PROFILE_ID:
            continue
        missing = [field for field in sorted(CANONICAL_STORYBOARD_PROFILE_FIELDS) if field not in profile]
        if missing:
            raise SkillManifestError("execution_profiles[%d] missing required field: %s" % (index, ",".join(missing)))
        for field in sorted(CANONICAL_STORYBOARD_PROFILE_FIELDS):
            if not isinstance(profile[field], str) or not profile[field]:
                raise SkillManifestError("execution_profiles[%d].%s must be a non-empty string" % (index, field))
        if profile["output_format"] != "json":
            raise SkillManifestError("execution_profiles[%d].output_format must be json" % index)
        if profile["required_schema_version"] != CANONICAL_STORYBOARD_PROFILE_ID:
            raise SkillManifestError("execution_profiles[%d].required_schema_version must be %s" % (index, CANONICAL_STORYBOARD_PROFILE_ID))


def load_skill_package(root):
    root = Path(root).resolve()
    data = _load_metadata(root)
    for field, expected in REQUIRED_FIELDS.items():
        _check_type(data, field, expected)
    _validate_execution_profiles(data["execution_profiles"])

    instructions = _safe_path(root, data["instructions_entry"], "instructions_entry")
    context_files = _safe_path_list(root, data["context_files"], "context_files")
    schemas = _safe_path_list(root, data["schemas"], "schemas")
    contracts = _safe_path_list(root, data["contracts"], "contracts")
    validator_support_files = _safe_path_list(root, data["validator_support_files"], "validator_support_files")

    validators = []
    for item in data["validators"]:
        if not isinstance(item, dict):
            raise SkillManifestError("validators[] must be objects")
        for field, expected in VALIDATOR_FIELDS.items():
            _check_type(item, field, "validators.%s" % field if False else expected)
        entrypoint = _safe_path(root, item["entrypoint"], "validators.%s.entrypoint" % item["validator_id"])
        validators.append(
            SkillValidator(
                validator_id=item["validator_id"],
                name=item["validator_id"],
                entrypoint=entrypoint,
                required=item["required"],
                applies_to=list(item["applies_to"]),
                command=[str(part) for part in item["command"]],
                dependencies=[str(part) for part in item["dependencies"]],
                timeout_seconds=item["timeout_seconds"],
                expected_exit_behavior=item["expected_exit_behavior"],
                validator_origin=item.get("validator_origin", "migrated_skill"),
                required_artifacts=list(item.get("required_artifacts", [])),
                current_profile_status=item.get("current_profile_status", "APPLICABLE"),
                current_profile_reason=item.get("current_profile_reason", ""),
            )
        )

    active_files = [root / "skill.json", instructions] + context_files + schemas + contracts + validator_support_files
    active_files += [validator.entrypoint for validator in validators]
    return SkillPackage(
        root=root,
        skill_id=data["skill_id"],
        version=data["version"],
        display_name=data["display_name"],
        description=data["description"],
        package_status=data["package_status"],
        instructions_entry=instructions,
        context_files=context_files,
        input_types=list(data["input_types"]),
        output_types=list(data["output_types"]),
        schemas=schemas,
        contracts=contracts,
        validator_support_files=validator_support_files,
        validators=validators,
        content_hash=_hash_files(root, active_files),
        metadata=data,
        execution_profiles=list(data.get("execution_profiles", [])),
    )


def discover_skill_packages(skills_root):
    from .registry import SkillRegistry

    return [entry.package for entry in SkillRegistry.scan([skills_root]).entries.values()]
