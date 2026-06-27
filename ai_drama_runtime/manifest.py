from dataclasses import dataclass
from pathlib import Path
import hashlib
import json


class SkillManifestError(ValueError):
    pass


@dataclass(frozen=True)
class SkillValidator:
    name: str
    entrypoint: Path
    required: bool
    command: list


@dataclass(frozen=True)
class SkillPackage:
    root: Path
    skill_id: str
    version: str
    instructions_entry: Path
    validators: list
    content_hash: str
    metadata: dict


def _hash_tree(root):
    hasher = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


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


def load_skill_package(root):
    root = Path(root).resolve()
    data = _load_metadata(root)
    skill_id = data.get("skill_id")
    version = data.get("version")
    if not skill_id or not version:
        raise SkillManifestError("skill_id and version are required")
    entry = root / data.get("instructions_entry", "SKILL.md")
    if not entry.is_file():
        raise SkillManifestError("instructions entry does not exist: %s" % entry)

    validators = []
    for item in data.get("validators", []):
        if not isinstance(item, dict):
            raise SkillManifestError("validator entries must be objects")
        name = item.get("name")
        entrypoint = (root / item.get("entrypoint", "")).resolve()
        if not name or not entrypoint.is_file():
            raise SkillManifestError("validator %r has a missing entrypoint" % name)
        command = item.get("command") or []
        if not isinstance(command, list):
            raise SkillManifestError("validator %s command must be a list" % name)
        validators.append(
            SkillValidator(
                name=name,
                entrypoint=entrypoint,
                required=bool(item.get("required", False)),
                command=[str(part) for part in command],
            )
        )
    return SkillPackage(
        root=root,
        skill_id=skill_id,
        version=version,
        instructions_entry=entry,
        validators=validators,
        content_hash=_hash_tree(root),
        metadata=data,
    )


def discover_skill_packages(skills_root):
    skills_root = Path(skills_root)
    packages = []
    for meta_path in sorted(skills_root.rglob("skill.json")):
        packages.append(load_skill_package(meta_path.parent))
    return packages
