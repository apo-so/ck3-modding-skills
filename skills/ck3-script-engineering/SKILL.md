---
name: ck3-script-engineering
description: "实现和诊断 CK3 事件、决议、互动、on_actions、变量、修正、本地化及非 GUI 兼容问题。"
license: MIT
metadata:
  author: apo-so
---


# CK3 脚本工程

共用玩法原则与证据标准见 [总入口](../ck3-modding-suite/SKILL.md)。先读项目当前交接和实际源码，不从旧包覆盖当前版本。

1. 沿触发入口、过滤、状态、执行、资源和反馈追完整链。区分 trigger/effect/value/GUI 表达式，写清 current/root/actor/recipient/target 与保存scope的类型和寿命。新增或不确定字段交给 [接口核验](../ck3-reference/SKILL.md)。
2. 每个变量、flag、列表、保存scope指定owner、写入者、读取者与清理；延迟运行时重新定位对象。新建和交换已有对象是不同操作，不给交换擅自套新建资格。
3. 变更覆盖完整用户路径，优先命名空间扩展，避免无关重构和大段复制原版。保留编码/BOM、换行和未修改定义。
4. 对会变的必要执行条件在动作前核对；可静默失败的引擎动作之后读回真实对象状态，再按需求结算。原型阶段不凭假想重复资源新增门槛。
5. 查实际数据库定义与所有调用者，包含scope限定的script_value；区分可调用符号、变量、参数、flag和本地化键，不做“所有前缀都必须定义”的错误检查。
6. 核验同键覆盖、数据库、加载顺序、模板和存档状态，按 [兼容分析](references/compatibility-analysis.md) 检查；无同名文件不等于兼容。
7. 静态检查后交付完整候选及差异。运行测试用 [探针](../ck3-runtime-probe/SKILL.md)，保存/部署用 [工程保存](../mod-project-storage/SKILL.md)。

按症状读取 [代码与参数检查](references/coding-review.md)、[静态诊断](references/static-diagnostics.md)、[消息与悬浮框](references/message-and-tooltip-evidence.md)。消息里的历史结果应冻结为该次实际结果，不能随当前变量一起变化；修显示不撤销已执行动作。
