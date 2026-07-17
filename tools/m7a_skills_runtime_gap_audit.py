#!/usr/bin/env python3
"""Read-only M7A local skills/runtime inventory audit.

The script intentionally records metadata only: paths, sizes, hashes, manifests,
archive listings, and runtime registration evidence. It does not read runtime DB
business rows, credentials, media content, or provider outputs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATE = time.strftime("%Y-%m-%d")
REPORT_MD = REPO_ROOT / "docs" / "superpowers" / "reports" / f"{DATE}-skills-runtime-gap-audit.md"
REPORT_JSON = REPO_ROOT / "docs" / "superpowers" / "reports" / f"{DATE}-skills-runtime-gap-audit.json"

SCAN_ROOTS = [
    Path("/Users/zengzhiwen/AI-manju"),
    Path("/Users/zengzhiwen/Downloads"),
    Path("/Users/zengzhiwen/Desktop"),
    Path("/Users/zengzhiwen/Documents"),
    Path("/Users/zengzhiwen"),
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "Library",
    "Caches",
    "Docker",
    "runtime-data",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".cache",
    ".Trash",
    "Applications",
    "Movies",
    "Music",
    "Pictures",
}

KEYWORDS = [
    "ai-drama",
    "skill",
    "skills",
    "orchestrator",
    "workflow",
    "v0.5",
    "v0.6",
    "v0.6.1",
    "rc2",
    "batch",
    "patch",
    "release",
    "migration",
    "manifest",
    "skill.json",
    "skill.md",
    "changelog",
    "release_notes",
    "verification",
    "e2e-report",
]

TEXT_EXTS = {".md", ".json", ".yaml", ".yml", ".toml", ".txt"}
ARCHIVE_EXTS = {".zip", ".tar.gz", ".tgz"}
MAX_TEXT_SCAN_BYTES = 2 * 1024 * 1024
MAX_HASH_BYTES = 1024 * 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def run_git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def version_key(version: str) -> tuple:
    text = version.lstrip("v")
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-rc(\d+)(?:\.(\d+))?)?", text)
    if not match:
        return (-1, version)
    major, minor, patch, rc, rc_patch = match.groups()
    base = (int(major or 0), int(minor or 0), int(patch or 0))
    rc_key = (0, int(rc or 0), int(rc_patch or 0)) if rc else (1, 999, 999)
    return (*base, *rc_key, version)


def infer_version_from_text(text: str) -> str:
    match = re.search(r"v\d+(?:\.\d+)*(?:-rc\d+(?:\.\d+)?)?", text.lower())
    return match.group(0) if match else ""


def infer_version_from_path(path: str | Path) -> str:
    return infer_version_from_text(Path(path).as_posix())


def is_archive(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".zip") or name.endswith(".tar.gz") or name.endswith(".tgz")


def candidate_by_name(path: Path) -> bool:
    lower = path.as_posix().lower()
    name = path.name.lower()
    if name in {"skill.json", "skill.md", "manifest.json", "changelog.md", "release_notes.md"}:
        return True
    if any(k in lower for k in KEYWORDS):
        return True
    return path.suffix.lower() in TEXT_EXTS and any(k in name for k in KEYWORDS)


def candidate_by_content(path: Path) -> bool:
    try:
        if path.suffix.lower() not in TEXT_EXTS or path.stat().st_size > MAX_TEXT_SCAN_BYTES:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        return any(k in text for k in KEYWORDS)
    except OSError:
        return False


def should_skip_dir(path: Path) -> bool:
    parts = set(path.parts)
    if path.name in EXCLUDED_DIR_NAMES:
        return True
    if ".git" in parts and "objects" in parts:
        return True
    if path.name.endswith(".photoslibrary"):
        return True
    return False


def walk_candidates() -> tuple[list[Path], list[Path]]:
    files: dict[str, Path] = {}
    dirs: dict[str, Path] = {}
    seen_roots: set[str] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        real = str(root.resolve())
        if real in seen_roots:
            continue
        seen_roots.add(real)
        for current, dirnames, filenames in os.walk(root, topdown=True):
            cur = Path(current)
            dirnames[:] = [
                item
                for item in dirnames
                if not should_skip_dir(cur / item)
            ]
            if cur.name.lower().startswith("ai-drama-skills") or (cur / "skill.json").is_file():
                dirs[str(cur.resolve())] = cur
            if (cur / "skills").is_dir() and "ai-drama" in cur.name.lower():
                dirs[str(cur.resolve())] = cur
            for filename in filenames:
                path = cur / filename
                try:
                    if not path.is_file():
                        continue
                    if is_archive(path) or candidate_by_name(path) or candidate_by_content(path):
                        files[str(path.resolve())] = path
                except OSError:
                    continue
    return sorted(files.values(), key=lambda p: p.as_posix()), sorted(dirs.values(), key=lambda p: p.as_posix())


def safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def directory_digest(path: Path) -> dict[str, Any]:
    entries = []
    for file in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = file.relative_to(path).as_posix()
        if any(part in EXCLUDED_DIR_NAMES for part in file.parts):
            continue
        try:
            size = file.stat().st_size
        except OSError:
            continue
        if size > MAX_HASH_BYTES:
            digest = "SKIPPED_LARGE_FILE"
        else:
            digest = sha256_file(file)
        entries.append({"path": rel, "size": size, "sha256": digest})
    structure = [{"path": item["path"], "size": item["size"], "sha256": item["sha256"]} for item in entries]
    return {
        "file_count": len(entries),
        "structure_sha256": sha256_text(stable_json(structure)),
        "files": entries[:200],
        "truncated_files": max(0, len(entries) - 200),
    }


def archive_summary(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "type": "archive", "error": ""}
    try:
        result["sha256"] = sha256_file(path)
        result["size"] = path.stat().st_size
        names: list[str] = []
        manifests: list[dict[str, Any]] = []
        skill_dirs: list[dict[str, Any]] = []
        bundle_version = infer_version_from_path(path)
        if path.name.lower().endswith(".zip"):
            with zipfile.ZipFile(path) as zf:
                names = sorted(item.filename for item in zf.infolist() if not item.is_dir())
                skill_md_paths = [name for name in names if name.endswith("/SKILL.md") or name == "SKILL.md"]
                for skill_md_path in sorted(skill_md_paths):
                    skill_dir = str(Path(skill_md_path).parent)
                    skill_id = Path(skill_dir).name
                    prefix = "" if skill_dir == "." else skill_dir.rstrip("/") + "/"
                    dir_names = [name for name in names if name.startswith(prefix)]
                    try:
                        raw = zf.read(skill_md_path)
                        skill_md_sha256 = hashlib.sha256(raw).hexdigest()
                    except Exception:
                        skill_md_sha256 = ""
                    skill_dirs.append({
                        "path": skill_dir,
                        "skill_id": skill_id,
                        "version": bundle_version,
                        "display_name": skill_id.replace("-", " ").title(),
                        "entry_count": len(dir_names),
                        "entry_list_sha256": sha256_text("\n".join(dir_names)),
                        "skill_md_sha256": skill_md_sha256,
                    })
                for name in names:
                    if name.endswith("skill.json") or name.lower().endswith("manifest.json"):
                        info = zf.getinfo(name)
                        if info.file_size <= MAX_TEXT_SCAN_BYTES:
                            try:
                                raw = zf.read(name)
                                manifests.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "json": json.loads(raw.decode("utf-8"))})
                            except Exception:
                                manifests.append({"path": name, "sha256": "", "json": None})
        else:
            with tarfile.open(path) as tf:
                members = [item for item in tf.getmembers() if item.isfile()]
                names = sorted(item.name for item in members)
                member_by_name = {member.name: member for member in members}
                skill_md_paths = [name for name in names if name.endswith("/SKILL.md") or name == "SKILL.md"]
                for skill_md_path in sorted(skill_md_paths):
                    skill_dir = str(Path(skill_md_path).parent)
                    skill_id = Path(skill_dir).name
                    prefix = "" if skill_dir == "." else skill_dir.rstrip("/") + "/"
                    dir_names = [name for name in names if name.startswith(prefix)]
                    skill_md_sha256 = ""
                    extracted = tf.extractfile(member_by_name[skill_md_path])
                    if extracted:
                        skill_md_sha256 = hashlib.sha256(extracted.read()).hexdigest()
                    skill_dirs.append({
                        "path": skill_dir,
                        "skill_id": skill_id,
                        "version": bundle_version,
                        "display_name": skill_id.replace("-", " ").title(),
                        "entry_count": len(dir_names),
                        "entry_list_sha256": sha256_text("\n".join(dir_names)),
                        "skill_md_sha256": skill_md_sha256,
                    })
                for member in members:
                    if member.name.endswith("skill.json") or member.name.lower().endswith("manifest.json"):
                        if member.size <= MAX_TEXT_SCAN_BYTES:
                            extracted = tf.extractfile(member)
                            if extracted:
                                raw = extracted.read()
                                try:
                                    parsed = json.loads(raw.decode("utf-8"))
                                except Exception:
                                    parsed = None
                                manifests.append({"path": member.name, "sha256": hashlib.sha256(raw).hexdigest(), "json": parsed})
        result["entry_count"] = len(names)
        result["entry_list_sha256"] = sha256_text("\n".join(names))
        result["sample_entries"] = names[:80]
        result["manifest_count"] = len(manifests)
        result["skill_dir_count"] = len(skill_dirs)
        result["skill_dirs"] = skill_dirs
        result["manifests"] = [
            {
                "path": item["path"],
                "sha256": item["sha256"],
                "skill_id": (item["json"] or {}).get("skill_id") if isinstance(item["json"], dict) else "",
                "version": (item["json"] or {}).get("version") if isinstance(item["json"], dict) else "",
                "display_name": (item["json"] or {}).get("display_name") if isinstance(item["json"], dict) else "",
            }
            for item in manifests
        ]
    except Exception as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
    return result


def package_summary(path: Path, source: str, archive_path: str = "") -> dict[str, Any]:
    meta = safe_read_json(path / "skill.json")
    digest = directory_digest(path)
    return {
        "source": source,
        "source_path": str(path),
        "archive_path": archive_path,
        "manifest_path": str(path / "skill.json") if (path / "skill.json").exists() else "",
        "skill_id": (meta or {}).get("skill_id", ""),
        "display_name": (meta or {}).get("display_name", ""),
        "skill_version": (meta or {}).get("version", ""),
        "package_status": (meta or {}).get("package_status", ""),
        "input_contract": (meta or {}).get("input_types", []),
        "output_contract": (meta or {}).get("output_types", []),
        "validators": [item.get("validator_id", "") for item in (meta or {}).get("validators", []) if isinstance(item, dict)],
        "dependencies": (meta or {}).get("dependency_requirements", []),
        "approval_gate": (meta or {}).get("approval_gate", ""),
        "execution_profiles": (meta or {}).get("execution_profiles", []),
        "sha256": digest["structure_sha256"],
        "file_count": digest["file_count"],
        "complete_package_shape": bool(meta and (path / "SKILL.md").exists()),
        "digest": digest,
    }


def bundle_summary(path: Path) -> dict[str, Any]:
    digest = directory_digest(path)
    skill_jsons = sorted(path.rglob("skill.json"))
    packages = [package_summary(item.parent, "bundle_dir", str(path)) for item in skill_jsons]
    version = infer_version_from_path(path)
    required = {
        "skills": (path / "skills").exists() or any("/skills/" in item.as_posix() for item in skill_jsons),
        "orchestrator": (path / "orchestrator").exists() or any("orchestrator" in item.as_posix().lower() for item in path.rglob("*")),
        "schemas": any("schemas" in item.as_posix() for item in path.rglob("*")),
        "validators": any("validators" in item.as_posix() for item in path.rglob("*")),
        "tests": any("test" in item.as_posix().lower() for item in path.rglob("*")),
        "release_notes": any("release" in item.name.lower() or "changelog" in item.name.lower() for item in path.rglob("*")),
        "checksums": any("checksum" in item.name.lower() or item.name.lower().endswith(".sha256") for item in path.rglob("*")),
    }
    return {
        "path": str(path),
        "version": version,
        "sha256": digest["structure_sha256"],
        "file_count": digest["file_count"],
        "skill_count": len(packages),
        "skills": packages,
        "required_release_shape": required,
        "status": "INCOMPLETE_RELEASE" if not all(required.values()) else "COMPLETE_RELEASE_CANDIDATE",
    }


def package_summary_from_archive_skill_dir(archive: dict[str, Any], skill_dir: dict[str, Any]) -> dict[str, Any]:
    skill_id = skill_dir.get("skill_id", "")
    version = skill_dir.get("version") or infer_version_from_path(archive.get("path", ""))
    return {
        "source": "archive_skill_dir",
        "source_path": skill_dir.get("path", ""),
        "archive_path": archive.get("path", ""),
        "manifest_path": str(Path(skill_dir.get("path", "")) / "SKILL.md"),
        "skill_id": skill_id,
        "display_name": skill_dir.get("display_name", skill_id),
        "skill_version": version,
        "package_status": "BUNDLE_SKILL_MD",
        "input_contract": [],
        "output_contract": [],
        "validators": [],
        "dependencies": [],
        "approval_gate": "",
        "execution_profiles": [],
        "sha256": skill_dir.get("entry_list_sha256") or skill_dir.get("skill_md_sha256", ""),
        "file_count": skill_dir.get("entry_count", 0),
        "complete_package_shape": True,
        "digest": {
            "file_count": skill_dir.get("entry_count", 0),
            "structure_sha256": skill_dir.get("entry_list_sha256", ""),
            "skill_md_sha256": skill_dir.get("skill_md_sha256", ""),
        },
    }


def is_ai_drama_package(package: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(package.get(key, ""))
        for key in ["skill_id", "display_name", "source_path", "archive_path"]
    ).lower()
    return "ai-drama" in haystack


def archive_bundle_candidate(archive: dict[str, Any]) -> dict[str, Any]:
    path = archive.get("path", "")
    version = infer_version_from_path(path) or "unknown"
    skill_dirs = archive.get("skill_dirs", [])
    sample_entries = archive.get("sample_entries", [])
    required = {
        "skills": bool(skill_dirs),
        "orchestrator": any("orchestrator" in item.get("skill_id", "").lower() for item in skill_dirs),
        "schemas": any("schema" in item.lower() for item in sample_entries),
        "validators": any("validator" in item.lower() for item in sample_entries),
        "tests": any("test" in item.lower() for item in sample_entries),
        "release_notes": "release" in Path(path).as_posix().lower(),
        "checksums": bool(archive.get("sha256")),
    }
    return {
        "path": path,
        "version": version,
        "sha256": archive.get("sha256", ""),
        "file_count": archive.get("entry_count", 0),
        "skill_count": len(skill_dirs),
        "skills": [package_summary_from_archive_skill_dir(archive, item) for item in skill_dirs],
        "required_release_shape": required,
        "status": "COMPLETE_RELEASE_ARCHIVE_CANDIDATE" if skill_dirs else "ARCHIVE_REFERENCE",
    }


def repo_runtime_state() -> dict[str, Any]:
    sys.path.insert(0, str(REPO_ROOT))
    from ai_drama_runtime.registry import SkillRegistry

    registry = SkillRegistry.scan([REPO_ROOT / "skills"])
    entries = registry.list()
    refs = {
        "script_web": "ai-drama-script-adaptation-skill@v0.6.1-rc2.4",
        "storyboard_web": "ai-drama-storyboard-design-skill@v0.2.1",
        "storyboard_web_fallback": "ai-drama-storyboard-design-skill@v0.2.0",
        "shot_prompt_web": "ai-drama-shot-prompt-skill@v0.1.0",
    }
    operations = {
        "script_web": ["/api/chapters/{chapter_id}/script/generate", "ai_drama_web.services.script_workflow"],
        "storyboard_web": ["/api/chapters/{chapter_id}/storyboard/generate", "ai_drama_web.services.storyboard_workflow"],
        "shot_prompt_web": ["/api/chapters/{chapter_id}/shot-prompts/generate", "ai_drama_web.services.shot_prompts"],
    }
    return {
        "registry_entries": entries,
        "invalid_packages": registry.invalid_packages,
        "web_runtime_refs": refs,
        "web_operations": operations,
    }


def git_skill_history() -> dict[str, Any]:
    result = {}
    for path in ["skills", "ai_drama_runtime", "ai_drama_web/services", "tools"]:
        try:
            result[path] = run_git(["log", "-1", "--format=%H %cs %s", "--", path])
        except subprocess.CalledProcessError:
            result[path] = ""
    return result


def classify_packages(packages: list[dict[str, Any]], runtime: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for package in packages:
        if package.get("skill_id"):
            by_id[package["skill_id"]].append(package)
    runtime_entries = {
        item["skill_id"]: item
        for item in runtime["registry_entries"]
    }
    runtime_refs = set(runtime["web_runtime_refs"].values())
    classified = []
    for skill_id, group in sorted(by_id.items()):
        latest = max(group, key=lambda item: version_key(item.get("skill_version", "")))
        hashes = defaultdict(list)
        for item in group:
            hashes[item.get("sha256", "")].append(item)
        duplicate_exact = sum(max(0, len(items) - 1) for items in hashes.values())
        diverged = max(0, len(hashes) - 1) if len(group) > 1 else 0
        for item in group:
            skill_ref = f"{item.get('skill_id')}@{item.get('skill_version')}"
            current_registered = any(
                entry["skill_id"] == item.get("skill_id") and entry["version"] == item.get("skill_version")
                for entry in runtime["registry_entries"]
            )
            web_connected = skill_ref in runtime_refs
            status = "CURRENT" if web_connected else "MISSING_FROM_RUNTIME"
            if current_registered and not web_connected:
                status = "CURRENT" if item is latest else "OBSOLETE"
            if item.get("skill_version") == latest.get("skill_version") and not current_registered:
                status = "NEWER_LOCAL_NOT_IN_RUNTIME"
            if not item.get("complete_package_shape"):
                status = "INCOMPLETE"
            classified.append({
                **item,
                "current_runtime_registered": current_registered,
                "current_execution_profile": ((item.get("execution_profiles") or [{}])[0]).get("profile_id", ""),
                "current_web_operation": next((value[0] for key, value in runtime["web_operations"].items() if runtime["web_runtime_refs"].get(key) == skill_ref), ""),
                "current_tests": infer_tests(skill_id),
                "latest_candidate": item.get("source_path") == latest.get("source_path"),
                "duplicate_count": duplicate_exact,
                "diverged_duplicate_group_count": diverged,
                "status": status,
                "recommended_action": recommended_action(skill_id, item, status, web_connected),
            })
    counts = {
        "skill_id_count": len(by_id),
        "package_count": len(packages),
        "exact_duplicate_count": sum(
            sum(max(0, len(items) - 1) for items in group.values())
            for group in [
                defaultdict(list, {
                    h: [item for item in items if item.get("skill_id") == sid]
                    for h, items in defaultdict(list, [(p.get("sha256", ""), [])]).items()
                })
                for sid in []
            ]
        ),
    }
    return classified, counts


def infer_tests(skill_id: str) -> list[str]:
    mapping = {
        "ai-drama-script-adaptation-skill": ["tests/test_manifest.py", "tests/test_cli.py", "tests/test_web_script_runtime.py", "tests/web/test_script_workflow_api.py"],
        "ai-drama-storyboard-design-skill": ["tests/test_storyboard_canonical_workflow.py", "tests/web/test_storyboard_workflow_api.py", "tools/verify_storyboard_workflow.py"],
        "ai-drama-shot-prompt-skill": ["tests/test_shot_prompt_skill_package.py", "tests/web/test_shot_prompt_api.py", "tools/verify_m2_assets_shot_prompts.py"],
    }
    return mapping.get(skill_id, [])


def recommended_action(skill_id: str, item: dict[str, Any], status: str, web_connected: bool) -> str:
    if status == "CURRENT" and web_connected:
        return "Use as current runtime baseline."
    if status == "CURRENT":
        return "Keep registered; treat as fallback/reference unless Web service selects it."
    if status == "NEWER_LOCAL_NOT_IN_RUNTIME":
        return "Evaluate for M7A migration; do not auto-switch."
    if status == "OBSOLETE":
        return "Keep reference; candidate for archive after approval."
    if status == "INCOMPLETE":
        return "Do not use as baseline; inspect missing package files."
    return "Compare against canonical source before M7A integration."


def duplicate_stats(records: list[dict[str, Any]]) -> dict[str, int]:
    by_hash = defaultdict(list)
    by_name = defaultdict(list)
    for record in records:
        sha = record.get("sha256")
        if sha:
            by_hash[sha].append(record)
        key = (Path(record.get("path", record.get("source_path", ""))).name.lower(), record.get("size", record.get("file_count", 0)))
        by_name[key].append(record)
    exact = sum(len(items) - 1 for items in by_hash.values() if len(items) > 1)
    diverged = 0
    for items in by_name.values():
        hashes = {item.get("sha256") for item in items if item.get("sha256")}
        if len(hashes) > 1:
            diverged += len(items)
    return {"exact_duplicate_count": exact, "diverged_duplicate_count": diverged}


def integration_order(classified: list[dict[str, Any]]) -> list[str]:
    desired = [
        "shared contracts / schemas",
        "workflow orchestrator",
        "material extraction",
        "ai-drama-script-adaptation-skill",
        "ai-drama-character-bible-skill",
        "ai-drama-scene-bible-skill",
        "ai-drama-prop-bible-skill",
        "ai-drama-visual-anchor-skill",
        "ai-drama-storyboard-design-skill",
        "ai-drama-image-prompt-skill",
        "ai-drama-shot-prompt-skill",
        "video execution",
        "video QC",
    ]
    known = {item["skill_id"] for item in classified}
    result = []
    for item in desired:
        if item.startswith("ai-drama-"):
            result.append(f"{item}: {'present' if item in known else 'missing'}")
        else:
            result.append(f"{item}: requires source confirmation")
    return result


def build_report(data: dict[str, Any]) -> str:
    answers = data["answers"]
    matrix = data["gap_matrix"]
    lines = [
        "# M7A Skills Runtime Gap Audit",
        "",
        "This is a read-only inventory of local AI Drama skill packages, archives, duplicate candidates, and current Runtime/Web integration evidence. It records metadata only: paths, versions, hashes, structure, manifest fields, tests, and registry references.",
        "",
        "## Executive Answers",
        "",
    ]
    for key, value in answers.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Gap Matrix",
        "",
        "| Skill | Latest source version | Runtime current version | Registered | Web integrated | Agent schedulable | Gate mapped | Test status | M7A action |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ])
    for row in matrix:
        lines.append(
            "| {skill} | {latest} | {runtime} | {registered} | {web} | {agent} | {gate} | {tests} | {action} |".format(
                skill=row["skill"],
                latest=row["latest_source_version"],
                runtime=row["runtime_current_version"],
                registered="yes" if row["registered"] else "no",
                web="yes" if row["web_integrated"] else "no",
                agent="yes" if row["agent_schedulable"] else "no",
                gate="yes" if row["gate_mapped"] else "no",
                tests=", ".join(row["tests"]) if row["tests"] else "not found",
                action=row["m7a_action"],
            )
        )
    lines.extend([
        "",
        "## Runtime Evidence",
        "",
    ])
    for entry in data["runtime"]["registry_entries"]:
        lines.append(f"- `{entry['skill_ref']}` registered at `{entry['root']}` with hash `{entry['content_hash']}`.")
    lines.extend([
        "",
        "## Web Runtime References",
        "",
    ])
    for key, ref in data["runtime"]["web_runtime_refs"].items():
        lines.append(f"- `{key}` -> `{ref}`")
    lines.extend([
        "",
        "## Bundle Candidates",
        "",
    ])
    for bundle in data["bundles"]:
        lines.append(f"- `{bundle['version'] or 'unknown'}` `{bundle['path']}` status `{bundle['status']}` skills `{bundle['skill_count']}` hash `{bundle['sha256']}`")
    lines.extend([
        "",
        "## Skill Package Inventory",
        "",
        "| Skill | Version | Status | Source | Runtime | Web operation | Hash | Recommended action |",
        "|---|---:|---|---|---:|---|---|---|",
    ])
    for item in data["classified_packages"]:
        lines.append(
            f"| {item['skill_id']} | {item['skill_version']} | {item['status']} | `{item['source_path']}` | {'yes' if item['current_runtime_registered'] else 'no'} | `{item['current_web_operation']}` | `{item['sha256']}` | {item['recommended_action']} |"
        )
    lines.extend([
        "",
        "## File Classification Summary",
        "",
    ])
    for key, value in data["classification_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Archive And Duplicate Evidence",
        "",
        f"- Exact duplicate count: `{data['duplicate_stats']['exact_duplicate_count']}`",
        f"- Diverged duplicate count: `{data['duplicate_stats']['diverged_duplicate_count']}`",
        f"- Archive candidate count: `{data['classification_counts']['ARCHIVE_CANDIDATE']}`",
        "",
        "## M7A Baselines",
        "",
        f"- `M7A_SOURCE_BASELINE`: `{data['m7a']['source_baseline']}`",
        f"- `M7A_RUNTIME_BASELINE`: `{data['m7a']['runtime_baseline']}`",
        f"- `M7A_MISSING_SKILLS`: `{', '.join(data['m7a']['missing_skills']) or 'NONE'}`",
        f"- `M7A_ORCHESTRATOR_STATUS`: `{data['m7a']['orchestrator_status']}`",
        "",
        "## Suggested Integration Order",
        "",
    ])
    for item in data["m7a"]["integration_order"]:
        lines.append(f"1. {item}")
    lines.extend([
        "",
        "## Safety Notes",
        "",
        "- No original files were deleted, moved, renamed, overwritten, or extracted into their original directories.",
        "- No real Provider request was made.",
        "- Runtime database business rows, credentials, signed URLs, image/video body content, and Provider output bodies were not read or reported.",
        "- Archives were inspected through Python zip/tar listing APIs and manifest reads only.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    files, dirs = walk_candidates()
    file_records = []
    archive_records = []
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        record = {"path": str(path), "size": size, "sha256": "", "classification": "KEEP_REFERENCE"}
        if size <= MAX_HASH_BYTES:
            try:
                record["sha256"] = sha256_file(path)
            except OSError:
                record["classification"] = "INCOMPLETE_OR_BROKEN"
        else:
            record["sha256"] = "SKIPPED_LARGE_FILE"
        if is_archive(path):
            archive = archive_summary(path)
            archive_records.append(archive)
            record["classification"] = "ARCHIVE_CANDIDATE" if "batch" in path.name.lower() or "patch" in path.name.lower() else "KEEP_REFERENCE"
        file_records.append(record)

    package_dirs = sorted({d for d in dirs if (d / "skill.json").is_file()}, key=lambda p: p.as_posix())
    packages = [package_summary(path, "local_dir") for path in package_dirs]
    bundle_dirs = sorted({d for d in dirs if d.name.lower().startswith("ai-drama-skills") or (d / "skills").is_dir()}, key=lambda p: p.as_posix())
    bundles = [bundle_summary(path) for path in bundle_dirs]
    archive_bundles = [
        archive_bundle_candidate(archive)
        for archive in archive_records
        if "ai-drama-skills" in Path(archive.get("path", "")).name.lower()
        and archive.get("skill_dir_count", 0) > 0
    ]
    bundles.extend(archive_bundles)

    for archive in archive_records:
        for skill_dir in archive.get("skill_dirs", []):
            packages.append(package_summary_from_archive_skill_dir(archive, skill_dir))
        for manifest in archive.get("manifests", []):
            if manifest.get("skill_id"):
                packages.append({
                    "source": "archive_manifest",
                    "source_path": manifest["path"],
                    "archive_path": archive["path"],
                    "manifest_path": manifest["path"],
                    "skill_id": manifest["skill_id"],
                    "display_name": manifest["display_name"],
                    "skill_version": manifest["version"],
                    "package_status": "",
                    "input_contract": [],
                    "output_contract": [],
                    "validators": [],
                    "dependencies": [],
                    "approval_gate": "",
                    "execution_profiles": [],
                    "sha256": manifest["sha256"],
                    "file_count": 0,
                    "complete_package_shape": False,
                    "digest": {},
                })

    packages = [package for package in packages if is_ai_drama_package(package)]
    runtime = repo_runtime_state()
    classified, _ = classify_packages(packages, runtime)
    dup = duplicate_stats(file_records + archive_records + packages)
    by_skill = defaultdict(list)
    for item in classified:
        by_skill[item["skill_id"]].append(item)
    latest_by_skill = {
        skill: max(items, key=lambda item: version_key(item.get("skill_version", "")))
        for skill, items in by_skill.items()
    }
    runtime_by_skill = {
        entry["skill_id"]: entry["version"]
        for entry in runtime["registry_entries"]
        if entry["skill_id"] in runtime["web_runtime_refs"].get("script_web", "")
        or entry["skill_id"] in runtime["web_runtime_refs"].get("storyboard_web", "")
        or entry["skill_id"] in runtime["web_runtime_refs"].get("shot_prompt_web", "")
    }
    current_refs = {
        ref for key, ref in runtime["web_runtime_refs"].items() if not key.endswith("fallback")
    }
    fallback_refs = {
        ref for key, ref in runtime["web_runtime_refs"].items() if key.endswith("fallback")
    }
    for ref in current_refs:
        if "@" in ref:
            sid, ver = ref.rsplit("@", 1)
            runtime_by_skill[sid] = ver

    def bundle_rank(item: dict[str, Any]) -> tuple:
        path_text = item.get("path", "").lower()
        release_preference = 1 if "/05-release/" in path_text or "05-release" in path_text else 0
        archive_preference = 1 if item.get("status") == "COMPLETE_RELEASE_ARCHIVE_CANDIDATE" else 0
        return (*version_key(item.get("version", "")), release_preference, archive_preference, item.get("skill_count", 0), path_text)

    latest_bundle = max(bundles, key=bundle_rank, default=None)

    bundle_skill_ids = {
        item.get("skill_id", "")
        for item in (latest_bundle or {}).get("skills", [])
        if item.get("skill_id")
    }
    expected_m7a = sorted(bundle_skill_ids) + ["material extraction", "video execution", "video QC"]
    present_skill_ids = set(by_skill)
    runtime_connected_skill_ids = {ref.rsplit("@", 1)[0] for ref in current_refs}
    missing_skills = [item for item in expected_m7a if item.startswith("ai-drama-") and item not in runtime_connected_skill_ids]
    orchestrator_candidates = [
        item for item in packages
        if "orchestrator" in (item.get("skill_id", "") + " " + item.get("source_path", "") + " " + item.get("display_name", "")).lower()
    ]
    orchestrator_status = "NOT_FOUND_IN_CURRENT_RUNTIME"
    latest_orchestrator_version = "not-found"
    if orchestrator_candidates:
        latest_orch = max(orchestrator_candidates, key=lambda item: version_key(item.get("skill_version", "")))
        latest_orchestrator_version = latest_orch.get("skill_version", "") or "unknown"
        orchestrator_status = "NEWER_LOCAL_NOT_IN_RUNTIME"

    gap_matrix = []
    matrix_skill_ids = sorted(bundle_skill_ids | runtime_connected_skill_ids | {"material extraction", "video execution", "video QC"})
    for skill_id in matrix_skill_ids:
        latest = latest_by_skill.get(skill_id, {})
        runtime_version = runtime_by_skill.get(skill_id, "")
        registered = any(entry["skill_id"] == skill_id for entry in runtime["registry_entries"])
        web = any(ref.startswith(skill_id + "@") for ref in current_refs)
        fallback = any(ref.startswith(skill_id + "@") for ref in fallback_refs)
        tests = infer_tests(skill_id)
        gap_matrix.append({
            "skill": skill_id,
            "latest_source_version": latest.get("skill_version", "not-found"),
            "runtime_current_version": runtime_version or "not-registered",
            "registered": registered,
            "web_integrated": web,
            "agent_schedulable": web,
            "gate_mapped": web or fallback,
            "tests": tests,
            "m7a_action": recommended_action(skill_id, latest, "CURRENT" if web else "MISSING_FROM_RUNTIME", web),
        })

    classification_counts = defaultdict(int)
    for record in file_records:
        classification_counts[record.get("classification", "KEEP_REFERENCE")] += 1
    for item in classified:
        if item["status"] in {"CURRENT"}:
            classification_counts["KEEP_CANONICAL"] += 1
        elif item["status"] in {"OBSOLETE"}:
            classification_counts["OBSOLETE"] += 1
        elif item["status"] in {"NEWER_LOCAL_NOT_IN_RUNTIME", "MISSING_FROM_RUNTIME"}:
            classification_counts["KEEP_REFERENCE"] += 1
        elif item["status"] == "INCOMPLETE":
            classification_counts["INCOMPLETE_OR_BROKEN"] += 1
    classification_counts["DUPLICATE_EXACT"] = dup["exact_duplicate_count"]
    classification_counts["DUPLICATE_DIVERGED"] = dup["diverged_duplicate_count"]

    bundle_skill_count = latest_bundle.get("skill_count", 0) if latest_bundle else 0
    missing_runtime_count = len([item for item in bundle_skill_ids if item not in runtime_connected_skill_ids])

    answers = {
        "1_latest_bundle_version": latest_bundle.get("version", "not-found") if latest_bundle else "not-found",
        "2_latest_bundle_path": latest_bundle.get("path", "not-found") if latest_bundle else "not-found",
        "3_latest_workflow_orchestrator_version": latest_orchestrator_version,
        "4_latest_script_adaptation_skill_version": latest_by_skill.get("ai-drama-script-adaptation-skill", {}).get("skill_version", "not-found"),
        "5_latest_storyboard_skill_version": latest_by_skill.get("ai-drama-storyboard-design-skill", {}).get("skill_version", "not-found"),
        "6_runtime_registered_skill_count": len(runtime_connected_skill_ids),
        "7_bundle_skills_not_in_runtime": missing_runtime_count,
        "8_agent_orchestrator_in_chain": orchestrator_status,
        "9_m7a_source_baseline": latest_bundle.get("path", str(REPO_ROOT / "skills")) if latest_bundle else str(REPO_ROOT / "skills"),
        "10_archive_candidates": sum(1 for item in file_records if item.get("classification") == "ARCHIVE_CANDIDATE"),
    }

    data = {
        "schema_version": "m7a-skills-runtime-gap-audit-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repository": "Java-zengzhiwen/ai-drama",
        "branch": run_git(["branch", "--show-current"]),
        "head": run_git(["rev-parse", "HEAD"]),
        "scan_roots": [str(item) for item in SCAN_ROOTS],
        "excluded_dir_names": sorted(EXCLUDED_DIR_NAMES),
        "git_history": git_skill_history(),
        "files_scanned": len(file_records),
        "candidate_dirs": len(dirs),
        "file_records": file_records[:1000],
        "file_records_truncated": max(0, len(file_records) - 1000),
        "archives": archive_records,
        "bundles": bundles,
        "packages": packages,
        "classified_packages": classified,
        "runtime": runtime,
        "gap_matrix": gap_matrix,
        "duplicate_stats": dup,
        "classification_counts": dict(classification_counts),
        "answers": answers,
        "m7a": {
            "source_baseline": answers["9_m7a_source_baseline"],
            "runtime_baseline": ", ".join(sorted(current_refs)),
            "missing_skills": missing_skills,
            "orchestrator_status": orchestrator_status,
            "integration_order": integration_order(classified),
        },
        "real_provider_requests": False,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(build_report(data), encoding="utf-8")
    print(json.dumps({
        "markdown": str(REPORT_MD),
        "json": str(REPORT_JSON),
        "latest_bundle_version": answers["1_latest_bundle_version"],
        "latest_script": answers["4_latest_script_adaptation_skill_version"],
        "latest_storyboard": answers["5_latest_storyboard_skill_version"],
        "runtime_count": answers["6_runtime_registered_skill_count"],
        "bundle_skill_count": bundle_skill_count,
        "missing_runtime_count": missing_runtime_count,
        "archives": len(archive_records),
        "files_scanned": len(file_records),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
