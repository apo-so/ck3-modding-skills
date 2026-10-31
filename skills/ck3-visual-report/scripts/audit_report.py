#!/usr/bin/env python3
"""离线结构审计。不证明 CK3 脚本语义、概率推导或游戏运行正确。仅用 Python 标准库。"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

REQUIRED = 'identity overview choices aftermath lifecycle conditions actors numbers browser results states evidence teaching raw sources audit'.split()

class Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids=[]; self.links=[]; self.resources=[]; self.raw=[]; self.scripts=[]; self.cards=[]; self.expected=[]
        self._raw=None; self._script=None; self._in_script=False; self.text=[]; self.status=''; self.tags=[]; self.language=''
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); self.tags.append(tag)
        if a.get('id'): self.ids.append(a['id'])
        if tag=='html': self.language=a.get('lang','')
        if tag=='meta' and a.get('name')=='report-status': self.status=a.get('content','')
        if tag=='a' and a.get('href','').startswith('#'): self.links.append(unquote(a['href'][1:]))
        for k in ['src','poster','srcset']:
            if a.get(k): self.resources.append((tag,k,a[k]))
        if tag=='link' and a.get('href'): self.resources.append((tag,'href',a['href']))
        if 'case-card' in a.get('class','').split(): self.cards.append(a)
        if 'data-browser' in a: self.expected.append(a.get('data-expected-count',''))
        if tag=='pre' and 'data-raw-source' in a:
            self._raw={'expected':a.get('data-sha256',''),'text':''}
        if tag=='script': self._in_script=True; self._script=''
    def handle_endtag(self,tag):
        if tag=='pre' and self._raw is not None: self.raw.append(self._raw); self._raw=None
        if tag=='script' and self._script is not None: self.scripts.append(self._script); self._script=None; self._in_script=False
    def handle_data(self,data):
        if self._raw is not None: self._raw['text']+=data
        if self._script is not None: self._script+=data
        elif not self._in_script: self.text.append(data)


def audit(path: Path, *, allow_template: bool=False) -> dict:
    result={'file':str(path),'errors':[],'warnings':[],'checks':{},'boundary':'仅结构检查；不验证游戏机制、来源真实性、逐词括注完整性或实机表现。'}
    errors=result['errors']; warnings=result['warnings']
    try:
        text=path.read_text('utf-8-sig')
    except (OSError,UnicodeError) as exc:
        errors.append(f'读取失败：{exc}'); result['passed']=False; return result
    p=Inspector()
    try: p.feed(text); p.close()
    except Exception as exc: errors.append(f'HTML 解析失败：{exc}')
    missing=[sid for sid in REQUIRED if sid not in p.ids]
    if missing: errors.append('缺少固定章节：'+','.join(missing))
    duplicated=sorted({i for i in p.ids if p.ids.count(i)>1})
    if duplicated: errors.append('元素编号重复：'+','.join(duplicated))
    broken=sorted(set(p.links)-set(p.ids))
    if broken: errors.append('失效页内锚点：'+','.join(broken))
    if p.language!='zh-CN': errors.append('缺少中文页面语言标记')
    if not re.search(r'<meta\b[^>]*name=["\']viewport["\']',text,re.I): errors.append('缺少移动端视口')
    if '@media' not in text or 'max-width:620px' not in text: errors.append('缺少已约定的窄屏样式')
    if re.search(r'<body\b[^>]*class=["\'][^"\']*\b(?:enhanced|js)\b',text,re.I): errors.append('正文预先写死脚本已启用类，可能破坏无脚本阅读')
    external=[r for r in p.resources if not r[2].startswith('data:')]
    if external: errors.append('存在非内嵌资源依赖：'+str(external[:5]))
    if re.search(r'@import\b|url\(\s*["\']?(?:https?:|//)',text,re.I): errors.append('样式有外部资源依赖')
    if any(re.search(r'\b(?:fetch\s*\(|XMLHttpRequest\b|WebSocket\s*\()',s) for s in p.scripts): errors.append('网页脚本有外部数据读取接口，单文件模式需要人工审查')
    for i,raw in enumerate(p.raw):
        actual=hashlib.sha256(raw['text'].encode('utf-8')).hexdigest()
        if actual!=raw['expected']: errors.append(f'第{i+1}个原始摘录文本哈希不匹配')
    if len(p.expected)>1: errors.append('基础母版仅支持一个汇总浏览器；多个需要升级审计器')
    if p.expected:
        try:
            if int(p.expected[0])!=len(p.cards): errors.append('浏览器声明数量与实际卡数不同')
        except ValueError: errors.append('浏览器数量不是整数')
    if not allow_template and p.status=='template': errors.append('当前是空白模板，不能作为正式报告交付')
    if not allow_template and ('【待填写】' in ''.join(p.text) or '@@SECTIONS@@' in text): errors.append('仍有模板占位符')
    node=shutil.which('node')
    if node:
        syntax_ok = True
        for i,script in enumerate(p.scripts):
            with tempfile.TemporaryDirectory() as td:
                script_file=Path(td)/f'inline-{i}.js'; script_file.write_text(script,'utf-8')
                check=subprocess.run([node,'--check',str(script_file)],capture_output=True,text=True,timeout=15)
                if check.returncode:
                    syntax_ok = False
                    errors.append('网页脚本语法错误：'+check.stderr[-500:])
        result['checks']['javascript_syntax']='PASS' if syntax_ok else 'FAIL'
    else:
        warnings.append('未找到 Node.js；网页脚本语法检查未执行')
        result['checks']['javascript_syntax']='NOT_RUN'
    result['checks'].update({'required_sections':len(REQUIRED)-len(missing),'case_cards':len(p.cards),'raw_excerpt_hashes':len(p.raw),'no_external_resources':not external})
    result['passed']=not errors
    return result


def main()->int:
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('files',nargs='+',type=Path);a.add_argument('--allow-template',action='store_true');a.add_argument('--json',dest='json_path',type=Path)
    args=a.parse_args();results=[audit(p,allow_template=args.allow_template) for p in args.files]
    output=json.dumps(results,ensure_ascii=False,indent=2)
    if args.json_path:
        args.json_path.parent.mkdir(parents=True,exist_ok=True);args.json_path.write_text(output+'\n','utf-8')
    print(output)
    return 0 if all(x['passed'] for x in results) else 1
if __name__=='__main__': raise SystemExit(main())
