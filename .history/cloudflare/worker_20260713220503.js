/**
 * Telegram webhook handler.
 * When you tap Approve/Reject in Telegram, this Worker:
 *   - reads the pending/<id>.json file from GitHub
 *   - Approve -> writes it to approved/<id>.json (deletes from pending/)
 *   - Reject  -> just deletes it from pending/
 * Writing to approved/ triggers publish.yml automatically via GitHub Actions.
 *
 * Deploy with: wrangler deploy
 * Set secrets with:
 *   wrangler secret put GH_PAT
 *   wrangler secret put TELEGRAM_BOT_TOKEN
 * Edit GITHUB_REPO below to "yourname/linkedin-auto-poster".
 */

const GITHUB_REPO = "smitranjansingh29/Linkedin-Auto-Post";
const GITHUB_API = `https://api.github.com/repos/${GITHUB_REPO}/contents`;

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("ok");
    }

    const update = await request.json();
    const callback = update.callback_query;
    if (!callback) {
      return new Response("ok");
    }

    const [action, draftId] = callback.data.split(":");
    const ghHeaders = {
      Authorization: `Bearer ${env.GH_PAT}`,
      "User-Agent": "linkedin-auto-poster-worker",
      Accept: "application/vnd.github+json",
    };

    // Fetch the pending file (need its sha to delete/move it)
    const getResp = await fetch(`${GITHUB_API}/pending/${draftId}.json`, {
      headers: ghHeaders,
    });
    if (!getResp.ok) {
      await answerCallback(env, callback.id, "Draft not found (already handled?)");
      return new Response("ok");
    }
    const fileData = await getResp.json();
    const content = fileData.content; // base64

    if (action === "approve") {
      // Create in approved/
      await fetch(`${GITHUB_API}/approved/${draftId}.json`, {
        method: "PUT",
        headers: ghHeaders,
        body: JSON.stringify({
          message: `Approve draft ${draftId}`,
          content,
        }),
      });
    }

    // Either way, remove from pending/
    await fetch(`${GITHUB_API}/pending/${draftId}.json`, {
      method: "DELETE",
      headers: ghHeaders,
      body: JSON.stringify({
        message: `Remove pending draft ${draftId} (${action})`,
        sha: fileData.sha,
      }),
    });

    await answerCallback(
      env,
      callback.id,
      action === "approve" ? "Approved — publishing shortly" : "Rejected"
    );

    return new Response("ok");
  },
};

async function answerCallback(env, callbackQueryId, text) {
  await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/answerCallbackQuery`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ callback_query_id: callbackQueryId, text }),
    }
  );
}
