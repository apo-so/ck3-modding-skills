"""Actual used native component metrics/frames with explicit historical image samples."""
import base64,copy,io,json
from pathlib import Path
from PIL import Image,ImageChops
from core.syntax import parse_bytes
from editing.title import require,digest

def walk_ast(node):
    yield node
    for child in node.get('ordered_statements',[]):yield from walk_ast(child)

def walk_scene(node):
    yield node
    for child in node['children']+node['item']:yield from walk_scene(child)

def scalar(node,key,default=None):
    rows=[p for p in node['ordered_statements']if p['kind']=='assignment'and p['key']==key]
    return rows[-1]['scalar']if rows and not rows[-1]['has_body']else default

def pair(node,key,default=None):
    rows=[p for p in node['ordered_statements']if p['kind']=='assignment'and p['key']==key]
    return [p['scalar']if p['scalar'].endswith('%')else float(p['scalar'])for p in rows[-1]['ordered_statements']if p['kind']=='atom']if rows else default

def native_metrics(definitions,tags):
    metrics={}
    for tag in tags:
        definition=definitions[tag]['tree'];base=definition
        visited=set()
        while not pair(base,'size')and not any(n['key']=='flowcontainer'for n in base['ordered_statements']):
            name=base['base'];require(name in definitions and name not in visited,'COMPONENT_BASE_UNRESOLVED:'+tag);visited.add(name);base=definitions[name]['tree']
        if tag.startswith('portrait'):
            size=pair(base,'size');require(size==[110.,120.],'COMPONENT_PORTRAIT_SIZE_UNEXPECTED')
            frame=next(n for n in walk_ast(definitions['widget_portrait_frame']['tree'])if scalar(n,'texture')=='gfx/portraits/portrait_rank.dds')
            metrics[tag]={'kind':'portrait','size':size,'basis':'DECLARED_NATIVE_SIZE','owner_id':base['node_id'],'background_color':pair(definitions['Background_Area_Solid']['tree'],'color'),'rank_frame':{'texture':scalar(frame,'texture'),'frame_size':pair(frame,'framesize'),'margins':[float(scalar(frame,k,'0'))for k in('margin_left','margin_top','margin_right','margin_bottom')]}}
        elif tag=='coa_house_small':
            body=next(n for n in walk_ast(base)if n['key']=='coa_house_widget');coa=next(n for n in body['ordered_statements']if n['key']=='coat_of_arms_icon')
            metrics[tag]={'kind':'house','size':pair(base,'size'),'basis':'DECLARED_NATIVE_SIZE','owner_id':base['node_id'],'body_size':pair(body,'size'),'coa_size':pair(coa,'size'),'frame_size':pair(definitions['coa_house_frame']['tree'],'framesize')}
        else:
            flow=next(n for n in base['ordered_statements']if n['key']=='flowcontainer');crown=next(n for n in flow['ordered_statements']if scalar(n,'name')=='crown')
            body=next(n for n in flow['ordered_statements']if n['key']=='widget'and any(c['key']=='coat_of_arms_icon'for c in n['ordered_statements']));coa=next(n for n in body['ordered_statements']if n['key']=='coat_of_arms_icon');frame=next(n for n in coa['ordered_statements']if n['key']=='coa_title_frame')
            crown_size=pair(crown,'framesize');body_size=pair(body,'size');space=float(scalar(flow,'spacing','0'));offset=next((pair(n,'position')for n in flow['ordered_statements']if n['kind']=='block'and n['name']=='position'),[0.,0.])
            metrics[tag]={'kind':'title_coa','size':[max(crown_size[0],body_size[0]),crown_size[1]+body_size[1]+space],'basis':'NATIVE_CHILD_FLOW_INTRINSIC_CANDIDATE','owner_id':base['node_id'],
               'crown':{'texture':scalar(crown,'texture'),'size':crown_size,'owner_id':crown['node_id']},'body_size':body_size,'coa_size':pair(coa,'size'),'frame_texture':scalar(frame,'texture'),'frame_size':pair(frame,'size'),
               'mask':scalar(coa,'coat_of_arms_mask'),'flow_offset':offset,'spacing':space}
    return metrics

def verify_contract(contract):
    require(contract['schema']=='guanchuang.native-component-contract.v1','COMPONENT_CONTRACT_SCHEMA')
    documents={}
    for name,record in contract['definitions'].items():
        cache=(record['path'],record['source'])
        if cache not in documents:
            raw=Path(record['path']).read_bytes();require(digest(raw)==record['sha256'],'COMPONENT_SOURCE_CONFLICT');documents[cache]=parse_bytes(raw,record['source'])
        doc=documents[cache];found=[n for n in doc.root.walk()if n.key==record['tree']['key']and n.name==name]
        require(len(found)==1 and found[0].to_dict()==record['tree'],'COMPONENT_DEFINITION_CONFLICT')
    require(native_metrics(contract['definitions'],contract['tags'])==contract['metrics'],'COMPONENT_METRICS_CONFLICT')

def apply_metrics(roots,contract,source_trees):
    verify_contract(contract);overrides={}
    for tree in source_trees:
        for node in walk_ast(tree):
            if node['key']not in contract['metrics']:continue
            block=next((p for p in node['ordered_statements']if p['kind']=='blockoverride'and p['name']=='position'),None)
            if block is not None:overrides[node['node_id']]={'flow_offset':pair(block,'position',[0.,0.])}
    for root in roots:
        for node in walk_scene(root):
            if node['tag']in contract['metrics']:
                metric=contract['metrics'][node['tag']];node['_component_size']=metric['size'];node['_component_basis']=metric['basis'];node['_component_override']=overrides.get(node['id'],{})

def _png(im):
    buf=io.BytesIO();im.save(buf,format='PNG');return base64.b64encode(buf.getvalue()).decode()

def _texture(path,virtual,mount):
    raw=Path(path).read_bytes()
    with Image.open(io.BytesIO(raw))as im:im=im.convert('RGBA')
    return {'source':{'path':str(path),'virtual_path':virtual,'mount':mount,'sha256':digest(raw)},'size':list(im.size),'png_base64':_png(im)}

def _sample_images(source,textures):
    path=Path(source['path']);raw=path.read_bytes();require(digest(raw)==source['sha256'],'COMPONENT_CAPTURE_SOURCE_CONFLICT');capture=Image.open(io.BytesIO(raw)).convert('RGBA');result={}
    for name,box in source['crops'].items():
        x,y,w,h=box;require(0<=x<x+w<=capture.width and 0<=y<y+h<=capture.height,'COMPONENT_CAPTURE_CROP_INVALID');sample=capture.crop((x,y,x+w,y+h))
        mask_name='gfx/portraits/portrait_mask_head.dds'if name=='portrait'else'gfx/interface/coat_of_arms/frames/house_frame_02_mask.dds'if name=='house'else'gfx/interface/coat_of_arms/title_mask.dds';mask=Image.open(io.BytesIO(base64.b64decode(textures[mask_name]['png_base64']))).convert('RGBA').getchannel('A').resize(sample.size,Image.Resampling.LANCZOS);sample.putalpha(ImageChops.multiply(sample.getchannel('A'),mask))
        result[name]={'size':list(sample.size),'png_base64':_png(sample),'origin':'HISTORICAL_NATIVE_CAPTURE_CROP_DISPLAY_SAMPLE_NOT_CURRENT_MOD_OR_CHARACTER','crop':box,'source_sha256':source['sha256']}
    return result

def build_components(index,main_preview,capture_path):
    nodes=[n for r in main_preview['roots']for n in walk_scene(r)];tags=sorted({n['tag']for n in nodes if n['tag'].startswith(('coa_','portrait'))});definitions={}
    def definition(name,origin,kinds=None,include_base=True):
        if name in definitions:return
        node,error=index.definition(name,origin,kinds or{'type'});require(error is None,'COMPONENT_TYPE_UNRESOLVED:'+name);definitions[name]={'source':node.source,'path':str(index.paths[node.source]),'sha256':index.document(node.source).sha256,'tree':node.to_dict()}
        if include_base and not pair(node.to_dict(),'size')and not any(n.key=='flowcontainer'for n in node.statements):definition(node.base,node.source)
    for tag in tags:definition(tag,'mod/'+main_preview['source'])
    for name in('widget_portrait_frame','coa_house_frame'):definition(name,'mod/'+main_preview['source'])
    definition('Background_Area_Solid','mod/'+main_preview['source'],{'template'},False)
    contract={'schema':'guanchuang.native-component-contract.v1','tags':tags,'definitions':definitions,'metrics':native_metrics(definitions,tags)};verify_contract(contract)
    textures={}
    def asset(relative):
        if relative in textures:return
        path,mount=index.asset(relative);require(path is not None,'COMPONENT_ASSET_MISSING:'+relative);textures[relative]=_texture(path,relative,mount)
    for metric in contract['metrics'].values():
        if metric['kind']=='title_coa':
            for name in(metric['crown']['texture'],metric['frame_texture'],metric['mask']):asset(name)
    for name in['gfx/portraits/portrait_mask_head.dds','gfx/portraits/portrait_rank.dds','gfx/interface/coat_of_arms/frames/house_frame_02.dds','gfx/interface/coat_of_arms/frames/house_frame_02_mask.dds','gfx/interface/icons/regimenttypes/_default.dds','gfx/interface/icons/faith/catholic.dds']:
        asset(name)
    for node in nodes:
        relative=node['props'].get('texture')
        if node['tag']=='icon'and isinstance(relative,str)and not relative.startswith('['):asset(relative)
    capture_path=Path(capture_path).resolve();source={'path':str(capture_path),'sha256':digest(capture_path.read_bytes()),'crops':{'portrait':[100,713,111,132],'coa':[677,501,52,60],'house':[677,501,52,60]},
       'origin':'R20 retained native no-Mod council frame, historical display samples only; not native reference for current Mod UI'}
    return {'schema':'guanchuang.native-components.v1','contract':contract,'textures':textures,'capture_source':source,'samples':_sample_images(source,textures),
       'dynamic_textures':{'[Regiment.GetMAAType.GetIcon]':'gfx/interface/icons/regimenttypes/_default.dds','[Faith.GetIcon]':'gfx/interface/icons/faith/catholic.dds'},
       'sample_frames':{'title_crown':4,'portrait_rank':4,'house_prestige':3},'scope':'Used source metrics/native raster frames; explicit historical image samples and demo frames/icons, no engine portrait/CoA generation or current-character/game-state claim. Intrinsic metrics/frame indexing/masks are source candidates, not independently calibrated native bounds.'}

def verify_components(registry):
    require(registry.get('schema')=='guanchuang.native-components.v1','COMPONENT_SCHEMA');verify_contract(registry['contract'])
    for name,texture in registry['textures'].items():
        ref=texture['source'];require(_texture(ref['path'],name,ref['mount'])==texture,'COMPONENT_TEXTURE_CONFLICT')
    require(_sample_images(registry['capture_source'],registry['textures'])==registry['samples'],'COMPONENT_IMAGE_SAMPLE_CONFLICT')
