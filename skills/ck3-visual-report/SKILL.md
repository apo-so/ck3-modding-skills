---
name: ck3-visual-report
description: "根据实际 CK3 源码和证据生成中文离线机制报告，保留调用链、数值、原始摘录、解释与未确定项。"
license: MIT
metadata:
  author: apo-so
---


# CK3 机制报告

先研究后生成。区分原版、Mod已实现、研究推断和设计推演；版本来自本轮来源，历史样本不能升级为当前源码确认。

按 [研究规范](references/02_统一研究与呈现规范.md) 和 [报告分型](references/03_七类报告分型.md) 建底稿。追入口、筛选、选择、实际效果、后继和长期状态；每个调用追定义与消费者，缺件逐项登记。数值写单位、符号、条件、基数、取整及上下限；权重不冒称概率，意愿不冒称成功率。

人物行为另读 [行为分层](references/09_人物行为与判断分层.md)。源摘录从真实文件提取，记录版本/路径/范围/原字节哈希；教学版和原样版分开，见 [中文注释与双源码](references/05_中文注释与双源码.md)。

正文首屏给结论、范围与验证状态，按读者问题形成连续主线。技术词就地中文括注；原样源码保持不变，解释写在旁边。细节原位展开、来源往返保留阅读位置，不做只是隐藏章节的重复重点/完整版。见 [连续阅读](references/11_连续阅读与原位深读.md)。

## 构建与验证

模板包含空白研究字段，先填完整、设正确的template/demo/report身份，不能把生成模板标为正式研究。

```sh
python scripts/build_report.py templates/04_变量与状态.json output/report.html
python scripts/audit_report.py output/report.html --json output/structure.json
python scripts/verify_research.py output/draft.json --review output/review.json --source-root inputs --json output/research.json
```

提取命令与复核字段见 [来源复核](references/10_研究复核与来源校验.md) 及 [底稿字段](references/08_结构化底稿字段说明.md)。各命令均可先运行 `--help`。需要Python 3；浏览器审计另依赖Playwright与可用浏览器，不自动安装。

实际生成页面还要在浏览器核对默认阅读、展开、来源返回、手机宽度与无脚本可读；静态审计不证明内容正确或浏览器通过。按 [验收清单](references/06_验收清单.md) 交付HTML、底稿、来源与真实复核记录。集合不附历史大页或原版源码。
