from enum import Enum


class EndpointName(Enum):
    SERVICE_OWNERS = "organizations"
    OWNER = "owner"
    USERS_LIST = "users"
    REPO_CONFIG = "repo-config"
    REPOS = "repos"
    REPO = "repo"
    BRANCHES = "branches"
    BRANCH = "branch"
    COMMITS = "commits"
    COMMIT = "commit"
    PULLS = "pulls"
    PULL = "pull"
    COMPONENTS = "components"
    FLAGS = "flags"
    COVERAGE_TREND = "coverage-trend"
