# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [Unreleased]

### Added

- 输出当前插件的信息
- 添加修改提示

### Fixed

- rc3 默认不自带 fastapi，修改为 none 驱动
- 修复插件测试中创建项目失败时，没有正确判断的问题
- 修复 Actions 排队后未能正确跳过关闭的议题的问题
- 修复拉取请求标签没有打上的问题

### Changed

- 优化运行条件，减少不必要的运行

## [1.1.0] - 2022-05-21

### Added

- 只有当文件发生变化后才强制推送
- 通过单独的测试脚本添加插件加载测试
- 评论内容无变化的时候，跳过修改

### Fixed

- 修复未同时修改议题与拉取请求标题的问题

### Changed

- 文件结尾加上换行符
- 抛弃 PyGithub 投入 githubkit 的怀抱

## [1.0.0] - 2022-05-21

### Added

- 添加检测是否重复发布

### Fixed

- 修复缺失信息时的错误匹配
- 修复当议题关闭仍然创建拉取请求的问题
- 修复解决冲突时没有重置的问题

### Changed

- 修改提交消息的格式，在最后添加上议题编号

### Removed

- 移除插件加载验证
- 移除 push 事件

## [0.5.2] - 2022-01-21

### Added

- 添加插件加载验证

### Fixed

- 拉取请求的标题少了冒号
- 处理合并冲突时，跳过未通过检查的发布

## [0.5.1] - 2022-01-06

### Added

- 添加针对 json 格式的检查

### Fixed

- 修复标签相关的报错

### Changed

- 使用自建的镜像以提升速度

## [0.5.0] - 2022-01-04

### Changed

- 利用 Python 重写 Action
- 更新至 beta1 的发布格式

## [0.4.0] - 2021-09-15

### Added

- 支持检查包是否发布到 PyPI
- 支持检查项目仓库/主页是否可以访问

## [0.3.0] - 2021-07-26

### Fixed

- 修改分支名为 publish

## [0.2.0] - 2020-11-20

### Changed

- 事件判定更严格
- 支持重开议题事件
- 检查拉取请求的标签是否为插件

### Fixed

- 拉取请求合并时报错
- 打开议题触发时，在插件信息中将仓库拥有者误设为插件作者

## [0.1.0] - 2020-11-19

### Added

- 最初的版本

[unreleased]: https://github.com/nonebot/nonebot2-publish-bot/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/nonebot/nonebot2-publish-bot/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.5.2...v1.0.0
[0.5.2]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/nonebot/nonebot2-publish-bot/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nonebot/nonebot2-publish-bot/releases/tag/v0.1.0
