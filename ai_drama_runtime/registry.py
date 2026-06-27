from dataclasses import dataclass
from pathlib import Path

from .manifest import SkillManifestError, load_skill_package


class DuplicateSkillError(ValueError):
    pass


class SkillNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class RegistryEntry:
    package: object


def parse_skill_ref(value):
    if "@" not in value:
        raise ValueError("skill ref must be skill_id@version")
    skill_id, version = value.rsplit("@", 1)
    if not skill_id or not version:
        raise ValueError("skill ref must be skill_id@version")
    return skill_id, version


class SkillRegistry:
    def __init__(self, entries, invalid_packages):
        self.entries = entries
        self.invalid_packages = invalid_packages

    @classmethod
    def scan(cls, roots):
        entries = {}
        invalid = []
        for root in roots:
            for meta in sorted(Path(root).rglob("skill.json")):
                try:
                    package = load_skill_package(meta.parent)
                except SkillManifestError as exc:
                    invalid.append({"root": str(meta.parent), "error": str(exc)})
                    continue
                key = (package.skill_id, package.version)
                if key in entries:
                    raise DuplicateSkillError("duplicate skill package: %s@%s" % key)
                entries[key] = RegistryEntry(package=package)
        return cls(entries, invalid)

    def get(self, skill_id, version):
        entry = self.entries.get((skill_id, version))
        if not entry:
            raise SkillNotFoundError("skill not found: %s@%s" % (skill_id, version))
        return entry.package

    def get_ref(self, skill_ref):
        return self.get(*parse_skill_ref(skill_ref))

    def list(self):
        return [self._summary(entry.package) for key, entry in sorted(self.entries.items())]

    def show(self, skill_ref):
        return self._summary(self.get_ref(skill_ref))

    def validate(self, skill_ref):
        data = self.show(skill_ref)
        data["valid"] = True
        return data

    def _summary(self, package):
        return {
            "skill_ref": package.skill_ref,
            "skill_id": package.skill_id,
            "version": package.version,
            "display_name": package.display_name,
            "root": str(package.root),
            "content_hash": package.content_hash,
            "validators": [
                {
                    "validator_id": item.validator_id,
                    "required": item.required,
                    "applies_to": item.applies_to,
                    "dependencies": item.dependencies,
                }
                for item in package.validators
            ],
        }
