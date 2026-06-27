from pathlib import Path

import pytest

from ai_drama_runtime.acceptance import AcceptanceError, load_acceptance_bundle


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def test_acceptance_bundle_excludes_approved_reference_from_runtime_request():
    bundle = load_acceptance_bundle(ACCEPTANCE_ROOT)

    assert bundle.manifest["id"] == "shengsi-chapter-001"
    assert set(bundle.input_files) == {
        "source_chapter",
        "series_canon",
        "characters",
        "production_brief",
    }
    assert bundle.reference_output.path.name == "approved-script.md"

    request_text = bundle.to_runtime_request_text()
    assert "source-chapter.md" in request_text
    assert "approved-script.md" not in request_text
    assert bundle.reference_output.text not in request_text


def test_acceptance_bundle_rejects_absolute_paths(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    (root / "source.md").write_text("source", encoding="utf-8")
    (root / "approved.md").write_text("approved", encoding="utf-8")
    (root / "acceptance-manifest.yaml").write_text(
        """
id: bad
inputs:
  source_chapter: /tmp/source.md
reference_outputs:
  approved_script:
    path: approved.md
evaluation:
  exact_text_match: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(AcceptanceError, match="absolute"):
        load_acceptance_bundle(root)


def test_acceptance_bundle_rejects_symlink_escape(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("source", encoding="utf-8")
    (root / "source.md").symlink_to(outside)
    (root / "approved.md").write_text("approved", encoding="utf-8")
    (root / "acceptance-manifest.yaml").write_text(
        """
id: bad
inputs:
  source_chapter: source.md
reference_outputs:
  approved_script:
    path: approved.md
    status: user_approved_reference
evaluation:
  exact_text_match: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(AcceptanceError, match="escapes"):
        load_acceptance_bundle(root)
