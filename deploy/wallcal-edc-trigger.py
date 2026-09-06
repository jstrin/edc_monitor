#!/usr/bin/env python3
"""edc-trigger — fire a workflow_dispatch on jstrin/edc_monitor (render.yml).

Runs from cron on the always-on 'wallcal' thin client. GitHub's own scheduled
cron for this repo is throttled on the free tier (fires roughly once every few
hours), so this box provides a reliable local-time heartbeat instead. It does
NOT render anything locally — it only makes one lightweight HTTPS API call and
lets GitHub's runners do the work.

Design constraints (flash-conscious device):
  - stdlib only: urllib.request / urllib.error. No venv, no pip, no curl.
  - all logging goes to a tmpfs path (/dev/shm) so routine runs never touch flash.
  - the token is read from a 0600 file at runtime; it is never a CLI arg, never
    logged, never placed in the crontab.

Exit status: 0 on a confirmed HTTP 204 dispatch, 1 on any failure (so a wrapper
or `echo $?` can tell, though cron output is discarded).
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request

TOKEN_FILE = os.path.expanduser("~/.config/edc-trigger/token")
LOG_DIR = "/dev/shm/edc-trigger"
LOG_FILE = os.path.join(LOG_DIR, "trigger.log")
LOG_MAX_LINES = 200  # trimmed each run; tmpfs clears on reboot anyway

OWNER = "jstrin"
REPO = "edc_monitor"
WORKFLOW = "render.yml"
REF = "main"
API_URL = (
    f"https://api.github.com/repos/{OWNER}/{REPO}"
    f"/actions/workflows/{WORKFLOW}/dispatches"
)


def log(msg):
    """Append one timestamped (local time) line to the tmpfs log, then trim."""
    ts = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    line = f"{ts}  {msg}\n"
    try:
        os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
        with open(LOG_FILE, "a") as fh:
            fh.write(line)
        with open(LOG_FILE) as fh:
            lines = fh.readlines()
        if len(lines) > LOG_MAX_LINES:
            with open(LOG_FILE, "w") as fh:
                fh.writelines(lines[-LOG_MAX_LINES:])
    except OSError as exc:
        # Can't write the log — surface on stderr as a last resort. Under cron
        # with output discarded this is invisible, but a manual run will show it.
        sys.stderr.write(f"edc-trigger: log write failed: {exc}\n{line}")


def read_token():
    try:
        with open(TOKEN_FILE) as fh:
            token = fh.read().strip()
    except OSError as exc:
        log(f"FAIL  cannot read token file {TOKEN_FILE}: {exc}")
        sys.exit(1)
    if not token:
        log(f"FAIL  token file {TOKEN_FILE} is empty — paste the PAT into it")
        sys.exit(1)
    return token


def dispatch(token):
    body = json.dumps({"ref": REF}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "edc-trigger/1.0 (wallcal cron)")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        hint = {
            401: "token invalid or expired — rotate the PAT",
            403: "token lacks Actions: Read and write, or you are rate-limited",
            404: "repo/workflow not found, or the token cannot see this repo",
            422: "ref 'main' missing, or workflow_dispatch not enabled on render.yml",
        }.get(exc.code, "unexpected error")
        detail = ""
        try:
            detail = exc.read().decode(errors="replace").strip().replace("\n", " ")
        except Exception:  # noqa: BLE001 - best effort only
            pass
        log(f"FAIL  HTTP {exc.code} ({hint}){'  ' + detail if detail else ''}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        log(f"FAIL  network error: {exc.reason}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - never let cron see a traceback
        log(f"FAIL  unexpected: {exc!r}")
        sys.exit(1)

    if status == 204:
        log(f"OK    dispatched {WORKFLOW} @ {REF} (HTTP 204)")
        sys.exit(0)
    log(f"WARN  unexpected HTTP {status} (expected 204)")
    sys.exit(1)


def main():
    dispatch(read_token())


if __name__ == "__main__":
    main()
