---
name: ck3-auxiliary-account-economy-gui
description: "诊断辅助头衔或住所的真实资源、定时结算、金币明细和多级悬浮框；迁移前核对当前对象和接口。"
license: MIT
metadata:
  author: apo-so
---


# 辅助账户与收入显示

本技能提炼历史辅助账户经验，不要求恢复旧版牧群或金币桥。当前机制是否需要这条路由由用户需求和当前源码决定。

## 先证明对象与资源

画出“人物 → 主头衔/默认住所”及“辅助头衔 → title_domicile → 资源getter/effect → 排程/引擎收入 → GUI行”。每个箭头给调用或运行证据。county、barony、title、domicile与默认住所不可互换；记录人物、头衔和住所身份以及PRE/POST真实余额。

看到“每月+N”只证明预测文本；验证tick真正执行、写入实际辅助对象、实际差值。排程报event/on_action未找到时先核对注册、namespace和scope，不先改倍率。

## 按症状定位

- tick未到：查on_action加载、延迟入口和对象scope。隐藏事件静态存在不证明运行期可触发。
- requested为正、actual为零：查对象失效、写错住所、实际上限或引擎限制，保留中间值区分原因。
- 跨季度增长翻倍或读档重发：查开局、继承、修复、读档和维护是否建立重复链。周期锁和补排只在需求或实际问题证明必要时加入；历史45天锁不是通用模板，维护不无故补发一次资源。
- 金币余额增加但收入明细没有：区分add_gold直接变化、monthly_income修正、原生收入类别和预测；一种结果不能冒称另一种接口。迁移前查清是否已有原生结算，报告重复计入，不把原型去重擅自升级为玩法门槛。
- 能展开父行但金额行没有悬浮框：沿ValueBreakdown/行datamodel定位实际呈现模板，hover挂在真正金额owner；别在父列表盲加。
- 空态过高或兼容故障：核对实际GUI owner、固定留白、模板和加载覆盖；优先只读展示，明确写入命令属于谁。

原版系数不能推出所有政体或辅助住所自动具有同样原生收入。接口组合先用 [原版核验](../ck3-reference/SKILL.md)，行为用 [运行探针](../ck3-runtime-probe/SKILL.md)，GUI绑定见 [GUI 修改](../ck3-modify-gui/SKILL.md)。
