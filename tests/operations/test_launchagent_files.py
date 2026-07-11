import plistlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

WEB_PLIST = ROOT / "ops/launchd/fun.deltadevalex.ai-drama-web.plist.template"
HEALTH_PLIST = ROOT / "ops/launchd/fun.deltadevalex.ai-drama-health.plist.template"
INSTALL = ROOT / "tools/install_ai_drama_launchagents.sh"
UNINSTALL = ROOT / "tools/uninstall_ai_drama_launchagents.sh"
CHECK = ROOT / "tools/check_ai_drama_gateway.sh"
DOC = ROOT / "docs/operations/ai-drama-launchagent.md"


def read(path: Path) -> str:
    assert path.exists(), f"missing expected file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def read_plist(path: Path) -> dict:
    assert path.exists(), f"missing expected file: {path.relative_to(ROOT)}"
    return plistlib.loads(path.read_bytes())


def test_launchagent_artifacts_do_not_embed_secret_material() -> None:
    combined = "\n".join(
        read(path)
        for path in (WEB_PLIST, HEALTH_PLIST, INSTALL, UNINSTALL, CHECK, DOC)
    )

    forbidden = ("AGNES_API_KEY", "Bearer", "password", "signature=", "X-Amz-Signature=")
    for needle in forbidden:
        assert needle not in combined

    assert "auth.token" not in combined
    assert "api_key=" not in combined


def test_web_plist_contains_required_launchd_and_runtime_configuration() -> None:
    text = read(WEB_PLIST)
    plist = read_plist(WEB_PLIST)

    assert "<string>fun.deltadevalex.ai-drama-web</string>" in text
    assert "<key>RunAtLoad</key>" in text
    assert "<key>KeepAlive</key>" in text
    assert "<key>WorkingDirectory</key>" in text
    assert "__PROJECT_ROOT__" in text
    assert "__HOME__" in text
    assert "__AI_DRAMA_WEB_BIN__" in text

    env = plist["EnvironmentVariables"]
    assert env["AI_DRAMA_RUNTIME_PROVIDER"] == "agnes"
    assert env["AI_DRAMA_PUBLIC_BASE_URL"] == "https://assets.deltadevalex.fun"
    assert env["AI_DRAMA_DATA_ROOT"] == "__PROJECT_ROOT__/runtime-data"
    assert env["AI_DRAMA_SKILLS_ROOT"] == "__PROJECT_ROOT__/skills"


def test_health_plist_runs_every_five_minutes_without_keepalive() -> None:
    text = read(HEALTH_PLIST)

    assert "<string>fun.deltadevalex.ai-drama-health</string>" in text
    assert "<key>RunAtLoad</key>" in text
    assert "<key>StartInterval</key>" in text
    assert "<integer>300</integer>" in text
    assert "<key>KeepAlive</key>" not in text
    assert "__PROJECT_ROOT__/tools/check_ai_drama_gateway.sh" in text


def test_install_script_only_installs_user_launchagents_without_sudo() -> None:
    text = read(INSTALL)

    assert "launchctl bootstrap \"gui/$(id -u)\"" in text
    assert "launchctl load" not in text
    assert "sudo" not in text
    assert "Library/LaunchAgents" in text
    without_user_dir = text.replace("$HOME/Library/LaunchAgents", "")
    without_user_dir = without_user_dir.replace("${HOME}/Library/LaunchAgents", "")
    assert "/Library/LaunchAgents" not in without_user_dir
    assert "plutil -lint" in text
    assert "Agnes configured=true" in text


def test_uninstall_script_does_not_remove_runtime_or_repository_data() -> None:
    text = read(UNINSTALL)

    assert "launchctl bootout \"gui/$(id -u)\"" in text
    assert "Library/LaunchAgents" in text
    for needle in ("runtime-data", "secrets", ".db", "rm -rf"):
        assert needle not in text


def test_health_script_is_read_only_gateway_check() -> None:
    text = read(CHECK)

    assert "--noproxy '*'" in text
    assert "--connect-timeout 5" in text
    assert "--max-time 15" in text
    assert "http://127.0.0.1:8000/api/health" in text
    assert "https://assets.deltadevalex.fun/healthz" in text
    assert "fun.deltadevalex.ai-drama-web" in text
    assert "fun.deltadevalex.frpc" in text

    forbidden_paths = ("/generation", "/generations", "/submit", "/rerun", "/videos")
    for path in forbidden_paths:
        assert path not in text
