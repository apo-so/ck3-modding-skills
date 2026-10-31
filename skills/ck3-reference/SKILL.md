---
name: ck3-reference
description: "核对 CK3 接口种类、作用域、参数、数据库结构和当前原版调用；用于新增或不确定的脚本及 GUI 接口。"
license: MIT
metadata:
  author: apo-so
---

# 核验原版接口

确定问题属于 effect、trigger、value、scope、event target、modifier、on_action、localization、schema 或 GUI 表达式。相同字符串出现在另一类别不构成证明。

## 证据优先级

按“当前版本、权威来源、最小读取量”检索：

1. **目标版本生成的 script_docs**：核对可用 trigger、effect、scope、event target、on_action 等声明。
2. **当前安装的游戏文件与 .info/schema**：核对数据库结构、定义、文件归属和实际内容。
3. **当前原版调用点及消费者**：确认参数、scope、执行上下文、调用顺序与结果如何被使用。
4. **官方开发资料与社区 Wiki**：用于理解概念、格式和常见模式；不能替代目标版本的本机证据。
5. **历史 Mod 示例与旧报告**：仅作为研究线索，必须重新核验版本与适用场景。

生成文档证明声明接口，schema 证明数据库形状，调用点证明具体用法，运行结果证明该场景效果。记录来源版本与哈希；版本不一致时旧证据标 STALE，针对所需符号补当前证据。来源相互冲突时，明确指出冲突，不把低等级资料提升为事实。

## 按任务定位资料

- trigger/effect：先查对应生成文档，再查原版调用和消费者。
- event scope/target：检查事件定义、触发入口、保存 scope 与后续事件链。
- on_action：检查原版入口是否已有 effect、挂接方式、触发频率和重复执行风险。
- modifier/script_value/variable：确认数据库定义、宿主 scope、求值时点及持久性。
- event/decision/interaction：结合目标类型的数据库定义、实际原版样例和触发上下文。
- GUI/Jomini：检查生成类型文档、receiver 类型、datacontext 继承、回调和控件所属子树。
- 文件加载与兼容：检查真实目录、虚拟文件覆盖、定义键冲突、加载顺序和调用方假设。

不要一次性加载整个参考库。先用索引定位，再只打开与当前问题相关的页面或源码片段。

## 精确定位

集合不附原版源码和生成日志。将本机游戏安装或 game 目录显式传入，只读查询：

    python scripts/search-current-symbol.py --game-root <本机游戏目录> --symbol <单一标识符>

需要 Python 3 与 PATH 中的 ripgrep。该脚本只搜索 txt/gui/info 的标识符边界并给来源哈希，返回 FOUND/NOT_FOUND；命中注释、定义或调用均不自动证明接口支持。输入只能为单一标识符，不含 scope 前缀或表达式。脚本路径从本技能目录解析，不假定当前工作目录。

对 effects.log、triggers.log 等生成文档使用现有文本查询工具；先确定确为目标游戏版本生成。需要生成文档时由用户选择可用环境，不主动启动游戏。

## 核验回执

给出符号和类别、版本、文件/行段与哈希、FOUND/NOT_FOUND、输入 scope、参数、当前调用点、消费者、未解决项。逐层阅读调用者和消费者，不能仅凭名称解释含义。精确名未找到时保留 NOT_FOUND；零调用点不证明引擎已移除。

GUI 表达式还需核对 receiver 类型与所属子树，交给 [GUI 修改](../ck3-modify-gui/SKILL.md)。源码不能区分的组合交给 [运行探针](../ck3-runtime-probe/SKILL.md)。

## 外部参考边界

可将 [ReikiMaple 的 CK3 Mod 技能仓库](https://github.com/ReikiMaple/Skills-for-CrusaderKing3-Modding/tree/d3098dd0551adc39f067eb3ed4fb6a15a7003644) 作为资料导航和工作流参考；其 Wiki 镜像、技能文件和工具不属于本仓库，也不因本仓库的 MIT 许可而获得再分发授权。任何具体接口仍须按上面的目标版本证据链重新核验。
