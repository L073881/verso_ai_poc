import requests

GITHUB_TOKEN = "YOUR_TOKEN_HERE"
OWNER = "EliLillyCo"
REPO = "lusa-verso-automation"
BRANCH = "qa"

def get_github_files(path=""):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}?ref={BRANCH}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"GitHub API Error {response.status_code}: {response.text}")

    return response.json()

# Fetch root folder
files = get_github_files()

for item in files:
    print(f"{item['type'].upper()} - {item['name']} - {item['path']}")
