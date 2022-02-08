import os

GITHUB_TOKEN: str = os.environ["GITHUB_TOKEN"]
GITHUB_REPO_ID: str = os.environ["GITHUB_REPO_ID"]

GITHUB_MAIN_BRANCH: str = os.environ.get("GITHUB_MAIN_BRANCH", "main")
