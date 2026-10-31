#!/usr/bin/env python3
"""将结构化研究底稿渲染成不依赖网络的单文件报告。只渲染，不推断 CK3 机制。"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION_IDS = ['identity','overview','choices','aftermath','lifecycle','conditions','actors','numbers','browser','results','states','evidence','teaching','raw','sources','audit']
TITLES = ['研究身份证','15 秒看懂','选择、收益与代价','主要后续与真正结束','完整生命周期','入口与条件','人物和作用域','数值与随机','事件／机制浏览器','最终结果矩阵','长期状态','研究完成度与不确定项','教学注释源码','原始证据摘录','来源索引','修改与验收']
LEVELS = {'源码直接确认','原版本地化确认','历史报告转述','研究推断','设计推演','待确认','本轮整理'}
PROFILES = {'event','scheme','interaction','state','value','design','behavior'}
SOURCE_KINDS = {'game_source','localization','report','design','method'}
CODE_ORIGIN_LABELS = {
    'game_source': '游戏源文件原样摘录',
    'localization': '游戏本地化文件原样摘录',
    'report_excerpt': '历史报告原文摘录',
    'concept': '设计伪代码／概念示例',
}


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def require_text(obj: dict, keys: list[str], label: str) -> None:
    for key in keys:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise ValueError(f'{label}.{key} 必须填写非空文本')


def validate(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError('研究底稿必须是对象')
    meta = data.get('meta', {})
    require_text(meta, ['title','subtitle','game_version','scope','report_version','basis','verification','profile','status'], 'meta')
    if meta['profile'] not in PROFILES:
        raise ValueError('未知报告类型')
    if meta['status'] not in {'template','demo','report'}:
        raise ValueError('status 只能是 template / demo / report')
    ids = [s.get('id') for s in data.get('sections', [])]
    if ids != SECTION_IDS:
        raise ValueError('sections 必须依照 0—15 章的固定顺序，不能跳过未确认章节')
    sources = data.get('sources', [])
    source_ids = [s.get('id') for s in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError('来源编号重复')
    for source in sources:
        require_text(source, ['id','name','kind','locator','boundary'], 'source')
        if source['kind'] not in SOURCE_KINDS:
            raise ValueError('未知来源类型')
    source_map = {s['id']: s for s in sources}
    def check_evidence(obj: dict, label: str) -> None:
        if obj.get('evidence') not in LEVELS:
            raise ValueError(f'{label} 缺少有效证据标签')
        refs = obj.get('source_ids', [])
        if not isinstance(refs, list) or any(r not in source_map for r in refs):
            raise ValueError(f'{label} 存在无效来源编号')
        if obj['evidence'] not in {'待确认','本轮整理'} and not refs:
            raise ValueError(f'{label} 的判断必须关联来源')
        if obj['evidence'] == '源码直接确认' and not any(source_map[r]['kind'] == 'game_source' for r in refs):
            raise ValueError(f'{label} 不能把历史报告转述升级为源码直接确认')
        if obj['evidence'] == '原版本地化确认' and not any(source_map[r]['kind'] == 'localization' for r in refs):
            raise ValueError(f'{label} 必须关联实际本地化来源')
    for sec in data['sections']:
        require_text(sec, ['id','summary'], 'section')
        check_evidence(sec, sec['id'])
        for block in sec.get('blocks', []):
            if block.get('type') not in {'paragraph','callout','cards','table','transitions','formula','calculator'}:
                raise ValueError(f'未知内容块：{block.get("type")}')
            if block['type'] == 'calculator' and block.get('kind') != 'allocation':
                raise ValueError('计算器仅支持明确标为教学的份额分配模型')
            if block['type'] == 'table':
                cols = len(block.get('headers', []))
                if not cols or any(len(row) != cols for row in block.get('rows', [])):
                    raise ValueError('表格表头与数据列数不一致')
            if block['type'] == 'transitions':
                for edge in block.get('items', []):
                    require_text(edge, ['from','to','cause'], 'transition')
    cards = data.get('cards', [])
    if len({c.get('id') for c in cards}) != len(cards):
        raise ValueError('事件／机制卡编号重复')
    for card in cards:
        require_text(card,['id','title','layer','category','result_type','root','eligibility','viewer','actors','original_text','options','direct_effects','hidden_effects','system_effects','follow_up','completion','end'], 'card')
        if not isinstance(card.get('recommended'), bool):
            raise ValueError('recommended 必须是布尔值')
        weight = card.get('weight')
        if weight is not None and (isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0):
            raise ValueError('相对权重必须是非负数或 null，不把未知写成零')
        check_evidence(card, card['id'])
    code_ids = [c.get('id') for c in data.get('code', [])]
    if len(code_ids) != len(set(code_ids)):
        raise ValueError('源码摘录编号重复')
    for card in cards:
        if not isinstance(card.get('code_ids', []), list) or any(x not in code_ids for x in card.get('code_ids', [])):
            raise ValueError('案例卡引用不存在的源码摘录')
    for identifier in source_ids + code_ids + [c['id'] for c in cards]:
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', identifier):
            raise ValueError('机器编号只能使用以字母起始的英文字母、数字、连字符或下划线；可见标题另填中文')
    for code in data.get('code', []):
        require_text(code, ['id','title','origin','source_id','raw','teaching','boundary'], 'code')
        if code['source_id'] not in source_map:
            raise ValueError('源码摘录引用未知来源')
        if code['origin'] not in CODE_ORIGIN_LABELS:
            raise ValueError('原始摘录类型无效')
        if code['origin'] == 'game_source' and source_map[code['source_id']]['kind'] != 'game_source':
            raise ValueError('没有游戏源文件，不能标注原版直接摘录')
        if code['origin'] == 'localization' and source_map[code['source_id']]['kind'] != 'localization':
            raise ValueError('没有实际本地化来源，不能标注本地化文件原样摘录')
        if code['origin'] == 'report_excerpt' and source_map[code['source_id']]['kind'] != 'report':
            raise ValueError('历史报告摘录必须关联report来源，不能与原文件身份混用')
        if '\r' in code['raw']:
            raise ValueError('HTML 展示摘录须统一使用 LF；原始字节另存并保留文件哈希')
        raw_lines = code['raw'].splitlines()
        cursor = 0
        added_comments = 0
        for line in code['teaching'].splitlines():
            if cursor < len(raw_lines) and line == raw_lines[cursor]:
                cursor += 1
            elif line.lstrip().startswith('# 中文：'):
                added_comments += 1
            else:
                raise ValueError('教学版改变或删去了原始语句；只允许额外插入中文注释行')
        if cursor != len(raw_lines) or added_comments == 0:
            raise ValueError('教学视图必须完整保留原始行并额外附带中文注释')
    if meta['status'] == 'report':
        # 未确认是合法研究结论；待填写不是交付内容。
        serialized = json.dumps(data, ensure_ascii=False)
        if '【待填写】' in serialized or '{{' in serialized:
            raise ValueError('正式报告中仍有未替换的模板占位符')


def badges(obj: dict) -> str:
    refs = ''.join(f'<a class="source-ref" href="#source-{e(r)}">来源 {e(r)}</a>' for r in obj.get('source_ids', []))
    return f'<div class="badges"><span class="badge">{e(obj["evidence"])}</span>{refs}</div>'


def allocation_block() -> str:
    return '''<div class="calculator" data-calculator="allocation">
<p class="callout warning"><strong>教学模型，不是游戏引擎模拟。</strong>公式：本期应付＝月收入×份额×效率×月数；实际支付＝应付与可用现金的较小值。只有一名持有者；不表示原版存在此收入接口。</p>
<div class="calc-grid"><div class="controls">
<label>地产月收入 <input data-input="income" type="number" min="0" max="1000000" step="0.1" value="6"></label>
<label>持有份额（百分比）<input data-input="share" type="number" min="0" max="100" step="1" value="40"></label>
<label>征收效率（百分比）<input data-input="efficiency" type="number" min="0" max="100" step="1" value="90"></label>
<label>结算月数 <input data-input="months" type="number" min="1" max="120" step="1" value="3"></label>
<label>可支付现金 <input data-input="cash" type="number" min="0" max="1000000000" step="0.1" value="4"></label>
</div><div><div class="metrics" aria-live="polite"><div><span>本期应付</span><strong data-output="due">6.48</strong></div><div><span>实际支付</span><strong data-output="paid">4.00</strong></div><div><span>形成欠款</span><strong data-output="arrears">2.48</strong></div></div><p data-calc-message>静态示例：6 × 40% × 90% × 3 ＝ 6.48；现金 4，支付 4，欠款 2.48。</p><button type="button" data-reset-calc>恢复示例</button></div></div></div>'''


def render_block(block: dict) -> str:
    kind = block['type']
    if kind == 'paragraph':
        return f'<p>{e(block["text"])}</p>'
    if kind == 'callout':
        return f'<p class="callout"><strong>{e(block.get("title", "提醒"))}</strong> {e(block["text"])}</p>'
    if kind == 'cards':
        return '<div class="card-grid">'+''.join(f'<article class="mini-card"><h3>{e(i["title"])}</h3><p>{e(i["text"])}</p></article>' for i in block['items'])+'</div>'
    if kind == 'table':
        heads = block['headers']
        rows = ''.join('<tr>'+''.join(f'<td data-label="{e(heads[j])}">{e(v)}</td>' for j,v in enumerate(row))+'</tr>' for row in block['rows'])
        return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th scope="col">{e(v)}</th>' for v in heads)+'</tr></thead><tbody>'+rows+'</tbody></table></div>'
    if kind == 'transitions':
        return '<div class="transition-list">'+''.join(f'<article class="transition"><div><span class="tiny">从</span><strong>{e(i["from"])}</strong></div><div class="edge-label"><span aria-hidden="true">→</span><span>{e(i["cause"])}</span></div><div><span class="tiny">到</span><strong>{e(i["to"])}</strong></div></article>' for i in block['items'])+'</div>'
    if kind == 'formula':
        return f'<div class="formula"><strong>{e(block["text"])}</strong><p>{e(block["boundary"])}</p></div>'
    if kind == 'calculator':
        return allocation_block()
    raise ValueError('无法渲染的内容块')


def render_browser(cards: list[dict]) -> str:
    if not cards:
        return '<p class="callout">本页没有收录事件或案例卡。原因见本章摘要；零张卡不等于整个游戏没有此机制。</p>'
    def options(field: str, title: str) -> str:
        vals = sorted({c[field] for c in cards})
        return f'<label>{title}<select data-filter="{field}"><option value="">全部</option>'+''.join(f'<option value="{e(v)}">{e(v)}</option>' for v in vals)+'</select></label>'
    tools = '<div class="browser-tools enhancement-only"><label class="search-label">搜索编号、标题、人物、结果与后续<input type="search" data-search placeholder="输入关键词"></label>'
    tools += options('layer','调用层级')+options('category','案例类别')+options('result_type','结果类型')
    tools += '<label>排序<select data-sort><option value="original">研究顺序</option><option value="weight">相对权重从高到低</option><option value="title">标题</option></select></label><label class="check"><input type="checkbox" data-recommended>只看推荐</label></div><div class="toolbar enhancement-only"><button type="button" data-expand>展开当前结果</button><button type="button" data-collapse>收起全部</button><button type="button" data-reset-filter>重置筛选</button></div>'
    names = [('root','根来源与调用层'),('eligibility','本次出现资格'),('viewer','谁会看到'),('actors','人物与当前作用域'),('original_text','原版正文／缺失说明'),('options','全部选项／收录范围'),('direct_effects','直接结果'),('hidden_effects','隐藏与共同结果'),('system_effects','对系统对象的影响'),('follow_up','后续与延迟'),('end','真正结束条件'),('completion','研究完成度')]
    rendered=[]
    for order,card in enumerate(cards):
        attrs = ' '.join(f'data-{k.replace("_","-")}="{e(card[k])}"' for k in ['layer','category','result_type'])
        weight = '' if card.get('weight') is None else str(card['weight'])
        content = '<dl class="card-details">'+''.join(f'<div><dt>{label}</dt><dd>{e(card[key])}</dd></div>' for key,label in names)+'</dl>'
        links = ''.join(f'<a href="#raw-{e(cid)}">原始摘录</a> <a href="#teaching-{e(cid)}">教学注释</a>' for cid in card.get('code_ids', []))
        if not links:
            links = '<span>本卡没有另附源码：当前范围见研究完成度。</span>'
        rendered.append(f'<details class="case-card" id="case-{e(card["id"])}" {attrs} data-order="{order}" data-weight="{e(weight)}" data-title="{e(card["title"])}" data-recommended="{str(card["recommended"]).lower()}"><summary><span><strong>{e(card["title"])}</strong><small>{e(card["id"])}（本报告案例编号） · {e(card["category"])}</small></span><span class="badge">{e(card["completion"])}</span></summary><div class="case-body">{badges(card)}{content}<div class="source-links">{links}</div></div></details>')
    return f'<div class="browser" data-browser data-expected-count="{len(cards)}">{tools}<p class="result-count" aria-live="polite">当前显示 <strong data-count>{len(cards)}</strong> / <span data-total>{len(cards)}</span> 张卡；数量仅代表本页收录范围。</p><div data-card-list>{"".join(rendered)}</div><p class="empty" data-empty hidden>没有符合当前条件的结果。请修改关键词或重置筛选。</p></div>'


def render(data: dict) -> str:
    validate(data)
    meta = data['meta']
    sections=[]
    research_ids = {'identity','lifecycle','conditions','actors','numbers','browser','states','teaching','raw','sources','audit'}
    for index,sec in enumerate(data['sections']):
        extra = ''.join(render_block(x) for x in sec.get('blocks', []))
        if sec['id'] == 'browser': extra += render_browser(data.get('cards', []))
        if sec['id'] in {'teaching','raw'}:
            for code in data.get('code', []):
                raw = sec['id'] == 'raw'
                text = code['raw'] if raw else code['teaching']
                original_type = {'localization':'原始本地化文本','report_excerpt':'原始摘录'}.get(code['origin'], '原始源码')
                label = CODE_ORIGIN_LABELS[code['origin']] if raw else f'教学注释版：增加了中文解释，不是{original_type}'
                attrs = f' data-raw-source data-sha256="{digest(text)}"' if raw else ' data-teaching-source'
                extra += f'<details class="source-block" id="{sec["id"]}-{e(code["id"])}"><summary>{e(code["title"])} · {label}</summary><p>{e(code["boundary"])}</p><pre{attrs}><code>{e(text)}</code></pre><button type="button" class="enhancement-only" data-copy>复制当前内容</button><span role="status" data-copy-status></span><p class="small">来源 <a href="#source-{e(code["source_id"])}">{e(code["source_id"])}</a>；校验的是展示摘录的统一换行文本，不是游戏原文件字节。</p></details>'
        if sec['id'] == 'sources':
            for source in data.get('sources', []):
                extra += f'<article class="source-entry" id="source-{e(source["id"])}"><h3>{e(source["id"])}（来源编号） · {e(source["name"])}</h3><p>{e(source["locator"])}</p><p class="small">证据边界：{e(source["boundary"])}</p></article>'
        layer = ' research-layer' if sec['id'] in research_ids else ''
        section_html = f'<section id="{sec["id"]}" class="report-section{layer}" data-section="{sec["id"]}"><div class="section-heading"><span class="chapter">{index:02d}</span><h2>{TITLES[index]}</h2></div><p class="section-summary">{e(sec["summary"])}</p>{badges(sec)}{extra}</section>'
        if sec['id'] in research_ids:
            section_html = f'<details class="reading-detail" data-local-detail><summary>展开：{TITLES[index]}</summary>{section_html}<button type="button" class="enhancement-only" data-close-local>收起，继续阅读</button></details>'
        sections.append(section_html)
    nav = ''.join(f'<a href="#{sid}"><span>{i:02d}</span> {title}</a>' for i,(sid,title) in enumerate(zip(SECTION_IDS,TITLES)))
    status = {'template':'空白模板 · 尚未研究','demo':'模板演示 · 非全量机制重研','report':'研究报告'}[meta['status']]
    lead = next(x['summary'] for x in data['sections'] if x['id'] == 'overview')
    verification_short = meta['verification'].split('。')[0]
    evidence_short = data['sections'][0]['evidence']
    header = f'<p class="eyebrow">CK3（十字军之王3） · 可视化机制研究</p><h1>{e(meta["title"])}</h1><p class="subtitle">{e(meta["subtitle"])}</p><div class="hero-conclusion"><strong>核心结论</strong><p>{e(lead)}</p></div><div class="meta-line"><span>{e(status)}</span><span>{e(evidence_short)}</span><span>{e(verification_short)}</span><span>样本游戏版本 {e(meta["game_version"])}</span><span>报告 {e(meta["report_version"])}</span></div><details class="boundary"><summary>研究范围与证据边界（展开核对）</summary><p><strong>研究范围</strong> {e(meta["scope"])}<br><strong>证据基础</strong> {e(meta["basis"])}<br><strong>验证状态</strong> {e(meta["verification"])}</p></details>'
    shell=(ROOT/'assets/report_shell.html').read_text('utf-8')
    replacements={'@@TITLE@@':e(meta['title']), '@@NAV@@':nav, '@@HEADER@@':header, '@@SECTIONS@@':'\n'.join(sections), '@@STATUS@@':e(meta['status'])}
    # 一次替换，避免用户正文中的保留字再次作为模板执行。
    return re.sub(r'@@(?:TITLE|NAV|HEADER|SECTIONS|STATUS)@@',lambda m:replacements[m.group()],shell)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path,help='结构化研究底稿 JSON')
    p.add_argument('output',type=Path,help='单文件 HTML 输出路径')
    p.add_argument('--overwrite',action='store_true',help='明确允许覆盖输出文件')
    args=p.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError('输出文件已存在；请换名或明确使用 --overwrite')
        data=json.loads(args.input.read_text('utf-8-sig'))
        text=render(data)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
        print(f'已生成：{args.output}（{len(text.encode("utf-8")):,} 字节）')
        print('生成成功不等于机制正确或游戏验证通过；请执行审计与人工复核。')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'生成失败：{exc}',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
