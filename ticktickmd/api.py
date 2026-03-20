"""TickTick Open API client."""

import time
from typing import Optional

from .exceptions import APIError, AuthError


BASE_URL = "https://api.ticktick.com/open/v1"
REQUEST_DELAY = 0.1  # 100ms between requests
MAX_RETRIES = 3


class TickTickClient:
    """HTTP client for the TickTick Open API."""

    def __init__(self, access_token: str, verbose: bool = False):
        try:
            import httpx
        except ImportError:
            raise AuthError("httpx is required for API access. Install with: pip install ticktickmd[api]")

        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        self._verbose = verbose
        self._last_request_time = 0.0

    def _request(self, method: str, path: str) -> dict | list:
        """Make an API request with rate limiting and retry logic."""
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

        for attempt in range(MAX_RETRIES):
            if self._verbose:
                print(f"  API: {method} {path}")

            self._last_request_time = time.time()
            response = self._client.request(method, path)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                # Rate limited — exponential backoff
                wait = 2 ** attempt
                if self._verbose:
                    print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            if response.status_code == 401:
                raise AuthError("Access token is invalid or expired. Run 'ticktickmd auth login'.")

            raise APIError(response.status_code, response.text)

        raise APIError(429, "Rate limit exceeded after retries")

    def get_projects(self) -> list[dict]:
        """Get all projects (lists)."""
        return self._request("GET", "/project")

    def get_project_data(self, project_id: str) -> dict:
        """Get all data for a project (tasks, columns, etc.)."""
        return self._request("GET", f"/project/{project_id}/data")

    def fetch_all_tasks(
        self, project_filter: Optional[str] = None
    ) -> tuple[list[dict], dict[str, list[dict]]]:
        """Fetch all tasks, optionally filtered by project name.

        Args:
            project_filter: If set, only fetch tasks from this project

        Returns:
            Tuple of (projects, tasks_by_project_id)
        """
        projects = self.get_projects()

        if project_filter:
            # Case-insensitive match
            filter_lower = project_filter.lower()
            matched = [p for p in projects if p.get("name", "").lower() == filter_lower]
            if not matched:
                available = ", ".join(p.get("name", "?") for p in projects)
                raise APIError(
                    404,
                    f"Project '{project_filter}' not found. Available: {available}",
                )
            projects = matched

        if self._verbose:
            print(f"Fetching tasks from {len(projects)} project(s)...")

        tasks_by_project: dict[str, list[dict]] = {}
        for project in projects:
            project_id = project["id"]
            data = self.get_project_data(project_id)
            tasks = data.get("tasks", [])
            tasks_by_project[project_id] = tasks

            if self._verbose:
                print(f"  {project.get('name', '?')}: {len(tasks)} tasks")

        return projects, tasks_by_project

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
