# External render trigger — `wallcal` thin client

The dashboard re-renders on GitHub's runners, but the **cadence is driven from
outside GitHub**. GitHub's free-tier `schedule:` cron was throttled to roughly
one run every few hours, so `render.yml` no longer uses `schedule:` — it renders
on `workflow_dispatch` and on push to `main`.

An always-on Debian 13 thin client on the home LAN (hostname `wallcal`, an
HP t630 that also drives a wall-calendar kiosk) runs a local-time `cron` job
that makes one lightweight HTTPS call to the `workflow_dispatch` API. No
rendering happens on that box — it only pokes GitHub.

## `wallcal-edc-trigger.py`

Python 3 standard library only (`urllib`) — no venv, no pip, no `curl` (the box
doesn't have it and is flash-constrained). It:

- reads a fine-grained PAT from `~/.config/edc-trigger/token` (mode `600`),
- POSTs `{"ref":"main"}` to
  `https://api.github.com/repos/jstrin/edc_monitor/actions/workflows/render.yml/dispatches`
  with the `Authorization: Bearer`, `Accept: application/vnd.github+json` and
  `X-GitHub-Api-Version: 2022-11-28` headers,
- treats HTTP **204** as success, logs anything else with a diagnostic hint,
- writes timestamped (local-time) OK/FAIL lines to `/dev/shm/edc-trigger/trigger.log`
  — tmpfs, so routine logging never touches flash; trimmed to 200 lines; clears
  on reboot.

Exit status is `0` only on a confirmed 204.

## Install on the box

```sh
install -Dm755 deploy/wallcal-edc-trigger.py ~/.local/bin/edc-trigger.py
mkdir -p ~/.config/edc-trigger && chmod 700 ~/.config/edc-trigger
( umask 077; : > ~/.config/edc-trigger/token )
```

### Fine-grained PAT

GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new:

- **Resource owner:** `jstrin`
- **Repository access:** Only select repositories → `jstrin/edc_monitor`
- **Permissions → Repository → Actions:** Read and write (nothing else)

Paste it as the only line of `~/.config/edc-trigger/token` (e.g. with `nano`, so
it never enters shell history). Blast radius if leaked: extra renders of a
public dashboard.

### Crontab (`crontab -e`, user account, box is on `America/New_York`)

```cron
# edc_monitor render trigger  (local time)
15,45 9-17 * * *  /usr/bin/python3 ~/.local/bin/edc-trigger.py >/dev/null 2>&1
15   18 * * *     /usr/bin/python3 ~/.local/bin/edc-trigger.py >/dev/null 2>&1
15   22 * * *     /usr/bin/python3 ~/.local/bin/edc-trigger.py >/dev/null 2>&1
15    6 * * *     /usr/bin/python3 ~/.local/bin/edc-trigger.py >/dev/null 2>&1
```

09:15–17:45 every 30 min, plus 18:15, 22:15, 06:15. Minute `:15/:45` is
deliberate — it sits between the `:08/:38` slots the old GitHub schedule used,
so if that schedule is ever restored the two interleave rather than colliding.

## Verify / operate

```sh
python3 ~/.local/bin/edc-trigger.py; echo $?      # expect: OK line, exit 0
tail -n 20 /dev/shm/edc-trigger/trigger.log
gh run list --repo jstrin/edc_monitor --event workflow_dispatch --limit 3
```

**Token expiry** shows as `FAIL  HTTP 401` in the log (cron output is
discarded, so the log is the only signal). Regenerate the PAT, paste it into
the same file — nothing else changes.

To pause: comment the four crontab lines.
