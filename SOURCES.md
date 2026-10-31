# 来源与外部引用

## 项目署名

作者与维护者：[apo-so](https://github.com/apo-so)。本项目原创文档、脚本、报告母版与 GUI 离线转换内核按根目录 [MIT 许可证](LICENSE) 发布。技能目录附同一许可，便于单独安装。

制作方法与案例来自亳伯奇、观窗及相关本地 Mod 工程的整理。历史模型标签、运行成绩、截图和私有日志没有整包导入；方法说明不代表本轮游戏实测。

## 外部参考（单独署名）

| 来源 | 参考范围 | 本仓库的处理 |
|---|---|---|
| [ReikiMaple / Skills-for-CrusaderKing3-Modding](https://github.com/ReikiMaple/Skills-for-CrusaderKing3-Modding/tree/d3098dd0551adc39f067eb3ed4fb6a15a7003644) | 文件/参数检查、静态诊断的研究线索 | 保留来源链接，以本项目工作流重新组织检查方法；不附上游技能文件、Wiki镜像或接口资料包，不将本项目MIT视为上游授权 |
| [XenoAmess / ck3_eternal_recurrence](https://github.com/XenoAmess/ck3_eternal_recurrence/tree/7aab62bb869a054175c699d0544f45cc2fabbdcb) | 原生桥接入思路、能力发现与动作后读回 | 只总结接入与验证方法，不附上游源码、DLL、注入器或服务器；上游版本的 [GPL-3.0许可证](https://github.com/XenoAmess/ck3_eternal_recurrence/blob/7aab62bb869a054175c699d0544f45cc2fabbdcb/LICENSE) 独立适用 |
| [Paradox Interactive / Crusader Kings III](https://www.paradoxinteractive.com/games/crusader-kings-iii/about) | 游戏接口、文件格式、作用域和必要语法示例 | 游戏名称、符号及示例用于说明兼容和调用；第三方权利归原权利人。本包不提供游戏源码全文、资产、生成文档快照或存档；实际核验读取使用者合法安装 |

## 外部工具（未捆绑）

- 标识符检索需要 [ripgrep](https://github.com/BurntSushi/ripgrep) 和 [Python](https://www.python.org/)。
- GUI 离线转换需要 [Pillow](https://python-pillow.org/)，JS一致性验证可选 [Node.js](https://nodejs.org/)。字体、纹理和特定截图由调用方提供，生成物需保留所用素材自身许可。
- 浏览器审计需要 [Playwright](https://github.com/microsoft/playwright-python) 和使用者提供的浏览器。
- 桌面操作依赖当前客户端实际提供的正式控制接口；原生桥是另行准备的外部组件。本包不分发第三方控制技能或服务，不承诺任一客户端自动拥有操控权限。

引用外部项目不表示其作者为本仓库背书。第三方代码或资产若后续加入，应保留其原署名和许可，并重新核对与本项目分发方式是否兼容。
