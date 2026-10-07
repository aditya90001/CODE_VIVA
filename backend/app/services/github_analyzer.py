from __future__ import annotations

import base64
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# File extensions worth fetching for RAG context
_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".h",
    ".sql", ".yaml", ".yml", ".toml", ".json", ".env.example",
    ".md", ".txt",
}

# Skip large / binary / irrelevant paths
_SKIP_PREFIXES = ("node_modules/", ".git/", "dist/", "build/", "venv/", "__pycache__/", ".venv/")
_MAX_FILE_BYTES = 30_000   # skip files larger than 30 KB
_MAX_FILES = 30             # index at most 30 files to stay within token budget


class GitHubRepositoryError(ValueError):
    pass


def normalize_github_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise GitHubRepositoryError("Only public GitHub repositories are supported")

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        raise GitHubRepositoryError("Repository URL must follow the format https://github.com/owner/repo")

    owner, repo = path_parts[0], path_parts[1]
    repo = repo.replace(".git", "")
    return f"https://github.com/{owner}/{repo}"


def _should_fetch(path: str, size: int) -> bool:
    """Return True if this file should be fetched for RAG indexing."""
    if any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return False
    if size > _MAX_FILE_BYTES:
        return False
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return ext in _CODE_EXTENSIONS


async def _fetch_tree(client: httpx.AsyncClient, owner: str, repo: str, branch: str) -> list[dict]:
    """Fetch the flat file tree for the repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = await client.get(url)
    if response.status_code != 200:
        logger.warning("Could not fetch file tree: %s", response.status_code)
        return []
    data = response.json()
    return [item for item in data.get("tree", []) if item.get("type") == "blob"]


async def _fetch_file(client: httpx.AsyncClient, owner: str, repo: str, path: str) -> str:
    """Fetch decoded content of a single file via GitHub Contents API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = await client.get(url)
    if response.status_code != 200:
        return ""
    payload = response.json()
    content_b64 = payload.get("content", "")
    if not content_b64:
        return ""
    try:
        return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    except Exception:
        return ""


async def analyze_repository(repository_url: str, github_token: str | None = None) -> dict:
    normalized = normalize_github_url(repository_url)
    parsed = urlparse(normalized)
    owner, repo = [part for part in parsed.path.split("/") if part][:2]

    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # --- Basic repo metadata ---
        repo_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if repo_response.status_code == 404:
            raise GitHubRepositoryError("Repository was not found or is private")
        if repo_response.status_code >= 400:
            raise GitHubRepositoryError(f"GitHub API request failed: {repo_response.status_code}")

        repo_data = repo_response.json()
        default_branch = repo_data.get("default_branch", "main")

        # --- README ---
        readme_text = ""
        readme_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/readme")
        if readme_response.status_code == 200:
            readme_payload = readme_response.json()
            if readme_payload.get("content"):
                readme_text = base64.b64decode(readme_payload["content"]).decode("utf-8", errors="ignore")[:8000]

        # --- Code files for RAG ---
        code_files: list[dict] = []
        try:
            tree = await _fetch_tree(client, owner, repo, default_branch)
            eligible = [
                item for item in tree
                if _should_fetch(item.get("path", ""), item.get("size", 0))
            ][:_MAX_FILES]

            for item in eligible:
                path = item["path"]
                content = await _fetch_file(client, owner, repo, path)
                if content.strip():
                    code_files.append({"path": path, "content": content})
                    logger.info("RAG: fetched %s (%d chars)", path, len(content))
        except Exception as exc:
            logger.warning("analyze_repository: code file fetch failed — %s", exc)

        topics = repo_data.get("topics", [])
        return {
            "repository_url": normalized,
            "owner": owner,
            "repo": repo,
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description") or "No description provided",
            "default_branch": default_branch,
            "language": repo_data.get("language"),
            "topics": topics,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "visibility": "public" if repo_data.get("private") is False else "private",
            "readme_summary": readme_text,
            "code_files": code_files,
            "commit_hash": repo_data.get("git_commit", {}).get("sha") or default_branch or "unknown",
        }
