"""
Send the top story to Gemini (free tier) and get back a LinkedIn-ready draft.
Writes pending/<id>.json for approval.
"""
import json
import os
import time
import urllib.request

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
)

# Edit this to match your voice / niche
SYSTEM_PROMPT = """You write short, punchy LinkedIn posts about tech news for a
personal profile in the software/AI space. Style rules:
- Start with a 1-line hook, no generic openers like "Exciting news!"
- 2-4 short paragraphs or bullet points with the actual insight, not just a summary
- End with a genuine question to spark comments, not "Thoughts?"
- 3-5 relevant hashtags on their own line at the end
- Under 1300 characters total
- No emojis, no corporate buzzwords
- Write in first person as if you found this interesting and want to discuss it
"""


def generate(story):
    prompt = (
        f"{SYSTEM_PROMPT}\n\nStory title: {story['title']}\n"
        f"Source: {story['source']}\nURL: {story['url']}\n\n"
        "Write the LinkedIn post now."
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode()

    req = urllib.request.Request(
        GEMINI_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def main():
    with open("data/top_story.json") as f:
        story = json.load(f)

    draft_text = generate(story)

    draft_id = str(int(time.time()))
    os.makedirs("pending", exist_ok=True)
    record = {
        "id": draft_id,
        "story": story,
        "draft": draft_text,
        "status": "pending",
    }
    with open(f"pending/{draft_id}.json", "w") as f:
        json.dump(record, f, indent=2)

    print(f"Draft {draft_id} created")
    # Make the id available to the next step in the same GitHub Actions job
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
        f.write(f"draft_id={draft_id}\n")


if __name__ == "__main__":
    main()
