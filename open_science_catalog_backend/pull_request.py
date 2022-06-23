import dataclasses
import datetime
from enum import Enum
import logging
import json
from pathlib import PurePath
import urllib.parse
import typing

import github
import github.Repository

from open_science_catalog_backend import config

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    add = "Add"
    update = "Update"
    delete = "Delete"


class PullRequestState(str, Enum):
    pending = "Pending"
    merged = "Merged"
    rejected = "Rejected"

    @classmethod
    def from_pull_request(cls, pr):
        if pr.state == "open":
            return cls.pending
        elif pr.merged_at is not None:
            # NOTE: the `merged` property has to be fetched from the server,
            #       so we use `merged_at`.
            return cls.merged
        else:
            return cls.rejected


def _repo() -> github.Repository.Repository:
    return github.Github(config.GITHUB_TOKEN).get_repo(config.GITHUB_REPO_ID)


@dataclasses.dataclass(frozen=True)
class PullRequestBody:
    filename: str
    item_type: str
    change_type: ChangeType
    state: PullRequestState
    url: typing.Optional[str]
    created_at: typing.Optional[datetime.datetime]
    user: str
    data_owner: bool

    def serialize(self) -> str:
        d = {
            k: v
            for k, v in dataclasses.asdict(self).items()
            if k not in ("url", "created_at", "state")
        }
        return json.dumps(d)

    @classmethod
    def deserialize(
        cls,
        data: str,
        url: str,
        state: PullRequestState,
        created_at: datetime.datetime,
    ) -> "PullRequestBody":
        try:
            return cls(
                **json.loads(data),
                url=url,
                state=state,
                created_at=created_at,
            )
        except (json.JSONDecodeError, TypeError) as e:
            raise cls.DeserializeError() from e

    class DeserializeError(Exception):
        pass


def pull_requests() -> typing.Iterable[PullRequestBody]:
    for pr in _repo().get_pulls(state="all"):
        try:
            yield PullRequestBody.deserialize(
                pr.body,
                url=pr.html_url,
                state=PullRequestState.from_pull_request(pr),
                created_at=pr.created_at,
            )
        except PullRequestBody.DeserializeError:
            # probably manually created PR
            logger.info("Found incompatible PR, ignoring..", exc_info=True)


# NOTE: this is currently unused and should be deleted
def files_in_directory(directory: str) -> typing.List[str]:
    logger.info(f"Fetching tree for {directory}")
    try:
        git_tree = _repo().get_git_tree(f"{config.GITHUB_MAIN_BRANCH}:{directory}")
    except github.UnknownObjectException:
        logger.info(f"Didn't find a git tree for {directory}")
        return []
    else:
        return [PurePath(node.path).name for node in git_tree.tree]


def create_pull_request(
    branch_base_name: str,
    pr_title: str,
    pr_body: str,
    file_to_create: typing.Optional[tuple[str, bytes]] = None,
    file_to_delete: typing.Optional[str] = None,
    labels: typing.Tuple[str, ...] = (),
):
    logger.info("Creating pull request")
    logger.info(f"File to create: {file_to_create[0] if file_to_create else None}")
    logger.info(f"File to delete: {file_to_delete}")

    repo = _repo()

    branch_name = _create_branch(repo, branch_base_name=branch_base_name)

    if file_to_create:
        repo.update_file(
            path=file_to_create[0],
            message=f"Add {file_to_create[0]} for pull request submission",
            content=file_to_create[1],
            sha=_previous_version_sha(repo, path=file_to_create[0]),
            branch=branch_name,
        )

    if file_to_delete:
        repo.delete_file(
            path=file_to_delete,
            message=f"Delete {file_to_delete} for pull request submission",
            sha=_previous_version_sha(repo, path=file_to_delete),
            branch=branch_name,
        )

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=config.GITHUB_MAIN_BRANCH,
        maintainer_can_modify=True,
    )
    if labels:
        pr.set_labels(*labels)

    logger.info("Pull request successfully created")


def _create_branch(
    repo: github.Repository.Repository,
    branch_base_name: str,
    postfix: int = 1,
) -> str:
    main_branch = repo.get_branch(config.GITHUB_MAIN_BRANCH)
    branch_name = branch_base_name + ("" if postfix == 1 else f"-{postfix}")
    logger.info(f"Creating branch with {branch_name}")
    try:
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=main_branch.commit.sha,
        )
        return branch_name
    except github.GithubException as e:
        if e.status == 422:
            # we assume that 422 unprocessable entity means branch exists

            if postfix > 15:  # safety
                raise

            return _create_branch(
                repo=repo,
                branch_base_name=branch_base_name,
                postfix=postfix + 1,
            )
        else:
            raise


def _previous_version_sha(
    repo: github.Repository.Repository,
    path: str,
) -> str:
    pure_path = PurePath(path)
    encoded_tree_ref = urllib.parse.urlencode(
        {"": f"{config.GITHUB_MAIN_BRANCH}:{pure_path.parent}"}
    )[1:]
    try:
        parent_tree = repo.get_git_tree(encoded_tree_ref, recursive=False)
    except github.UnknownObjectException:
        # parent doesn't exist, so this is a new file
        return ""

    return next(
        (
            tree_elem.sha
            for tree_elem in parent_tree.tree
            if tree_elem.path == pure_path.name
        ),
        "",  # this submission is a new file, that's fine
    )
