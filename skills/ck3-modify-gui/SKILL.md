---
name: ck3-modify-gui
description: "实现和诊断 CK3 GUI 的类型上下文、scope、列表、选择刷新、模板、布局和实际渲染。"
license: MIT
metadata:
  author: apo-so
---


# CK3 GUI 修改

以当前源码和实际渲染为依据。有效表达式放在错误owner或子树仍是语义缺陷。

## 绑定与动作

先画控件祖先链：继承的typed context、按顺序安装的datacontext、datamodel、选择/可见性、回调及布局owner。多条datacontext不是一个标量上下文的简单替换；重复回调与声明顺序原样保留。见 [绑定所有权](references/binding-ownership.md) 与 [结构顺序](references/structural-order.md)。

区分列表集合、显示过滤、允许条件与执行资格。原生picker过滤不能扩大底层候选集合。选择变化后让依赖选择/列表失效并重建；回调传递scope应按实际receiver证明。接口与schema见 [原版核验](../ck3-reference/SKILL.md)。

## 最小布局修改

唯一定位控件owner，保留无关字节和模板。按 [最小修改](references/minimal-edit.md) 与 [文件完整性](references/file-integrity.md) 执行。

分别判断横向位置、视口高度、滚动内容高度和每行分配；父布局的扩展策略也会间接影响未改控件。见 [几何所有权](references/geometry-ownership.md)。继承模板、动态尺寸和hit区域缺证据时不能靠静态宽度算术宣布通过。

## 验收

静态核对上下文、owner、定义/消费者、回调顺序及加载覆盖。游戏内分别验证入口可见、点击命中、候选集、选择刷新、执行后置条件、空态、长列表、滚动、悬浮框与不同分辨率。见 [渲染验收](references/rendered-acceptance.md)。热加载生效与冷启动分别记录；离线页面不是原生渲染证明。
