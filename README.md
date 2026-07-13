# LinkedIn Auto-Poster — $0/month tech news bot

Automatically finds trending tech news, drafts a LinkedIn post with AI, sends it to you
on Telegram for a one-tap approval, then publishes it to LinkedIn. No paid services.

## How it works (2 workflows)

```
WORKFLOW A — runs every few hours (GitHub Actions cron)
  1. Fetch news from RSS / Hacker News / Reddit
  2. Dedupe + score by trend strength
  3. Ask Gemini (free tier) to draft a LinkedIn post
  4. Save draft as pending/<id>.json in the repo
  5. Send you a Telegram message with Approve / Reject buttons

WORKFLOW B — triggered instantly when you tap a button
  6. Telegram sends the button tap to a Cloudflare Worker (free, always-on)
  7. Worker moves the file from pending/ to approved/ (or deletes it) via GitHub API
  8. That file move triggers a second GitHub Action
  9. That action publishes the approved post to LinkedIn
```

Why two workflows instead of one? GitHub Actions only runs on a schedule or a trigger —
it can't sit there waiting for you to tap a Telegram button. Cloudflare Workers *can*
sit there (as a webhook endpoint) for free, so it bridges the gap.

## Accounts you need to create (all free tier)

| Service | What for | Link |
|---|---|---|
| GitHub | Hosts the code + runs the cron jobs | github.com |
| Telegram | Bot that sends you drafts to approve | Use @BotFather in Telegram to create a bot, get a token |
| Google AI Studio | Free Gemini API key for drafting posts | aistudio.google.com |
| Cloudflare | Free Worker to catch the button tap | dash.cloudflare.com |
| LinkedIn Developer | App + access token to post on your behalf | developer.linkedin.com |
| Reddit (optional) | API app for r/technology etc. | reddit.com/prefs/apps |

## Setup steps

1. **Create the repo** — push this folder to a new GitHub repo (private is fine).

2. **Create a Telegram bot**
   - Message `@BotFather` → `/newbot` → get your `TELEGRAM_BOT_TOKEN`
   - Message your new bot once, then visit
     `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your `chat_id`

3. **Get a Gemini API key** — aistudio.google.com → "Get API key" → copy it.

4. **Set up LinkedIn API access**
   - Create an app at developer.linkedin.com
   - Request the `w_member_social` scope (needed to post on your behalf) —
     this requires LinkedIn's review/approval, it's the one step that isn't instant
   - Complete OAuth once to get a long-lived access token + your LinkedIn member URN

5. **Add secrets to your GitHub repo**
   Settings → Secrets and variables → Actions → New repository secret, add:
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
   - `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_URN`
   - `GH_PAT` — a GitHub Personal Access Token with `repo` scope, used by the
     Cloudflare Worker to push commits back to this repo
   - `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` (optional)

6. **Deploy the Cloudflare Worker**
   - `cloudflare/worker.js` in this repo is the webhook handler
   - `npm install -g wrangler`, then `wrangler deploy` from that folder
   - Set the same secrets (`GH_PAT`, `TELEGRAM_BOT_TOKEN`) as Worker secrets via `wrangler secret put`
   - Register the webhook:
     `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<your-worker-url>`

7. **Turn on the schedule** — the workflow in `.github/workflows/generate.yml`
   already has a cron trigger (every 4 hours). Edit the cron expression to taste.

8. **Test it** — go to Actions tab → run `generate.yml` manually once →
   check Telegram → tap Approve → check the Actions tab again for `publish.yml` running.

## Folder structure

```
scripts/
  fetch_sources.py       # pulls RSS / HN / Reddit stories
  dedupe_score.py         # dedupes + ranks by trend strength
  generate_draft.py       # calls Gemini, writes pending/<id>.json
  send_telegram.py        # sends the draft with Approve/Reject buttons
  publish_linkedin.py     # posts an approved draft to LinkedIn
cloudflare/
  worker.js                # Telegram webhook -> moves file pending/ -> approved/
.github/workflows/
  generate.yml              # cron: steps 1-5
  publish.yml                # triggered on push to approved/: step 9
pending/                      # drafts awaiting your approval (auto-created)
approved/                     # approved drafts, picked up by publish.yml
posted/                       # archive of what's already gone out
```

## Costs at this scale (roughly 1 post/day)

- GitHub Actions: free tier is 2,000 min/month, this uses a few minutes/month
- Cloudflare Workers: free tier is 100,000 requests/day, this uses maybe 30/month
- Gemini API free tier: comfortably covers a few requests/day
- Telegram Bot API: free, no limits at this volume
- LinkedIn API: free to use once approved

**Total: $0/month.**

## Notes

- Start with the human-approval step even if you plan to remove it later —
  it catches bad drafts before they go out.
- LinkedIn's `w_member_social` approval can take time; while waiting, test the
  rest of the pipeline by having `publish_linkedin.py` just print instead of post.
- If you outgrow Gemini's free tier, swap `generate_draft.py`'s API call for
  Claude or keep Gemini — the rest of the pipeline doesn't care which model you use.
