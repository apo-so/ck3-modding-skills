---
name: ck3-launcher-playset-management
description: Use when adding an installed Crusader Kings III mod to a named Paradox Launcher playset or selecting the playset active by default. Resolve exact targets, preserve unrelated state, and verify the saved membership or selection. Not for editing mod source or proving in-game behavior.
license: MIT
metadata:
  author: apo-so
---

# CK3 启动器播放集管理

只修改用户指定的 CK3 播放集状态。用户说“加入”时，默认把 Mod 加入并启用，除非用户明确说只收录但不启用。切换默认播放集是独立操作；只有用户明确要求时才改当前活动播放集。不要启动游戏、修改 Mod 文件、重排其他 Mod 或触碰其他播放集。

## 核对目标

- 从当前 CK3 用户数据和启动器状态确认唯一的目标播放集。存在多个 CK3 安装、多个同名播放集或不一致状态时，先消除歧义。
- 用启动器 Mod 记录与本机 descriptor/安装目录核对名称、路径或 ID、来源和可用状态。中文近形字也可能是不同 Mod（如“亳”与“毫”）；不按模糊名称选择。候选不唯一时询问用户。
- 目标状态已符合请求时不写入。若用户要求加入但关联已存在且禁用，只调整所需启用状态，不重复新增。

## 优先使用启动器界面

- 优先使用当前会话实际可调用的官方 Windows Computer Use 工具。若提供 node_repl + @oai/sky，先读取应用清单、唯一绑定 Paradox Launcher 窗口，再按 $windows-computer-use-workflow 逐步观察、操作与核验。
- 用户未要求建立共享接入时，不擅自安装或注册 MCP 服务。若没有可用 GUI 且没有已接入的本机 MCP，才评估数据库回退。不得以终端脚本模拟 GUI，也不得把“尝试点击”当成完成。

## 本地数据库回退

- 定位本机实际 CK3 用户数据目录和启动器数据库。常见文件名为 launcher-v2.sqlite，但路径、schema、ID 都必须从当前机器重新发现；不照搬旧任务结果。
- 启动器运行或数据库被占用时不写入，不强制结束进程。请用户正常退出；检查进程、锁和 WAL/日志 sidecar。不得手工删除 sidecar；状态不明时停止。
- 只读检查当前 schema、约束、目标记录、关联和唯一的活动播放集。记录 Before SHA-256，将数据库复制到新的、未存在的备份路径，并验证源与备份哈希一致。
- 使用单一 SQLite 事务和严格前置条件；如果 Before hash、播放集、Mod、关联状态或活动播放集与刚核验的基线不符，回滚并重新检查。
  - 加 Mod：只改目标关联及用户要求的启用状态；保留其他成员及相对顺序。
  - 设默认播放集：只改当前 schema/状态所确认的默认或活动选择字段。若以 isActive 表示活动播放集，先确认原状态唯一；只切换原活动项和目标项，不碰 Mod 关联、启用状态、排序或时间戳。
- 事务后重新读取：确认目标状态正确且唯一；加 Mod 时检查关联恰一条；设默认时检查目标为唯一活动项。运行 SQLite 完整性与外键检查，并确认非目标数据未变；记录 After hash、备份和核验输出。
- 事务失败时回滚。已提交后若需恢复，先确认当前 DB 仍与记录的 After hash 一致；若启动器或用户之后写入过，不能整库覆盖备份，应先比较并停止。

## 结果边界

分别报告“界面已确认”“数据库配置已读回”或“仍待核验”。经数据库回退但未重开启动器时，只能声称本地配置已保存。播放集选择不证明游戏已启动、Mod 已加载或兼容性已验证。
