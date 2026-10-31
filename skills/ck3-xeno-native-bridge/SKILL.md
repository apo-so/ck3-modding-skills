---
name: ck3-xeno-native-bridge
description: "为指定 CK3 精确版本核对 XenoAmess 原生桥的构建、连接、能力与动作读回；仅在用户选择原生路线时使用。"
license: MIT
metadata:
  author: apo-so
---


# 原生桥接入合同

这是外部组件的接入方法，不附DLL、注入器、服务器或第三方源码。先由使用者提供已核验来源与许可的实现，再读取其当前构建文档和API；本集合不声称任一游戏补丁已适配。

1. 记录源码commit、匹配的游戏版本、EXE哈希和目标进程身份；构建保留命令、header/source指纹、日志及DLL/注入器哈希。仅有旧DLL或构建目录不构成匹配证据。
2. 在用户明确授权的边界内采用实现方的连接/加载流程，使用本轮真实返回的PID/pipe，核对独占服务器、fresh hello、连接代数与capabilities。不能凭文件存在声称已注入或客户端已加载MCP。
3. 先只读frontend route、GUI tree或领域snapshot；动作ACK必须通过新route或实际状态独立复查。保存原始请求/响应和失败，不假造缺失命令。
4. 书签接口需要实现方定义的对象/指针时，不把任意CharacterID塞入参数；局内set-played-character不自动支持lobby选人。缺任意角色选择时标TARGET_SELECTOR_UNSUPPORTED，允许UI回退则用 [游戏验证](../ck3-hybrid-gameplay-testing/SKILL.md)。
5. 故障保存进程、管道与未完成命令，确认前任停止后才接管。旧桥明确清理后不重连；重新建立会话需重新验证。不得擅自强制卸载已加载DLL或重启游戏。

独立副屏与不抢焦点按 [桌面通道](../windows-computer-use-workflow/SKILL.md) 验证。没有外部实现或版本不匹配即标BLOCKED/NOT RUN，不能把本文当即开即用工具。

外部来源：[XenoAmess / ck3_eternal_recurrence](https://github.com/XenoAmess/ck3_eternal_recurrence)，其源码和二进制遵守上游许可；本技能只提供接入方法。
