import shutil
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from respx import MockRouter


@pytest.fixture
def mocked_store_data(tmp_path: Path, mocker: MockerFixture) -> dict[str, Path]:
    plugin_test_path = tmp_path / "plugin_test"
    store_path = plugin_test_path / "store"

    paths = {
        "results": plugin_test_path / "results.json",
        "adapters": plugin_test_path / "adapters.json",
        "bots": plugin_test_path / "bots.json",
        "drivers": plugin_test_path / "drivers.json",
        "plugins": plugin_test_path / "plugins.json",
        "store_adapters": store_path / "adapters.json",
        "store_bots": store_path / "bots.json",
        "store_drivers": store_path / "drivers.json",
        "store_plugins": store_path / "plugins.json",
        "previous_results": store_path / "previous_results.json",
        "previous_plugins": store_path / "previous_plugins.json",
    }

    mocker.patch(
        "src.utils.store_test.store.RESULTS_PATH",
        paths["results"],
    )
    mocker.patch(
        "src.utils.store_test.store.ADAPTERS_PATH",
        paths["adapters"],
    )
    mocker.patch("src.utils.store_test.store.BOTS_PATH", paths["bots"])
    mocker.patch(
        "src.utils.store_test.store.DRIVERS_PATH",
        paths["drivers"],
    )
    mocker.patch(
        "src.utils.store_test.store.PLUGINS_PATH",
        paths["plugins"],
    )

    mocker.patch(
        "src.utils.store_test.store.STORE_ADAPTERS_PATH",
        paths["store_adapters"],
    )
    mocker.patch("src.utils.store_test.store.STORE_BOTS_PATH", paths["store_bots"])
    mocker.patch(
        "src.utils.store_test.store.STORE_DRIVERS_PATH",
        paths["store_drivers"],
    )
    mocker.patch(
        "src.utils.store_test.store.STORE_PLUGINS_PATH",
        paths["store_plugins"],
    )
    mocker.patch(
        "src.utils.store_test.store.PREVIOUS_RESULTS_PATH",
        paths["previous_results"],
    )
    mocker.patch(
        "src.utils.store_test.store.PREVIOUS_PLUGINS_PATH",
        paths["previous_plugins"],
    )

    shutil.copytree(Path(__file__).parent / "store", store_path)
    return paths


async def test_store_test(
    mocked_store_data: dict[str, Path], mocked_api: MockRouter, mocker: MockerFixture
) -> None:
    """验证插件信息

    第一个插件因为版本号无变化跳过
    第二插件验证通过
    因为 limit=1 所以只测试了一个插件，第三个插件未测试
    """
    from src.utils.store_test.store import Plugin, StoreTest, TestResult

    mocked_validate_plugin = mocker.patch("src.utils.store_test.store.validate_plugin")
    mocked_validate_plugin.return_value = (
        TestResult(
            time="2023-08-28T00:00:00.000000+08:00",
            version="1.0.0",
            inputs={"config": ""},
            results={
                "load": True,
                "metadata": True,
                "validation": True,
            },
            outputs={
                "load": "output",
                "metadata": {
                    "name": "帮助",
                    "description": "获取插件帮助信息",
                    "usage": "获取插件列表\n/help\n获取插件树\n/help -t\n/help --tree\n获取某个插件的帮助\n/help 插件名\n获取某个插件的树\n/help --tree 插件名\n",
                    "type": "application",
                    "homepage": "https://nonebot.dev/",
                    "supported_adapters": None,
                },
                "validation": None,
            },
        ),
        Plugin(
            name="帮助",
            module_name="module_name",
            author="author",
            version="0.3.0",
            desc="获取插件帮助信息",
            homepage="https://nonebot.dev/",
            project_link="project_link",
            tags=[],
            supported_adapters=None,
            type="application",
            time="2023-08-28T00:00:00.000000+08:00",
            is_official=True,
            valid=True,
            skip_test=False,
        ),
    )

    test = StoreTest(0, 1, False)
    await test.run()

    mocked_validate_plugin.assert_called_once_with(
        plugin={
            "module_name": "nonebot_plugin_treehelp",
            "project_link": "nonebot-plugin-treehelp",
            "author": "he0119",
            "tags": [],
            "is_official": False,
        },
        config="",
        skip_test=False,
        previous_plugin={
            "module_name": "nonebot_plugin_treehelp",
            "project_link": "nonebot-plugin-treehelp",
            "name": "帮助",
            "desc": "获取插件帮助信息",
            "author": "he0119",
            "homepage": "https://github.com/he0119/nonebot-plugin-treehelp",
            "tags": [],
            "is_official": False,
            "type": "application",
            "supported_adapters": None,
            "valid": True,
            "time": "2023-06-22 12:10:18",
        },
    )
    assert mocked_api["project_link_treehelp"].called
    assert mocked_api["project_link_datastore"].called

    assert (
        mocked_store_data["results"].read_text(encoding="utf8")
        == '{"nonebot-plugin-datastore:nonebot_plugin_datastore":{"time":"2023-06-26T22:08:18.945584+08:00","version":"1.0.0","results":{"validation":true,"load":true,"metadata":true},"inputs":{"config":""},"outputs":{"validation":"通过","load":"datastore","metadata":{"name":"数据存储","description":"NoneBot 数据存储插件","usage":"请参考文档","type":"library","homepage":"https://github.com/he0119/nonebot-plugin-datastore","supported_adapters":null}}},"nonebot-plugin-treehelp:nonebot_plugin_treehelp":{"time":"2023-08-28T00:00:00.000000+08:00","version":"1.0.0","inputs":{"config":""},"results":{"load":true,"metadata":true,"validation":true},"outputs":{"load":"output","metadata":{"name":"帮助","description":"获取插件帮助信息","usage":"获取插件列表\\n/help\\n获取插件树\\n/help -t\\n/help --tree\\n获取某个插件的帮助\\n/help 插件名\\n获取某个插件的树\\n/help --tree 插件名\\n","type":"application","homepage":"https://nonebot.dev/","supported_adapters":null},"validation":null}}}'
    )
    assert (
        mocked_store_data["adapters"].read_text(encoding="utf8")
        == '[{"module_name":"nonebot.adapters.onebot.v11","project_link":"nonebot-adapter-onebot","name":"OneBot V11","desc":"OneBot V11 协议","author":"yanyongyu","homepage":"https://onebot.adapters.nonebot.dev/","tags":[],"is_official":true}]'
    )
    assert (
        mocked_store_data["bots"].read_text(encoding="utf8")
        == '[{"name":"CoolQBot","desc":"基于 NoneBot2 的聊天机器人","author":"he0119","homepage":"https://github.com/he0119/CoolQBot","tags":[],"is_official":false}]'
    )
    assert (
        mocked_store_data["drivers"].read_text(encoding="utf8")
        == '[{"module_name":"~none","project_link":"","name":"None","desc":"None 驱动器","author":"yanyongyu","homepage":"/docs/advanced/driver","tags":[],"is_official":true},{"module_name":"~fastapi","project_link":"nonebot2[fastapi]","name":"FastAPI","desc":"FastAPI 驱动器","author":"yanyongyu","homepage":"/docs/advanced/driver","tags":[],"is_official":true}]'
    )
    assert (
        mocked_store_data["plugins"].read_text(encoding="utf8")
        == '[{"module_name":"nonebot_plugin_datastore","project_link":"nonebot-plugin-datastore","name":"数据存储","desc":"NoneBot 数据存储插件","author":"he0119","homepage":"https://github.com/he0119/nonebot-plugin-datastore","tags":[],"is_official":false,"type":"library","supported_adapters":null,"valid":true,"time":"2023-06-22 11:58:18"},{"name":"帮助","module_name":"module_name","author":"author","version":"0.3.0","desc":"获取插件帮助信息","homepage":"https://nonebot.dev/","project_link":"project_link","tags":[],"supported_adapters":null,"type":"application","time":"2023-08-28T00:00:00.000000+08:00","is_official":true,"valid":true,"skip_test":false}]'
    )


async def test_store_test_with_key(
    mocked_store_data: dict[str, Path], mocked_api: MockRouter, mocker: MockerFixture
) -> None:
    """测试指定插件，因为版本更新正常测试"""
    from src.utils.store_test.store import StoreTest

    mocked_validate_plugin = mocker.patch("src.utils.store_test.store.validate_plugin")
    mocked_validate_plugin.return_value = ({}, {})

    test = StoreTest(0, 1, False)
    await test.run(key="nonebot-plugin-treehelp:nonebot_plugin_treehelp")

    mocked_validate_plugin.assert_called_once_with(
        plugin={
            "module_name": "nonebot_plugin_treehelp",
            "project_link": "nonebot-plugin-treehelp",
            "author": "he0119",
            "tags": [],
            "is_official": False,
        },
        config="",
        skip_test=False,
        data=None,
        previous_plugin={
            "module_name": "nonebot_plugin_treehelp",
            "project_link": "nonebot-plugin-treehelp",
            "name": "帮助",
            "desc": "获取插件帮助信息",
            "author": "he0119",
            "homepage": "https://github.com/he0119/nonebot-plugin-treehelp",
            "tags": [],
            "is_official": False,
            "type": "application",
            "supported_adapters": None,
            "valid": True,
            "time": "2023-06-22 12:10:18",
        },
    )
    assert mocked_api["project_link_treehelp"].called
    assert not mocked_api["project_link_datastore"].called


async def test_store_test_with_key_skip(
    mocked_store_data: dict[str, Path], mocked_api: MockRouter, mocker: MockerFixture
) -> None:
    """测试指定插件，因为版本未更新跳过测试"""
    from src.utils.store_test.store import StoreTest

    mocked_validate_plugin = mocker.patch("src.utils.store_test.store.validate_plugin")

    test = StoreTest(0, 1, False)
    await test.run(key="nonebot-plugin-datastore:nonebot_plugin_datastore")

    mocked_validate_plugin.assert_not_called()
    assert not mocked_api["project_link_treehelp"].called
    assert mocked_api["project_link_datastore"].called


async def test_store_test_with_key_not_in_previous(
    mocked_store_data: dict[str, Path], mocked_api: MockRouter, mocker: MockerFixture
) -> None:
    """测试指定插件，因为从未测试过，正常测试"""
    from src.utils.store_test.store import StoreTest

    mocked_validate_plugin = mocker.patch("src.utils.store_test.store.validate_plugin")
    mocked_validate_plugin.return_value = ({}, {})

    test = StoreTest(0, 1, False)
    await test.run(key="nonebot-plugin-wordcloud:nonebot_plugin_wordcloud")

    mocked_validate_plugin.assert_called_once_with(
        plugin={
            "module_name": "nonebot_plugin_wordcloud",
            "project_link": "nonebot-plugin-wordcloud",
            "author": "he0119",
            "tags": [],
            "is_official": False,
        },
        config="",
        skip_test=False,
        data=None,
        previous_plugin=None,
    )

    # 不需要判断版本号
    assert not mocked_api["project_link_wordcloud"].called
    assert not mocked_api["project_link_treehelp"].called
    assert not mocked_api["project_link_datastore"].called
