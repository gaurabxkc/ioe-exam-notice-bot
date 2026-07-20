# IOE Notice → Discord Bot

Checks the Tribhuvan University IOE Examination Control Division notice page
every 15 minutes and posts new notices to a Discord channel.

## Setup (5 minutes)

### 1. Create a Discord webhook
1. In Discord, go to the channel you want notices posted to.
2. Channel Settings → Integrations → Webhooks → New Webhook.
3. Copy the Webhook URL.

### 2. Create a GitHub repo
1. Create a new **private or public** repo on GitHub (e.g. `ioe-notice-bot`).
2. Upload all the files in this folder to it (or `git push` them).

### 3. Add the webhook as a secret
1. In your repo: Settings → Secrets and variables → Actions → New repository secret.
2. Name: `DISCORD_WEBHOOK_URL`
3. Value: paste the webhook URL from step 1.

### 4. Enable Actions
1. Go to the "Actions" tab of your repo and enable workflows if prompted.
2. The workflow `Check IOE Notices` will now run automatically every 15 minutes.
3. To test it immediately: Actions tab → "Check IOE Notices" → "Run workflow".

## How it works
- `check_notices.py` fetches the notice list page and finds all notice links
  (`/Notice/Index/<id>`).
- `seen_notices.json` keeps track of which notice IDs have already been posted.
  The workflow commits this file back to the repo after each run so state
  persists between runs.
- On the very first run, it just records the current notices as "seen" and
  does **not** post them to Discord (so you don't get flooded with the whole
  history) — only genuinely new notices after that get posted.

## Adjusting the check frequency
Edit the cron line in `.github/workflows/check-notices.yml`:
```
- cron: "*/15 * * * *"   # every 15 minutes
- cron: "0 * * * *"      # every hour
- cron: "0 */6 * * *"    # every 6 hours
```
(Note: GitHub Actions free-tier schedules can run a few minutes late during
peak load — this is normal.)

## If parsing breaks
The site's HTML structure changing could break detection. If you stop
getting notified and suspect this, run `python check_notices.py` locally
(with `DISCORD_WEBHOOK_URL` unset) and check the console output / open an
issue — the scraper may need its link pattern updated.
