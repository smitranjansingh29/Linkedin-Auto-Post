"""
Send a pending draft to Telegram with Approve / Reject inline buttons.
The callback from those buttons is handled by cloudflare/worker.js, not this script.
"""
import json
import os
import sys
import urllib.request

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send(draft_id, draft_text, story_title):
    text = f"New draft ready:\n\n{draft_text}\n\n---\nSource: {story_title}"
    keyboard = {
        "inline_keyboard": [[
            {"text": "Approve", "callback_data": f"approve:{draft_id}"},
            {"text": "Reject", "callback_data": f"reject:{draft_id}"},
        ]]
    }
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "reply_markup": keyboard,
    }).encode()

    req = urllib.request.Request(
        API_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main():
    draft_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not draft_id:
        raise SystemExit("Usage: send_telegram.py <draft_id>")

    with open(f"pending/{draft_id}.json") as f:
        record = json.load(f)

    send(draft_id, record["draft"], record["story"]["title"])
    print(f"Sent draft {draft_id} to Telegram for approval")


if __name__ == "__main__":
    main()
