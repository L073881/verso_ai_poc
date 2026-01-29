"""
Verso AI - Intelligent GitHub Assistant

An intelligent assistant that can:
- Chat and answer questions
- Edit files (targeted changes like "change X to Y")
- Create new files with AI-generated content
- Automatically handle git operations and create PRs

IMPORTANT: Git operations happen in a SEPARATE 'git_workspace' folder
to avoid overwriting the agent's own code.
"""

import os
import re
import sys
import shutil
import subprocess
from light_client import LIGHTClient
from dotenv import load_dotenv

# Import our modules
from github_operations import GitWorkflow, GitHubClient, GitHubClientError, create_branch
from ai_file_assistant import (
    AIIntentParser,
    ContentGenerator,
    ActionType,
    ParsedIntent,
    create_file,
    update_file,
    edit_file,
    read_file,
    get_file_extension
)

load_dotenv()

CORTEX_BASE = "https://api.cortex.lilly.com"

# CRITICAL: Use separate workspace for git operations
# This prevents the agent from overwriting its own code when pulling
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
GIT_WORKSPACE = os.path.join(AGENT_DIR, "git_workspace")


def get_env_config() -> dict:
    """Get configuration from .env file."""
    return {
        "email": os.getenv("EMAIL", "").strip(),
        "github_token": os.getenv("GITHUB_TOKEN", "").strip(),
        "github_owner": os.getenv("GITHUB_OWNER", "").strip(),
        "github_repo": os.getenv("GITHUB_REPO", "").strip(),
        "base_branch": os.getenv("BASE_BRANCH", "dev").strip(),
    }


def setup_git_workspace(config: dict) -> str:
    """
    Setup the git workspace folder for safe git operations.
    Clones the repo if not exists, or verifies it's correct.
    Always ensures the BASE_BRANCH is checked out.
    
    Returns:
        Path to the git workspace
    """
    github_owner = config['github_owner']
    github_repo = config['github_repo']
    github_token = config['github_token']
    base_branch = config['base_branch']
    
    # Create workspace if not exists
    if not os.path.exists(GIT_WORKSPACE):
        os.makedirs(GIT_WORKSPACE)
        print(f"  📁 Created workspace: git_workspace/")
    
    repo_path = os.path.join(GIT_WORKSPACE, github_repo)
    
    # Check if repo already cloned
    if os.path.exists(os.path.join(repo_path, ".git")):
        print(f"  ✅ Repo exists: git_workspace/{github_repo}/")
        # Ensure we're on the correct base branch
        subprocess.run(
            ["git", "checkout", base_branch],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        # Pull latest changes (good practice to ensure we have fresh code)
        print(f"  📥 Pulling latest changes...")
        subprocess.run(
            ["git", "pull", "origin", base_branch],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        print(f"  🌿 On branch: {base_branch} (up to date)")
        return repo_path
    
    # Clone the repository with the specific branch
    print(f"  📥 Cloning {github_owner}/{github_repo} (branch: {base_branch})...")
    clone_url = f"https://{github_token}@github.com/{github_owner}/{github_repo}.git"
    
    try:
        result = subprocess.run(
            ["git", "clone", "-b", base_branch, clone_url, repo_path],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✅ Cloned to: git_workspace/{github_repo}/ (branch: {base_branch})")
        return repo_path
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Clone failed: {e.stderr}")
        raise RuntimeError(f"Failed to clone repository: {e.stderr}")


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
        "model_description": "Verso AI Model",
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
    raise RuntimeError(f"Model create failed: {r.status_code} {r.text}")


def ask_cortex(client: LIGHTClient, model_name: str, prompt: str) -> str:
    r = client.post(f"{CORTEX_BASE}/model/ask/{model_name}", data={"q": prompt})
    r.raise_for_status()
    return r.json().get("message", "")


def execute_edit_action(
    intent: ParsedIntent,
    existing_content: str,
    cortex_client: LIGHTClient,
    model_name: str,
    repo_path: str,
    base_branch: str = "dev"
) -> bool:
    """Execute a targeted file edit with git workflow."""
    print("\n🔄 Processing edit...")
    
    content_gen = ContentGenerator(cortex_client, model_name)
    git_workflow = GitWorkflow(repo_path, base_branch)
    
    user_query = intent.raw_query
    edit_description = intent.edit_instruction or intent.ai_summary or user_query
    
    try:
        # Step 1: Prepare repository (fetch + pull in git_workspace)
        print("  📥 Syncing with remote...")
        success, message = git_workflow.prepare_for_changes()
        if not success:
            print(f"  ❌ {message}")
            return False
        
        # Step 2: Create branch
        print("  🌿 Creating branch...")
        branch_name = content_gen.generate_branch_name("edit", intent.file_name, edit_description, user_query)
        success, actual_branch = create_branch(repo_path, branch_name)
        if not success:
            print(f"  ❌ Branch failed: {actual_branch}")
            return False
        branch_name = actual_branch  # Use actual branch name (may have suffix)
        git_workflow.feature_branch = branch_name
        
        # Step 3: Apply the edit
        print("  🤖 Applying edit...")
        try:
            new_content, change_description = content_gen.generate_smart_edit(
                existing_content,
                user_query,
                intent.file_name
            )
            print(f"  ✅ {change_description}")
        except ValueError as e:
            print(f"  ❌ {e}")
            git_workflow.cleanup()
            return False
        
        # Step 4: Save file
        success, result = edit_file(repo_path, intent.file_name, new_content)
        if not success:
            print(f"  ❌ Save failed: {result}")
            git_workflow.cleanup()
            return False
        
        # Step 5: Commit and push
        print("  📤 Pushing changes...")
        commit_msg = content_gen.generate_commit_message("edit", intent.file_name, edit_description, user_query)
        success, message = git_workflow.commit_and_push(commit_msg, [intent.file_name])
        if not success:
            print(f"  ❌ {message}")
            git_workflow.cleanup()
            return False
        
        # Step 6: Create PR
        print("  🔀 Creating PR...")
        pr_title = content_gen.generate_pr_title("edit", intent.file_name, edit_description, user_query)
        pr_body = content_gen.generate_pr_description("edit", intent.file_name, edit_description, new_content, user_query)
        
        try:
            with GitHubClient() as gh_client:
                pr = gh_client.create_pull_request(
                    title=pr_title,
                    head=branch_name,
                    base=base_branch,
                    body=pr_body,
                    draft=False
                )
                print(f"\n✅ Done! PR #{pr.number} created")
                print(f"🔗 {pr.html_url}")
        except GitHubClientError as e:
            print(f"  ❌ PR failed: {e}")
            print("  💡 Changes pushed. Create PR manually.")
            git_workflow.cleanup()
            return False
        
        git_workflow.cleanup()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        try:
            git_workflow.cleanup()
        except:
            pass
        return False


def execute_create_action(
    intent: ParsedIntent,
    cortex_client: LIGHTClient,
    model_name: str,
    repo_path: str,
    base_branch: str = "dev"
) -> bool:
    """Execute file creation with git workflow."""
    print("\n🔄 Processing...")
    
    content_gen = ContentGenerator(cortex_client, model_name)
    git_workflow = GitWorkflow(repo_path, base_branch)
    
    action_word = "create" if intent.action == ActionType.CREATE_FILE else "update"
    topic = intent.topic or intent.content_description or "General content"
    user_query = intent.raw_query
    
    try:
        # Prepare repository
        print("  📥 Syncing with remote...")
        success, message = git_workflow.prepare_for_changes()
        if not success:
            print(f"  ❌ {message}")
            return False
        
        # Create branch
        print("  🌿 Creating branch...")
        branch_name = content_gen.generate_branch_name(action_word, intent.file_name, topic, user_query)
        success, actual_branch = create_branch(repo_path, branch_name)
        if not success:
            print(f"  ❌ Branch failed: {actual_branch}")
            return False
        branch_name = actual_branch  # Use actual branch name (may have suffix)
        git_workflow.feature_branch = branch_name
        
        # Generate content
        print("  🤖 Generating content...")
        file_ext = get_file_extension(intent.file_name)
        content = content_gen.generate_file_content(
            topic=topic,
            file_type=file_ext,
            word_count=intent.word_count
        )
        
        # Create file
        if intent.action == ActionType.CREATE_FILE:
            success, result = create_file(repo_path, intent.file_name, content)
        else:
            success, result = update_file(repo_path, intent.file_name, content, intent.update_type or "append")
        
        if not success:
            print(f"  ❌ {result}")
            git_workflow.cleanup()
            return False
        print(f"  ✅ File saved: {intent.file_name}")
        
        # Commit and push
        print("  📤 Pushing changes...")
        commit_msg = content_gen.generate_commit_message(action_word, intent.file_name, topic, user_query)
        success, message = git_workflow.commit_and_push(commit_msg, [intent.file_name])
        if not success:
            print(f"  ❌ {message}")
            git_workflow.cleanup()
            return False
        
        # Create PR
        print("  🔀 Creating PR...")
        pr_title = content_gen.generate_pr_title(action_word, intent.file_name, topic, user_query)
        pr_body = content_gen.generate_pr_description(action_word, intent.file_name, topic, content, user_query)
        
        try:
            with GitHubClient() as gh_client:
                pr = gh_client.create_pull_request(
                    title=pr_title,
                    head=branch_name,
                    base=base_branch,
                    body=pr_body,
                    draft=False
                )
                print(f"\n✅ Done! PR #{pr.number} created")
                print(f"🔗 {pr.html_url}")
        except GitHubClientError as e:
            print(f"  ❌ PR failed: {e}")
            git_workflow.cleanup()
            return False
        
        git_workflow.cleanup()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        try:
            git_workflow.cleanup()
        except:
            pass
        return False


# Shared cache for repo path (used by both get_repo_path and cleanup_git_workspace)
_repo_cache: dict = {}


def cleanup_git_workspace() -> None:
    """
    Delete the git_workspace folder after operation completes.
    Also clears the cache so next operation will re-clone.
    """
    global _repo_cache
    if os.path.exists(GIT_WORKSPACE):
        try:
            shutil.rmtree(GIT_WORKSPACE)
            print("  🧹 Cleaned up workspace")
        except Exception as e:
            print(f"  ⚠️ Cleanup warning: {e}")
    # Clear the cache
    _repo_cache.clear()


def get_repo_path(config: dict) -> str:
    """
    Lazy initialization of git workspace.
    Only sets up when first GitHub operation is needed.
    Uses cache to avoid re-cloning on subsequent calls.
    """
    global _repo_cache
    if 'repo_path' not in _repo_cache:
        print("\n📂 Setting up git workspace...")
        _repo_cache['repo_path'] = setup_git_workspace(config)
    return _repo_cache['repo_path']


def main():
    """Main entry point."""
    print("\n" + "=" * 50)
    print("  🚀 Verso AI")
    print("=" * 50)
    
    config = get_env_config()
    base_branch = config['base_branch']
    
    # Initialize Cortex ONLY - NO git setup at startup
    try:
        client = LIGHTClient()
        email = config['email'] or get_user_email()
        localpart = email.split("@")[0]
        model_name = slugify(f"{localpart}-verso-ai")
        ensure_model(client, email, model_name)
        print(f"\n✅ Ready")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    parser = AIIntentParser(client, model_name)
    
    print("\nType your request or 'help' for examples.")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break
        
        if not query:
            continue
        
        if query.lower() == "exit":
            print("\nGoodbye! 👋")
            break
        
        if query.lower() == "help":
            print("""
💬 CHAT: "Who founded OpenAI?", "Explain REST APIs"
✏️ EDIT: "In readme.md, change Technical Owner to Aneesh"
📝 CREATE: "Create test.md about machine learning"
📖 READ: "Show me readme.md"
""")
            continue
        
        # Parse intent
        print("\n💭 Understanding...")
        intent = parser.parse(query)
        
        # CHAT - Answer question (NO git needed)
        if intent.action == ActionType.CHAT:
            if intent.chat_response:
                print(f"\n🤖 {intent.chat_response}")
            else:
                try:
                    answer = ask_cortex(client, model_name, query)
                    print(f"\n🤖 {answer}")
                except Exception as e:
                    print(f"\n❌ Error: {e}")
        
        # READ FILE - Setup git workspace only when needed
        elif intent.action == ActionType.READ_FILE:
            if not intent.file_name:
                print("💡 Which file? Example: readme.md")
                continue
            try:
                repo_path = get_repo_path(config)
                success, content = read_file(repo_path, intent.file_name)
                if success:
                    print(f"\n📄 {intent.file_name}:")
                    print("-" * 40)
                    lines = content.split('\n')[:30]
                    print('\n'.join(lines))
                    if len(content.split('\n')) > 30:
                        print(f"... ({len(content.split(chr(10))) - 30} more lines)")
                else:
                    print(f"\n❌ {content}")
            except RuntimeError as e:
                print(f"\n❌ {e}")
        
        # EDIT FILE - Setup git workspace only when needed
        elif intent.action == ActionType.EDIT_FILE:
            if not intent.file_name:
                print("💡 Which file to edit?")
                continue
            try:
                repo_path = get_repo_path(config)
                success, existing_content = read_file(repo_path, intent.file_name)
                if not success:
                    print(f"\n❌ Cannot read: {existing_content}")
                    cleanup_git_workspace()
                    continue
                result = execute_edit_action(intent, existing_content, client, model_name, repo_path, base_branch)
                cleanup_git_workspace()  # Clean up after operation
            except RuntimeError as e:
                print(f"\n❌ {e}")
                cleanup_git_workspace()
        
        # CREATE FILE - Setup git workspace only when needed
        elif intent.action == ActionType.CREATE_FILE:
            if not intent.file_name:
                print("💡 What filename? Example: test.md")
                continue
            try:
                repo_path = get_repo_path(config)
                execute_create_action(intent, client, model_name, repo_path, base_branch)
                cleanup_git_workspace()  # Clean up after operation
            except RuntimeError as e:
                print(f"\n❌ {e}")
                cleanup_git_workspace()
        
        # UPDATE FILE - Setup git workspace only when needed
        elif intent.action == ActionType.UPDATE_FILE:
            if not intent.file_name:
                print("💡 Which file to update?")
                continue
            try:
                repo_path = get_repo_path(config)
                execute_create_action(intent, client, model_name, repo_path, base_branch)
                cleanup_git_workspace()  # Clean up after operation
            except RuntimeError as e:
                print(f"\n❌ {e}")
                cleanup_git_workspace()
        
        # DELETE - Not supported
        elif intent.action == ActionType.DELETE_FILE:
            print("⚠️ File deletion not supported for safety.")
        
        # Unknown - fallback to chat (NO git needed)
        else:
            try:
                answer = ask_cortex(client, model_name, query)
                print(f"\n🤖 {answer}")
            except Exception as e:
                print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
