"""Check repository integrity without starting CK3 or installing dependencies."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys


def check(root):
    errors=[]
    license_text=(root/'LICENSE').read_text(encoding='utf-8')
    sums=root/'SHA256SUMS'
    tracked={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        digest,rel=line.split('  ',1)
        p=(root/rel).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file():
            errors.append('invalid manifest target: '+rel);continue
        if rel in tracked:errors.append('duplicate manifest target: '+rel)
        tracked[rel]=digest
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:errors.append('hash mismatch: '+rel)
    skills=sorted((root/'skills').iterdir())
    for skill in skills:
        entry=skill/'SKILL.md'
        text=entry.read_text(encoding='utf-8')
        if not text.startswith('---\n'):errors.append('missing frontmatter: '+skill.name);continue
        fm=text.split('---',2)[1]
        expected={'name':skill.name,'license':'MIT'}
        for key,value in expected.items():
            if not re.search(r'^'+key+r':\s*'+re.escape(value)+r'\s*$',fm,re.M):errors.append('invalid '+key+': '+skill.name)
        if not re.search(r'^description:\s*\S',fm,re.M):errors.append('missing description: '+skill.name)
        if not re.search(r'^  author:\s*apo-so\s*$',fm,re.M):errors.append('missing author: '+skill.name)
        if (skill/'LICENSE').read_text(encoding='utf-8')!=license_text:errors.append('license mismatch: '+skill.name)
    scanned=0
    for rel in sorted(tracked):
        p=root/rel
        if p.suffix=='.py':
            try:ast.parse(p.read_text(encoding='utf-8-sig'),filename=rel)
            except (SyntaxError,UnicodeError) as e:errors.append('python syntax: '+rel+': '+str(e))
        if p.suffix!='.md':continue
        text=p.read_text(encoding='utf-8-sig');scanned+=1
        for target in re.findall(r'\[[^\]]*\]\(([^\n)]+)\)',text):
            if target.startswith(('https://','http://','mailto:','#')):continue
            dest=(p.parent/target.split('#')[0].strip('<>')).resolve()
            if not dest.is_relative_to(root.resolve()) or not dest.exists():errors.append('broken link: '+rel+' -> '+target)
    return {'status':'PASS' if not errors else 'FAIL','manifest_files':len(tracked),'skills':len(skills),'markdown_files':scanned,'errors':errors,'boundary':'package integrity only; no runtime, rendering or semantic proof'}


if __name__=='__main__':
    report=check(Path(__file__).resolve().parents[1])
    print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(0 if report['status']=='PASS' else 1)
