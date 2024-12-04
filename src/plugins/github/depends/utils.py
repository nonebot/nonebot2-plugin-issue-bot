import re

from src.plugins.github.typing import PullRequestLabels
from src.providers.validation.models import PublishType


def extract_issue_number_from_ref(ref: str) -> int | None:
    """从 Ref 中提取议题号"""
    match = re.search(r"(\w{4,10})\/issue(\d+)", ref)
    if match:
        return int(match.group(2))


def get_type_by_labels(labels: PullRequestLabels) -> PublishType | None:
    """通过拉取请求的标签获取发布类型"""
    for label in labels:
        if isinstance(label, str):
            continue
        for type in PublishType:
            if label.name == type.value:
                return type
    return None
