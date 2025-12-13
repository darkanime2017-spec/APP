import os
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_PAT = os.getenv("GITHUB_PAT")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main") # Default to 'main' if not specified

async def upload_file_to_github(
    file_path_in_repo: str,
    file_content: bytes,
    commit_message: str,
    owner: str = GITHUB_REPO_OWNER,
    repo: str = GITHUB_REPO_NAME,
    branch: str = GITHUB_BRANCH,
    pat: str = GITHUB_PAT,
):
    """
    Uploads a file to a GitHub repository.

    Args:
        file_path_in_repo (str): The full path to the file in the repository (e.g., "submissions/user1/file.ipynb").
        file_content (bytes): The content of the file as bytes.
        commit_message (str): The commit message for the upload.
        owner (str): The owner of the repository (user or organization).
        repo (str): The name of the repository.
        branch (str): The branch to push to.
        pat (str): The GitHub Personal Access Token.

    Returns:
        dict: A dictionary containing information about the uploaded file, or None if the upload fails.
    """
    if not all([owner, repo, branch, pat]):
        print("Error: GitHub configuration missing. Ensure GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_BRANCH, and GITHUB_PAT are set in .env")
        return None

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path_in_repo}"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Check if the file already exists to get its SHA for update
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            sha = None
            if response.status_code == 200:
                sha = response.json().get("sha")
            elif response.status_code != 404: # If not 200 (found) or 404 (not found), it's an error
                print(f"Error checking file existence: {response.status_code} - {response.text}")
                return None
        except httpx.RequestError as e:
            print(f"Network error checking file existence: {e}")
            return None

        content_encoded = base64.b64encode(file_content).decode("utf-8")

        data = {
            "message": commit_message,
            "content": content_encoded,
            "branch": branch,
        }
        if sha:
            data["sha"] = sha # Include SHA for updating an existing file

        try:
            response = await client.put(url, headers=headers, json=data)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error uploading file to GitHub: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Network error uploading file to GitHub: {e}")
            return None

