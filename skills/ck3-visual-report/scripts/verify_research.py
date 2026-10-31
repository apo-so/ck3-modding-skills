#!/usr/bin/env python3
"""核验真实来源、摘录保真及研究复核记录；不自动判断中文解释或游戏机制正确。"""
from __future__ import annotations
import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import build_report

DIMENSIONS = ('coverage', 'facts_units_conditions', 'scope_causality', 'source_identity',
              'raw_preservation', 'teaching_depth', 'cross_artifact_consistency')
STATUSES = {'PASS', 'PARTIAL', 'FAIL', 'NOT_RUN', 'NA'}

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def lf(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')

def ensure_distinct_output(output: Path, inputs: list[Path]) -> None:
    """验收输出不能覆盖底稿、复核清单或原件；同时识别符号链接及硬链接别名。"""
    resolved = output.resolve()
    for item in inputs:
        if resolved == item.resolve() or (output.exists() and item.exists() and output.samefile(item)):
            raise ValueError(f'输出与输入指向同一文件，拒绝覆盖：{item}')

class Elements(HTMLParser):
    """提取指定标签的可见文本；解码实体，保留标签内文本顺序与空白。"""
    def __init__(self, tag: str):
        super().__init__(convert_charrefs=True)
        self.tag = tag
        self.stack = []
        self.items = []
    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self.handle_data('\n')
        if tag == self.tag:
            self.items.append('')
            self.stack.append(len(self.items)-1)
    def handle_endtag(self, tag):
        if tag == self.tag and self.stack:
            self.stack.pop()
    def handle_data(self, data):
        for index in self.stack:
            self.items[index] += data

def extract(text: str, selector: dict) -> str:
    """只支持可审计的行段、完整文本、HTML元素；没有任意搜索替换。"""
    if not isinstance(selector, dict):
        raise ValueError('提取选择器必须是JSON对象')
    text = lf(text)
    kind = selector.get('kind')
    separator = selector.get('separator', '\n')
    if separator not in ('', '\n', '\n\n'):
        raise ValueError('separator 只能为空、一个或两个换行')
    if kind == 'whole_text':
        result = text
    elif kind == 'lines':
        lines = text.split('\n')
        ranges = selector.get('ranges', [])
        if not ranges:
            raise ValueError('行段为空')
        parts = []
        previous = 0
        for pair in ranges:
            if not isinstance(pair, list) or len(pair) != 2 or any(type(i) is not int for i in pair):
                raise ValueError('行段必须是两个整数')
            start, end = pair
            if start <= previous or end < start or end > len(lines):
                raise ValueError('行号越界、重叠或逆序；行号从1开始')
            parts.append('\n'.join(lines[start-1:end]))
            previous = end
        result = separator.join(parts)
    elif kind == 'html_elements':
        tag = selector.get('tag')
        if tag not in {'pre','p','h1','h2','h3','h4','h5','h6','title','div','li'}:
            raise ValueError('不支持的HTML摘录标签')
        parser = Elements(tag)
        parser.feed(text)
        indices = selector.get('indices', [])
        if not indices or any(type(i) is not int for i in indices) or indices != sorted(set(indices)):
            raise ValueError('HTML索引须为不重复升序整数，从0开始')
        if indices[0] < 0 or indices[-1] >= len(parser.items):
            raise ValueError('HTML元素索引越界')
        result = separator.join(parser.items[i] for i in indices)
    else:
        raise ValueError('未知摘录选择器')
    trim = selector.get('trim', 'none')
    if trim == 'outer_blank_lines':
        lines = result.split('\n')
        while lines and not lines[0].strip(): lines.pop(0)
        while lines and not lines[-1].strip(): lines.pop()
        result = '\n'.join(lines)
    elif trim != 'none':
        raise ValueError('trim只支持none或outer_blank_lines；不能默默删注释或重排语句')
    return result

def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip()) and '【待填写】' not in value

def verify(draft_path: Path, review_path: Path | None, source_root: Path) -> dict:
    result = {'status':'REVIEW_REQUIRED', 'integrity_status':'NOT_RUN', 'errors':[], 'review_gaps':[],
              'warnings':[], 'source_checks':[], 'excerpt_checks':[],
              'semantic_truth':'NOT_AUTOMATICALLY_VERIFIED',
              'boundary':'通过只证明文件/摘录匹配与复核记录齐备。复核内容由记录者负责，程序不能证明研究覆盖完整、逐条教学充分或游戏结论正确。'}
    errors, gaps = result['errors'], result['review_gaps']
    try:
        raw = draft_path.read_bytes()
        data = json.loads(raw.decode('utf-8-sig'))
        build_report.validate(data)
        result['draft_sha256'] = digest(raw)
        if review_path is None or not review_path.is_file():
            gaps.append('缺少研究复核清单；结构通过不能替代研究验收')
            return result
        review = json.loads(review_path.read_text('utf-8-sig'))
        if review.get('schema_version') != 1:
            raise ValueError('研究复核schema_version必须是1')
        if review.get('draft_sha256') != digest(raw):
            errors.append('复核对应的底稿哈希与当前文件不同；需要重核变化部分并冻结')
        root = source_root.resolve()
        sources = {s['id']:s for s in data['sources']}
        code = {c['id']:c for c in data.get('code', [])}
        verified = {}
        seen = set()
        for source in review.get('sources', []):
            sid = source.get('source_id')
            if sid not in sources or sid in seen:
                errors.append(f'未知或重复来源证明：{sid}')
                continue
            seen.add(sid)
            rel = Path(source.get('path', ''))
            path = (root/rel).resolve()
            if rel.is_absolute() or not path.is_relative_to(root) or not path.is_file():
                errors.append(f'来源不存在或超出source-root：{sid}')
                continue
            content = path.read_bytes()
            actual_hash = digest(content)
            matched = source.get('sha256') == actual_hash
            result['source_checks'].append({'source_id':sid,'path':rel.as_posix(), 'sha256':actual_hash,'matched':matched})
            if not matched:
                errors.append(f'来源字节哈希不一致：{sid}')
                continue
            verified[sid] = content.decode(source.get('encoding', 'utf-8-sig'))
        # 所有被用于事实的现存原件须有证明；method/design不冒充游戏原件。
        for sid, source in sources.items():
            if source['kind'] in {'game_source','localization','report'} and sid not in verified:
                gaps.append(f'未核实所声明来源的本地原件：{sid}')
        extracted = set()
        for item in review.get('excerpts', []):
            cid, sid = item.get('code_id'), item.get('source_id')
            if cid not in code or cid in extracted:
                errors.append(f'未知或重复摘录证明：{cid}')
                continue
            extracted.add(cid)
            if sid != code[cid]['source_id'] or sid not in verified:
                errors.append(f'摘录没有匹配且已核实的来源：{cid}')
                continue
            selected = extract(verified[sid], item.get('selector', {}))
            matched = selected == code[cid]['raw']
            result['excerpt_checks'].append({'code_id':cid, 'source_id':sid, 'matched':matched,
                                            'selected_sha256':digest(selected.encode('utf-8')),
                                            'displayed_sha256':digest(code[cid]['raw'].encode('utf-8'))})
            if not matched:
                errors.append(f'原始摘录与实际提取文本不同：{cid}；检查删注释、空白调整、范围或省略声明')
        for cid, item in code.items():
            if item['origin'] != 'concept' and cid not in extracted:
                gaps.append(f'原始摘录未提供可核对范围：{cid}')
            original_comments = sum(line.lstrip().startswith('# 中文：') for line in item['raw'].splitlines())
            teaching_comments = sum(line.lstrip().startswith('# 中文：') for line in item['teaching'].splitlines())
            meaningful = sum(bool(line.strip()) and not line.lstrip().startswith('#') and line.strip() not in {'{','}'} for line in item['raw'].splitlines())
            if meaningful > 1 and teaching_comments - original_comments <= 1:
                result['warnings'].append(f'{cid} 多条原始语句仅新增一条中文注释；须复核teaching_depth，注释数量本身不作语义判定')
        integrity_error_count, integrity_gap_count = len(errors), len(gaps)
        result['integrity_status'] = 'FAIL' if integrity_error_count else ('PARTIAL' if integrity_gap_count else 'PASS')
        targets = {'section:'+s['id'] for s in data['sections']}
        targets |= {'card:'+c['id'] for c in data.get('cards', [])}
        targets |= {'code:'+c for c in code}
        coverage = review.get('coverage', [])
        if not coverage:
            gaps.append('内容覆盖清单为空；必须对照本次用户范围逐项登记')
        identifiers = set()
        def inspect_check(item, label):
            status = item.get('status')
            if status not in STATUSES:
                errors.append(f'{label}状态无效')
            elif status == 'FAIL':
                errors.append(f'{label}复核记录明确失败：{item.get("reason", "")}')
            elif status in {'PARTIAL','NOT_RUN'}:
                gaps.append(f'{label}尚未通过：{item.get("reason", "")}')
            elif status == 'NA' and not nonempty(item.get('reason')):
                gaps.append(f'{label}未说明不适用原因')
            elif status == 'PASS' and not nonempty(item.get('evidence')):
                gaps.append(f'{label}只有通过声明，没有核对依据')
        for item in coverage:
            identifier = item.get('id')
            if not nonempty(identifier) or identifier in identifiers:
                errors.append('覆盖项编号为空或重复')
            identifiers.add(identifier)
            if not nonempty(item.get('requirement')):
                gaps.append(f'覆盖项{identifier}没有实际要求')
            linked = item.get('targets', [])
            if not isinstance(linked, list) or any(t not in targets for t in linked):
                errors.append(f'覆盖项{identifier}引用不存在的报告位置')
            if item.get('status') == 'PASS' and not linked:
                gaps.append(f'覆盖项{identifier}没有映射到交付内容')
            inspect_check(item, f'覆盖项{identifier}')
        semantic = review.get('semantic_review', {})
        if not isinstance(semantic, dict):
            raise ValueError('semantic_review必须是JSON对象；这是复核记录格式错误，不等同来源字节不匹配')
        if not nonempty(semantic.get('reviewer')) or not nonempty(semantic.get('method')):
            gaps.append('缺实际复核者或实际方法；不得代填未执行检查')
        recorded = set()
        for item in semantic.get('checks', []):
            dim = item.get('dimension')
            if dim not in DIMENSIONS or dim in recorded:
                errors.append(f'未知或重复语义复核维度：{dim}')
            recorded.add(dim)
            inspect_check(item, f'语义复核{dim}')
        for dim in DIMENSIONS:
            if dim not in recorded: gaps.append(f'缺语义复核记录：{dim}')
        result['integrity_status'] = 'FAIL' if integrity_error_count else ('PARTIAL' if integrity_gap_count else 'PASS')
        result['status'] = 'FAIL' if errors else ('REVIEW_REQUIRED' if gaps else 'CHECKS_COMPLETE_REVIEW_RECORDED')
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, LookupError) as exc:
        errors.append(str(exc))
        result['status'] = 'FAIL'
        if result['integrity_status'] == 'NOT_RUN': result['integrity_status'] = 'FAIL'
        return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    try:
        if args.json:
            inputs = [args.draft]
            if args.review:
                inputs.append(args.review)
                if args.review.is_file():
                    review = json.loads(args.review.read_text('utf-8-sig'))
                    root = args.source_root.resolve()
                    for item in review.get('sources', []):
                        rel = Path(item.get('path', ''))
                        path = (root/rel).resolve()
                        if not rel.is_absolute() and path.is_relative_to(root): inputs.append(path)
            ensure_distinct_output(args.json, inputs)
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        print(json.dumps({'status':'FAIL','errors':[str(exc)],'output_written':False},ensure_ascii=False))
        return 1
    result = verify(args.draft, args.review, args.source_root)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding='utf-8')
    print(text)
    return {'CHECKS_COMPLETE_REVIEW_RECORDED':0,'FAIL':1,'REVIEW_REQUIRED':2}[result['status']]

if __name__ == '__main__':
    raise SystemExit(main())
