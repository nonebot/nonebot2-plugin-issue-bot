from pathlib import Path
from typing import TypedDict

import httpx
import nonebot
import pytest
from nonebot.adapters.github import Adapter
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.app import App
from pytest_asyncio import is_async_test
from pytest_mock import MockerFixture
from respx import MockRouter

from src.providers.constants import (
    REGISTRY_ADAPTERS_URL,
    REGISTRY_BOTS_URL,
    REGISTRY_DRIVERS_URL,
    REGISTRY_PLUGIN_CONFIG_URL,
    REGISTRY_PLUGINS_URL,
    REGISTRY_RESULTS_URL,
    STORE_ADAPTERS_URL,
    STORE_BOTS_URL,
    STORE_DRIVERS_URL,
    STORE_PLUGINS_URL,
)


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "driver": "~none",
        "input_config": {
            "base": "master",
            "adapter_path": "adapter_path",
            "bot_path": "bot_path",
            "plugin_path": "plugin_path",
            "registry_repository": "owner/registry",
            "store_repository": "owner/store",
        },
        "github_repository": "owner/repo",
        "github_run_id": "123456",
        "github_event_path": "event_path",
        "github_apps": [],
        "github_step_summary": "step_summary",
    }


def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def _after_nonebot_init(after_nonebot_init: None):
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)

    # 加载插件
    nonebot.load_plugins(str(Path(__file__).parent.parent.parent / "src" / "plugins"))


@pytest.fixture
async def app(
    app: App, tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
):
    from src.plugins.github import plugin_config
    from src.providers.utils import dump_json5

    adapter_path = tmp_path / "adapters.json5"
    dump_json5(
        adapter_path,
        [
            {
                "module_name": "module_name1",
                "project_link": "project_link1",
                "name": "name",
                "desc": "desc",
                "author_id": 1,
                "homepage": "https://v2.nonebot.dev",
                "tags": [],
                "is_official": False,
            }
        ],
    )
    bot_path = tmp_path / "bots.json5"
    dump_json5(
        bot_path,
        [
            {
                "name": "name",
                "desc": "desc",
                "author_id": 1,
                "homepage": "https://v2.nonebot.dev",
                "tags": [],
                "is_official": False,
            }
        ],
    )
    plugin_path = tmp_path / "plugins.json5"
    dump_json5(
        plugin_path,
        [
            {
                "module_name": "module_name1",
                "project_link": "project_link1",
                "author_id": 1,
                "tags": [],
                "is_official": False,
            }
        ],
    )

    mocker.patch.object(plugin_config.input_config, "adapter_path", adapter_path)
    mocker.patch.object(plugin_config.input_config, "bot_path", bot_path)
    mocker.patch.object(plugin_config.input_config, "plugin_path", plugin_path)
    mocker.patch.object(
        plugin_config, "github_step_summary", tmp_path / "step_summary.txt"
    )
    # NOTE: 由于 providers 中没有初始化 nonebot，所以不能使用插件中的配置，只能直接使用环境变量。
    # 以后需要想想办法，如果能通过 nb-cli 启动就好了。
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "step_summary.md"))

    yield app

    from src.providers.utils import get_pypi_data

    get_pypi_data.cache_clear()


@pytest.fixture(autouse=True)
def _clear_cache(app: App):
    """每次运行前都清除 cache"""
    from src.providers.validation.utils import get_url

    get_url.cache_clear()


class PyPIProject(TypedDict):
    url: str
    name: str
    version: str
    upload_time_iso_8601: str


@pytest.fixture
def mocked_api(respx_mock: MockRouter):
    # 主页数据
    respx_mock.get("https://nonebot.dev/", name="homepage").respond()
    respx_mock.get("https://www.baidu.com", name="homepage_failed").respond(404)
    respx_mock.get("exception", name="exception").mock(side_effect=httpx.ConnectError)
    # GitHub 数据
    respx_mock.get("https://api.github.com/user/1", name="github_username_1").respond(
        json={"login": "he0119"}
    )
    respx_mock.get("https://api.github.com/user/2", name="github_username_2").respond(
        json={"login": "BigOrangeQWQ"}
    )
    # PyPI 数据
    pypi_projects = [
        PyPIProject(
            url="project_link",
            name="project_link",
            version="0.0.1",
            upload_time_iso_8601="2023-09-01T00:00:00.000000Z",
        ),
        PyPIProject(
            url="project_link/",
            name="project_link/",
            version="0.0.1",
            upload_time_iso_8601="2023-10-01T00:00:00.000000Z",
        ),
        PyPIProject(
            url="nonebot-plugin-datastore",
            name="nonebot-plugin-datastore",
            version="1.3.0",
            upload_time_iso_8601="2024-06-20T07:53:23.524486Z",
        ),
        PyPIProject(
            url="nonebot-plugin-treehelp",
            name="nonebot-plugin-treehelp",
            version="0.5.0",
            upload_time_iso_8601="2024-07-13T04:41:40.905441Z",
        ),
        PyPIProject(
            url="nonebot-plugin-wordcloud",
            name="nonebot-plugin-wordcloud",
            version="0.8.0",
            upload_time_iso_8601="2024-08-15T13:06:51.084754Z",
        ),
        PyPIProject(
            url="project_link_normalization",
            name="project-link-normalization",
            version="0.0.1",
            upload_time_iso_8601="2023-10-01T00:00:00.000000Z",
        ),
        PyPIProject(
            url="nonebot2",
            name="nonebot2",
            version="2.4.0",
            upload_time_iso_8601="2024-10-31T13:47:14.152851Z",
        ),
    ]
    for project in pypi_projects:
        respx_mock.get(
            f"https://pypi.org/pypi/{project['url']}/json",
            name=f"pypi_{project['url']}",
        ).respond(
            json={
                "info": {"name": project["name"], "version": project["version"]},
                "urls": [{"upload_time_iso_8601": project["upload_time_iso_8601"]}],
            }
        )
    respx_mock.get(
        "https://pypi.org/pypi/project_link_failed/json",
        name="pypi_project_link_failed",
    ).respond(404)
    # 商店数据
    store_path = Path(__file__).parent / "store"
    respx_mock.get(STORE_ADAPTERS_URL).respond(
        text=(store_path / "store_adapters.json5").read_text(encoding="utf8")
    )
    respx_mock.get(STORE_BOTS_URL).respond(
        text=(store_path / "store_bots.json5").read_text(encoding="utf8")
    )
    respx_mock.get(STORE_DRIVERS_URL).respond(
        text=(store_path / "store_drivers.json5").read_text(encoding="utf8")
    )
    respx_mock.get(STORE_PLUGINS_URL).respond(
        text=(store_path / "store_plugins.json5").read_text(encoding="utf8")
    )
    respx_mock.get(REGISTRY_ADAPTERS_URL).respond(
        text=(store_path / "registry_adapters.json").read_text(encoding="utf8")
    )
    respx_mock.get(REGISTRY_BOTS_URL).respond(
        text=(store_path / "registry_bots.json").read_text(encoding="utf8")
    )
    respx_mock.get(REGISTRY_DRIVERS_URL).respond(
        text=(store_path / "registry_drivers.json").read_text(encoding="utf8")
    )
    respx_mock.get(REGISTRY_PLUGINS_URL).respond(
        text=(store_path / "registry_plugins.json").read_text(encoding="utf8")
    )
    respx_mock.get(REGISTRY_RESULTS_URL).respond(
        text=(store_path / "registry_results.json").read_text(encoding="utf8")
    )
    respx_mock.get(REGISTRY_PLUGIN_CONFIG_URL).respond(
        text=(store_path / "plugin_configs.json").read_text(encoding="utf8")
    )

    return respx_mock
