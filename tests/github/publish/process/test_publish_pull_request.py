from pathlib import Path

from inline_snapshot import snapshot
from nonebot.adapters.github import Adapter, PullRequestClosed
from nonebug import App
from pytest_mock import MockerFixture
from respx import MockRouter

from tests.github.utils import (
    MockIssue,
    MockUser,
    generate_issue_body_plugin_skip_test,
    get_github_bot,
)


async def test_process_pull_request(
    app: App, mocker: MockerFixture, mock_installation
) -> None:
    from src.plugins.github.plugins.publish import pr_close_matcher

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_sleep = mocker.patch("asyncio.sleep")
    mock_sleep.return_value = None

    mock_issue = MockIssue(
        body="### PyPI 项目名\n\nproject_link1\n\n### 插件 import 包名\n\nmodule_name1\n\n### 插件配置项\n\n```dotenv\nlog_level=DEBUG\n```"
    ).as_mock(mocker)

    mock_issues_resp = mocker.MagicMock()
    mock_issues_resp.parsed_data = mock_issue

    mock_pulls_resp = mocker.MagicMock()
    mock_pulls_resp.parsed_data = []

    mock_comment = mocker.MagicMock()
    mock_comment.body = "Bot: test"
    mock_list_comments_resp = mocker.MagicMock()
    mock_list_comments_resp.parsed_data = [mock_comment]

    async with app.test_matcher(pr_close_matcher) as ctx:
        adapter, bot = get_github_bot(ctx)
        event_path = Path(__file__).parent.parent.parent / "events" / "pr-close.json"
        event = Adapter.payload_to_event("1", "pull_request", event_path.read_bytes())
        assert isinstance(event, PullRequestClosed)
        event.payload.pull_request.merged = True

        ctx.should_call_api(
            "rest.apps.async_get_repo_installation",
            {"owner": "he0119", "repo": "action-test"},
            mock_installation,
        )
        ctx.should_call_api(
            "rest.issues.async_get",
            {"owner": "he0119", "repo": "action-test", "issue_number": 76},
            mock_issues_resp,
        )
        ctx.should_call_api(
            "rest.issues.async_update",
            {
                "owner": "he0119",
                "repo": "action-test",
                "issue_number": 76,
                "state": "closed",
                "state_reason": "completed",
            },
            True,
        )
        ctx.should_call_api(
            "rest.pulls.async_list",
            {"owner": "he0119", "repo": "action-test", "state": "open"},
            mock_pulls_resp,
        )
        ctx.should_call_api(
            "rest.issues.async_list_comments",
            {"owner": "he0119", "repo": "action-test", "issue_number": 80},
            mock_list_comments_resp,
        )
        ctx.should_call_api(
            "rest.repos.async_create_dispatch_event",
            {
                "repo": "registry",
                "owner": "owner",
                "event_type": "registry_update",
                "client_payload": {
                    "type": "Plugin",
                    "key": "project_link1:module_name1",
                    "config": "log_level=DEBUG\n",
                },
            },
            True,
        )

        ctx.receive_event(bot, event)

    # 测试 git 命令
    mock_subprocess_run.assert_has_calls(
        [
            mocker.call(
                ["git", "config", "--global", "safe.directory", "*"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "push", "origin", "--delete", "publish/issue76"],
                check=True,
                capture_output=True,
            ),
        ],  # type: ignore
        any_order=True,
    )

    # NOTE: 不知道为什么会调用两次
    # 那个 0 不知道哪里来的。
    # 在 GitHub Actions 上又只有一个了，看来是本地的环境问题。
    mock_sleep.assert_awaited_once_with(300)


async def test_process_pull_request_not_merged(
    app: App, mocker: MockerFixture, mock_installation
) -> None:
    from src.plugins.github.plugins.publish import pr_close_matcher

    event_path = Path(__file__).parent.parent.parent / "events" / "pr-close.json"

    mock_subprocess_run = mocker.patch("subprocess.run")

    mock_issue = MockIssue().as_mock(mocker)

    mock_issues_resp = mocker.MagicMock()
    mock_issues_resp.parsed_data = mock_issue

    async with app.test_matcher(pr_close_matcher) as ctx:
        adapter, bot = get_github_bot(ctx)
        event = adapter.payload_to_event("1", "pull_request", event_path.read_bytes())
        assert isinstance(event, PullRequestClosed)

        ctx.should_call_api(
            "rest.apps.async_get_repo_installation",
            {"owner": "he0119", "repo": "action-test"},
            mock_installation,
        )
        ctx.should_call_api(
            "rest.issues.async_get",
            {"owner": "he0119", "repo": "action-test", "issue_number": 76},
            mock_issues_resp,
        )
        ctx.should_call_api(
            "rest.issues.async_update",
            {
                "owner": "he0119",
                "repo": "action-test",
                "issue_number": 76,
                "state": "closed",
                "state_reason": "not_planned",
            },
            True,
        )

        ctx.receive_event(bot, event)

    # 测试 git 命令
    mock_subprocess_run.assert_has_calls(
        [
            mocker.call(
                ["git", "config", "--global", "safe.directory", "*"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "push", "origin", "--delete", "publish/issue76"],
                check=True,
                capture_output=True,
            ),
        ],  # type: ignore
        any_order=True,
    )


async def test_process_pull_request_skip_plugin_test(
    app: App, mocker: MockerFixture, mocked_api: MockRouter, mock_installation
) -> None:
    """跳过测试的插件合并时的情况"""
    from src.plugins.github.plugins.publish import pr_close_matcher

    event_path = Path(__file__).parent.parent.parent / "events" / "pr-close.json"

    mock_subprocess_run = mocker.patch("subprocess.run")
    mock_sleep = mocker.patch("asyncio.sleep")
    mock_sleep.return_value = None

    mock_issue = MockIssue(
        body=generate_issue_body_plugin_skip_test(), user=MockUser(login="user", id=1)
    ).as_mock(mocker)

    mock_issues_resp = mocker.MagicMock()
    mock_issues_resp.parsed_data = mock_issue

    mock_pulls_resp = mocker.MagicMock()
    mock_pulls_resp.parsed_data = []

    mock_comment = mocker.MagicMock()
    mock_comment.body = "/skip"
    mock_comment.author_association = "OWNER"
    mock_list_comments_resp = mocker.MagicMock()
    mock_list_comments_resp.parsed_data = [mock_comment]

    async with app.test_matcher(pr_close_matcher) as ctx:
        adapter, bot = get_github_bot(ctx)
        event = Adapter.payload_to_event("1", "pull_request", event_path.read_bytes())
        assert isinstance(event, PullRequestClosed)
        event.payload.pull_request.merged = True

        ctx.should_call_api(
            "rest.apps.async_get_repo_installation",
            {"owner": "he0119", "repo": "action-test"},
            mock_installation,
        )
        ctx.should_call_api(
            "rest.issues.async_get",
            {"owner": "he0119", "repo": "action-test", "issue_number": 76},
            mock_issues_resp,
        )
        ctx.should_call_api(
            "rest.issues.async_update",
            {
                "owner": "he0119",
                "repo": "action-test",
                "issue_number": 76,
                "state": "closed",
                "state_reason": "completed",
            },
            True,
        )
        ctx.should_call_api(
            "rest.pulls.async_list",
            {"owner": "he0119", "repo": "action-test", "state": "open"},
            mock_pulls_resp,
        )
        ctx.should_call_api(
            "rest.issues.async_list_comments",
            {"owner": "he0119", "repo": "action-test", "issue_number": 80},
            mock_list_comments_resp,
        )
        ctx.should_call_api(
            "rest.repos.async_create_dispatch_event",
            {
                "repo": "registry",
                "owner": "owner",
                "event_type": "registry_update",
                "client_payload": snapshot(
                    {
                        "type": "Plugin",
                        "key": "project_link:module_name",
                        "config": "log_level=DEBUG\n",
                        "data": '{"module_name": "module_name", "project_link": "project_link", "name": "name", "desc": "desc", "author": "user", "author_id": 1, "homepage": "https://nonebot.dev", "tags": [{"label": "test", "color": "#ffffff"}], "is_official": false, "type": "application", "supported_adapters": ["nonebot.adapters.onebot.v11"], "load": false, "metadata": {"name": "name", "desc": "desc", "homepage": "https://nonebot.dev", "type": "application", "supported_adapters": ["~onebot.v11"]}}',
                    }
                ),
            },
            True,
        )

        ctx.receive_event(bot, event)

    # 测试 git 命令
    mock_subprocess_run.assert_has_calls(
        [
            mocker.call(
                ["git", "config", "--global", "safe.directory", "*"],
                check=True,
                capture_output=True,
            ),
            mocker.call(
                ["git", "push", "origin", "--delete", "publish/issue76"],
                check=True,
                capture_output=True,
            ),
        ],  # type: ignore
        any_order=True,
    )

    mock_sleep.assert_awaited_once_with(300)


async def test_not_publish(app: App, mocker: MockerFixture) -> None:
    """测试与发布无关的拉取请求"""
    from src.plugins.github.plugins.publish import pr_close_matcher

    event_path = Path(__file__).parent.parent.parent / "events" / "pr-close.json"

    mock_subprocess_run = mocker.patch("subprocess.run")

    async with app.test_matcher(pr_close_matcher) as ctx:
        adapter, bot = get_github_bot(ctx)
        event = Adapter.payload_to_event("1", "pull_request", event_path.read_bytes())
        assert isinstance(event, PullRequestClosed)
        event.payload.pull_request.labels = []

        ctx.receive_event(bot, event)

    # 测试 git 命令
    mock_subprocess_run.assert_not_called()


async def test_extract_issue_number_from_ref_failed(
    app: App, mocker: MockerFixture
) -> None:
    """测试从分支名中提取议题号失败"""
    from src.plugins.github.plugins.publish import pr_close_matcher

    event_path = Path(__file__).parent.parent.parent / "events" / "pr-close.json"

    mock_subprocess_run = mocker.patch("subprocess.run")

    async with app.test_matcher(pr_close_matcher) as ctx:
        adapter, bot = get_github_bot(ctx)
        event = Adapter.payload_to_event("1", "pull_request", event_path.read_bytes())
        assert isinstance(event, PullRequestClosed)
        event.payload.pull_request.head.ref = "1"

        ctx.receive_event(bot, event)

    # 测试 git 命令
    mock_subprocess_run.assert_not_called()
