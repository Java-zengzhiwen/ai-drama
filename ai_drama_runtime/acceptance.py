from dataclasses import dataclass
from pathlib import Path
import json


class AcceptanceError(ValueError):
    pass


@dataclass(frozen=True)
class AcceptanceFile:
    key: str
    path: Path
    text: str


@dataclass(frozen=True)
class AcceptanceBundle:
    root: Path
    manifest: dict
    input_files: dict
    reference_output: AcceptanceFile

    def to_runtime_request_text(self):
        parts = [
            "Acceptance manifest:",
            json.dumps(
                {
                    "id": self.manifest.get("id"),
                    "title": self.manifest.get("title"),
                    "language": self.manifest.get("language"),
                    "inputs": self.manifest.get("inputs", {}),
                    "evaluation": self.manifest.get("evaluation", {}),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        ]
        for key, item in self.input_files.items():
            parts.append("\n--- INPUT: %s (%s) ---\n%s" % (key, item.path.name, item.text))
        return "\n".join(parts)


def _load_yaml(path):
    try:
        import yaml
    except Exception as exc:
        raise AcceptanceError("PyYAML is required to read acceptance manifests") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AcceptanceError("acceptance manifest must be a mapping")
    return data


def _relative_file(root, value, field):
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceError("%s must be a relative file path" % field)
    path = Path(value)
    if path.is_absolute():
        raise AcceptanceError("%s contains an absolute path: %s" % (field, value))
    if ".." in path.parts:
        raise AcceptanceError("%s escapes acceptance root: %s" % (field, value))
    resolved = root / path
    if not resolved.is_file():
        raise AcceptanceError("%s does not exist: %s" % (field, value))
    return resolved


def _check_tree(root):
    for path in root.rglob("*"):
        if path.name == ".DS_Store":
            raise AcceptanceError("system file is not allowed: %s" % path)
        if path.name == "__MACOSX":
            raise AcceptanceError("macOS archive folder is not allowed: %s" % path)
        if path.suffix.lower() == ".zip":
            raise AcceptanceError("zip files are not allowed: %s" % path)
        if path.is_file():
            path.read_text(encoding="utf-8")


def load_acceptance_bundle(root):
    root = Path(root).resolve()
    manifest_path = root / "acceptance-manifest.yaml"
    if not manifest_path.is_file():
        raise AcceptanceError("missing acceptance-manifest.yaml")
    _check_tree(root)
    manifest = _load_yaml(manifest_path)

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise AcceptanceError("manifest inputs must be a non-empty mapping")

    input_files = {}
    for key, value in inputs.items():
        path = _relative_file(root, value, "inputs.%s" % key)
        input_files[key] = AcceptanceFile(key=key, path=path, text=path.read_text(encoding="utf-8"))

    approved = (
        manifest.get("reference_outputs", {})
        .get("approved_script", {})
    )
    approved_path = _relative_file(root, approved.get("path"), "reference_outputs.approved_script.path")
    if approved.get("status") != "user_approved_reference":
        raise AcceptanceError("approved_script must be declared as user_approved_reference")
    if manifest.get("evaluation", {}).get("exact_text_match") is not False:
        raise AcceptanceError("evaluation.exact_text_match must be false")

    return AcceptanceBundle(
        root=root,
        manifest=manifest,
        input_files=input_files,
        reference_output=AcceptanceFile(
            key="approved_script",
            path=approved_path,
            text=approved_path.read_text(encoding="utf-8"),
        ),
    )
