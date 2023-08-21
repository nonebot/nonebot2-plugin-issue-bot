from functools import cache

import httpx
from nonebot import logger

from .constants import STORE_ADAPTERS_URL


def check_pypi(project_link: str) -> bool:
    """检查项目是否存在"""
    url = f"https://pypi.org/pypi/{project_link}/json"
    status_code = check_url(url)
    return status_code == 200


@cache
def check_url(url: str) -> int | None:
    """检查网址是否可以访问

    返回状态码，如果报错则返回 None
    """
    logger.info(f"检查网址 {url}")
    try:
        r = httpx.get(url, follow_redirects=True)
        return r.status_code
    except:
        pass


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
