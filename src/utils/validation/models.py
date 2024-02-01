import abc
import json
from enum import Enum
from typing import TYPE_CHECKING, Any, TypedDict

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError
from pydantic_extra_types.color import Color

from .constants import (
    MAX_NAME_LENGTH,
    PLUGIN_VALID_TYPE,
    PYPI_PACKAGE_NAME_PATTERN,
    PYTHON_MODULE_NAME_REGEX,
)
from .utils import check_pypi, check_url, get_adapters, resolve_adapter_name

if TYPE_CHECKING:
    from pydantic_core import ErrorDetails


class ValidationDict(TypedDict):
    valid: bool
    type: "PublishType"
    name: str
    author: str
    data: dict[str, Any]
    errors: "list[ErrorDetails]"


class PublishType(Enum):
    """发布的类型

    值为标签名
    """

    BOT = "Bot"
    PLUGIN = "Plugin"
    ADAPTER = "Adapter"


class PyPIMixin(BaseModel):
    module_name: str
    project_link: str

    @field_validator("module_name", mode="before")
    def module_name_validator(cls, v: str) -> str:
        if not PYTHON_MODULE_NAME_REGEX.match(v):
            raise PydanticCustomError("value_error.module_name", "包名不符合规范")
        return v

    @field_validator("project_link", mode="before")
    def project_link_validator(cls, v: str) -> str:
        if not PYPI_PACKAGE_NAME_PATTERN.match(v):
            raise PydanticCustomError(
                "value_error.project_link.name", "PyPI 项目名不符合规范"
            )

        if v and not check_pypi(v):
            raise PydanticCustomError(
                "value_error.project_link.not_found", "PyPI 项目名不存在"
            )
        return v

    @model_validator(mode="before")
    def prevent_duplication(
        cls, values: dict[str, Any], info: ValidationInfo
    ) -> dict[str, Any]:
        module_name = values.get("module_name")
        project_link = values.get("project_link")

        context = info.context
        if context is None:
            raise ValueError("未获取到验证上下文")
        data = context.get("previous_data")
        if data is None:
            raise ValueError("未获取到数据列表")

        if (
            module_name
            and project_link
            and any(
                x["module_name"] == module_name and x["project_link"] == project_link
                for x in data
            )
        ):
            raise PydanticCustomError(
                "value_error.duplication",
                "PyPI 项目名 {project_link} 加包名 {module_name} 的值与商店重复",
                {"project_link": project_link, "module_name": module_name},
            )
        return values


class Tag(BaseModel):
    """标签"""

    label: str = Field(max_length=10)
    color: Color


class PublishInfo(abc.ABC, BaseModel):
    """发布信息"""

    name: str = Field(max_length=MAX_NAME_LENGTH)
    desc: str
    author: str
    homepage: str
    tags: list[Tag] = Field(max_length=3)
    is_official: bool = False

    @field_validator("*", mode="wrap")
    def collect_valid_values(
        cls, v: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ):
        context = info.context
        if context is None:
            raise ValueError("未获取到验证上下文")

        result = handler(v)
        context["valid_data"][info.field_name] = result
        return result

    @field_validator("homepage", mode="before")
    def homepage_validator(cls, v: str) -> str:
        if v:
            status_code, msg = check_url(v)
            if status_code != 200:
                raise PydanticCustomError(
                    "value_error.homepage",
                    "项目主页无法访问",
                    {"status_code": status_code, "msg": msg},
                )
        return v

    @field_validator("tags", mode="before")
    def tags_validator(cls, v: str) -> list[dict[str, str]]:
        try:
            tags: list[Any] | Any = json.loads(v)
        except json.JSONDecodeError:
            raise PydanticCustomError("value_error.json", "JSON 格式不合法")
        return tags

    @classmethod
    @abc.abstractmethod
    def get_type(cls) -> PublishType:
        """获取发布类型"""
        raise NotImplementedError


class PluginPublishInfo(PublishInfo, PyPIMixin):
    """发布插件所需信息"""

    type: str
    """插件类型"""
    supported_adapters: list[str] | None = None
    """插件支持的适配器"""

    @field_validator("type", mode="before")
    def type_validator(cls, v: str) -> str:
        if v not in PLUGIN_VALID_TYPE:
            raise PydanticCustomError("value_error.plugin.type", "插件类型不符合规范")
        return v

    @field_validator("supported_adapters", mode="before")
    def supported_adapters_validator(
        cls,
        v: str | list[str] | None,
        info: ValidationInfo,
    ) -> list[str] | None:
        context = info.context
        if context is None:
            raise ValueError("未获取到验证上下文")

        skip_plugin_test = context.get("skip_plugin_test")
        # 如果是从 issue 中获取的数据，需要先解码
        if skip_plugin_test and isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                raise PydanticCustomError("value_error.json", "JSON 格式不合法")

        # 如果是支持所有适配器，值应该是 None，不需要检查
        if v is None:
            return None

        if not isinstance(v, (list, set)):
            raise PydanticCustomError("type_error.set", "值应该是一个集合")

        supported_adapters = {resolve_adapter_name(x) for x in v}
        store_adapters = get_adapters()

        missing_adapters = supported_adapters - store_adapters
        if missing_adapters:
            raise PydanticCustomError(
                "value_error.plugin.supported_adapters.missing",
                "适配器 {missing_adapters_str} 不存在",
                {
                    "missing_adapters": list(missing_adapters),
                    "missing_adapters_str": ", ".join(missing_adapters),
                },
            )
        return sorted(supported_adapters)

    @classmethod
    def get_type(cls) -> PublishType:
        return PublishType.PLUGIN


class AdapterPublishInfo(PublishInfo, PyPIMixin):
    """发布适配器所需信息"""

    @classmethod
    def get_type(cls) -> PublishType:
        return PublishType.ADAPTER


class BotPublishInfo(PublishInfo):
    """发布机器人所需信息"""

    @classmethod
    def get_type(cls) -> PublishType:
        return PublishType.BOT
