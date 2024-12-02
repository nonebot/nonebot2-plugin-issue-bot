from githubkit.rest import PullRequest, PullRequestSimple
from nonebot import logger, on_type
from nonebot.adapters.github import GitHubBot, PullRequestClosed
from nonebot.params import Depends

from src.plugins.github.depends import (
    bypass_git,
    get_installation_id,
    get_related_issue_handler,
    get_related_issue_number,
    get_type_by_labels_name,
    install_pre_commit_hooks,
)
from src.plugins.github.depends.utils import (
    is_remove_by_pull_request_labels,
)
from src.plugins.github.models import GithubHandler, IssueHandler
from src.plugins.github.plugins.publish.utils import (
    resolve_conflict_pull_requests as resolve_conflict_publish_pull_requests,
)
from src.plugins.github.plugins.remove.utils import (
    resolve_conflict_pull_requests as resolve_conflict_remove_pull_requests,
)
from src.providers.validation.models import PublishType


async def resolve_conflict_pull_requests(
    handler: GithubHandler, pull_requests: list[PullRequest] | list[PullRequestSimple]
):
    for pull_request in pull_requests:
        is_remove = is_remove_by_pull_request_labels(pull_request.labels)
        if is_remove:
            await resolve_conflict_remove_pull_requests(handler, [pull_request])
        else:
            await resolve_conflict_publish_pull_requests(handler, [pull_request])


async def pr_close_rule(
    publish_type: PublishType | None = Depends(get_type_by_labels_name),
    related_issue_number: int | None = Depends(get_related_issue_number),
) -> bool:
    if publish_type is None:
        logger.info("拉取请求与流程无关，已跳过")
        return False

    if not related_issue_number:
        logger.error("无法获取相关的议题编号")
        return False

    return True


pr_close_matcher = on_type(PullRequestClosed, rule=pr_close_rule, priority=10)


@pr_close_matcher.handle(
    parameterless=[Depends(bypass_git), Depends(install_pre_commit_hooks)]
)
async def handle_pr_close(
    event: PullRequestClosed,
    bot: GitHubBot,
    installation_id: int = Depends(get_installation_id),
    publish_type: PublishType = Depends(get_type_by_labels_name),
    handler: IssueHandler = Depends(get_related_issue_handler),
) -> None:
    async with bot.as_installation(installation_id):
        if handler.issue.state == "open":
            reason = "completed" if event.payload.pull_request.merged else "not_planned"
            await handler.close_issue(reason)
        logger.info(f"议题 #{handler.issue.number} 已关闭")

        try:
            handler.delete_origin_branch(event.payload.pull_request.head.ref)
            logger.info("已删除对应分支")
        except Exception:
            logger.info("对应分支不存在或已删除")

        if event.payload.pull_request.merged:
            logger.info("发布的拉取请求已合并，准备更新拉取请求的提交")
            pull_requests = await handler.get_pull_requests_by_label(publish_type.value)
            await resolve_conflict_pull_requests(handler, pull_requests)
        else:
            logger.info("发布的拉取请求未合并，已跳过")
