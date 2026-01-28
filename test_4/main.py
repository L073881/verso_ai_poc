import os
import re
from light_client import LIGHTClient
from dotenv import load_dotenv

load_dotenv()

CORTEX_BASE = "https://api.cortex.lilly.com"

def slugify(name: str) -> str:
    s = re.sub(r'[^a-z0-9-]+', '-', name.lower())
    s = re.sub(r'-+', '-', s).strip('-')
    return s

def get_user_email() -> str:
    email = os.getenv("EMAIL", "").strip()
    if not email:
        email = input("Enter your Lilly email (UPN): ").strip()
    return email

def ensure_model(client: LIGHTClient, user_email: str, model_name: str):
    payload = {
        "name": model_name,
        "auth": {"owners": [user_email], "private": True},
        "displayName": model_name,
        "model_description": "Simple demo model",
        "chain": [
            {"chain_class": "model-only-chain", "model_iteration": 1, "order": 1, "chain_params": {}}
        ],
        "model_versions": [
            {"model_class": "lilly-openai", "model_iteration": 30, "priority": 0}
        ],
        "prompts": {"no_context": "default_no_context"}
    }
    r = client.post(f"{CORTEX_BASE}/model", json=payload)
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 409 or "already exists" in r.text.lower():
        return {"name": model_name}
    raise Exception(f"Model create failed: {r.status_code} {r.text}")

def ask_cortex(client: LIGHTClient, model_name: str, prompt: str) -> str:
    r = client.post(f"{CORTEX_BASE}/model/ask/{model_name}", data={"q": prompt})
    r.raise_for_status()
    return r.json().get("message", "")

def main():
    client = LIGHTClient()
    email = get_user_email()
    localpart = email.split("@")[0]
    model_name = slugify(f"{localpart}-simple-demo")
    ensure_model(client, email, model_name)

    print("Cortex Chat (type 'exit' to quit)")
    print("-" * 40)
    
    while True:
        query = input("\nUser query:- ").strip()
        if not query:
            continue
        if query.lower() == "exit":
            print("Goodbye!")
            break
        answer = ask_cortex(client, model_name, query)
        print(f"\nCortex: {answer}")

if __name__ == "__main__":
    main()
