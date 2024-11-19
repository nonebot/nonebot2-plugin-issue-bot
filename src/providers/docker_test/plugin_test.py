"""插件加载测试

测试代码修改自 <https://github.com/Lancercmd/nonebot2-store-test>，谢谢 [Lan 佬](https://github.com/Lancercmd)。

在 GitHub Actions 中运行，通过 GitHub Event 文件获取所需信息。并将测试结果保存至 GitHub Action 的输出文件中。

当前会输出 RESULT, OUTPUT, METADATA 三个数据，分别对应测试结果、测试输出、插件元数据。

经测试可以直接在 Python 3.10+ 环境下运行，无需额外依赖。
"""
# ruff: noqa: T201, ASYNC109

import asyncio
import json
import os
import re
from asyncio import create_subprocess_shell, subprocess
from pathlib import Path
from urllib.request import urlopen

# NoneBot Store
PLUGINS_URL = os.environ.get("PLUGINS_URL")
# 匹配信息的正则表达式
ISSUE_PATTERN = r"### {}\s+([^\s#].*?)(?=(?:\s+###|$))"

# 伪造的驱动
FAKE_SCRIPT = """from typing import Optional, Union

from nonebot import logger
from nonebot.drivers import (
    ASGIMixin,
    HTTPClientMixin,
    HTTPClientSession,
    HTTPVersion,
    Request,
    Response,
    WebSocketClientMixin,
)
from nonebot.drivers import Driver as BaseDriver
from nonebot.internal.driver.model import (
    CookieTypes,
    HeaderTypes,
    QueryTypes,
)
from typing_extensions import override


class Driver(BaseDriver, ASGIMixin, HTTPClientMixin, WebSocketClientMixin):
    @property
    @override
    def type(self) -> str:
        return "fake"

    @property
    @override
    def logger(self):
        return logger

    @override
    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)

    @property
    @override
    def server_app(self):
        return None

    @property
    @override
    def asgi(self):
        raise NotImplementedError

    @override
    def setup_http_server(self, setup):
        raise NotImplementedError

    @override
    def setup_websocket_server(self, setup):
        raise NotImplementedError

    @override
    async def request(self, setup: Request) -> Response:
        raise NotImplementedError

    @override
    async def websocket(self, setup: Request) -> Response:
        raise NotImplementedError

    @override
    def get_session(
        self,
        params: QueryTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        version: Union[str, HTTPVersion] = HTTPVersion.H11,
        timeout: Optional[float] = None,
        proxy: Optional[str] = None,
    ) -> HTTPClientSession:
        raise NotImplementedError
"""

RUNNER_SCRIPT = """import json
import os

from nonebot import init, load_plugin, logger, require
from pydantic import BaseModel


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


init()
plugin = load_plugin("{}")

if not plugin:
    exit(1)
else:
    if plugin.metadata:
        metadata = {{
            "name": plugin.metadata.name,
            "description": plugin.metadata.description,
            "usage": plugin.metadata.usage,
            "type": plugin.metadata.type,
            "homepage": plugin.metadata.homepage,
            "supported_adapters": plugin.metadata.supported_adapters,
        }}
        with open("metadata.json", "w", encoding="utf-8") as f:
            f.write(f"{{json.dumps(metadata, cls=SetEncoder)}}")

        if plugin.metadata.config and not issubclass(plugin.metadata.config, BaseModel):
            logger.error("插件配置项不是 Pydantic BaseModel 的子类")
            exit(1)

{}
"""


def strip_ansi(text: str | None) -> str:
    """去除 ANSI 转义字符"""
    if not text:
        return ""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def get_plugin_list() -> dict[str, str]:
    """获取插件列表

    通过 package_name 获取 module_name
    """
    if PLUGINS_URL is None:
        raise ValueError("PLUGINS_URL 环境变量未设置")

    with urlopen(PLUGINS_URL) as response:
        plugins = json.loads(response.read())

    return {plugin["project_link"]: plugin["module_name"] for plugin in plugins}


def extract_version(output: str, project_link: str) -> str | None:
    """提取插件版本"""
    output = strip_ansi(output)

    # 匹配 poetry show 的输出
    match = re.search(r"version\s+:\s+(\S+)", output)
    if match:
        return match.group(1).strip()

    # 匹配版本解析失败的情况
    # 目前有很多插件都把信息填错了，没有使用 - 而是使用了 _
    project_link = project_link.replace("_", "-")
    match = re.search(
        rf"depends on {project_link} \(\^(\S+)\), version solving failed\.", output
    )
    if match:
        return match.group(1).strip()


class PluginTest:
    def __init__(self, project_info: str, config: str | None = None) -> None:
        """插件测试构造函数

        Args:
            project_info (str): 项目信息，格式为 project_link:module_name
            config (str | None, optional): 插件配置. 默认为 None.
        """
        self.project_link = project_info.split(":")[0]
        self.module_name = project_info.split(":")[1]
        self.config = config
        self._version = None
        self._plugin_list = None

        self._create = False
        self._run = False
        self._deps = []

        self._lines_output = []

        # 插件测试目录
        self.test_dir = Path("plugin_test")

    @property
    def key(self) -> str:
        """插件的标识符

        project_link:module_name
        例：nonebot-plugin-test:nonebot_plugin_test
        """
        return f"{self.project_link}:{self.module_name}"

    @property
    def path(self) -> Path:
        """插件测试目录"""
        # 替换 : 为 -，防止文件名不合法
        key = self.key.replace(":", "-")
        return self.test_dir / f"{key}"

    @property
    def env(self) -> dict[str, str]:
        """获取环境变量"""
        env = os.environ.copy()
        # 删除虚拟环境变量，防止 poetry 使用运行当前脚本的虚拟环境
        env.pop("VIRTUAL_ENV", None)
        # 启用 LOGURU 的颜色输出
        env["LOGURU_COLORIZE"] = "true"
        # Poetry 配置
        # https://python-poetry.org/docs/configuration/#virtualenvsin-project
        env["POETRY_VIRTUALENVS_IN_PROJECT"] = "true"
        # https://python-poetry.org/docs/configuration/#virtualenvsprefer-active-python-experimental
        env["POETRY_VIRTUALENVS_PREFER_ACTIVE_PYTHON"] = "true"
        return env

    def _log_output(self, msg: str):
        # print(msg)
        self._lines_output.append(msg)

    async def run(self):
        """插件测试入口"""

        # 创建测试目录
        if not self.test_dir.exists():
            self.test_dir.mkdir()
            self._log_output(f"创建测试目录 {self.test_dir}")

        # 创建插件测试项目
        await self.create_poetry_project()
        if self._create:
            await asyncio.gather(
                self.show_package_info(),
                self.show_plugin_dependencies(),
            )
            await self.run_poetry_project()

        metadata = {}
        metadata_path = self.path / "metadata.json"
        if metadata_path.exists():
            with open(self.path / "metadata.json", encoding="utf-8") as f:
                metadata = json.load(f)

        # 输出测试结果
        print(
            json.dumps(
                {
                    "metadata": metadata,
                    "outputs": self._lines_output,
                    "load": self._run,
                    "run": self._create,
                    "version": self._version,
                    "config": self.config,
                }
            )
        )

        return self._run, self._lines_output

    async def command(self, cmd: str, timeout: int = 300) -> tuple[bool, str, str]:
        """执行命令

        Args:
            cmd (str): 命令
            timeout (int, optional): 超时限制. Defaults to 300.

        Returns:
            tuple[bool, str, str]: 命令执行返回值，标准输出，标准错误
        """
        proc = await create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.path,
            env=self.env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
            code = proc.returncode
        except TimeoutError:
            proc.terminate()
            stdout, stderr = b"", "执行命令超时".encode()
            code = 1

        return not code, stdout.decode(), stderr.decode()

    async def create_poetry_project(self):
        """创建 poetry 项目用来测试插件"""
        if not self.path.exists():
            self.path.mkdir()

            code, stdout, stderr = await self.command(
                f"""poetry init -n && sed -i "s/\\^/~/g" pyproject.toml && poetry env info --ansi && poetry add {self.project_link}"""
            )

            self._create = code

            if self._create:
                self._log_output(f"项目 {self.project_link} 创建成功。")
                self._std_output(stdout, "")
            else:
                self._log_output(f"项目 {self.project_link} 创建失败：")
                self._std_output(stdout, stderr)

        else:
            self._log_output(f"项目 {self.project_link} 已存在，跳过创建。")
            self._create = True

    async def show_package_info(self) -> None:
        """获取插件的版本与插件信息"""
        if self.path.exists():
            code, stdout, stderr = await self.command(
                f"poetry show {self.project_link}"
            )
            if code:
                # 获取插件版本
                self._version = extract_version(stdout, self.project_link)

                # 记录插件信息至输出
                self._log_output(f"插件 {self.project_link} 的信息如下：")
                self._std_output(stdout, "")
            else:
                self._log_output(f"插件 {self.project_link} 信息获取失败。")
                self._std_output(stdout, stderr)

    async def run_poetry_project(self) -> None:
        """运行插件"""
        if self.path.exists():
            # 默认使用 fake 驱动
            with open(self.path / ".env", "w", encoding="utf-8") as f:
                f.write("DRIVER=fake")
            # 如果提供了插件配置项，则写入配置文件
            if self.config is not None:
                with open(self.path / ".env.prod", "w", encoding="utf-8") as f:
                    f.write(self.config)

            with open(self.path / "fake.py", "w", encoding="utf-8") as f:
                f.write(FAKE_SCRIPT)

            with open(self.path / "runner.py", "w", encoding="utf-8") as f:
                f.write(
                    RUNNER_SCRIPT.format(
                        self.module_name,
                        "\n".join([f"require('{i}')" for i in self._deps]),
                    )
                )

            code, stdout, stderr = await self.command(
                "poetry run python runner.py", timeout=600
            )

            self._run = code

            if self._run:
                self._log_output(f"插件 {self.module_name} 加载正常：")
                self._std_output(stdout, "")
            else:
                self._log_output(f"插件 {self.module_name} 加载出错：")
                self._std_output(stdout, stderr)

    async def show_plugin_dependencies(self) -> None:
        """获取插件的依赖"""
        if self.path.exists():
            code, stdout, stderr = await self.command("poetry export --without-hashes")

            if code:
                self._log_output(f"插件 {self.project_link} 依赖的插件如下：")
                for i in stdout.strip().splitlines():
                    module_name = self._get_plugin_module_name(i)
                    if module_name:
                        self._deps.append(module_name)
                self._log_output(f"    {', '.join(self._deps)}")
            else:
                self._log_output(f"插件 {self.project_link} 依赖获取失败。")
                self._std_output(stdout, stderr)

    @property
    def plugin_list(self) -> dict[str, str]:
        """
        获取插件列表
        """
        if self._plugin_list is None:
            self._plugin_list = get_plugin_list()
        return self._plugin_list

    def _std_output(self, stdout: str, stderr: str):
        """
        将标准输出流与标准错误流记录并输出
        """
        _out = stdout.strip().splitlines()
        _err = stderr.strip().splitlines()
        for i in _out:
            self._log_output(f"    {i}")

        for i in _err:
            self._log_output(f"    {i}")

    def _get_plugin_module_name(self, require: str) -> str | None:
        """
        解析插件的依赖名称
        """
        # anyio==3.6.2 ; python_version >= "3.11" and python_version < "4.0"
        # pydantic[dotenv]==1.10.6 ; python_version >= "3.10" and python_version < "4.0"
        match = re.match(r"^(.+?)(?:\[.+\])?==", require.strip())
        if match:
            package_name = match.group(1)
            # 不用包括自己
            if package_name in self.plugin_list and package_name != self.project_link:
                return self.plugin_list[package_name]


def main():
    """
    根据传入的环境变量 PLUGIN_INFO 和 PLUGIN_CONFIG 进行测试

    PLUGIN_INFO 即为该插件的 KEY
    """

    plugin_info = os.environ.get("PLUGIN_INFO", "")
    plugin_config = os.environ.get("PLUGIN_CONFIG", None)
    plugin = PluginTest(plugin_info, plugin_config)

    asyncio.run(plugin.run())


if __name__ == "__main__":
    main()
