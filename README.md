# Esprit de Corps — Monitoring Dashboard

Static Quarto dashboard rendered by GitHub Actions and published to GitHub
Pages. Reads bilge pump and power data from a public Google Sheet plus rainfall
from Open-Meteo. No server, no runtime quota, no credentials.

Rendering is triggered by an external local-time cron on an always-on thin
client (`workflow_dispatch`), because GitHub's own `schedule:` cron is throttled
on the free tier. See [`deploy/README.md`](deploy/README.md).

## One-time setup

1. **Create a new GitHub repository** (public is fine; private also works with
   Pages on any plan now).

2. **Add these files** to the repo root, preserving the folder structure:
   ```
   dashboard.qmd
   custom.scss
   _quarto.yml
   index.html
   README.md
   .github/workflows/render.yml
   ```

3. **Enable GitHub Pages with Actions as the source:**
   - Repo → Settings → Pages
   - Under "Build and deployment" → Source → select **GitHub Actions**

4. **Trigger the first render:**
   - Repo → Actions tab → "Render and Deploy Dashboard" → **Run workflow**
   - Or just push a commit — it renders on push to `main`

5. **View it:** once the workflow finishes, the dashboard is at
   `https://<your-username>.github.io/<repo-name>/`

6. **Set up the recurring trigger:** follow [`deploy/README.md`](deploy/README.md)
   to install the cron trigger on the thin client.

## Schedule

Renders every 30 min from 9 AM–6 PM EDT, plus 10 PM and 6 AM EDT. This cadence
is set by a `cron` job on the `wallcal` thin client, which calls the
`workflow_dispatch` API — GitHub's built-in `schedule:` cron was throttled on
the free tier to roughly one run every few hours, so it was removed. Full setup
in [`deploy/README.md`](deploy/README.md).

## Updating

Edit `dashboard.qmd` and push. The push triggers a re-render and redeploy
automatically. To change the render cadence, edit the crontab on the `wallcal`
box (see [`deploy/README.md`](deploy/README.md)), not this repo.

## Cost

Free. GitHub Actions free tier is 2,000 minutes/month; with R package caching
each run is ~1 minute. The trigger fires roughly 21 runs/day × ~1 min ≈ 630
min/month, well under the limit.

## Data source

The Google Sheet must remain shared as "Anyone with the link → Viewer" for the
public fetch to work. No API key or secret is stored anywhere.

## Follow-ups

Open items for the render pipeline, in priority order:

1. **Monitor for a silent trigger stall.** The fine-grained PAT on the `wallcal`
   box expires; when it does, the trigger fails with `HTTP 401` into a tmpfs log
   nobody watches, and renders quietly stop. The dashboard navbar shows its last
   render time, so a stale page is visible to anyone looking — but nothing
   actively alerts. Best fix: a dead-man's-switch check (e.g. healthchecks.io,
   free tier) — one added line in `deploy/wallcal-edc-trigger.py` to ping a URL
   on a successful dispatch, with the service alerting when a ping is missed.
   That covers token expiry, box offline, cron disabled and dead network in one
   go. Until it's in place: record the PAT expiry date and rotate a week ahead.

2. **Concurrency can back renders up.** `render.yml` uses `concurrency: pages`
   with `cancel-in-progress: false`. With ~1-minute cached renders on a
   30-minute trigger this is fine, but if a render runs long (a cold R-package
   cache is ~4 min, or a slow runner) dispatches queue and you get
   cancelled-run cascades plus delayed deploys. No change needed now — just
   recognise the pattern if cancelled runs start piling up.

3. **Housekeeping.**
   - A cluster of manual `workflow_dispatch` runs around 2026-09-06 is from
     building and testing the trigger — harmless.
   - `/etc/fstab.bak-20260906` on the `wallcal` box is a backup from switching
     `/` to `noatime`; safe to delete once the mount is confirmed good.
