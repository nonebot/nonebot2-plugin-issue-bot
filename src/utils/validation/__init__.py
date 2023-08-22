""" 验证数据是否符合规范 """

from typing import Any, cast

from pydantic import validate_model

from .models import AdapterPublishInfo, BotPublishInfo, PluginPublishInfo, PublishInfo
from .models import PublishType as PublishType
from .models import Tag
from .models import ValidationDict as ValidationDict
from .utils import color_to_hex

validation_model_map = {
    PublishType.BOT: BotPublishInfo,
    PublishType.ADAPTER: AdapterPublishInfo,
    PublishType.PLUGIN: PluginPublishInfo,
}


def validate_info(
    publish_type: PublishType, raw_data: dict[str, Any]
) -> ValidationDict:
    """验证信息是否符合规范"""
    if publish_type not in validation_model_map:
        raise ValueError("⚠️ 未知的发布类型。")  # pragma: no cover

    data, _, errors = validate_model(validation_model_map[publish_type], raw_data)

    # tags 会被转成 list[Tag]，需要转成 dict
    if "tags" in data:
        tags = cast(list[Tag], data["tags"])
        data["tags"] = [
            {
                "label": tag.label,
                "color": color_to_hex(tag.color),
            }
            for tag in tags
        ]

    # 有些字段不需要返回
    data.pop("previous_data", None)

    errors_with_input = []
    if errors:
        for error in errors.errors():
            error = cast(dict[str, Any], error)
            match error["loc"]:
                case (name,) if isinstance(name, str):
                    # 可能会有字段数据缺失的情况，这种时候不设置 input
                    if name in raw_data:
                        error["input"] = raw_data[name]
                case ("tags", index) if isinstance(index, int):
                    error["input"] = PublishInfo.tags_validator(raw_data["tags"])[index]
                # 标签 list[Tag] 的情况
                case ("tags", index, field) if isinstance(index, int) and isinstance(
                    field, str
                ):
                    tags = PublishInfo.tags_validator(raw_data["tags"])
                    if field in tags[index]:
                        error["input"] = tags[index][field]
                case _:
                    continue
            errors_with_input.append(error)

    return {
        "valid": errors is None,
        "data": data,
        "errors": errors_with_input,
        # 方便插件使用的数据
        "type": publish_type,
        "name": data.get("name") or raw_data.get("name", ""),
        "author": data.get("author", ""),
    }
