from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .acceptance import load_acceptance_bundle
from .parser import PARSER_VERSION


REQUEST_FORMAT_VERSION = "runtime-request-v1"
SYSTEM_INSTRUCTION = "Follow the skill package and return only the requested Markdown DramaScript revision."


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
    context_files = [
        _file_item(skill.root, path, "context")
        for path in skill.context_files + skill.schemas + skill.contracts
    ]
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
