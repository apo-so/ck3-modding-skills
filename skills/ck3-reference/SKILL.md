---
name: ck3-reference
description: "核对 CK3 接口种类、作用域、参数、数据库结构和当前原版调用；用于新增或不确定的脚本及 GUI 接口。"
license: MIT
metadata:
  author: apo-so
---


# 核验原版接口

确定问题属于 effect、trigger、value、scope、event target、modifier、on_action、localization、schema 或 GUI 表达式。相同字符串出现在另一类别不构成证明。

分别使用目标版本生成文档、当前安装的 `.info`、当前原版调用和新鲜项目日志：生成文档证明声明接口，schema 证明数据库形状，调用点证明具体用法，运行结果证明该场景效果。记录来源版本与哈希；版本不一致时旧证据标 STALE，针对所需符号补当前证据。

## 精确定位

集合不附原版源码和生成日志。将本机游戏安装或 `game` 目录显式传入，只读查询：

```sh
python scripts/search-current-symbol.py --game-root <本机游戏目录> --symbol <单一标识符>
```

需要 Python 3 与 PATH 中的 ripgrep。该脚本只搜索 txt/gui/info 的标识符边界并给来源哈希，返回 FOUND/NOT_FOUND；命中注释、定义或调用均不自动证明接口支持。输入只能为单一标识符，不含 scope 前缀或表达式。脚本路径从本技能目录解析，不假定当前工作目录。

对 `effects.log`、`triggers.log` 等生成文档使用现有文本查询工具；先确定确为目标游戏版本生成。需要生成文档时由用户选择可用环境，不主动启动游戏。

## 核验回执

给出符号和类别、版本、文件/行段与哈希、FOUND/NOT_FOUND、输入scope、参数、当前调用点、未解决项。逐层阅读调用者和消费者，不能仅凭名称解释含义。精确名未找到时保留 NOT_FOUND；零调用点不证明引擎已移除。

GUI 表达式还需核对 receiver 类型与所属子树，交给 [GUI 修改](../ck3-modify-gui/SKILL.md)。源码不能区分的组合交给 [运行探针](../ck3-runtime-probe/SKILL.md)。
