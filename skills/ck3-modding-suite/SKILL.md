---
name: ck3-modding-suite
description: "协调 CK3 Mod 的脚本、GUI、机制研究、运行验证与交付；按问题选择所需技能。"
license: MIT
metadata:
  author: apo-so
---


# CK3 Mod 开发入口

先明确目标行为、当前源码/游戏版本与任务范围。研究、计划、实施、部署、游戏测试分别按用户授权执行；本集合不授予外部工具或游戏权限。

## 按问题读取

| 问题 | 技能 |
|---|---|
| 接口、scope、schema 或原版调用 | [原版核验](../ck3-reference/SKILL.md) |
| 事件、决议、互动、资源与兼容 | [脚本工程](../ck3-script-engineering/SKILL.md) |
| GUI 上下文、列表、刷新、布局 | [GUI 修改](../ck3-modify-gui/SKILL.md) |
| 辅助头衔/住所资源与收入明细 | [账户经济](../ck3-auxiliary-account-economy-gui/SKILL.md) |
| 引擎行为不能由源码区分 | [运行探针](../ck3-runtime-probe/SKILL.md) |
| 源码绑定的 GUI/页面互转 | [离线转换](../ck3-gui-page-fidelity/SKILL.md) |
| 机制研究与中文离线报告 | [可视化报告](../ck3-visual-report/SKILL.md) |
| 选人、读界面或场景验收 | [游戏验证](../ck3-hybrid-gameplay-testing/SKILL.md) |
| 精确版本原生控制桥 | [原生桥](../ck3-xeno-native-bridge/SKILL.md) |
| 当前桌面工具与独立副屏路线 | [桌面通道](../windows-computer-use-workflow/SKILL.md) |
| 启动器播放集 | [播放集管理](../ck3-launcher-playset-management/SKILL.md) |
| 检查点、保存、交接与部署 | [工程保存](../mod-project-storage/SKILL.md) |

只读本题需要的技能及参考，不全量加载。

## 先打通完整功能

按“入口 → 候选/数据 → 执行 → 实际状态 → 成本或奖励 → 反馈/清理”追调用链。默认不增玩法门槛，资源重复、容量与平衡合理化后置。后加条件须有明确需求、引擎硬限制、实际问题或最终逻辑审查依据。该原型偏好不改变真实文件、存档与账户保护。

保留原生世族、冒险者和其他住所载体的头衔；只能在任务授权内拆除已证实由 Mod 额外创建的住所头衔，来源不明不拆。

不把界面预测、命令 ACK、变量名命中当效果发生。关键动作以真实 holder、lessee、对象绑定、余额或日期的后置状态验证。先修因果链中最早失效处，再修显示。

## 统一证据与交付

记录版本、源码哈希、具体对象和观察条件。分别报告 REFERENCE VERIFIED、STATIC PASS、DEPLOYED READBACK、ACTUALLY LOADED、HOT RELOAD、RENDER OBSERVED、SCENARIO PASS；各项独立标 PASS/FAIL/INCONCLUSIVE/NOT RUN。旧实测只支持原版本及原场景。

使用 [变更与证据记录](templates/change-record.md) 保存复杂变更。只复查受新变更影响的证据；失效方案保留失败原因及重新开启条件。最终说明结果、已验证范围、未运行项、部署/恢复位置和下一步。

亳伯奇迁移与验收问题可按需读 [项目经验精编](references/pgh-lessons.md)，不附原始run或存档。
