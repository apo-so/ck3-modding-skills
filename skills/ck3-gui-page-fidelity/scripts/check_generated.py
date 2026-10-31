"""Known contracts for generated explicit GUI; not a complete engine validator."""
import argparse,json,sys,re
from pathlib import Path
sys.dont_write_bytecode=True
from convert import kernel
kernel()
from core.syntax import parse_bytes


def validate_gui(raw, source, registered_names=()):
    doc=parse_bytes(raw,source)
    issues=[dict(x) for x in doc.diagnostics]
    def issue(code,node,message,severity='error'):
        issues.append({'code':code,'severity':severity,'source':source,'line':node.source_span.get('start',{}).get('line'),'message':message})
    defs={n.name:n for n in doc.root.walk() if n.key=='type' and n.name}
    roots=[n for n in doc.root.statements if n.kind=='assignment' and n.has_body]
    names={n.value('name') or (defs[n.key].value('name') if n.key in defs else None) for n in roots}
    for name in registered_names:
        if name in names:continue
        unresolved=[n for n in roots if n.value('using') is not None or (n.key not in defs and n.key not in ('window','widget'))]
        if unresolved:
            issue('REGISTERED_ROOT_NEEDS_TYPE_RESOLUTION',unresolved[0],name+' may depend on external types/templates; resolve before claiming registration.', 'warning')
        else:
            issue('REGISTERED_ROOT_MISSING',doc.root,'Registered widget '+name+' has no named root instance; a type declaration alone does not instantiate it.')
    # Only literal, explicitly positioned primitives. Inherited/layout/scroll
    # coordinates require resolution; painting beyond a root is not hit proof.
    def vector(n,key,default=None):
        values=n.occurrences(key)
        if not values:return default
        a=values[-1].atoms()
        if len(a)!=2 or not all(re.fullmatch(r'-?\d+(?:\.\d+)?',str(v)) for v in a):return None
        return tuple(map(float,a))
    def hit_bounds(n,x,y,rw,rh):
        for c in n.statements:
            if c.key not in ('widget','window','button','icon','textbox') or not c.has_body:continue
            if any(c.occurrences(k) for k in ('using','parentanchor','layoutpolicy_horizontal','layoutpolicy_vertical','anchor')):continue
            pos=vector(c,'position',(0,0));size=vector(c,'size')
            if pos is None or size is None:continue
            cx,cy=x+pos[0],y+pos[1];w,h=size
            if c.key=='button' and w>0 and h>0 and (cx+w<=0 or cy+h<=0 or cx>=rw or cy>=rh):
                issue('CONTROL_OUTSIDE_REGISTERED_ROOT',c,'Literal button lies completely outside its registered root. Verify a separate hit owner; visible paint alone is not click evidence.')
            hit_bounds(c,cx,cy,rw,rh)
    for root in roots:
        if root.value('name') not in registered_names:continue
        size=vector(root,'size')
        if size is not None and min(size)>0:hit_bounds(root,0,0,*size)
    for n in doc.root.walk():
        if n.key!='scrollwidget' or not n.has_body:continue
        children=[c for c in n.statements if c.kind=='assignment' and c.has_body]
        other=[c for c in n.statements if c not in children]
        if any(c.key in ('block','blockoverride','using') for c in n.statements):
            issue('SCROLLWIDGET_NEEDS_TEMPLATE_RESOLUTION',n,'Materialize this template before applying the explicit single-child contract.','warning')
        elif len(children)!=1 or other:
            issue('SCROLLWIDGET_ITEM_DESC_INVALID',n,'Explicit scrollwidget must contain one widget child and no wrapper properties. Put size on the child.')
    return {'source':source,'diagnostics':issues,'status':'KNOWN_CONTRACTS_FAIL' if any(i['severity']=='error' for i in issues) else 'NEEDS_RESOLUTION' if issues else 'KNOWN_CONTRACTS_PASS_NATIVE_PENDING','native_pixels':'NOT_VERIFIED','full_engine_schema':'NOT_IMPLEMENTED'}


def check_mod(mod_root):
    root=Path(mod_root).resolve(); registrations={}; registry_issues=[]
    for path in sorted((root/'gui/scripted_widgets').glob('*.txt')):
        doc=parse_bytes(path.read_bytes(),str(path));registry_issues.extend(doc.diagnostics)
        for n in doc.root.statements:
            if n.kind=='assignment' and n.key.startswith('gui/') and n.scalar:
                rel=Path(n.key)
                if rel.is_absolute() or '..' in rel.parts:
                    registry_issues.append({'code':'UNSAFE_REGISTRY_PATH','severity':'error','source':str(path)});continue
                registrations.setdefault(n.key,[]).append(n.scalar)
    results=[]
    for rel,names in registrations.items():
        p=root/rel
        if not p.is_file():registry_issues.append({'code':'REGISTERED_FILE_MISSING','severity':'error','source':str(p)})
    for p in sorted((root/'gui').rglob('*.gui')):
        rel=p.relative_to(root).as_posix();results.append(validate_gui(p.read_bytes(),rel,registrations.get(rel,[])))
    bad=bool(registry_issues) or any(v['status']=='KNOWN_CONTRACTS_FAIL' for v in results)
    return {'status':'KNOWN_CONTRACTS_FAIL' if bad else 'NEEDS_RESOLUTION' if any(v['status']=='NEEDS_RESOLUTION' for v in results) else 'KNOWN_CONTRACTS_PASS_NATIVE_PENDING','registrations':registrations,'registry_diagnostics':registry_issues,'files':results,'native_pixels':'NOT_VERIFIED'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mod-root',required=True);p.add_argument('--out');a=p.parse_args();v=check_mod(a.mod_root)
    if a.out:
        dest=Path(a.out);assert not dest.exists(),'Do not overwrite earlier check results';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(v,ensure_ascii=False,indent=2));return 1 if v['status']=='KNOWN_CONTRACTS_FAIL' else 2 if v['status']=='NEEDS_RESOLUTION' else 0

if __name__=='__main__':sys.exit(main())
