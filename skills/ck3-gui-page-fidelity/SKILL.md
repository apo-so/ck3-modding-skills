---
name: ck3-gui-page-fidelity
description: "将来源明确的 CK3 GUI 转为离线编辑页，并在支持字段内保留原字节和回调进行回写；独立网页重建单独处理。"
license: MIT
metadata:
  author: apo-so
---


# GUI 与页面转换

三种任务分别处理：原GUI→页面以原文件为真源；带manifest的编辑页→GUI按owner/token跨度回写；独立网页或截图→新GUI属于有损重建，不能恢复缺失条件与回调。

本模块附可运行内核，保留有序AST、源字节及未修改区域。需要Python 3.10+、Pillow；Node可选，用于JS/Python字节对照。游戏字体、纹理、截图、原版源和回调均由使用者提供，不附游戏资产，也不执行游戏效果。

```sh
python scripts/convert.py doctor
python scripts/convert.py selftest --out <新的结果JSON>
python scripts/convert.py inspect --gui <源文件.gui> --out <新的清点JSON>
python scripts/convert.py prepare --mod-root <Mod目录> --game-root <游戏game目录> --source <相对GUI路径> --window <窗口名> --title <标题> --button <命名按钮> --out <新输出目录>
python scripts/convert.py apply --package <已导入包> --request <编辑请求JSON> --out <新草稿目录>
```

prepare输出editor.html、完整original.gui、manifest和source-profile。编辑后导出请求，再apply获得完整候选GUI、diff和回执。当前受支持字段为唯一定位的标题raw_text/fontsize及命名按钮raw_text/width/height；其他Mod通常只有基础两控件编辑，完整窗口需补适配器。不能声称任意HTML/CSS自动编译为完整GUI。

检查来源hash、owner、token跨度，冲突则停。验证重复datacontext/回调顺序、不相关字节、BOM/CRLF和回写后再解析；逆变更应恢复原字节。自检仅证明工具处理，不证明原生像素、注册、命中或玩法。

未能还原的模板、贴图、动态绑定和shader列缺口。特定历史截图裁剪器有严格尺寸与来源hash限制，不套到新图。源码结构检查可用 `python scripts/check_generated.py --help`，它不是完整引擎验证器。原生验收使用 [GUI 修改](../ck3-modify-gui/SKILL.md)。
