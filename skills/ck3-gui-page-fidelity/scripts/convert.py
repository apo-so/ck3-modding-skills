"""Portable offline entry points for the bundled, source-preserving GUI converter."""
import argparse,base64,hashlib,json,shutil,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
SKILL=Path(__file__).resolve().parents[1];ENGINE=SKILL/'scripts/engine'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def kernel():
    inventory=json.loads((SKILL/'engine-manifest.json').read_text(encoding='utf-8'))
    for item in inventory['files']:
        path=(ENGINE/item['path']).resolve()
        if not path.is_relative_to(ENGINE.resolve())or not path.is_file()or sha(path).casefold()!=item['sha256'].casefold():raise ValueError('BUNDLED_ENGINE_CONFLICT:'+item['path'])
    sys.path.insert(0,str(ENGINE));return inventory
def save_result(path,value,inputs=()):
    if not path:return
    dest=Path(path).resolve()
    if dest.exists()or dest in[Path(p).resolve()for p in inputs]:raise ValueError('RESULT_OUTPUT_MUST_BE_NEW')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def selftest(node):
    from editing.workspace import bind_workspace,apply_workspace,make_request
    text='''# untouched comment and duplicate callbacks\r\nwindow={name=demo size={1420 800}\r\ntext_single={position={44 12} size={1220 48} raw_text="原始标题" fontsize=32}\r\nhbox={size={1340 42} spacing=12 button_standard={name=legal size={326 42} raw_text="法理管理" enabled="[Original.Valid]" datacontext="[Scope.Title]" onclick="[First.Callback]" onclick="[Second.Callback]"}}\r\n}\r\n'''
    raw=b'\xef\xbb\xbf'+text.encode('utf-8');m=bind_workspace(raw,'gui/demo.gui','demo','原始标题','legal');edits={'title':{'raw_text':'新标题\\😀','fontsize':30},'button':{'raw_text':'军府"法理','width':300,'height':40}}
    unchanged,_,_=apply_workspace(raw,m,make_request(m,{}));assert unchanged==raw
    request=make_request(m,edits);draft,after,receipt=apply_workspace(raw,m,request);assert len(receipt['patches'])==5 and receipt['untouched_bytes_verified']and receipt['protected_button_logic_preserved']
    inverse={target:{name:field['value']for name,field in owner['fields'].items()}for target,owner in m['targets'].items()};restored,_,_=apply_workspace(draft,after,make_request(after,inverse));assert restored==raw
    js='NOT_RUN_NO_NODE';binary=node or shutil.which('node')
    if binary:
        code="const fs=require('fs');require(process.argv[1]);require(process.argv[2]);const d=JSON.parse(fs.readFileSync(0,'utf8'));GuanchuangWorkspace.apply(d.m,d.request).then(r=>process.stdout.write(Buffer.from(r.bytes).toString('base64'))).catch(e=>{console.error(e);process.exit(1)})"
        p=subprocess.run([binary,'-e',code,str(ENGINE/'editing/title_runtime.js'),str(ENGINE/'editing/workspace_runtime.js')],input=json.dumps({'m':m,'request':request},ensure_ascii=False),capture_output=True,encoding='utf-8',check=True);assert base64.b64decode(p.stdout)==draft;js='PASS'
    return {'status':'OFFLINE_ROUNDTRIP_SELFTEST_PASS','five_fields':True,'duplicate_callbacks_and_context_preserved':True,'untouched_bytes_verified':True,'BOM_CRLF_and_unicode_preserved':True,'reparsed':True,'inverse_original_bytes':True,'JS_Python_bytes':js,'browser_pixels':'NOT_VERIFIED','native_pixels':'NOT_VERIFIED','game_actions':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description='CK3 GUI/page fidelity: offline source-bound conversion, no game control');commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('doctor');p.add_argument('--out')
    p=commands.add_parser('selftest');p.add_argument('--node');p.add_argument('--out')
    p=commands.add_parser('inspect');p.add_argument('--gui',required=True);p.add_argument('--out',required=True)
    p=commands.add_parser('prepare')
    for name in('mod-root','game-root','source','window','title','button','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--capture-sample',help='Existing authorized1760x990 R20 council-layout display sample only')
    p=commands.add_parser('apply')
    for name in('package','request','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--current-source')
    args=parser.parse_args(argv)
    try:
        inventory=kernel()
        if args.command=='doctor':
            import PIL
            result={'status':'BUNDLED_OFFLINE_ENGINE_READY','files':len(inventory['files']),'source_checkpoint':inventory['source_checkpoint'],'Pillow':PIL.__version__,'node':shutil.which('node'),'game_control':False};save_result(args.out,result)
        elif args.command=='selftest':result=selftest(args.node);save_result(args.out,result)
        elif args.command=='inspect':
            from core.syntax import parse_bytes
            path=Path(args.gui).resolve();raw=path.read_bytes();doc=parse_bytes(raw,path.name);parents={c.node_id:n.node_id for n in doc.root.walk()for c in n.statements};windows=[]
            for n in doc.root.walk():
                if n.key=='window'and n.has_body:windows.append({'name':n.value('name'),'owner_id':n.node_id,'declared_parent':parents.get(n.node_id),'line':n.source_span['start']['line'],'size':next((p.atoms()for p in n.occurrences('size')),None),'visible':n.value('visible'),'ordered_callbacks':[{'key':p.key,'value':p.scalar}for p in n.statements if p.key in('onclick','onrightclick')]})
            result={'status':'SOURCE_INVENTORY_ONLY','path':str(path),'sha256':sha(path),'diagnostics':doc.diagnostics,'windows':windows,'native_registration':'NOT_VERIFIED'};save_result(args.out,result,[path])
        elif args.command=='prepare':
            from editing.workspace import prepare_workspace,rebind
            if args.capture_sample:
                from PIL import Image
                capture=Path(args.capture_sample).resolve()
                with Image.open(capture)as im:sample_size=list(im.size)
                adapter=inventory.get('capture_adapter',{})
                if sample_size!=adapter.get('size')or sha(capture).casefold()!=adapter.get('accepted_sha256','').casefold():raise ValueError('CAPTURE_REQUIRES_KNOWN_R20_LAYOUT_AND_SOURCE_HASH_OR_NEW_ADAPTER')
            result=prepare_workspace(args.mod_root,args.game_root,args.source,args.window,args.title,args.button,args.out)
            if args.capture_sample:
                from adapters.mod_index import ModSourceIndex
                from preview.components import build_components,verify_components
                from editing.workspace_viewer import write_viewer
                dest=Path(args.out);m=json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
                if 'main_preview'not in m:raise ValueError('CAPTURE_ADAPTER_ONLY_FOR_CURRENT_MANAGER_PREVIEW')
                components=build_components(ModSourceIndex(args.game_root,args.mod_root),m['main_preview'],capture);verify_components(components);m=rebind((dest/'original.gui').read_bytes(),dict(m,resources=dict(m['resources'],native_components=components)));(dest/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');(dest/'editor.html').write_text(write_viewer(m),encoding='utf-8');result['historical_display_sample']=True
        else:
            from editing.title import apply_package
            result=apply_package(args.package,args.request,args.out,args.current_source)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,AssertionError,ImportError,subprocess.CalledProcessError)as exc:
        message=str(exc)
        if isinstance(exc,subprocess.CalledProcessError):message+=' '+(exc.stderr or'')[-800:]
        print(json.dumps({'status':'ERROR','error':message,'game_actions':False},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
