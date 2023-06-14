from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase
from django.utils import timezone

from core.enums import EndpointName
from core.models import Notification, SlackInstallation
from core.resolvers import (BranchesResolver, BranchResolver,
                            CommitCoverageReport, CommitCoverageTotals,
                            CommitResolver, CommitsResolver,
                            ComparisonResolver, ComponentsResolver,
                            CoverageTrendResolver, CoverageTrendsResolver,
                            FileCoverageReport, FlagsResolver,
                            NotificationResolver, OrgsResolver, OwnerResolver,
                            PullResolver, PullsResolver, RepoConfigResolver,
                            RepoResolver, ReposResolver, UsersResolver,
                            resolve_help, resolve_service_login,
                            resolve_service_logout)
from service_auth.models import Service, SlackUser


class TestServiceAuthResolvers(TestCase):
    def setUp(self):
        installation = SlackInstallation.objects.create(
            bot_token="xoxb-1234567890",
            installed_at=timezone.now(),
        )
        self.slack_user = SlackUser.objects.create(
            installation=installation,
            username="my_slack_user",
            user_id="user_random_id",
            email="",
            codecov_access_token="12345678-1234-5678-1234-567822245672",
        )
        self.client = Mock()
        self.command = {
            "user_id": "user_random_id",
            "trigger_id": "random_trigger_id",
        }
        self.say = Mock()

    @patch("service_auth.actions.get_or_create_slack_user")
    def test_resolve_service_logout_no_active_service(
        self, mock_get_or_create_slack_user
    ):
        self.client.users_info.return_value = {
            "user": {"id": "user_random_id"}
        }

        mock_get_or_create_slack_user.return_value = self.slack_user

        resolve_service_logout(
            client=self.client, command=self.command, say=self.say
        )
        assert self.say.call_count == 1
        assert self.say.call_args[0] == (
            "You are not logged in to any service",
        )

    @patch("service_auth.actions.get_or_create_slack_user")
    def test_resolve_service_logout(self, mock_get_or_create_slack_user):
        self.client.users_info.return_value = {
            "user": {"id": "user_random_id"}
        }
        Service.objects.create(
            name="active_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )
        self.slack_user.active = True
        self.slack_user.save()

        mock_get_or_create_slack_user.return_value = self.slack_user

        resolve_service_logout(
            client=self.client, command=self.command, say=self.say
        )
        assert self.say.call_count == 1
        assert self.say.call_args[0] == (
            "Successfully logged out of active_service",
        )

    @patch("service_auth.actions.get_or_create_slack_user")
    def test_resolve_service_login(self, mock_get_or_create_slack_user):
        mock_get_or_create_slack_user.return_value = self.slack_user
        resolve_service_login(
            client=self.client, command=self.command, say=self.say
        )

        assert self.client.views_open.call_count == 1


class TestBaseResolvers(TestCase):
    def setUp(self):
        self.client = Mock()
        self.command = {"user_id": "random-userid"}
        self.say = Mock()

        self.params_dict = {
            "username": "owner1",
            "service": "gh",
            "repository": "repo1",
            "branch": "branch1",
            "pullid": "pull1",
            "commitid": "commit1",
        }
        self.optional_params = {}

        installation = SlackInstallation.objects.create(
            bot_token="xoxb-1234567890",
            installed_at=timezone.now(),
        )
        self.slack_user = SlackUser.objects.create(
            installation=installation,
            username="my_slack_user",
            user_id="random-userid",
            email="",
        )

    @patch("requests.get")
    def test_orgs_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"org1": "org1"}]},
        )

        res = OrgsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith("*Organizations you have access to*: (1)")

    @patch("requests.get")
    def test_orgs_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = OrgsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "You are not a member of any organization"

    @patch("requests.get")
    def test_orgs_resolver_status_code_is_not_200(self, mock_requests_get):
        mock_requests_get.return_value = Mock(status_code=400)

        with self.assertRaises(Exception):
            OrgsResolver(
                client=self.client, command=self.command, say=self.say
            ).resolve(self.params_dict, self.optional_params)

    @patch("requests.get")
    def test_owner_resolver(self, mock_requests_get):
        data = {
            "service": "gh",
            "username": "random-userid",
            "name": "my_slack_user",
        }
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: data
        )

        res = OwnerResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith("*Owner information for owner1*")

    @patch("requests.get")
    def test_owner_resolver_status_code_is_not_200(self, mock_requests_get):
        mock_requests_get.return_value = Mock(status_code=400)

        with self.assertRaises(Exception):
            OwnerResolver(
                client=self.client, command=self.command, say=self.say
            ).resolve(self.params_dict, self.optional_params)

    @patch("requests.get")
    def test_users_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"user1": "user1"}]},
        )

        res = UsersResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Users for owner1*: (1)\n\n*User1*: user1\n------------------\n"
        )

    @patch("requests.get")
    def test_users_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = UsersResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No users found for owner1"

    @patch("requests.get")
    def test_users_resolver_status_code_is_not_200(self, mock_requests_get):
        mock_requests_get.return_value = Mock(status_code=400)

        with self.assertRaises(Exception):
            UsersResolver(
                client=self.client, command=self.command, say=self.say
            ).resolve(self.params_dict, self.optional_params)

    @patch("requests.get")
    def test_repositories_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"repo1": "repo1"}]},
        )

        res = ReposResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Repositories for owner1*: (1)\n\n*Repo1*: repo1\n------------------\n"
        )

    @patch("requests.get")
    def test_repositories_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = ReposResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No repositories found for owner1"

    @patch("requests.get")
    def test_repositories_resolver_status_code_is_not_200(
        self, mock_requests_get
    ):
        mock_requests_get.return_value = Mock(status_code=400)

        with self.assertRaises(Exception):
            ReposResolver(
                client=self.client, command=self.command, say=self.say
            ).resolve(self.params_dict, self.optional_params)

    @patch("requests.get")
    def test_repository_resolver(self, mock_requests_get):
        data = {
            "service": "gh",
            "username": "random-userid",
            "name": "my_slack_user",
        }
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: data
        )

        res = RepoResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "*Repository repo1*\n\nService: gh\nUsername: random-userid\nName: my_slack_user\n"
        )

    @patch("requests.get")
    def test_repo_config_resolver(self, mock_requests_get):
        data = {
            "service": "gh",
            "username": "random-userid",
            "name": "my_slack_user",
        }
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: data
        )

        res = RepoConfigResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith("*Repository configuration for owner1*")

    @patch("requests.get")
    def test_branches_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"branch1": "branch1"}]},
        )

        res = BranchesResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Branches for repo1*: (1)\n\n*Branch1*: branch1\n------------------\n"
        )

    @patch("requests.get")
    def test_branches_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = BranchesResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No branches found for repo1"

    @patch("requests.get")
    def test_branch_resolver(self, mock_requests_get):
        data = {
            "service": "gh",
            "username": "random-userid",
            "name": "my_slack_user",
        }
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: data
        )

        res = BranchResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "Branch branch1 found for repo1 \n\n*Branch branch1 for repo1*\n\nService: gh\nUsername: random-userid\nName: my_slack_user\n"
        )

    @patch("requests.get")
    def test_pulls_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"pull1": "pull1"}]},
        )

        res = PullsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Pulls for repo1*: (1)\n*Pull1*: pull1\n------------------\n"
        )

    @patch("requests.get")
    def test_pulls_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = PullsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No pulls found for repo1"

    @patch("requests.get")
    def test_pull_resolver(self, mock_requests_get):
        data = {
            "service": "gh",
            "username": "random-userid",
            "name": "my_slack_user",
        }
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: data
        )

        res = PullResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith("*Pull pull1 for repo1*")

    @patch("requests.get")
    def test_commits_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"commit1": "commit1"}]},
        )

        res = CommitsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Commits for repo1*: (1)\n*Commit1*: commit1\n------------------\n"
        )

    @patch("requests.get")
    def test_commits_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = CommitsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No commits found for repo1"

    @patch("requests.get")
    def test_commit_resolver(self, mock_requests_get):
        data = {
            "service": "gh",
            "username": "random-userid",
            "name": "my_slack_user",
        }
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: data
        )

        res = CommitResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "*Commit commit1 for repo1*\n\nService: gh\nUsername: random-userid\nName: my_slack_user\n"
        )

    @patch("requests.get")
    def test_flags_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"count": 1, "results": [{"flag1": "flag1"}]},
        )

        res = FlagsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Flags for repo1*: (1)\n*Flag1*: flag1\n------------------\n"
        )

    @patch("requests.get")
    def test_flags_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = FlagsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No flags found for repo1"

    @patch("requests.get")
    def test_components_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: [{"component1": "component1"}]
        )

        res = ComponentsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Components for repo1*: (1)\nComponent1: component1\n---------------- \n"
        )

    @patch("requests.get")
    def test_components_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(status_code=200, json=lambda: [])

        res = ComponentsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No components found for repo1"

    @patch("requests.get")
    def test_coverage_trends_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "count": 1,
                "results": [{"coverage_trend1": "coverage_trend1"}],
            },
        )

        res = CoverageTrendsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Coverage trends for None*: (1)\n*Coverage_trend1*: coverage_trend1\n------------------\n"
        )

    @patch("requests.get")
    def test_coverage_trends_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = CoverageTrendsResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No coverage trends found for None"

    @patch("requests.get")
    def test_comparison_resolver_missing_pullid(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "count": 1,
                "results": [{"comparison1": "comparison1"}],
            },
        )

        with self.assertRaises(Exception) as e:
            ComparisonResolver(
                client=self.client,
                command=self.command,
                say=self.say,
                command_name=EndpointName.COMPONENT_COMPARISON,
            ).resolve(self.params_dict, self.optional_params)

        assert (
            str(e.exception)
            == "Comparison requires both a base and head parameter or a pullid parameter"
        )

    @patch("requests.get")
    def test_coverage_trend_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "count": 1,
                "results": [{"coverage_trend1": "coverage_trend1"}],
            },
        )

        res = CoverageTrendResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "*Coverage trend for repo1*: (1)\n*Coverage_trend1*: coverage_trend1\n------------------\n"
        )

    @patch("requests.get")
    def test_coverage_trend_resolver_count_is_zero(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = CoverageTrendResolver(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No coverage trend found for repo1"

    @patch("requests.get")
    def test_commit_coverage_report_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "count": 1,
                "results": [
                    {"commit_coverage_report1": "commit_coverage_report1"}
                ],
            },
        )

        res = CommitCoverageReport(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res.startswith(
            "*Coverage report for head of the default branch in repo1*:"
        )

    @patch("requests.get")
    def test_commit_coverage_report_resolver_count_is_zero(
        self, mock_requests_get
    ):
        mock_requests_get.return_value = Mock(status_code=200, json=lambda: {})

        res = CommitCoverageReport(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "No coverage report found for head of the default branch in repo1"
        )

    @patch("requests.get")
    def test_commit_coverage_totals_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "count": 1,
                "results": [
                    {"commit_coverage_totals1": "commit_coverage_totals1"}
                ],
            },
        )

        res = CommitCoverageTotals(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "*Coverage report for head of the default branch in repo1*\nCount: 1\nResults: [{'commit_coverage_totals1': 'commit_coverage_totals1'}]\n"
        )

    @patch("requests.get")
    def test_commit_coverage_totals_resolver_count_is_zero(
        self, mock_requests_get
    ):
        mock_requests_get.return_value = Mock(status_code=200, json=lambda: {})

        res = CommitCoverageTotals(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "No coverage report found for head of the default branch in repo1"
        )

    @patch("requests.get")
    def test_file_coverage_report_resolver(self, mock_requests_get):
        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "count": 1,
                "results": [
                    {"file_coverage_report1": "file_coverage_report1"}
                ],
            },
        )

        res = FileCoverageReport(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == "*Coverage report for None in repo1*: (1)\nCount: 1\nResults: [{'file_coverage_report1': 'file_coverage_report1'}]\n"
        )

    @patch("requests.get")
    def test_file_coverage_report_resolver_count_is_zero(
        self, mock_requests_get
    ):
        mock_requests_get.return_value = Mock(
            status_code=200, json=lambda: {"count": 0}
        )

        res = FileCoverageReport(
            client=self.client, command=self.command, say=self.say
        ).resolve(self.params_dict, self.optional_params)
        assert res == "No coverage report found for None in repo1"


def test_help_resolver():
    say = Mock()
    resolve_help(say=say)
    assert say.call_count == 1


class TestNotifications(TestCase):
    def setUp(self):
        installation = SlackInstallation.objects.create(
            bot_token="xoxb-1234567890",
            installed_at=timezone.now(),
        )
        self.slack_user = SlackUser.objects.create(
            installation=installation,
            username="my_slack_user",
            user_id="random_user_id",
            email="",
            codecov_access_token="12345678-1234-5678-1234-567822245672",
        )

        self.params_dict = {
            "username": "owner1",
            "service": "gh",
            "repository": "repo1",
        }
        self.optional_params = {}

        self.client = MagicMock()
        self.client.users_info.return_value = {
            "user": {"name": "John Doe", "id": "random_user_id"}
        }
        self.client.token = "random_token"

        self.command = {
            "trigger_id": "random_trigger_id",
            "channel_id": "random_channel_id",
            "user_id": "random_user_id",
        }
        self.say = Mock()

    def test_notification_already_exists(self):
        installation = SlackInstallation.objects.create(
            bot_token=self.client.token,
            installed_at=timezone.now(),
        )

        notification = Notification.objects.create(
            repo=self.params_dict["repository"],
            owner=self.params_dict["username"],
            installation=installation,
        )

        notification.channels = [self.command["channel_id"]]
        notification.save()

        res = NotificationResolver(
            command=self.command, client=self.client, say=self.say, notify=True
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == f"Notification already enabled for {self.params_dict['repository']} in this channel 👀"
        )

    def test_disable_notifications(self):
        installation = SlackInstallation.objects.create(
            bot_token=self.client.token,
            installed_at=timezone.now(),
        )

        notification = Notification.objects.create(
            repo=self.params_dict["repository"],
            owner=self.params_dict["username"],
            installation=installation,
        )

        notification.channels = [self.command["channel_id"]]
        notification.save()

        res = NotificationResolver(
            command=self.command,
            client=self.client,
            say=self.say,
            notify=False,
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == f"Notifications disabled for {self.params_dict['repository']} in this channel 📴"
        )

    def test_notification_already_not_enabled(self):
        installation = SlackInstallation.objects.create(
            bot_token=self.client.token,
            installed_at=timezone.now(),
        )

        notification = Notification.objects.create(
            repo=self.params_dict["repository"],
            owner=self.params_dict["username"],
            installation=installation,
        )

        notification.channels = []
        notification.save()

        res = NotificationResolver(
            command=self.command,
            client=self.client,
            say=self.say,
            notify=False,
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == f"Notification is not enabled for {self.params_dict['repository']} in this channel 👀"
        )

    @patch("requests.get")
    def test_notification_resolver_public_repo(self, mock_requests_get):
        Service.objects.create(
            name="active_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )

        installation = SlackInstallation.objects.create(
            bot_token=self.client.token,
            installed_at=timezone.now(),
        )

        Notification.objects.create(
            repo=self.params_dict["repository"],
            owner=self.params_dict["username"],
            installation=installation,
        )

        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"private": False},
        )

        res = NotificationResolver(
            command=self.command, client=self.client, say=self.say, notify=True
        ).resolve(self.params_dict, self.optional_params)
        assert (
            res
            == f"Notifications for {self.params_dict['repository']} enabled in this channel 📳."
        )

    @patch("requests.get")
    def test_notification_resolver_repo_not_found(self, mock_requests_get):
        Service.objects.create(
            name="active_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )

        installation = SlackInstallation.objects.create(
            bot_token=self.client.token,
            installed_at=timezone.now(),
        )

        Notification.objects.create(
            repo=self.params_dict["repository"],
            owner=self.params_dict["username"],
            installation=installation,
        )

        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {},
        )

        with self.assertRaises(Exception) as e:
            NotificationResolver(
                command=self.command,
                client=self.client,
                say=self.say,
                notify=True,
            ).resolve(self.params_dict, self.optional_params)

        assert str(e.exception) == f"Error: 404 Repo Not Found."

    @patch("requests.get")
    def test_notification_resolver_private_repo(self, mock_requests_get):
        Service.objects.create(
            name="active_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )

        installation = SlackInstallation.objects.create(
            bot_token=self.client.token,
            installed_at=timezone.now(),
        )

        Notification.objects.create(
            repo=self.params_dict["repository"],
            owner=self.params_dict["username"],
            installation=installation,
        )

        mock_requests_get.return_value = Mock(
            status_code=200,
            json=lambda: {"private": True},
        )

        res = NotificationResolver(
            command=self.command, client=self.client, say=self.say, notify=True
        ).resolve(self.params_dict, self.optional_params)

        assert self.client.views_open.call_count == 1
