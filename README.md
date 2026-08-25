# Esprit de Corps — Monitoring Dashboard

Static Quarto dashboard rendered on a schedule by GitHub Actions and published
to GitHub Pages. Reads bilge pump and power data from a public Google Sheet plus
rainfall from Open-Meteo. No server, no runtime quota, no credentials.

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

## Schedule

Renders every 30 min from 9 AM–6 PM EDT, plus 10 PM and 6 AM EDT. Times are set
in UTC in the workflow and assume EDT (boat is hauled out before EST). GitHub
cron can be delayed 5–15 min under load; that's expected and harmless here.

## Updating

Edit `dashboard.qmd` and push. The push triggers a re-render and redeploy
automatically. To change the schedule, edit the `cron:` lines in
`.github/workflows/render.yml`.

## Cost

Free. GitHub Actions free tier is 2,000 minutes/month; with R package caching
each run is ~1 minute. The schedule uses roughly 21 runs/day × ~1 min ≈ 630
min/month, well under the limit.

## Data source

The Google Sheet must remain shared as "Anyone with the link → Viewer" for the
public fetch to work. No API key or secret is stored anywhere.
