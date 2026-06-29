import json
import os

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
