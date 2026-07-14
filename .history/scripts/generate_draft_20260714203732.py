"""
Send the top story to Gemini (free tier) and get back a LinkedIn-ready draft.
Writes pending/<id>.json for approval.
"""

import json
import os
import time
import urllib.request
from urllib.error import HTTPError, URLError

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
)

SYSTEM_PROMPT = """
You write short, punchy LinkedIn posts about tech news for a
personal profile in the software/AI space.

Style rules:
- Start with a 1-line hook.
- No generic openers like "Exciting news!"
- 2-4 short paragraphs or bullet points.
- Add actual insight, not just a summary.
- End with a genuine question.
- 3-5 relevant hashtags on a separate line.
- Under 1300 characters.
- No emojis.
- No corporate buzzwords.
- Write in first person.
"""

MAX_RETRIES = 5


# -------------------------------------------------------------------
# Gemini API
# -------------------------------------------------------------------


def generate(story):
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Story title: {story['title']}\n"
        f"Source: {story['source']}\n"
        f"URL: {story['url']}\n\n"
        "Write the LinkedIn post now."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    body = json.dumps(payload).encode("utf-8")

    for attempt in range(MAX_RETRIES):

        req = urllib.request.Request(
            GEMINI_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:

                response = json.loads(resp.read().decode())

                if "candidates" not in response:
                    raise Exception(
                        f"Unexpected Gemini response:\n"
                        f"{json.dumps(response, indent=2)}"
                    )

                return response["candidates"][0]["content"]["parts"][0]["text"].strip()

        except HTTPError as e:

            error_text = e.read().decode()

            print("=" * 80)
            print(f"HTTP ERROR {e.code}")
            print(error_text)
            print("=" * 80)

            if e.code == 429:

                wait = 2**attempt

                print(f"Gemini rate limit reached." f" Waiting {wait} seconds...")

                time.sleep(wait)
                continue

            raise

        except URLError as e:

            print(f"Network Error: {e}")

            wait = 2**attempt
            time.sleep(wait)

    raise Exception(
        "Failed after multiple retries because Gemini API " "kept returning HTTP 429."
    )


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


def main():

    with open("data/top_story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    print("Generating LinkedIn draft...\n")

    draft_text = generate(story)

    draft_id = str(int(time.time()))

    os.makedirs("pending", exist_ok=True)

    record = {
        "id": draft_id,
        "story": story,
        "draft": draft_text,
        "status": "pending",
    }

    file_path = f"pending/{draft_id}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"\nDraft saved successfully:")
    print(file_path)

    github_output = os.environ.get("GITHUB_OUTPUT")

    if github_output:
        with open(github_output, "a") as f:
            f.write(f"draft_id={draft_id}\n")


if __name__ == "__main__":
    main()
