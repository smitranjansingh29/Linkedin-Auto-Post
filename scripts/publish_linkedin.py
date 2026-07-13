"""
Publish an approved draft to LinkedIn. Triggered by publish.yml whenever a
file lands in approved/. Moves the file to posted/ once done.
"""
import glob
import json
import os
import shutil
import urllib.request

ACCESS_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
AUTHOR_URN = os.environ["LINKEDIN_URN"]  # e.g. "urn:li:person:xxxxxxxx"
POST_URL = "https://api.linkedin.com/v2/ugcPosts"

# Set to True while waiting on LinkedIn API approval, to test the pipeline
# without actually posting.
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def publish(text):
    body = {
        "author": AUTHOR_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }
    req = urllib.request.Request(
        POST_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read()


def main():
    os.makedirs("posted", exist_ok=True)
    for path in glob.glob("approved/*.json"):
        with open(path) as f:
            record = json.load(f)

        if DRY_RUN:
            print(f"[dry run] would post:\n{record['draft']}")
        else:
            status, resp = publish(record["draft"])
            print(f"Posted draft {record['id']} -> status {status}")

        shutil.move(path, f"posted/{os.path.basename(path)}")


if __name__ == "__main__":
    main()
