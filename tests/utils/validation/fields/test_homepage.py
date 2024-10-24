from inline_snapshot import snapshot
from respx import MockRouter

from tests.utils.validation.utils import generate_bot_data


async def test_homepage_failed_http_exception(mocked_api: MockRouter) -> None:
    """测试验证失败的情况，HTTP 请求报错"""
    from src.providers.validation import PublishType, validate_info

    data, context = generate_bot_data(homepage="exception")

    result = validate_info(PublishType.BOT, data, context)

    assert not result.valid
    assert "homepage" not in result.data
    assert result.errors == [
        snapshot(
            {
                "type": "homepage",
                "loc": ("homepage",),
                "msg": "项目主页无法访问",
                "input": "exception",
                "ctx": {"status_code": -1, "msg": "Mock Error"},
            }
        )
    ]

    assert mocked_api["exception"].called


async def test_homepage_failed_empty_homepage(mocked_api: MockRouter) -> None:
    """主页为空字符串的情况"""
    from src.providers.validation import PublishType, validate_info

    data, context = generate_bot_data(homepage="")

    result = validate_info(PublishType.BOT, data, context)

    assert not result.valid
    assert "homepage" not in result.data
    assert result.errors == [
        snapshot(
            {
                "type": "string_pattern_mismatch",
                "loc": ("homepage",),
                "msg": "字符串应满足格式 '^https?://.*$'",
                "input": "",
                "ctx": {"pattern": "^https?://.*$"},
            }
        )
    ]

    assert not mocked_api["homepage"].called
    assert not mocked_api["homepage_failed"].called
