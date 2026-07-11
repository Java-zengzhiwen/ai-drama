# AI Drama LaunchAgent Runbook

This runbook keeps `ai-drama-web` available after the Codex terminal exits.
It installs user-level macOS LaunchAgents only. It does not change FRP, Nginx,
certificates, firewall rules, project data, generation jobs, results, reviews,
or provider requests.

## Files

- Web service template:
  `ops/launchd/fun.deltadevalex.ai-drama-web.plist.template`
- Health monitor template:
  `ops/launchd/fun.deltadevalex.ai-drama-health.plist.template`
- Installed web plist:
  `~/Library/LaunchAgents/fun.deltadevalex.ai-drama-web.plist`
- Installed health plist:
  `~/Library/LaunchAgents/fun.deltadevalex.ai-drama-health.plist`

The templates use placeholders for local paths:

- `__PROJECT_ROOT__`
- `__HOME__`
- `__AI_DRAMA_WEB_BIN__`

## Install

From the project root:

```bash
tools/install_ai_drama_launchagents.sh
```

The installer checks:

- `.venv/bin/ai-drama-web` exists;
- `runtime-data` exists;
- `skills` exists;
- `runtime-data/secrets/agnes-api-key` exists and has mode `600`.

It prints only `Agnes configured=true` for key readiness. It must not read or
print the key value. Do not put the Agnes key in a plist, shell profile, script,
document, commit, or log.

## Uninstall

```bash
tools/uninstall_ai_drama_launchagents.sh
```

The uninstaller unloads and removes only the two user LaunchAgent plist files.
It does not remove logs, local data, secrets, databases, repository files, or
provider artifacts.

## Status

```bash
launchctl print "gui/$(id -u)/fun.deltadevalex.ai-drama-web"
launchctl print "gui/$(id -u)/fun.deltadevalex.ai-drama-health"
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Expected web service state is `running`. The health monitor is loaded and runs
at load time, then every 300 seconds.

## Health Checks

Run the same read-only check used by the health LaunchAgent:

```bash
tools/check_ai_drama_gateway.sh
```

It checks only:

- `http://127.0.0.1:8000/api/health`
- `https://assets.deltadevalex.fun/healthz`
- `fun.deltadevalex.ai-drama-web`
- `fun.deltadevalex.frpc`

The script uses `curl --noproxy '*'`, a five second connect timeout, and a
fifteen second maximum request time. It does not submit generation work, change
network configuration, or print signed asset URLs.

To verify Agnes key readiness without exposing the key:

```bash
curl --noproxy '*' --connect-timeout 5 --max-time 15 \
  http://127.0.0.1:8000/api/settings/agnes
```

Record only whether `configured` is true.

## Logs

- `~/Library/Logs/ai-drama-web/stdout.log`
- `~/Library/Logs/ai-drama-web/stderr.log`
- `~/Library/Logs/ai-drama-health/stdout.log`
- `~/Library/Logs/ai-drama-health/stderr.log`

Logs must not contain authorization headers, provider keys, signed URL query
parameters, or complete temporary asset URLs.

## Port 8000 Conflicts

Before installing, inspect the current listener:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
ps -p <PID> -o pid=,ppid=,tty=,command=
```

Only stop the process if the command proves it belongs to this project's
temporary `ai-drama-web` or Uvicorn process. Do not stop unrelated listeners.

## Restart Verification

The safer reboot test is manual:

1. Quit open work safely.
2. Restart from the macOS menu.
3. Log back in as the same user.
4. Run `tools/check_ai_drama_gateway.sh`.
5. Confirm local health, public health, web LaunchAgent, and FRP LaunchAgent.

LaunchAgents start after user login. They do not prove availability while the
Mac is powered off, logged out, asleep, disconnected from the network, or out
of public traffic quota.

## Public Gateway Dependencies

The public asset route depends on all of these layers:

- this Mac running `ai-drama-web`;
- the `fun.deltadevalex.frpc` user LaunchAgent;
- ECS `frps`;
- ECS Nginx;
- DNS and certificate validity;
- available public bandwidth and traffic quota.

If public health fails while local health passes, inspect FRP, ECS, Nginx, DNS,
certificate, and traffic quota separately.
