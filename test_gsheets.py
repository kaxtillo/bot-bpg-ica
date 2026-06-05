import os, json

# Check for any Google credentials
paths = [
    os.path.expanduser("~/.openclaw/workspace/credentials.json"),
    os.path.expanduser("~/.openclaw/workspace/service_account.json"),
    os.path.expanduser("~/.openclaw/workspace/token.json"),
    os.path.expanduser("~/.openclaw/workspace/gsheets_token.json"),
    os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
]

found = []
for p in paths:
    if os.path.exists(p):
        found.append(p)
        print(f"FOUND: {p}")
        with open(p) as f:
            try:
                data = json.load(f)
                print(f"  Keys: {list(data.keys())[:5]}")
            except:
                print(f"  (not JSON)")
        print()

if not found:
    print("No Google credentials found. Cannot use Google Sheets API.")
    print("Checking env vars for GOOGLE_APPLICATION_CREDENTIALS...")
    env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    print(f"  GOOGLE_APPLICATION_CREDENTIALS = {env}")
    if env and os.path.exists(env):
        print(f"  FOUND at env path!")
