import dataclasses
import requests
import re
import datetime
from enum import Enum
import logging
import json
from pathlib import PurePath
import urllib.parse
import typing

import github
import github.Repository

from fairicube_catalog_backend import config

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

def _org() -> github.Organization.Organization:
    return github.Github(config.GITHUB_TOKEN).get_organization(config.GITHUB_ORGANIZATION)

def _get_headers():
    return {'Accept': 'application/json',
               'Authorization': f'token {config.GITHUB_TOKEN}'}
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

def branch_items(pulls_object):
    filename_list = []
    file_href_list = []
    repo = _repo()
    branches = repo.get_branches()
    for branch in branches:
        if branch.name != config.GITHUB_MAIN_BRANCH:
            comparison = repo.compare(config.GITHUB_MAIN_BRANCH, branch.name)
            if len(comparison.files) > 0 and comparison.files[0].filename.startswith('stac_dist'):
                filename = comparison.files[0].filename[10:]
                filename_list.append(filename)
                file_href_list.append({
                    "name": re.search(r"(?<=/)(.*)(?=.json)", filename).group(1),
                    "path": f"{config.GITHUB_REPO_ID}/{branch.name}/stac_dist/{filename}",
                    "pull": pulls_object[branch.name],
                    "assignees": pulls_object[f"{branch.name}_assignees"]
                })

    # main_items = get_items_from_catalog(config.GITHUB_MAIN_BRANCH, "catalog.json", filename_list, file_href_list)

    return(file_href_list)


def get_items_from_catalog(
        branch,
        file_name,
        branch_list,
        items_links
        ):

    catalog = requests.get(f"https://raw.githubusercontent.com/{config.GITHUB_REPO_ID}/{branch}/stac_dist/{file_name}",
                           headers=_get_headers()
                           )
    for link in catalog.json()["links"]:
        if (link["rel"] == "item" and link["href"][2:] not in branch_list):
            items_links.append({
                    "name":re.search(r"(?<=/)(.*)(?=.json)", link['href'][2:]).group(1),
                    "path": f"{config.GITHUB_REPO_ID}/{branch}/stac_dist/{link['href'][2:]}"
                })
    return items_links

def fetch_items():
    edit_list = []
    pulls = {}
    pull_list = _repo().get_pulls(
            state="open"
        )
    for pull in pull_list:
        branch_name = pull.head.ref
        html_url = pull.html_url
        pulls[branch_name] = html_url
        pulls[f"{branch_name}_assignees"] = [assignee.login for assignee in pull.assignees]

    stac_items = branch_items(pulls)
    for item in stac_items:
        edit_list.append(item)
    return edit_list


def get_members():
    org = _org()
    member_list = list()
    members = org.get_members()
    for member in members:
        member_list.append({
            "label": member.name if member.name != None else member.login,
            "value":member.login
        })
    return member_list

def get_item(body):
    stac_item = requests.get(f"https://raw.githubusercontent.com/{body['path']}", headers=_get_headers())
    stac_json = stac_item.json()
    return stac_json

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
    file_is_updated: typing.Optional[str] = None,
    labels: typing.Tuple[str, ...] = (),
    assignees: typing.Optional[list[str]] =None,
    reviewers: typing.Optional[list[str]] =None,
):
    logger.info("Creating pull request")
    logger.info(f"File to create: {file_to_create[0] if file_to_create else None}")
    logger.info(f"File to delete: {file_to_delete}")

    repo = _repo()
    assignee_list = []
    for assignee in assignees:
        if isinstance(assignees, str) == "string":
            assignee_list.append(github.Github(config.GITHUB_TOKEN).get_user(assignee))
    if file_is_updated == "edited":
        pull_list = repo.get_pulls(
            state="open"
        )
        for pull in pull_list:
            if json.loads(pr_body)["filename"] == json.loads(pull.body)["filename"]:
                branch_name = pull.head.ref
                sha = repo.get_contents(file_to_create[0], ref=branch_name).sha
                for assignee in assignee_list:
                    pull.add_to_assignees(assignee)
                pull.create_review_request(reviewers)
                break

    else:
        branch_name = _create_branch(repo, branch_base_name=branch_base_name)
        sha =_previous_version_sha(repo, path=file_to_create[0])

    if file_to_create:
        repo.update_file(
            path=file_to_create[0],
            message=f"Add {file_to_create[0]} for pull request submission",
            content=file_to_create[1],
            sha=sha,
            branch=branch_name,
        )

    if file_to_delete:
        repo.delete_file(
            path=file_to_delete,
            message=f"Delete {file_to_delete} for pull request submission",
            sha=sha,
            branch=branch_name,
        )

    if file_is_updated != "edited":
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=config.GITHUB_MAIN_BRANCH,
            maintainer_can_modify=True,
        )
        if labels:
            pr.set_labels(*labels)
        for assignee in assignee_list:
            pr.add_to_assignees(assignee)
        pr.create_review_request(reviewers)


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
