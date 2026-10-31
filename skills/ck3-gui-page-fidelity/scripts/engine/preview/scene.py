"""Reusable source-owned authored scene projection, with explicit uncertainty.

Reads ordered AST and explicit snapshot values. It never executes game bindings,
callbacks or native layout. Native type/style inheritance remains a separate gate.
"""
import math
import re
from core.state import split_args
from editing.title import require

PAIR_KEYS={'size','position','minimumsize','maximumsize','framesize','spriteborder','margin'}
VISUAL={'window','widget','vbox','hbox','flowcontainer','margin_widget','text_single','text_multi','textbox',
        'button','button_standard','button_standard_list','icon','background','expand','scrollbox','scrollarea',
        'fixedgridbox','dynamicgridbox','gridbox','overlappingitembox'}
TEXT={'text_single','text_multi','textbox'}


def known(value,basis='MODELED_SUBSET'):
    return {'status':'KNOWN','value':value,'basis':basis}


def value(expression,bindings):
    if expression is None:return {'status':'UNKNOWN','value':None,'basis':'MISSING_EXPRESSION'}
    expr=str(expression).strip()
    if expr.startswith('[')and expr.endswith(']'):expr=expr[1:-1].strip()
    if expr in bindings:
        v=bindings[expr]
        return known(v,'EXPLICIT_SNAPSHOT')if type(v)not in(int,float)or math.isfinite(v)else {'status':'INVALID','value':None,'basis':'NONFINITE_SNAPSHOT_VALUE'}
    if expr.endswith('|0'):
        r=value(expr[:-2],bindings)
        return known(str(round(r['value'])),'MODELED_FORMAT_0')if r['status']=='KNOWN'and type(r['value'])in(int,float)else r
    literals={'yes':True,'no':False,'true':True,'false':False}
    if expr in literals:return known(literals[expr],'LITERAL')
    if len(expr)>=2 and expr[0]==expr[-1]=="'":return known(expr[1:-1].replace("\\'","'"),'LITERAL')
    if re.fullmatch(r'-?\d+(?:\.\d+)?',expr):return known(float(expr),'LITERAL')
    m=re.fullmatch(r'(And|Or|Not|Select_CString|ObjectsEqual|EqualTo_CFixedPoint|GreaterThan_CFixedPoint|GreaterThanOrEqualTo_CFixedPoint|LessThan_CFixedPoint|LessThanOrEqualTo_CFixedPoint|GetVariableSystem.HasValue|GetVariableSystem.Exists)\((.*)\)',expr,re.S)
    if m:
        op,raw=m.groups();args=split_args(raw)
        arity=1 if op in('Not','GetVariableSystem.Exists')else 3 if op=='Select_CString'else 2
        if len(args)!=arity:return {'status':'INVALID','value':None,'basis':'MODELED_FUNCTION_ARITY'}
        if op.startswith('GetVariableSystem.'):
            name=value(args[0],bindings);key='GetVariableSystem.'+str(name['value'])
            if key in bindings:
                if op.endswith('Exists'):return known(bindings[key]is not None)
                expected=value(args[1],bindings)
                if expected['status']=='KNOWN':return known(bindings[key]==expected['value'])
        else:
            first=value(args[0],bindings)
            if op=='Select_CString':
                if first['status']=='KNOWN'and type(first['value'])is bool:return value(args[1]if first['value']else args[2],bindings)
            elif op=='Not':
                if first['status']=='KNOWN'and type(first['value'])is bool:return known(not first['value'])
            else:
                second=value(args[1],bindings);rows=[first,second]
                if op in('And','Or'):
                    vals=[r['value']if r['status']=='KNOWN'and type(r['value'])is bool else None for r in rows]
                    if op=='And'and False in vals:return known(False)
                    if op=='Or'and True in vals:return known(True)
                    if None not in vals:return known(all(vals)if op=='And'else any(vals))
                elif all(r['status']=='KNOWN'for r in rows):
                    a,b=first['value'],second['value']
                    if op=='ObjectsEqual':
                        if isinstance(a,dict)and isinstance(b,dict):return known((a.get('type'),a.get('id'))==(b.get('type'),b.get('id')))
                        return known(a==b)
                    try:
                        a=float(str(a).replace('(CFixedPoint)',''));b=float(str(b).replace('(CFixedPoint)',''))
                        return known({'EqualTo_CFixedPoint':a==b,'GreaterThan_CFixedPoint':a>b,'GreaterThanOrEqualTo_CFixedPoint':a>=b,'LessThan_CFixedPoint':a<b,'LessThanOrEqualTo_CFixedPoint':a<=b}[op])
                    except(ValueError,TypeError):pass
    return {'status':'UNKNOWN','value':None,'basis':'UNMODELED_OR_MISSING_SNAPSHOT','expression':expr}


def normalize(ast,inherited_contexts=()):
    statements=ast.get('ordered_statements',[]);props={};origins={};ordered=[];contexts=list(inherited_contexts);callbacks=[]
    explicit_size=any(p['key']=='size'and not p.get('_from_template')for p in statements)
    for p in statements:
        if p['kind']!='assignment':continue
        if not p['has_body']or p['key']in PAIR_KEYS:
            data=[a['scalar']for a in p['ordered_statements']if a['kind']=='atom']if p['has_body']else p['scalar']
            entry={'key':p['key'],'value':data,'owner_id':p['node_id']}
            if p.get('_from_template'):entry['template_origin']=p['_from_template'];entry['template_instance']=p['_template_instance']
            ordered.append(entry)
            if not(p['key']=='size'and p.get('_from_template')and explicit_size):props[p['key']]=data;origins[p['key']]=p['node_id']
        if p['key']=='datacontext':contexts.append({'owner_id':ast['node_id'],'expression':p['scalar']})
        if p['key'].startswith(('onclick','onrightclick')):callbacks.append({'key':p['key'],'expression':p['scalar'],'owner_id':p['node_id']})
    def children(rows):
        result=[]
        for p in rows:
            if p['kind']=='assignment'and p['has_body']and(p['key']in VISUAL or p['key'].startswith(('coa_','portrait','container_'))):result.append(normalize(p,contexts))
        return result
    kids=children(statements);item=[];issues=[]
    for p in statements:
        if p['kind']=='assignment'and p['key']=='item':item+=children(p['ordered_statements'])
    if ast['key']in('scrollbox','scrollarea'):
        blocks={p['name']:p for p in statements if p['kind']=='blockoverride'}
        if 'scrollbox_replace_vbox'in blocks:kids=children(blocks['scrollbox_replace_vbox']['ordered_statements'])
        elif 'scrollbox_content'in blocks:
            kids=children(blocks['scrollbox_content']['ordered_statements'])
            for p in blocks.get('scrollbox_margins',{}).get('ordered_statements',[]):
                if p['kind']=='assignment'and not p['has_body']:props[p['key']]=p['scalar'];origins[p['key']]=p['node_id']
        else:issues.append('SCROLL_CONTENT_NATIVE_INHERITANCE_UNRESOLVED')
    if any(p['key']=='using'and not(p.get('_scalar_composed')or p.get('_visual_composed'))for p in statements):issues.append('TYPE_TEMPLATE_STYLE_NOT_EXPANDED')
    return {'id':ast['node_id'],'tag':ast['key'],'source':ast.get('source'),'props':props,'property_owners':origins,
            'ordered_properties':ordered,'contexts':contexts,'callbacks':callbacks,'children':kids,'item':item,'issues':issues}


def intersect(a,b):
    x=max(a[0],b[0]);y=max(a[1],b[1]);right=min(a[0]+a[2],b[0]+b[2]);bottom=min(a[1]+a[3],b[1]+b[3])
    return [x,y,max(0,right-x),max(0,bottom-y)]


def context_bindings(node,bindings,nodes,extra=None):
    """Replace only recognized receiver slots, never the whole typed environment."""
    result=dict(bindings)
    for context in node['contexts']:
        if context['owner_id']!=node['id']:continue
        expr=context['expression']or'';receiver=None
        direct=re.fullmatch(r'\[Scope\.(Title|Story|Char|Regiment|Army)\]',expr)
        if direct:receiver='Character'if direct[1]=='Char'else direct[1]
        elif expr.endswith(('.GetHolder]','.GetHeir]','.Char]')):receiver='Character'
        elif expr.endswith('.Title]'):receiver='Title'
        elif expr.endswith('.Story]'):receiver='Story'
        if receiver:
            pattern=re.compile(r'(?<![A-Za-z0-9_.])'+receiver+r'\.')
            result={k:v for k,v in result.items()if not pattern.search(k)}
    result.update(nodes.get(node['id'],{}).get('bindings',{}))
    result.update(extra or {})
    return result


def project(roots,snapshot,viewport=(1760,990),resources=None):
    require(len(viewport)==2 and all(type(v)in(int,float)and math.isfinite(v)and 0<v<=16384 for v in viewport),'SCENE_VIEWPORT_INVALID')
    rows=[];windows=[];scrollboxes=[];global_bindings=snapshot.get('bindings',{});base_values=snapshot.get('nodes',{});datasets=snapshot.get('lists',{});offsets=snapshot.get('scrolls',{})
    require(all(isinstance(v,dict)for v in(global_bindings,base_values,datasets,offsets)),'SCENE_SNAPSHOT_TABLES_REQUIRED')
    metric_resource=(resources or{}).get('text_metrics',{});intrinsic=bool(metric_resource)and any(r['id']in metric_resource['root_ids']for r in roots)
    from preview.text_metrics import key as metric_key
    text_sizes={metric_key(e['text'],e['fontsize'],e['style']):e['size']for e in metric_resource.get('entries',[])}if intrinsic else{}
    def number(v,base=0):
        try:
            n=base*float(v[:-1])/100 if isinstance(v,str)and v.endswith('%')else float(v)
            return n if math.isfinite(n)else None
        except(TypeError,ValueError):return None
    def pair(n,key,available):
        data=n['props'].get(key,[]);return [number(data[i],available[i])if i<len(data)else None for i in range(2)]if isinstance(data,list)else[None,None]
    def condition(n,nodes,bindings,key='visible'):
        own=nodes.get(n['id'],{})
        if key in own:return known(own[key],'EXPLICIT_OWNER_SNAPSHOT')
        return value(n['props'][key],bindings)if key in n['props']else known(True,'NO_CONDITION')
    def margins(n,size):
        p=n['props'];raw=p.get('margin',[]);v=number(raw[0],size[1])if raw else 0;h=number(raw[1],size[0])if len(raw)>1 else 0
        return [(number(p.get(k),size[i%2])or 0)if k in p else(h if i%2==0 else v)or 0 for i,k in enumerate(['margin_left','margin_top','margin_right','margin_bottom'])]
    def measure(n,available,nodes,bindings,applied=False):
        if not applied:bindings=context_bindings(n,bindings,nodes)
        p=n['props'];dims=pair(n,'size',available);w=dims[0]if dims[0]is not None and dims[0]>0 else available[0]
        auto_size=None
        if intrinsic and n['tag']=='text_single'and p.get('autoresize',metric_resource['default_autoresize'])!='no':
            rendered,status=text(n,nodes,bindings);style='bold'if re.search(r'#(?:bold|b)\b',rendered)else'regular';auto_size=text_sizes.get(metric_key(rendered,number(p.get('fontsize'))or 15,style))
        if n.get('_component_size'):natural=n['_component_size']
        elif n['tag']=='background':natural=list(available)
        elif all(v is not None and v>0 for v in dims):natural=dims
        elif auto_size is not None:natural=auto_size
        elif p.get('datamodel'):
            records=datasets.get(n['id']);step=number(p.get('addrow'));column=number(p.get('addcolumn'))
            count=len(records)if records is not None else 1;cols=max(1,int(w//column))if column and column>0 else 1
            natural=[w,math.ceil(count/cols)*(step if step and step>0 else 24)]
        else:
            kids=[c for c in n['children']if condition(c,nodes,context_bindings(c,bindings,nodes))['value']is not False and c['tag']!='expand'];sizes=[measure(c,[w,available[1]],nodes,bindings)for c in kids];space=number(p.get('spacing'))or 0
            if n['tag']=='hbox':natural=[sum(s[0]for s in sizes)+max(0,len(sizes)-1)*space,max([s[1]for s in sizes]or[0])]
            elif n['tag']in('vbox','flowcontainer'):
                ml,mt,mr,mb=margins(n,[w,available[1]]);natural_width=max([s[0]for s in sizes]or[0])+ml+mr if intrinsic and p.get('layoutpolicy_horizontal')!='expanding'else w;natural=[natural_width,sum(s[1]for s in sizes)+max(0,len(sizes)-1)*space+mt+mb]
            elif n['tag']in TEXT or n['tag'].startswith('button'):natural=[w,number(p.get('fontsize'))or 24]
            else:natural=[w,max([((pair(c,'position',available)[1]or 0)+s[1])for c,s in zip(kids,sizes)]or[0])]
        result=[dims[i]if dims[i]is not None and dims[i]>0 else natural[i]for i in range(2)]
        for key,op in [('minimumsize',max),('maximumsize',min)]:
            bounds=pair(n,key,available)
            result=[op(result[i],bounds[i])if bounds[i]is not None and bounds[i]>=0 else result[i]for i in range(2)]
        return result
    def text(n,nodes,bindings):
        own=nodes.get(n['id'],{});p=n['props']
        if 'text'in own:return own['text'],'OWNER_SNAPSHOT'
        raw=p.get('raw_text',p.get('text',''))
        if not isinstance(raw,str):return '〔结构文本未知〕','UNKNOWN'
        missing=[];localized=False
        from adapters.localization import resolve_key
        from adapters.native_localization import combined_entries
        entries=combined_entries(resources or {})
        if 'raw_text'not in p and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]+',raw):
            loc=resolve_key(raw,entries);raw=loc['text'];localized=True
            if loc['status']!='KNOWN':missing.append('localization')
        if '$'in raw:
            def macro(m):
                result=resolve_key(m[1],entries)
                if result['status']!='KNOWN':missing.append('localization')
                return result['text']
            raw=re.sub(r'\$([^$]+)\$',macro,raw);localized=True
        def substitute(m):
            concept=re.fullmatch(r'\[([A-Za-z_][A-Za-z0-9_]*)\|E\]',m[0])
            if concept:
                resolved=resolve_key('game_concept_'+concept[1],entries)
                if resolved['status']!='KNOWN':missing.append(m[0])
                return resolved['text']
            r=value(m.group(),bindings)
            if r['status']=='KNOWN'and isinstance(r['value'],(str,int,float))and type(r['value'])is not bool:
                v=r['value'];return str(int(v))if type(v)is float and v.is_integer()else str(v)
            missing.append(m.group());return '〔未知绑定〕'
        concept_only=re.fullmatch(r'\[([A-Za-z_][A-Za-z0-9_]*)\|E\]',raw)is not None
        result=re.sub(r'\[[^\]]*\]',substitute,raw)
        if '$'in result:return '〔本地化未知：'+result+'〕','UNKNOWN'
        return result,'UNKNOWN_PARTIAL'if missing else'CONCEPT_LOCALIZATION_SUBSET'if concept_only else'LOCALIZATION_SUBSET'if localized else'SNAPSHOT_SUBSET'if '['in raw else'STATIC_LITERAL'
    def arrange(n,region,nodes,bindings,path,window,clip,conditional=False,flow=False,assigned=None,extra=None):
        bindings=context_bindings(n,bindings,nodes,extra)
        visible=condition(n,nodes,bindings)
        if visible['value']is False:return
        p=n['props'];x,y,aw,ah=region;w,h=assigned or measure(n,[aw,ah],nodes,bindings,True)
        if assigned is None:
            if p.get('layoutpolicy_horizontal')=='expanding':w=aw
            if p.get('layoutpolicy_vertical')=='expanding':h=ah
        if not flow:
            anchor=str(p.get('parentanchor','top|left'));widget=str(p.get('widgetanchor',anchor))
            def factor(s,axis):
                parts=s.split('|');return .5 if 'center'in parts or('hcenter'if axis==0 else'vcenter')in parts else 1 if('right'if axis==0 else'bottom')in parts else 0
            x+=factor(anchor,0)*aw-factor(widget,0)*w;y+=factor(anchor,1)*ah-factor(widget,1)*h
            pos=pair(n,'position',[aw,ah]);x+=pos[0]or 0;y+=pos[1]or 0
        rect=[x,y,w,h];content=margins(n,[w,h])if n['tag']in('hbox','vbox','flowcontainer','scrollbox','scrollarea','margin_widget')else[0,0,0,0];ml,mt,mr,mb=content
        txt,status=text(n,nodes,bindings);row={'owner_id':n['id'],'instance_id':path,'window':window,'tag':n['tag'],'name':p.get('name'),
          'rect':rect,'clip':intersect(rect,clip),'clip_limit':clip,'text':txt,'text_status':status,'visibility':visible,
          'enabled':condition(n,nodes,bindings,'enabled'),'down':condition(n,nodes,bindings,'down')if'down'in p else known(False,'NO_DOWN_CONDITION'),'conditional':conditional or visible['status']!='KNOWN','callbacks':n['callbacks'],'contexts':n['contexts'],
          'fontsize':number(p.get('fontsize'))or 15,'font_basis':'EXPLICIT'if p.get('fontsize')else'UNRESOLVED_FALLBACK',
          'geometry_basis':'AUTHORED_CANDIDATE'if p.get('size')else n.get('_component_basis','INHERITED_SIZE_UNRESOLVED_CANDIDATE'),'issues':list(n['issues'])}
        if n.get('_component_size'):row['component_override']=n.get('_component_override',{})
        rows.append(row);inner=[x+ml,y+mt,max(0,w-ml-mr),max(0,h-mt-mb)];flag=row['conditional']
        if p.get('datamodel'):
            records=datasets.get(n['id']);row['list_status']='SNAPSHOT'if records is not None else'UNKNOWN'
            step=number(p.get('addrow'));column=number(p.get('addcolumn'))
            if not step or not column:row['issues'].append('GRID_METRICS_UNRESOLVED');return
            if records is None:return
            require(isinstance(records,list)and len(records)<=10000,'SCENE_DATASET_INVALID')
            if records and not n['item']:row['issues'].append('DATAMODEL_ITEM_TEMPLATE_UNRESOLVED')
            cols=max(1,int(w//column));seen=set()
            for i,record in enumerate(records):
                require(isinstance(record.get('row_id'),str)and record['row_id']not in seen,'SCENE_ROW_ID_NOT_UNIQUE');seen.add(record['row_id'])
                rn=record.get('nodes',{})
                for k,child in enumerate(n['item']):arrange(child,[x+i%cols*column,y+i//cols*step,column,step],rn,bindings,path+'/row:'+record['row_id']+'/'+str(k),window,clip,flag,extra=record.get('bindings',{}))
            return
        if n['tag']in('scrollbox','scrollarea'):
            natural=max([measure(c,inner[2:],nodes,bindings)[1]for c in n['children']]or[0]);maximum=max(0,natural-inner[3]);requested=offsets.get(n['id'],0)
            require(type(requested)in(int,float)and math.isfinite(requested),'SCENE_SCROLL_NOT_FINITE');offset=min(max(0,requested),maximum)
            row['scroll']={'offset':offset,'maximum':maximum,'natural_height':natural};scrollboxes.append({'owner_id':n['id'],'instance_id':path,'window':window,'viewport':inner,'offset':offset,'maximum':maximum})
            for i,child in enumerate(n['children']):arrange(child,[inner[0],inner[1]-offset,inner[2],max(inner[3],natural)],nodes,bindings,path+'/'+str(i),window,intersect(inner,clip),flag)
            return
        kids=[c for c in n['children']if condition(c,nodes,context_bindings(c,bindings,nodes))['value']is not False]
        if n['tag']not in('hbox','vbox','flowcontainer'):
            for i,c in enumerate(kids):arrange(c,inner,nodes,bindings,path+'/'+str(i),window,clip,flag)
            return
        axis=0 if n['tag']=='hbox'else 1;space=number(p.get('spacing'))or 0;sizes=[measure(c,inner[2:],nodes,bindings)for c in kids]
        expand=[i for i,c in enumerate(kids)if c['tag']=='expand'or c['props'].get('layoutpolicy_horizontal'if axis==0 else'layoutpolicy_vertical')=='expanding']
        free=max(0,inner[axis+2]-sum(s[axis]for i,s in enumerate(sizes)if i not in expand)-max(0,len(kids)-1)*space);cursor=0
        for i,c in enumerate(kids):
            size=sizes[i][:]
            if i in expand:size[axis]=free/len(expand)
            if c['props'].get('layoutpolicy_vertical'if axis==0 else'layoutpolicy_horizontal')=='expanding':size[1-axis]=inner[3-axis]
            origin=[inner[0]+(cursor if axis==0 else 0),inner[1]+(cursor if axis==1 else 0),*size]
            arrange(c,origin,nodes,bindings,path+'/'+str(i),window,clip,flag,True,size);cursor+=size[axis]+space
    for i,root in enumerate(roots):
        visible=condition(root,base_values,global_bindings)
        before=len(rows);arrange(root,[0,0,*viewport],base_values,global_bindings,'root:'+str(i),root['id'],[0,0,*viewport])
        windows.append({'owner_id':root['id'],'name':root['props'].get('name'),'visibility':visible,'rect':rows[before]['rect']if len(rows)>before else None})
    return {'schema':'guanchuang.authored-scene.v1','basis':'SOURCE_AUTHORED_CANDIDATE_NOT_NATIVE_RENDER','viewport':list(viewport),'windows':windows,'rows':rows,'scrollboxes':scrollboxes}


def hit_test(scene,x,y):
    require(all(type(v)in(int,float)and math.isfinite(v)for v in(x,y)),'SCENE_POINT_INVALID')
    def inside(rect):return rect and rect[0]<=x<rect[0]+rect[2]and rect[1]<=y<rect[1]+rect[3]
    for window in reversed(scene['windows']):
        if not inside(window['rect']):continue
        for row in reversed(scene['rows']):
            if row['window']==window['owner_id']and row['callbacks']and inside(row['clip']):return row
        return None
    return None
