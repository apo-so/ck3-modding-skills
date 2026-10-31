# CK3 Mod 制作技能

面向需要开发、研究与验证CK3 Mod的AI助手。涵盖脚本、GUI、账户经济、报告、GUI离线转换、游戏操控和工程保存。作者与维护者：[apo-so](https://github.com/apo-so)。采用 [MIT 许可证](LICENSE)。

内容来自实际 Mod 工程方法的精编；不附Mod、原版源码、存档、历史大页、DLL或游戏控制服务。

## 安装与使用

将 skills/ 下所需目录复制到客户端支持的技能目录，每个目录以SKILL.md为入口。首次推荐安装整个skills目录以保留相对引用；先备份同名技能，不覆盖已有定制版本。若客户端不支持技能自动发现，可直接让助手读取对应SKILL.md。

从 [开发总入口](skills/ck3-modding-suite/SKILL.md) 按题选用。所有命令从相应技能目录运行，或改成绝对脚本路径；占位符替换为本机真实路径。不要把安装回读当作客户端已加载或游戏测试通过。

| 能力 | 入口 |
|---|---|
| 接口核验 | [ck3-reference](skills/ck3-reference/SKILL.md) |
| 玩法脚本 | [ck3-script-engineering](skills/ck3-script-engineering/SKILL.md) |
| GUI修改 | [ck3-modify-gui](skills/ck3-modify-gui/SKILL.md) |
| 运行探针 | [ck3-runtime-probe](skills/ck3-runtime-probe/SKILL.md) |
| 辅助账户经济 | [ck3-auxiliary-account-economy-gui](skills/ck3-auxiliary-account-economy-gui/SKILL.md) |
| 机制报告 | [ck3-visual-report](skills/ck3-visual-report/SKILL.md) |
| GUI离线转换 | [ck3-gui-page-fidelity](skills/ck3-gui-page-fidelity/SKILL.md) |
| 游戏验证 | [ck3-hybrid-gameplay-testing](skills/ck3-hybrid-gameplay-testing/SKILL.md) |
| 原生桥方法 | [ck3-xeno-native-bridge](skills/ck3-xeno-native-bridge/SKILL.md) |
| 桌面通道 | [windows-computer-use-workflow](skills/windows-computer-use-workflow/SKILL.md) |
| 启动器播放集 | [ck3-launcher-playset-management](skills/ck3-launcher-playset-management/SKILL.md) |
| 保存与交接 | [mod-project-storage](skills/mod-project-storage/SKILL.md) |

## 环境与验证范围

- 文档方法：支持读取Markdown技能的客户端；所有具体游戏接口重新核对目标版本。
- 标识符搜索：Python 3、ripgrep、本机只读游戏源码。
- 报告构建/静态审计：Python 3；浏览器审计另需Playwright和可用浏览器。
- GUI转换：Python 3.10+、Pillow；Node用于可选JS一致性验证。
- 游戏操控：当前会话实际提供的正式桌面API，或明确选用且匹配当前EXE的原生桥。仓库不提供这些外部服务。

本候选不保证任何历史游戏补丁适配；离线自检、实际加载、渲染和场景验收分别记录。不要从技能文件存在推断操控能力。

## 作者、许可与来源

Copyright (c) 2026 apo-so。

本项目原创代码和文档采用 MIT，可使用、修改、分发和商用，须保留版权与许可声明。每个技能目录附带 LICENSE，单独复制时一并保留。外部参考及独立工具见 [来源说明](SOURCES.md)；本项目的许可不改变第三方内容的权利与许可。

## 包完整性检查

在仓库根目录运行 python scripts/check_package.py，检查文件哈希、技能元数据、许可、引用及 Python 语法。它不启动游戏，不安装依赖，不等于游戏功能或渲染验收。
