"""
Send the top story to Groq and get back a LinkedIn-ready draft.
Writes pending/<id>.json for approval.
"""

import json
import os
import time
import requests

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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

MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 5


# -------------------------------------------------------------------
# Groq API
# -------------------------------------------------------------------


def generate(story):
    prompt = f"""
Story title: {story['title']}
Source: {story['source']}
URL: {story['url']}

Write the LinkedIn post now.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
        "max_tokens": 700,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(MAX_RETRIES):

        try:
            response = requests.post(
                GROQ_URL,
                headers=headers,
                json=payload,
                timeout=(10, 120),  # connect timeout, read timeout
            )

            if response.status_code == 200:
                data = response.json()

                return data["choices"][0]["message"]["content"].strip()

            print("=" * 80)
            print(f"HTTP ERROR {response.status_code}")
            print(response.text)
            print("=" * 80)

            if response.status_code in [429, 500, 502, 503, 504]:
                wait = 2**attempt
                print(f"Retrying in {wait} seconds...")
                time.sleep(wait)
                continue

            response.raise_for_status()

        except requests.exceptions.Timeout:

            wait = 2**attempt

            print(f"Request timed out. Retrying in {wait} seconds...")

            time.sleep(wait)

        except requests.exceptions.ConnectionError:

            wait = 2**attempt

            print(f"Connection error. Retrying in {wait} seconds...")

            time.sleep(wait)

        except requests.exceptions.RequestException as e:

            wait = 2**attempt

            print(f"Request failed: {e}")
            print(f"Retrying in {wait} seconds...")

            time.sleep(wait)

    raise Exception("Groq API failed after multiple retries.")


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

    print("\nDraft saved successfully:")
    print(file_path)

    github_output = os.environ.get("GITHUB_OUTPUT")

    if github_output:
        with open(github_output, "a") as f:
            f.write(f"draft_id={draft_id}\n")


if __name__ == "__main__":
    main()
