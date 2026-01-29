"""
GitHub Operations Module

Unified module for all Git and GitHub operations:
- Git CLI operations (subprocess-based)
- GitHub API operations (HTTP-based)
- GitWorkflow class (orchestration)

Used by Verso AI for automated file operations and PR creation.
"""

import os
import subprocess
import logging
import time
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Less noise


# =============================================================================
# EXCEPTIONS
# =============================================================================

class GitError(Exception):
    """Exception raised for git operation failures."""
    def __init__(self, message: str, command: str = "", stderr: str = ""):
        super().__init__(message)
        self.command = command
        self.stderr = stderr


class GitHubClientError(Exception):
    """Base exception for GitHub client errors."""
    pass


class GitHubAuthError(GitHubClientError):
    """Authentication error."""
    pass


class GitHubAPIError(GitHubClientError):
    """API request error."""
    def __init__(self, message: str, status_code: int, response_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class GitHubNotFoundError(GitHubClientError):
    """Resource not found error."""
    pass


class GitHubValidationError(GitHubClientError):
    """Validation error for API requests."""
    pass


# =============================================================================
# DATA CLASSES & ENUMS
# =============================================================================

class PRState(Enum):
    """Pull Request state options."""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class PullRequest:
    """Data class representing a GitHub Pull Request."""
    number: int
    title: str
    body: str
    state: str
    html_url: str
    head_branch: str
    base_branch: str
    draft: bool
    mergeable: Optional[bool] = None
    merged: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "PullRequest":
        """Create PullRequest instance from GitHub API response."""
        return cls(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            state=data["state"],
            html_url=data["html_url"],
            head_branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            draft=data.get("draft", False),
            mergeable=data.get("mergeable"),
            merged=data.get("merged", False)
        )


# =============================================================================
# GIT CLI OPERATIONS
# =============================================================================

def run_git_command(command: list[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    """
    Execute a git command and return the result.
    
    Args:
        command: List of command parts (e.g., ["git", "status"])
        cwd: Working directory for the command
    
    Returns:
        Tuple of (success: bool, output: str)
    """
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
        logger.error(f"Git command failed: {' '.join(command)}")
        logger.error(f"Error: {e.stderr}")
        return False, e.stderr.strip()


def fetch_origin(repo_path: str) -> Tuple[bool, str]:
    """Fetch latest changes from origin."""
    logger.info("Fetching latest from origin...")
    success, output = run_git_command(["git", "fetch", "origin"], repo_path)
    if success:
        logger.info("✅ Fetched latest from origin")
    return success, output


def get_current_branch(repo_path: str) -> Tuple[bool, str]:
    """Get the name of the current branch."""
    return run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path)


def checkout_branch(repo_path: str, branch_name: str, create: bool = False) -> Tuple[bool, str]:
    """
    Checkout to a branch, optionally creating it.
    
    Args:
        repo_path: Path to the git repository
        branch_name: Name of the branch to checkout
        create: If True, create the branch if it doesn't exist
    """
    logger.info(f"Checking out branch: {branch_name}")
    
    if create:
        command = ["git", "checkout", "-b", branch_name]
    else:
        command = ["git", "checkout", branch_name]
    
    success, output = run_git_command(command, repo_path)
    
    if not success and not create:
        logger.info(f"Local branch not found, trying origin/{branch_name}")
        success, output = run_git_command(
            ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
            repo_path
        )
    
    if success:
        logger.info(f"✅ Checked out: {branch_name}")
    return success, output


def pull_branch(repo_path: str, branch_name: str, remote: str = "origin") -> Tuple[bool, str]:
    """Pull latest changes for a branch."""
    logger.info(f"Pulling latest changes from {remote}/{branch_name}...")
    success, output = run_git_command(
        ["git", "pull", remote, branch_name],
        repo_path
    )
    if success:
        logger.info("✅ Pulled latest changes")
    return success, output


def create_branch(repo_path: str, branch_name: str, from_branch: Optional[str] = None) -> Tuple[bool, str]:
    """
    Create a new branch. If branch already exists, appends a unique suffix.
    
    Returns:
        Tuple of (success, actual_branch_name)
    """
    original_name = branch_name
    max_attempts = 5
    
    for attempt in range(max_attempts):
        logger.info(f"Creating new branch: {branch_name}")
        
        if from_branch:
            command = ["git", "checkout", "-b", branch_name, from_branch]
        else:
            command = ["git", "checkout", "-b", branch_name]
        
        success, output = run_git_command(command, repo_path)
        
        if success:
            logger.info(f"✅ Created branch: {branch_name}")
            return success, branch_name
        
        if "already exists" in output.lower():
            timestamp = int(time.time()) % 10000
            branch_name = f"{original_name}_{timestamp}"
            logger.info(f"Branch exists, trying: {branch_name}")
            continue
        else:
            return success, output
    
    return False, f"Failed to create branch after {max_attempts} attempts"


def stage_file(repo_path: str, file_path: str) -> Tuple[bool, str]:
    """Stage a file for commit."""
    logger.info(f"Staging file: {file_path}")
    success, output = run_git_command(["git", "add", file_path], repo_path)
    if success:
        logger.info(f"✅ Staged: {file_path}")
    return success, output


def stage_all(repo_path: str) -> Tuple[bool, str]:
    """Stage all changes."""
    logger.info("Staging all changes...")
    success, output = run_git_command(["git", "add", "-A"], repo_path)
    if success:
        logger.info("✅ All changes staged")
    return success, output


def commit_changes(repo_path: str, message: str) -> Tuple[bool, str]:
    """Commit staged changes."""
    logger.info(f"Committing: {message}")
    success, output = run_git_command(
        ["git", "commit", "-m", message],
        repo_path
    )
    if success:
        logger.info("✅ Changes committed")
    return success, output


def push_branch(repo_path: str, branch_name: str, remote: str = "origin", set_upstream: bool = True) -> Tuple[bool, str]:
    """Push branch to remote."""
    logger.info(f"Pushing branch: {branch_name} to {remote}")
    
    if set_upstream:
        command = ["git", "push", "-u", remote, branch_name]
    else:
        command = ["git", "push", remote, branch_name]
    
    success, output = run_git_command(command, repo_path)
    if success:
        logger.info(f"✅ Pushed: {branch_name}")
    return success, output


def get_status(repo_path: str) -> Tuple[bool, str]:
    """Get git status."""
    return run_git_command(["git", "status", "--porcelain"], repo_path)


def has_uncommitted_changes(repo_path: str) -> bool:
    """Check if there are uncommitted changes."""
    success, output = get_status(repo_path)
    return success and bool(output.strip())


def stash_changes(repo_path: str, message: Optional[str] = None) -> Tuple[bool, str]:
    """Stash current changes."""
    logger.info("Stashing changes...")
    if message:
        command = ["git", "stash", "push", "-m", message]
    else:
        command = ["git", "stash"]
    
    success, output = run_git_command(command, repo_path)
    if success:
        logger.info("✅ Changes stashed")
    return success, output


def stash_pop(repo_path: str) -> Tuple[bool, str]:
    """Pop stashed changes."""
    logger.info("Popping stashed changes...")
    success, output = run_git_command(["git", "stash", "pop"], repo_path)
    if success:
        logger.info("✅ Stash popped")
    return success, output


# =============================================================================
# GITHUB API CLIENT
# =============================================================================

class GitHubClient:
    """
    GitHub API client for Pull Request management.
    
    Usage:
        with GitHubClient() as client:
            pr = client.create_pull_request(
                title="Feature: Add new functionality",
                head="feature-branch",
                base="main",
                body="Description of changes"
            )
    """
    
    GITHUB_API_BASE = "https://api.github.com"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    
    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token. Falls back to GITHUB_TOKEN env var.
            owner: Repository owner (organization or user).
            repo: Repository name.
            base_url: Custom GitHub API base URL (for GitHub Enterprise).
            timeout: Request timeout in seconds.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAuthError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable."
            )
        
        self.owner = owner or os.getenv("GITHUB_OWNER")
        self.repo = repo or os.getenv("GITHUB_REPO")
        self.base_url = (base_url or os.getenv("GITHUB_API_URL") or self.GITHUB_API_BASE).rstrip("/")
        self.timeout = timeout
        
        self._session = self._create_session()
        logger.info(f"GitHubClient initialized for {self.owner}/{self.repo}")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry configuration."""
        session = requests.Session()
        
        session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "VersoAI/1.0"
        })
        
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _get_repo_url(self, owner: Optional[str] = None, repo: Optional[str] = None) -> str:
        """Get repository API URL."""
        owner = owner or self.owner
        repo = repo or self.repo
        
        if not owner or not repo:
            raise GitHubValidationError("Repository owner and name are required.")
        
        return f"{self.base_url}/repos/{owner}/{repo}"
    
    def _handle_response(self, response: requests.Response, action: str) -> Dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        try:
            response_data = response.json() if response.content else {}
        except ValueError:
            response_data = {"message": response.text}
        
        if response.status_code in (200, 201):
            return response_data
        
        error_message = response_data.get("message", "Unknown error")
        errors = response_data.get("errors", [])
        
        if errors:
            error_details = "; ".join(e.get("message", str(e)) for e in errors)
            error_message = f"{error_message}: {error_details}"
        
        full_message = f"Failed to {action}: {error_message}"
        
        if response.status_code == 401:
            raise GitHubAuthError("Invalid or expired GitHub token.")
        elif response.status_code == 403:
            raise GitHubAuthError(f"Access denied. {error_message}")
        elif response.status_code == 404:
            raise GitHubNotFoundError(full_message)
        elif response.status_code == 422:
            raise GitHubValidationError(full_message)
        else:
            raise GitHubAPIError(
                full_message,
                status_code=response.status_code,
                response_body=response.text
            )
    
    def create_pull_request(
        self,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False,
        maintainer_can_modify: bool = True,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> PullRequest:
        """
        Create a new Pull Request.
        
        Args:
            title: PR title (required).
            head: The name of the branch where your changes are implemented.
            base: The name of the branch you want the changes pulled into.
            body: PR description/body (optional).
            draft: Create as draft PR (default: False).
            maintainer_can_modify: Allow maintainers to push to head branch.
            owner: Repository owner (overrides instance default).
            repo: Repository name (overrides instance default).
        
        Returns:
            PullRequest: Created pull request object.
        """
        if not title or not title.strip():
            raise GitHubValidationError("PR title is required and cannot be empty.")
        if not head or not head.strip():
            raise GitHubValidationError("Head branch is required.")
        if not base or not base.strip():
            raise GitHubValidationError("Base branch is required.")
        
        url = f"{self._get_repo_url(owner, repo)}/pulls"
        
        payload = {
            "title": title.strip(),
            "head": head.strip(),
            "base": base.strip(),
            "draft": draft,
            "maintainer_can_modify": maintainer_can_modify
        }
        
        if body:
            payload["body"] = body
        
        logger.info(f"Creating PR: '{title}' ({head} -> {base})")
        
        try:
            response = self._session.post(url, json=payload, timeout=self.timeout)
            data = self._handle_response(response, "create pull request")
            pr = PullRequest.from_api_response(data)
            logger.info(f"Successfully created PR #{pr.number}: {pr.html_url}")
            return pr
        except requests.RequestException as e:
            logger.error(f"Network error creating PR: {e}")
            raise GitHubAPIError(f"Network error: {e}", status_code=0, response_body="")
    
    def get_pull_request(
        self,
        pr_number: int,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> PullRequest:
        """Get a Pull Request by number."""
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise GitHubValidationError("PR number must be a positive integer.")
        
        url = f"{self._get_repo_url(owner, repo)}/pulls/{pr_number}"
        
        try:
            response = self._session.get(url, timeout=self.timeout)
            data = self._handle_response(response, f"get pull request #{pr_number}")
            return PullRequest.from_api_response(data)
        except requests.RequestException as e:
            logger.error(f"Network error fetching PR #{pr_number}: {e}")
            raise GitHubAPIError(f"Network error: {e}", status_code=0, response_body="")
    
    def list_pull_requests(
        self,
        state: PRState = PRState.OPEN,
        head: Optional[str] = None,
        base: Optional[str] = None,
        per_page: int = 30,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> List[PullRequest]:
        """List Pull Requests with optional filters."""
        url = f"{self._get_repo_url(owner, repo)}/pulls"
        
        params: Dict[str, Any] = {
            "state": state.value,
            "per_page": min(per_page, 100)
        }
        
        if head:
            params["head"] = head
        if base:
            params["base"] = base
        
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            data = self._handle_response(response, "list pull requests")
            return [PullRequest.from_api_response(pr) for pr in data]
        except requests.RequestException as e:
            logger.error(f"Network error listing PRs: {e}")
            raise GitHubAPIError(f"Network error: {e}", status_code=0, response_body="")
    
    def close(self):
        """Close the HTTP session."""
        self._session.close()
        logger.debug("GitHubClient session closed")
    
    def __enter__(self) -> "GitHubClient":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# =============================================================================
# GIT WORKFLOW ORCHESTRATION
# =============================================================================

class GitWorkflow:
    """
    High-level git workflow manager.
    Orchestrates multiple git operations for common workflows.
    """
    
    def __init__(self, repo_path: str, base_branch: str = "dev"):
        """
        Initialize git workflow.
        
        Args:
            repo_path: Path to the git repository
            base_branch: Base branch name (default: dev)
        """
        self.repo_path = repo_path
        self.base_branch = base_branch
        self.feature_branch = None
    
    def prepare_for_changes(self) -> Tuple[bool, str]:
        """
        Prepare repository for making changes:
        1. Fetch origin
        2. Checkout base branch
        3. Pull latest
        """
        logger.info(f"Preparing repository on {self.base_branch}...")
        
        if has_uncommitted_changes(self.repo_path):
            logger.warning("Uncommitted changes detected, stashing...")
            stash_changes(self.repo_path, "Auto-stash before workflow")
        
        success, output = fetch_origin(self.repo_path)
        if not success:
            logger.warning(f"Fetch warning: {output}")
        
        success, output = checkout_branch(self.repo_path, self.base_branch)
        if not success:
            return False, f"Failed to checkout {self.base_branch}: {output}"
        
        success, output = pull_branch(self.repo_path, self.base_branch)
        if not success:
            logger.warning(f"Pull warning: {output}")
        
        return True, f"Ready on {self.base_branch}"
    
    def commit_and_push(self, commit_message: str, files: Optional[list[str]] = None) -> Tuple[bool, str]:
        """
        Stage, commit, and push changes.
        
        Args:
            commit_message: Commit message
            files: Specific files to stage (None for all)
        """
        if not self.feature_branch:
            return False, "No feature branch created"
        
        if files:
            for f in files:
                success, output = stage_file(self.repo_path, f)
                if not success:
                    return False, f"Failed to stage {f}: {output}"
        else:
            success, output = stage_all(self.repo_path)
            if not success:
                return False, f"Failed to stage changes: {output}"
        
        success, output = commit_changes(self.repo_path, commit_message)
        if not success:
            return False, f"Failed to commit: {output}"
        
        success, output = push_branch(self.repo_path, self.feature_branch)
        if not success:
            return False, f"Failed to push: {output}"
        
        return True, f"Pushed {self.feature_branch}"
    
    def cleanup(self) -> Tuple[bool, str]:
        """Return to base branch after workflow."""
        success, output = checkout_branch(self.repo_path, self.base_branch)
        if success:
            return True, f"Returned to {self.base_branch}"
        return False, output
