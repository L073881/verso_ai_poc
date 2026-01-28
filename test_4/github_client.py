"""
GitHub Client Module

Production-ready GitHub API client for managing Pull Requests.
Supports creating and updating pull requests with comprehensive error handling.
"""

import os
import logging
from typing import Optional, List, Dict, Any
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


class GitHubClient:
    """
    Production-ready GitHub API client for Pull Request management.
    
    Usage:
        client = GitHubClient(token="ghp_xxx", owner="myorg", repo="myrepo")
        
        # Create a PR
        pr = client.create_pull_request(
            title="Feature: Add new functionality",
            head="feature-branch",
            base="main",
            body="Description of changes"
        )
        
        # Update a PR
        updated_pr = client.update_pull_request(
            pr_number=123,
            title="Updated title",
            body="Updated description"
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
        
        Raises:
            GitHubAuthError: If no token is provided or found in environment.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAuthError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable "
                "or pass token parameter."
            )
        
        self.owner = owner or os.getenv("GITHUB_OWNER")
        self.repo = repo or os.getenv("GITHUB_REPO")
        self.base_url = (base_url or os.getenv("GITHUB_API_URL") or self.GITHUB_API_BASE).rstrip("/")
        self.timeout = timeout
        
        # Configure session with retry logic
        self._session = self._create_session()
        
        logger.info(f"GitHubClient initialized for {self.owner}/{self.repo}")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry configuration."""
        session = requests.Session()
        
        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitHubClient/1.0"
        })
        
        # Configure retry strategy
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
        """
        Handle API response and raise appropriate errors.
        
        Args:
            response: The HTTP response object.
            action: Description of the action for error messages.
        
        Returns:
            Parsed JSON response.
        
        Raises:
            GitHubAuthError: For 401/403 responses.
            GitHubNotFoundError: For 404 responses.
            GitHubValidationError: For 422 responses.
            GitHubAPIError: For other error responses.
        """
        try:
            response_data = response.json() if response.content else {}
        except ValueError:
            response_data = {"message": response.text}
        
        if response.status_code in (200, 201):
            return response_data
        
        error_message = response_data.get("message", "Unknown error")
        errors = response_data.get("errors", [])
        
        if errors:
            error_details = "; ".join(
                e.get("message", str(e)) for e in errors
            )
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
                  For cross-repo PRs, use format "username:branch".
            base: The name of the branch you want the changes pulled into.
            body: PR description/body (optional).
            draft: Create as draft PR (default: False).
            maintainer_can_modify: Allow maintainers to push to head branch (default: True).
            owner: Repository owner (overrides instance default).
            repo: Repository name (overrides instance default).
        
        Returns:
            PullRequest: Created pull request object.
        
        Raises:
            GitHubValidationError: If required parameters are missing or invalid.
            GitHubAPIError: If API request fails.
        
        Example:
            pr = client.create_pull_request(
                title="Add new feature",
                head="feature/my-feature",
                base="main",
                body="## Changes\\n- Added X\\n- Fixed Y",
                draft=True
            )
            print(f"Created PR #{pr.number}: {pr.html_url}")
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
    
    def update_pull_request(
        self,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[PRState] = None,
        base: Optional[str] = None,
        maintainer_can_modify: Optional[bool] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> PullRequest:
        """
        Update an existing Pull Request.
        
        Args:
            pr_number: The PR number to update (required).
            title: New PR title (optional).
            body: New PR description/body (optional).
            state: New state - PRState.OPEN or PRState.CLOSED (optional).
            base: New base branch (optional, can only change if no commits).
            maintainer_can_modify: Allow maintainers to push (optional).
            owner: Repository owner (overrides instance default).
            repo: Repository name (overrides instance default).
        
        Returns:
            PullRequest: Updated pull request object.
        
        Raises:
            GitHubValidationError: If pr_number is invalid.
            GitHubNotFoundError: If PR doesn't exist.
            GitHubAPIError: If API request fails.
        
        Example:
            # Update title and body
            pr = client.update_pull_request(
                pr_number=123,
                title="Updated: Add new feature",
                body="Updated description with more details"
            )
            
            # Close a PR
            pr = client.update_pull_request(
                pr_number=123,
                state=PRState.CLOSED
            )
        """
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise GitHubValidationError("PR number must be a positive integer.")
        
        url = f"{self._get_repo_url(owner, repo)}/pulls/{pr_number}"
        
        payload: Dict[str, Any] = {}
        
        if title is not None:
            if not title.strip():
                raise GitHubValidationError("PR title cannot be empty.")
            payload["title"] = title.strip()
        
        if body is not None:
            payload["body"] = body
        
        if state is not None:
            payload["state"] = state.value
        
        if base is not None:
            if not base.strip():
                raise GitHubValidationError("Base branch cannot be empty.")
            payload["base"] = base.strip()
        
        if maintainer_can_modify is not None:
            payload["maintainer_can_modify"] = maintainer_can_modify
        
        if not payload:
            logger.warning(f"No updates provided for PR #{pr_number}")
            # Fetch and return current state
            return self.get_pull_request(pr_number, owner, repo)
        
        logger.info(f"Updating PR #{pr_number} with: {list(payload.keys())}")
        
        try:
            response = self._session.patch(url, json=payload, timeout=self.timeout)
            data = self._handle_response(response, f"update pull request #{pr_number}")
            pr = PullRequest.from_api_response(data)
            logger.info(f"Successfully updated PR #{pr.number}")
            return pr
        except requests.RequestException as e:
            logger.error(f"Network error updating PR #{pr_number}: {e}")
            raise GitHubAPIError(f"Network error: {e}", status_code=0, response_body="")
    
    def get_pull_request(
        self,
        pr_number: int,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> PullRequest:
        """
        Get a Pull Request by number.
        
        Args:
            pr_number: The PR number to fetch.
            owner: Repository owner (overrides instance default).
            repo: Repository name (overrides instance default).
        
        Returns:
            PullRequest: The pull request object.
        
        Raises:
            GitHubNotFoundError: If PR doesn't exist.
            GitHubAPIError: If API request fails.
        """
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise GitHubValidationError("PR number must be a positive integer.")
        
        url = f"{self._get_repo_url(owner, repo)}/pulls/{pr_number}"
        
        logger.debug(f"Fetching PR #{pr_number}")
        
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
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> List[PullRequest]:
        """
        List Pull Requests with optional filters.
        
        Args:
            state: Filter by state (default: OPEN).
            head: Filter by head branch (format: "user:branch" or "branch").
            base: Filter by base branch.
            sort: Sort by "created", "updated", "popularity", "long-running".
            direction: Sort direction - "asc" or "desc".
            per_page: Results per page (max 100).
            page: Page number.
            owner: Repository owner (overrides instance default).
            repo: Repository name (overrides instance default).
        
        Returns:
            List of PullRequest objects.
        """
        url = f"{self._get_repo_url(owner, repo)}/pulls"
        
        params: Dict[str, Any] = {
            "state": state.value,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
            "page": page
        }
        
        if head:
            params["head"] = head
        if base:
            params["base"] = base
        
        logger.debug(f"Listing PRs with params: {params}")
        
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


# Convenience functions for standalone usage
def create_pull_request(
    title: str,
    head: str,
    base: str,
    body: Optional[str] = None,
    draft: bool = False,
    token: Optional[str] = None,
    owner: Optional[str] = None,
    repo: Optional[str] = None
) -> PullRequest:
    """
    Standalone function to create a Pull Request.
    
    Args:
        title: PR title.
        head: Source branch.
        base: Target branch.
        body: PR description.
        draft: Create as draft.
        token: GitHub token (or set GITHUB_TOKEN env var).
        owner: Repo owner (or set GITHUB_OWNER env var).
        repo: Repo name (or set GITHUB_REPO env var).
    
    Returns:
        PullRequest object.
    
    Example:
        pr = create_pull_request(
            title="My PR",
            head="feature-branch",
            base="main",
            body="Description here"
        )
    """
    with GitHubClient(token=token, owner=owner, repo=repo) as client:
        return client.create_pull_request(
            title=title,
            head=head,
            base=base,
            body=body,
            draft=draft
        )


def update_pull_request(
    pr_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[PRState] = None,
    token: Optional[str] = None,
    owner: Optional[str] = None,
    repo: Optional[str] = None
) -> PullRequest:
    """
    Standalone function to update a Pull Request.
    
    Args:
        pr_number: PR number to update.
        title: New title (optional).
        body: New body (optional).
        state: New state (optional).
        token: GitHub token (or set GITHUB_TOKEN env var).
        owner: Repo owner (or set GITHUB_OWNER env var).
        repo: Repo name (or set GITHUB_REPO env var).
    
    Returns:
        Updated PullRequest object.
    
    Example:
        pr = update_pull_request(
            pr_number=123,
            title="Updated Title",
            body="New description"
        )
    """
    with GitHubClient(token=token, owner=owner, repo=repo) as client:
        return client.update_pull_request(
            pr_number=pr_number,
            title=title,
            body=body,
            state=state
        )


if __name__ == "__main__":
    # Example usage / testing
    import sys
    
    print("GitHub Client - Pull Request Management")
    print("=" * 50)
    
    # Check for required environment variables
    required_vars = ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"\nMissing environment variables: {', '.join(missing)}")
        print("\nSet these variables in your .env file:")
        print("  GITHUB_TOKEN=ghp_your_token_here")
        print("  GITHUB_OWNER=your_org_or_username")
        print("  GITHUB_REPO=your_repo_name")
        sys.exit(1)
    
    try:
        with GitHubClient() as client:
            # List open PRs
            print("\nOpen Pull Requests:")
            print("-" * 40)
            prs = client.list_pull_requests(state=PRState.OPEN, per_page=5)
            
            if not prs:
                print("No open pull requests found.")
            else:
                for pr in prs:
                    print(f"  #{pr.number}: {pr.title}")
                    print(f"    {pr.head_branch} -> {pr.base_branch}")
                    print(f"    URL: {pr.html_url}")
                    print()
            
    except GitHubClientError as e:
        print(f"\nError: {e}")
        sys.exit(1)
