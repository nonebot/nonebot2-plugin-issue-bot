from inline_snapshot import snapshot
from nonebug import App


async def test_render(app: App):
    from src.plugins.github.plugins.remove.render import render_comment
    from src.plugins.github.plugins.remove.validation import RemoveInfo
    from src.providers.validation.models import PublishType

    result = RemoveInfo(publish_type=PublishType.BOT, key="omg", name="omg")
    assert await render_comment(result, "nonebot/nonebot2") == snapshot(
        """\
# 📃 商店下架检查

> Bot: remove omg

**✅ 所有检查通过，一切准备就绪！**

> 成功发起插件下架流程，对应的拉取请求 nonebot/nonebot2 已经创建。

---

💡 如需修改信息，请直接修改 issue，机器人会自动更新检查结果。

💪 Powered by [NoneFlow](https://github.com/nonebot/noneflow)
<!-- NONEFLOW -->
"""
    )


async def test_exception_author_info_no_eq(app: App):
    from pydantic_core import PydanticCustomError

    from src.plugins.github.plugins.remove.render import render_error

    exception = PydanticCustomError("author_info", "作者信息不匹配")

    assert await render_error(exception) == snapshot(
        """\
# 📃 商店下架检查

> Error

**⚠️ 在下架检查过程中，我们发现以下问题：**

> ⚠️ 作者信息不匹配

---

💡 如需修改信息，请直接修改 issue，机器人会自动更新检查结果。

💪 Powered by [NoneFlow](https://github.com/nonebot/noneflow)
<!-- NONEFLOW -->
"""
    )


async def test_exception_package_not_found(app: App):
    from pydantic_core import PydanticCustomError

    from src.plugins.github.plugins.remove.render import render_error

    exception = PydanticCustomError("not_found", "没有包含对应主页链接的包")

    assert await render_error(exception) == snapshot(
        """\
# 📃 商店下架检查

> Error

**⚠️ 在下架检查过程中，我们发现以下问题：**

> ⚠️ 没有包含对应主页链接的包

---

💡 如需修改信息，请直接修改 issue，机器人会自动更新检查结果。

💪 Powered by [NoneFlow](https://github.com/nonebot/noneflow)
<!-- NONEFLOW -->
"""
    )
