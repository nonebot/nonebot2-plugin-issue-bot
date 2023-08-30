from functools import cache
from typing import TYPE_CHECKING

import httpx
from nonebot import logger
from pydantic import ValidationError
from pydantic.color import Color, float_to_255

from .constants import STORE_ADAPTERS_URL

if TYPE_CHECKING:
    from pydantic.error_wrappers import ErrorDict


def check_pypi(project_link: str) -> bool:
    """检查项目是否存在"""
    url = f"https://pypi.org/pypi/{project_link}/json"
    status_code, _ = check_url(url)
    return status_code == 200


@cache
def check_url(url: str) -> tuple[int, str]:
    """检查网址是否可以访问

    返回状态码，如果报错则返回 -1
    """
    logger.info(f"检查网址 {url}")
    try:
        r = httpx.get(url, follow_redirects=True)
        return r.status_code, ""
    except Exception as e:
        return -1, str(e)


def get_adapters() -> set[str]:
    """获取适配器列表"""
    resp = httpx.get(STORE_ADAPTERS_URL)
    adapters = resp.json()
    return {adapter["module_name"] for adapter in adapters}


def resolve_adapter_name(name: str) -> str:
    """解析适配器名称

    例如：`~onebot.v11` -> `nonebot.adapters.onebot.v11`
    """
    if name.startswith("~"):
        name = "nonebot.adapters." + name[1:]
    return name


def color_to_hex(color: Color) -> str:
    values = [float_to_255(c) for c in color._rgba[:3]]
    hex = "".join(f"{v:02x}" for v in values)
    return f"#{hex}"


def convert_errors(
    e: ValidationError, custom_messages: dict[str, str]
) -> list["ErrorDict"]:
    """翻译 Pydantic 错误信息"""
    new_errors: list["ErrorDict"] = []
    for error in e.errors():
        custom_message = custom_messages.get(error["type"])
        if custom_message:
            ctx = error.get("ctx")
            error["msg"] = custom_message.format(**ctx) if ctx else custom_message
        new_errors.append(error)
    return new_errors
