import json
import os
import hashlib

from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.storyboard_renderer import (
    RENDERER_ID,
    RENDERER_VERSION,
    render_storyboard_markdown,
)


def _fixture(name):
    with open("tests/fixtures/storyboard_canonical/%s" % name, encoding="utf-8") as handle:
        return json.load(handle)


def test_renderer_matches_minimal_golden():
    data = _fixture("valid_minimal.json")
    expected = open("tests/golden/storyboard_renderer/expected_rendered_minimal.md", encoding="utf-8").read()

    rendered = render_storyboard_markdown(data)

    assert rendered == expected
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")


def test_renderer_matches_full_golden():
    data = _fixture("valid_full.json")
    expected = open("tests/golden/storyboard_renderer/expected_rendered_full.md", encoding="utf-8").read()

    assert render_storyboard_markdown(data) == expected


def test_renderer_is_deterministic_across_environment_changes(monkeypatch):
    data = _fixture("valid_minimal.json")
    first = render_storyboard_markdown(data)

    monkeypatch.setenv("COLUMNS", "12")
    monkeypatch.setenv("LANG", "C")
    os.environ["AI_DRAMA_RENDERER_NOISE"] = "ignored"
    second = render_storyboard_markdown(data)

    assert second == first
    assert RENDERER_ID == "storyboard-canonical-markdown-renderer"
    assert RENDERER_VERSION == "1.0.0"


def test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash():
    service = RuntimeService(store=None)
    canonical_hash = "a" * 64
    markdown_hash = "b" * 64

    first = service._build_storyboard_bundle_manifest(
        revision_id="revision-a",
        canonical_content_hash=canonical_hash,
        rendered_markdown_hash=markdown_hash,
    )
    second = service._build_storyboard_bundle_manifest(
        revision_id="revision-b",
        canonical_content_hash=canonical_hash,
        rendered_markdown_hash=markdown_hash,
    )

    assert first["business_preimage"] == second["business_preimage"]
    assert "revision_id" not in first["business_preimage"]
    assert "bundle_manifest_hash" not in first["business_preimage"]
    assert first["bundle_manifest_hash"] == second["bundle_manifest_hash"]
    assert first["manifest"]["revision_id"] == "revision-a"
    assert second["manifest"]["revision_id"] == "revision-b"
    assert first["manifest"]["bundle_manifest_hash"] == first["bundle_manifest_hash"]
    assert first["manifest"]["outputs"] == [
        {
            "logical_type": "rendered_markdown",
            "content_hash": markdown_hash,
            "media_type": "text/markdown",
            "generator": "storyboard-canonical-markdown-renderer",
            "generator_version": "1.0.0",
        }
    ]


def test_bundle_manifest_uses_canonical_json_v1_bytes():
    service = RuntimeService(store=None)
    value = {"z": "终", "a": [3, {"b": 2, "a": 1}]}

    data = service._canonical_json_v1_bytes(value)

    assert data == b'{"a":[3,{"a":1,"b":2}],"z":"\xe7\xbb\x88"}'
    assert not data.endswith(b"\n")
    assert hashlib.sha256(data).hexdigest() == service._sha256_bytes(data)


def test_bundle_output_metadata_matches_frozen_contract():
    service = RuntimeService(store=None)
    canonical = _fixture("valid_minimal.json")

    rendered = service._rendered_markdown_output(canonical)
    manifest = service._build_storyboard_bundle_manifest(
        revision_id="revision-a",
        canonical_content_hash="a" * 64,
        rendered_markdown_hash=rendered["content_hash"],
    )

    assert rendered == {
        "logical_type": "rendered_markdown",
        "bytes": render_storyboard_markdown(canonical).encode("utf-8"),
        "content_hash": hashlib.sha256(render_storyboard_markdown(canonical).encode("utf-8")).hexdigest(),
        "media_type": "text/markdown",
        "generator": "storyboard-canonical-markdown-renderer",
        "generator_version": "1.0.0",
    }
    assert manifest["logical_type"] == "bundle_manifest"
    assert manifest["media_type"] == "application/json"
    assert manifest["generator"] == "bundle-manifest-builder"
    assert manifest["generator_version"] == "1"
    assert manifest["bytes"] == service._canonical_json_v1_bytes(manifest["manifest"])
    assert not manifest["bytes"].endswith(b"\n")
    assert manifest["content_hash"] == hashlib.sha256(manifest["bytes"]).hexdigest()
    assert manifest["content_hash"] != manifest["bundle_manifest_hash"]
