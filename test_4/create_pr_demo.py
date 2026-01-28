"""
Demo script to create/update files, push to a branch, and create a Pull Request.
"""

import os
import sys
import subprocess
from datetime import datetime
from github_client import GitHubClient, GitHubClientError
from dotenv import load_dotenv

load_dotenv()


def run_git_command(command: list[str], cwd: str = None) -> tuple[bool, str]:
    """Run a git command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def update_existing_file():
    """
    Update an existing file in the repository and create a Pull Request.
    """
    print("=" * 60)
    print("  Update Existing File & Create Pull Request")
    print("=" * 60)
    
    # Configuration
    repo_path = os.getcwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"update/file-update-{timestamp}"
    base_branch = "main"
    
    # Step 1: Fetch latest and checkout base branch FIRST
    print("\n" + "-" * 40)
    print("Step 1: Fetching latest code from remote...")
    success, output = run_git_command(["git", "fetch", "origin"], repo_path)
    if not success:
        print(f"⚠️  Warning: {output}")
    else:
        print("✅ Fetched latest from origin")
    
    # Checkout to base branch to get latest files
    print(f"\nStep 2: Switching to {base_branch} branch...")
    success, output = run_git_command(["git", "checkout", base_branch], repo_path)
    if not success:
        # Try origin/main if local main doesn't exist
        success, output = run_git_command(["git", "checkout", "-b", base_branch, f"origin/{base_branch}"], repo_path)
        if not success:
            print(f"❌ Failed to checkout {base_branch}: {output}")
            return
    print(f"✅ Switched to {base_branch}")
    
    # Pull latest changes
    print(f"\nStep 3: Pulling latest changes...")
    success, output = run_git_command(["git", "pull", "origin", base_branch], repo_path)
    if not success:
        print(f"⚠️  Warning: {output}")
    else:
        print("✅ Pulled latest changes")
    
    # NOW list existing files to update (after getting latest)
    print("\n" + "-" * 40)
    print("📂 Available files in current directory:")
    print("-" * 40)
    
    files = [f for f in os.listdir(repo_path) 
             if os.path.isfile(os.path.join(repo_path, f)) 
             and not f.startswith('.')]
    
    for idx, file in enumerate(files, 1):
        print(f"  {idx}. {file}")
    
    print()
    
    # Get user input for file selection
    try:
        choice = input("Enter file number to update (or filename): ").strip()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                target_file = files[idx]
            else:
                print("❌ Invalid selection")
                return
        else:
            target_file = choice
            if not os.path.exists(os.path.join(repo_path, target_file)):
                print(f"❌ File not found: {target_file}")
                return
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return
    
    file_path = os.path.join(repo_path, target_file)
    
    print(f"\n📄 Selected file: {target_file}")
    print(f"🌿 New branch: {branch_name}")
    print(f"🎯 Target branch: {base_branch}")
    
    # Read current content
    print("\n" + "-" * 40)
    print("Current file content (first 10 lines):")
    print("-" * 40)
    
    with open(file_path, "r") as f:
        current_content = f.read()
        lines = current_content.split('\n')[:10]
        for line in lines:
            print(f"  {line}")
        if len(current_content.split('\n')) > 10:
            print("  ...")
    
    print("-" * 40)
    
    # Get update type
    print("\nUpdate options:")
    print("  1. Append content to end of file")
    print("  2. Prepend content to beginning of file")
    print("  3. Replace entire file content")
    print("  4. Add a new section/comment")
    
    try:
        update_type = input("\nSelect update type (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return
    
    # Get new content
    print("\nEnter the content to add (press Enter twice to finish):")
    new_lines = []
    try:
        while True:
            line = input()
            if line == "" and new_lines and new_lines[-1] == "":
                new_lines.pop()  # Remove the empty line
                break
            new_lines.append(line)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return
    
    new_content = '\n'.join(new_lines)
    
    if not new_content.strip():
        # Default update content if nothing entered
        new_content = f"""
# Updated on {datetime.now().isoformat()}
# This update was made by the create_pr_demo.py script
# Branch: {branch_name}
"""
    
    # Step 4: Create new branch from current (already on latest main)
    print("\n" + "-" * 40)
    print("Step 4: Creating new branch...")
    success, output = run_git_command(
        ["git", "checkout", "-b", branch_name],
        repo_path
    )
    if not success:
        print(f"❌ Failed to create branch: {output}")
        return
    print(f"✅ Created branch: {branch_name}")
    
    # Step 5: Update the file
    print("\nStep 5: Updating file...")
    
    if update_type == "1":  # Append
        updated_content = current_content + "\n" + new_content
    elif update_type == "2":  # Prepend
        updated_content = new_content + "\n" + current_content
    elif update_type == "3":  # Replace
        updated_content = new_content
    else:  # Add section (default)
        section_header = f"\n\n{'#' * 40}\n# UPDATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'#' * 40}\n"
        updated_content = current_content + section_header + new_content
    
    with open(file_path, "w") as f:
        f.write(updated_content)
    print(f"✅ Updated file: {target_file}")
    
    # Step 6: Stage
    print("\nStep 6: Staging changes...")
    success, output = run_git_command(["git", "add", target_file], repo_path)
    if not success:
        print(f"❌ Failed to stage: {output}")
        return
    print("✅ Changes staged")
    
    # Step 7: Commit
    print("\nStep 7: Committing changes...")
    commit_message = f"chore: Update {target_file}"
    success, output = run_git_command(
        ["git", "commit", "-m", commit_message],
        repo_path
    )
    if not success:
        print(f"❌ Failed to commit: {output}")
        return
    print(f"✅ Committed: {commit_message}")
    
    # Step 8: Push
    print("\nStep 8: Pushing branch...")
    success, output = run_git_command(
        ["git", "push", "-u", "origin", branch_name],
        repo_path
    )
    if not success:
        print(f"❌ Failed to push: {output}")
        return
    print(f"✅ Pushed: {branch_name}")
    
    # Step 9: Create PR
    print("\nStep 9: Creating Pull Request...")
    print("-" * 40)
    
    try:
        with GitHubClient() as client:
            pr = client.create_pull_request(
                title=f"📝 Update: {target_file}",
                head=branch_name,
                base=base_branch,
                body=f"""## 📋 Summary
This PR updates an existing file in the repository.

## 📄 File Updated
- `{target_file}`

## ✏️ Changes Made
```
{new_content[:500]}{'...' if len(new_content) > 500 else ''}
```

## 🔧 Details
- Update Type: {'Append' if update_type == '1' else 'Prepend' if update_type == '2' else 'Replace' if update_type == '3' else 'Add Section'}
- Branch: `{branch_name}`
- Timestamp: {datetime.now().isoformat()}

---
*This PR was automatically created using create_pr_demo.py*
""",
                draft=False
            )
            
            print("\n" + "=" * 60)
            print("  ✅ PULL REQUEST CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"\n  PR Number: #{pr.number}")
            print(f"  Title: {pr.title}")
            print(f"  Branch: {pr.head_branch} → {pr.base_branch}")
            print(f"\n  🔗 URL: {pr.html_url}")
            print("\n" + "=" * 60)
            
    except GitHubClientError as e:
        print(f"\n❌ Failed to create PR: {e}")
        return
    
    # Step 10: Switch back
    print("\nStep 10: Switching back to main...")
    run_git_command(["git", "checkout", "main"], repo_path)
    print("✅ Done!")


def main():
    print("=" * 60)
    print("  Create File & Pull Request Demo")
    print("=" * 60)
    
    # Configuration
    repo_path = os.getcwd()  # Current directory should be the repo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"feature/demo-{timestamp}"
    new_file_name = f"demo_file_{timestamp}.txt"
    base_branch = "main"
    
    print(f"\n📁 Repository path: {repo_path}")
    print(f"🌿 New branch: {branch_name}")
    print(f"📄 New file: {new_file_name}")
    print(f"🎯 Target branch: {base_branch}")
    
    # Step 1: Ensure we're on latest main
    print("\n" + "-" * 40)
    print("Step 1: Fetching latest from remote...")
    success, output = run_git_command(["git", "fetch", "origin"], repo_path)
    if not success:
        print(f"⚠️  Warning: {output}")
    
    # Step 2: Create and checkout new branch from main
    print("\nStep 2: Creating new branch...")
    success, output = run_git_command(
        ["git", "checkout", "-b", branch_name, f"origin/{base_branch}"],
        repo_path
    )
    if not success:
        # Try creating from current HEAD if origin/main doesn't exist
        success, output = run_git_command(
            ["git", "checkout", "-b", branch_name],
            repo_path
        )
        if not success:
            print(f"❌ Failed to create branch: {output}")
            return
    print(f"✅ Created branch: {branch_name}")
    
    # Step 3: Create a new file
    print("\nStep 3: Creating new file...")
    file_path = os.path.join(repo_path, new_file_name)
    file_content = f"""# Demo File
Created: {datetime.now().isoformat()}
Branch: {branch_name}

This file was automatically created by the create_pr_demo.py script.

## Purpose
Demonstrating the GitHub Pull Request workflow using the github_client module.

## Details
- Script: create_pr_demo.py
- Client: github_client.py
- Repository: verso_ai_poc
"""
    
    with open(file_path, "w") as f:
        f.write(file_content)
    print(f"✅ Created file: {new_file_name}")
    
    # Step 4: Stage the file
    print("\nStep 4: Staging file...")
    success, output = run_git_command(["git", "add", new_file_name], repo_path)
    if not success:
        print(f"❌ Failed to stage file: {output}")
        return
    print("✅ File staged")
    
    # Step 5: Commit
    print("\nStep 5: Committing changes...")
    commit_message = f"feat: Add demo file {new_file_name}"
    success, output = run_git_command(
        ["git", "commit", "-m", commit_message],
        repo_path
    )
    if not success:
        print(f"❌ Failed to commit: {output}")
        return
    print(f"✅ Committed: {commit_message}")
    
    # Step 6: Push branch to remote
    print("\nStep 6: Pushing branch to remote...")
    success, output = run_git_command(
        ["git", "push", "-u", "origin", branch_name],
        repo_path
    )
    if not success:
        print(f"❌ Failed to push: {output}")
        print("\n💡 Make sure you have push access to the repository.")
        return
    print(f"✅ Pushed branch: {branch_name}")
    
    # Step 7: Create Pull Request using our client
    print("\nStep 7: Creating Pull Request...")
    print("-" * 40)
    
    try:
        with GitHubClient() as client:
            pr = client.create_pull_request(
                title=f"✨ Demo: Add {new_file_name}",
                head=branch_name,
                base=base_branch,
                body=f"""## 📋 Summary
This PR adds a demo file to test the GitHub client functionality.

## 📄 Changes
- Added `{new_file_name}`

## 🔧 Created By
- Script: `create_pr_demo.py`
- Client: `github_client.py`
- Timestamp: {datetime.now().isoformat()}

---
*This PR was automatically created using the github_client module.*
""",
                draft=False
            )
            
            print("\n" + "=" * 60)
            print("  ✅ PULL REQUEST CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"\n  PR Number: #{pr.number}")
            print(f"  Title: {pr.title}")
            print(f"  Branch: {pr.head_branch} → {pr.base_branch}")
            print(f"  State: {pr.state}")
            print(f"\n  🔗 URL: {pr.html_url}")
            print("\n" + "=" * 60)
            
    except GitHubClientError as e:
        print(f"\n❌ Failed to create PR: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check GITHUB_TOKEN is valid")
        print("   2. Check GITHUB_OWNER and GITHUB_REPO are correct")
        print("   3. Ensure token has 'repo' or 'pull_requests' scope")
        return
    
    # Optional: Switch back to original branch
    print("\nStep 8: Switching back to master...")
    run_git_command(["git", "checkout", "master"], repo_path)
    print("✅ Done!")


def show_menu():
    """Display main menu and get user choice."""
    print("\n" + "=" * 60)
    print("  GitHub Pull Request Demo - Main Menu")
    print("=" * 60)
    print("\n  1. Create NEW file and Pull Request")
    print("  2. Update EXISTING file and Pull Request")
    print("  3. Exit")
    print()
    
    try:
        choice = input("Select an option (1-3): ").strip()
        return choice
    except KeyboardInterrupt:
        return "3"


if __name__ == "__main__":
    while True:
        choice = show_menu()
        
        if choice == "1":
            main()
        elif choice == "2":
            update_existing_file()
        elif choice == "3":
            print("\nGoodbye! 👋")
            break
        else:
            print("Invalid option. Please select 1, 2, or 3.")
