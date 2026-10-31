"""Source-owned detail projection. Every sample value belongs to a concrete owner.

This is an authored-geometry candidate, not a CK3 expression interpreter or renderer.
"""
import copy
import math
import re
from pathlib import Path

from core.state import evaluate
from core.syntax import parse_bytes
from editing.title import digest, require, _pair
from preview.office_list import one

VISUAL = {'widget','vbox','hbox','text_single','text_multi','button','button_standard','button_standard_list',
          'icon','background','expand','scrollbox','fixedgridbox','dynamicgridbox','overlappingitembox','flowcontainer'}
PROPERTIES = {'size','position','minimumsize','maximumsize','spriteborder','framesize'}


def walk(node, items=False):
    yield node
    for child in node['children']:
        yield from walk(child, items)
    if items:
        for child in node.get('item', []):
            yield from walk(child, items)


def export_template_node(n,contexts=()):
    chain=list(contexts)+[{'owner_id':n.node_id,'expression':x.scalar}for x in n.occurrences('datacontext')]
    return {'id':n.node_id,'source':n.source,'line':n.source_span['start']['line'],'tag':n.key,
      'props':{p.key:p.atoms()if p.has_body else p.scalar for p in n.statements if p.kind=='assignment'and(not p.has_body or p.key in PROPERTIES)},
      'contexts':chain,'callbacks':[{'key':p.key,'expression':p.scalar}for p in n.statements if p.key.startswith(('onclick','onrightclick'))],
      'ordered_properties':[{'key':p.key,'value':p.atoms()if p.has_body and p.key in PROPERTIES else p.scalar,'body_owner':p.node_id if p.has_body else None}for p in n.statements if p.kind=='assignment'],
      'children':[export_template_node(p,chain)for p in n.statements if p.kind=='assignment'and p.has_body and(p.key in VISUAL or p.key.startswith(('coa_','portrait')))],'item':[]}


def bind_detail(raw, source, window, templates=None):
    templates = templates or {}
    doc = parse_bytes(raw, source)
    root = one([n for n in doc.root.statements if n.key=='window' and n.value('name')==window], 'WINDOW_NOT_UNIQUE')
    def named(name):return one([n for n in root.walk()if n.value('name')==name], 'DETAIL_OWNER_NOT_UNIQUE:'+name)
    pane=named('cmm40_detail_pane');content=named('cmm40_detail_content');empty=named('cmm40_no_selection')
    def subtree(n):return digest(raw[doc.byte_offsets[n.start]:doc.byte_offsets[n.end]])
    def convert(n, contexts=(), stack=()):
        chain=list(contexts)+[{'owner_id':n.node_id,'expression':p.scalar}for p in n.occurrences('datacontext')]
        props={p.key:p.atoms()if p.has_body else p.scalar for p in n.statements if p.kind=='assignment' and(not p.has_body or p.key in PROPERTIES)}
        tree={'id':n.node_id,'source':n.source,'line':n.source_span['start']['line'],'tag':n.key,'props':props,
              'contexts':chain,'callbacks':[{'key':p.key,'expression':p.scalar}for p in n.statements if p.key.startswith(('onclick','onrightclick','on_start'))],
              'ordered_properties':[{'key':p.key,'value':p.atoms()if p.has_body and p.key in PROPERTIES else p.scalar,
                                     'body_owner':p.node_id if p.has_body else None}for p in n.statements if p.kind=='assignment'],
              'children':[],'item':[]}
        def children(rows,destination):
            for child in rows:
                if child.kind=='assignment' and child.has_body and(child.key in VISUAL or child.key.startswith(('coa_','portrait','container_'))):
                    destination.append(convert(child,chain,stack))
                elif child.kind=='assignment' and child.key=='using' and child.scalar in templates:
                    require(child.scalar not in stack,'DETAIL_TEMPLATE_CYCLE')
                    for value in copy.deepcopy(templates[child.scalar]['children']):
                        for member in walk(value,True):member['contexts']=chain+member['contexts']
                        destination.append(value)
                elif child.kind=='blockoverride' and child.name=='scrollbox_replace_vbox':
                    children(child.statements,destination)
        children(n.statements,tree['children'])
        for item in n.occurrences('item'):children(item.statements,tree['item'])
        return tree
    summary=convert(named('cmm40_summary'));tabs=convert(named('cmm40_detail_tabs'));body=convert(content);actions=convert(named('cmm40_actions'))
    scroll=named('cmm40_detail_scroll')
    tab_rows=[]
    for n in tabs['children']:
        calls=[r['expression']for r in n['callbacks']if r['key']=='onclick']
        require(len(calls)==1,'DETAIL_TAB_CALLBACK_NOT_UNIQUE')
        match=re.fullmatch(r"\[GetVariableSystem.Set\('cmm40_detail_tab','(overview|military|holder|territory)'\)\]",calls[0])
        require(match is not None,'DETAIL_TAB_COMMAND_UNSUPPORTED')
        tab_rows.append({'value':match[1],'label':n['props'].get('raw_text'),'owner_id':n['id'],'down':n['props'].get('down'),'callbacks':calls,
                         'size':[float(v)for v in n['props']['size']]})
    require(len(tab_rows)==4,'DETAIL_FOUR_TABS_REQUIRED')
    return {'schema':'guanchuang.detail-contract.v1','source':source,'window':window,'source_sha256':digest(raw),
        'subtree_hashes':{'pane':subtree(pane),'empty':subtree(empty)},'owner_id':pane.node_id,
        'selection_visible':pane.value('visible'),'selected_contexts':[p.scalar for p in content.occurrences('datacontext')],
        'geometry':{'pane':_pair(pane,'size'),'summary':_pair(named('cmm40_summary'),'size'),
           'tabs':_pair(named('cmm40_detail_tabs'),'size'),'scroll':_pair(scroll,'size'),'actions':_pair(named('cmm40_actions'),'size'),
           'spacing':float(pane.value('spacing','0'))},
        'tabs':tab_rows,'tab_spacing':float(named('cmm40_detail_tabs').value('spacing','0')),
        'summary':summary,'content':body,'actions':actions,'empty':convert(empty),
        'basis':'SOURCE_AUTHORED_LAYOUT_CANDIDATE; native style/fonts/flow inheritance unaccepted',
        'unknown_policy':'Owner/row values absent => UNKNOWN; no cross-owner expression fallback; unknown visibility explicitly marked'}


def build_detail(index, raw, source, window, list_preview):
    templates={};used=[]
    # Expand only the Mod's actual overview row templates. Native style remains explicit unknown.
    for name in ['cmm40_regiment_row','cmm40_army_row','cmm40_title_row','cmm40_child_row','cmm40_county_row','cmm40_governor_row']:
        definition,error=index.definition(name,'mod/'+source,{'template','local_template'})
        require(error is None,'DETAIL_TEMPLATE_UNRESOLVED:'+name)
        used.append(definition.source)
        templates[name]={'source':definition.source,'children':[]}
        # Reuse the same ownership-preserving converter through a small source wrapper.
        doc=index.document(definition.source)
        templates[name]['raw']=doc.text[definition.start:definition.end]
    for name,t in templates.items():
        definition,_=index.definition(name,'mod/'+source,{'template','local_template'})
        t['children']=[export_template_node(n)for n in definition.statements if n.has_body and n.key in VISUAL]
        t.pop('raw')
    contract=bind_detail(raw,source,window,templates)
    reference={'files':[{'path':str(index.paths[p]),'qualified':p,'sha256':index.document(p).sha256}for p in sorted(set(used))],
               'status':'MOD_TEMPLATE_SOURCE_READ_ONLY; native styles not expanded'}
    return {'contract':contract,'templates':templates,'profiles':make_profiles(contract,list_preview),'reference':reference}


def make_profiles(contract,list_preview):
    records=list_preview['scenarios']['overflow']['rows'];profiles={}
    root_nodes=[n for part in ['summary','content','actions']for n in walk(contract[part])]
    grids=[n for n in root_nodes if n['props'].get('datamodel')]
    for i,row in enumerate(records):
        name=row['bindings'][list_preview['contract']['texts'][0]['expression']];holder=i%3!=1
        profile={'schema':'guanchuang.detail-profile.v1','origin':'SYNTHETIC_OWNER_FIXTURE_NOT_GAME_DATA','title_id':row['title_id'],
                 'node_values':{},'lists':{}}
        def values(nodes, sample_name, has_holder, number, is_row=False):
            result={}
            for node in nodes:
                p=node['props'];record={};raw=p.get('raw_text',p.get('text',''));expr=p.get('visible')
                if expr:
                    if expr in ["[Title.HasHolder]","[GetPlayer.MakeScope.Var('cmm23_selected').Title.HasHolder]"]:record['visible']=has_holder
                    elif expr in ["[Not(Title.HasHolder)]","[Not(GetPlayer.MakeScope.Var('cmm23_selected').Title.HasHolder)]"]:record['visible']=not has_holder
                    elif expr=='[Title.GetHeir.IsValid]':record['visible']=has_holder
                    elif expr=='[Not(Title.GetHeir.IsValid)]':record['visible']=not has_holder
                    elif expr in ['[Regiment.IsValid]','[Regiment.GetOriginProvince.IsValid]']:record['visible']=True
                    elif expr=='[Not(Regiment.GetOriginProvince.IsValid)]':record['visible']=False
                if isinstance(raw,str)and '['in raw:
                    context=' '.join(c['expression']for c in node['contexts'])
                    def replace(match):
                        expression=match.group(0)
                        if expression in ['[Title.GetNameNoTooltip]',"[GetPlayer.MakeScope.Var('cmm23_selected').Title.GetNameNoTooltip]",'[Regiment.GetNameNoTooltip]','[Army.GetNameNoTooltip]']:return sample_name
                        if expression=='[Character.GetNameNoTooltip]':return ('示例继承人'if'Title.GetHeir'in context else '示例统领')+str(number)
                        if expression=='[Title.GetTierAsNameNoTooltip]':return '公国'
                        if re.fullmatch(r"\[GetPlayer.MakeScope.Var\('cmm40_[a-z_]+count'\).GetValue\|0\]",expression):return str(number)
                        if expression=='[Regiment.BuildCurrentRegimentCountString]':return '1000 / 1000'
                        return expression
                    rendered=re.sub(r'\[[^\]]*\]',replace,raw)
                    if '['not in rendered:record['text']=rendered
                    if raw.startswith('统领：')and has_holder:record['text']='统领：示例统领'+str(number)+' · 个人总兵力：'+str(number*1000)
                if record:result[node['id']]=record
            return result
        profile['node_values']=values(root_nodes,name,holder,i+1)
        for j,grid in enumerate(grids):
            expression=grid['props']['datamodel'];count=(i+j)%3
            if not holder and any(k in expression for k in ['personal','armies','holder_titles','governors','Traits']):count=0
            items=[]
            for k in range(count):
                nodes=[n for item in grid['item']for n in walk(item)]
                label=name+' · 示例条目'+str(k+1)
                items.append({'row_id':row['title_id']+':'+grid['id']+':'+str(k),'node_values':values(nodes,label,True,k+1,True)})
            profile['lists'][grid['id']]=items
        for node in root_nodes:
            expression=node['props'].get('visible','')
            for grid in grids:
                expected='[IsDataModelEmpty('+grid['props']['datamodel'].strip('[]')+')]'
                if expression==expected:profile['node_values'].setdefault(node['id'],{})['visible']=not profile['lists'][grid['id']]
        profiles[row['title_id']]=profile
    return profiles


def verify_detail_reference(reference,templates=None):
    documents={}
    for item in reference['files']:
        require(digest(Path(item['path']).read_bytes())==item['sha256'],'DETAIL_DEPENDENCY_CONFLICT')
        if templates is not None:documents[item['qualified']]=parse_bytes(Path(item['path']).read_bytes(),item['qualified'])
    if templates is not None:
        for name,template in templates.items():
            require(template['source']in documents,'DETAIL_TEMPLATE_SOURCE_CONFLICT')
            definition=one([n for n in documents[template['source']].root.walk()if n.key in('template','local_template')and n.name==name],
                           'DETAIL_TEMPLATE_OWNER_NOT_UNIQUE')
            expected=[export_template_node(n)for n in definition.statements if n.has_body and n.key in VISUAL]
            require(expected==template['children'],'DETAIL_TEMPLATE_REPRESENTATION_CONFLICT')


def validate_profile(profile,title_id):
    require(isinstance(profile,dict)and profile.get('schema')=='guanchuang.detail-profile.v1'and profile.get('origin')=='SYNTHETIC_OWNER_FIXTURE_NOT_GAME_DATA','DETAIL_PROFILE_SCHEMA')
    require(profile.get('title_id')==title_id,'DETAIL_PROFILE_TITLE_CONFLICT')
    require(isinstance(profile.get('node_values'),dict)and isinstance(profile.get('lists'),dict),'DETAIL_OWNER_VALUES_REQUIRED')
    sets=[profile['node_values']]
    for rows in profile['lists'].values():
        require(isinstance(rows,list)and len(rows)<=10000,'DETAIL_LIST_ROWS_INVALID')
        require(all(isinstance(r,dict)and isinstance(r.get('node_values'),dict)for r in rows),'DETAIL_OWNER_VALUES_REQUIRED')
        ids=[r.get('row_id')for r in rows];require(all(isinstance(v,str)and v for v in ids)and len(ids)==len(set(ids)),'DETAIL_ROW_ID_NOT_UNIQUE')
        sets.extend(r['node_values']for r in rows)
    for values in sets:
        require(isinstance(values,dict),'DETAIL_OWNER_VALUES_REQUIRED')
        for record in values.values():
            require(isinstance(record,dict)and set(record)<={'text','visible','enabled'},'DETAIL_VALUE_UNSUPPORTED')
            require(all(isinstance(v,str)if k=='text'else type(v)is bool for k,v in record.items()),'DETAIL_VALUE_TYPE')


def project(preview,title_id,tab='overview',coverage='direct',scroll=0):
    c=preview['contract'];require(tab in [t['value']for t in c['tabs']]and coverage in ['direct','all'],'DETAIL_TAB_UNSUPPORTED')
    require(title_id is None or isinstance(title_id,str),'DETAIL_SELECTED_ID_INVALID')
    require(type(scroll)in(int,float)and math.isfinite(scroll),'DETAIL_SCROLL_NOT_FINITE')
    if title_id is None:return {'status':'NO_SELECTION','title_id':None,'rows':[],'max_scroll':0,'scroll':0,'empty':c['empty']}
    if title_id not in preview['profiles']:return {'status':'UNKNOWN_SELECTION_SNAPSHOT','title_id':title_id,'rows':[],'max_scroll':0,'scroll':0}
    profile=preview['profiles'][title_id];validate_profile(profile,title_id)
    bindings={'GetVariableSystem.cmm40_detail_tab':tab,'GetVariableSystem.cmm40_coverage_view':coverage}
    rows=[]
    def number(v,base=0):
        try:return base*float(v[:-1])/100 if isinstance(v,str)and v.endswith('%')else float(v)
        except(ValueError,TypeError):return None
    def pair(n,key,available):
        value=n['props'].get(key,[]);return [number(value[i],available[i])if i<len(value)else None for i in range(2)]if isinstance(value,list)else[None,None]
    def condition(n,values,key='visible'):
        owned=values.get(n['id'],{})
        if key in owned:return {'status':'KNOWN','value':owned[key],'basis':'EXPLICIT_OWNER_FIXTURE'}
        return evaluate(n['props'].get(key),bindings)
    def text(n,values):
        p=n['props'];raw=p.get('raw_text',p.get('text',''));owned=values.get(n['id'],{})
        if 'text'in owned:return owned['text'],'OWNER_FIXTURE'
        if not isinstance(raw,str)or '['in raw or '$'in raw:return '〔未提供此控件的绑定值〕','UNKNOWN'
        if p.get('text')and re.fullmatch(r'[A-Z][A-Z0-9_]+',raw):return '〔未解析本地化：'+raw+'〕','UNKNOWN'
        return raw,'STATIC_LITERAL'
    def measure(n,width,values):
        p=n['props'];dims=pair(n,'size',[width,0]);w=dims[0]if dims[0]is not None and dims[0]>0 else width
        if p.get('datamodel'):
            items=profile['lists'].get(n['id']);return [w,(len(items)if items is not None else 1)*(number(p.get('addrow'))or 50)]
        if dims[1]is not None and dims[1]>0:return[w,dims[1]]
        children=[x for x in n['children']if condition(x,values).get('value')is not False and x['tag']!='expand']
        sizes=[measure(x,w,values)for x in children];spacing=number(p.get('spacing'))or 0
        if n['tag']=='hbox':return[w,max([s[1]for s in sizes]or[0])]
        if n['tag']in['vbox','flowcontainer']:return[w,sum(s[1]for s in sizes)+max(0,len(sizes)-1)*spacing+(number(p.get('margin_top'))or 0)+(number(p.get('margin_bottom'))or 0)]
        if n['tag'].startswith(('text','button')):return[w,number(p.get('fontsize'))or 24]
        return[w,max([s[1]for s in sizes]or[0])]
    def arrange(n,x,y,width,values,path,clip=None,conditional=False):
        visible=condition(n,values)
        if visible.get('value')is False:return
        p=n['props'];w,h=measure(n,width,values);position=pair(n,'position',[width,h]);x+=position[0]or 0;y+=position[1]or 0
        value,status=text(n,values);rows.append({'owner_id':n['id'],'instance_id':path,'tag':n['tag'],'name':p.get('name'),
          'rect':[x,y,w,h],'text':value,'text_status':status,'visibility':visible,'enabled':condition(n,values,'enabled'),
          'contexts':n['contexts'],'callbacks':n['callbacks'],'clip':clip,'conditional':conditional or visible['status']!='KNOWN',
          'geometry_status':'AUTHORED_CANDIDATE'if p.get('size')else'INHERITED_SIZE_UNMODELED_CANDIDATE',
          'fontsize':number(p.get('fontsize'))or 15,
          'font_basis':'EXPLICIT'if p.get('fontsize')else'FALLBACK_NOT_RESOLVED','elide':p.get('elide')})
        if p.get('datamodel'):
            records=profile['lists'].get(n['id'])
            if records is None:rows[-1]['list_status']='UNKNOWN';return
            rows[-1]['list_status']='FIXTURE';step=number(p.get('addrow'))or 50
            for i,record in enumerate(records):
                for child in n['item']:arrange(child,x,y+i*step,w,record['node_values'],path+'/'+record['row_id'],clip,conditional or visible['status']!='KNOWN')
            return
        cursor=0;spacing=number(p.get('spacing'))or 0;ml=number(p.get('margin_left'))or 0;mt=number(p.get('margin_top'))or 0
        children=[child for child in n['children']if child['tag']!='expand'and condition(child,values).get('value')is not False]
        for i,child in enumerate(children):
            if n['tag']in['vbox','hbox','flowcontainer']:
                horizontal=n['tag']=='hbox';cw,ch=measure(child,max(0,w-ml),values)
                arrange(child,x+ml+(cursor if horizontal else 0),y+mt+(0 if horizontal else cursor),cw,values,path+'/'+str(i),clip,conditional or visible['status']!='KNOWN')
                cursor+=(cw if horizontal else ch)+spacing
            else:arrange(child,x,y,w,values,path+'/'+str(i),clip,conditional or visible['status']!='KNOWN')
    g=c['geometry'];spacing=g['spacing'];summary_y=0;tabs_y=g['summary'][1]+spacing;content_y=tabs_y+g['tabs'][1]+spacing
    actions_y=content_y+g['scroll'][1]+spacing
    natural=measure(c['content'],g['scroll'][0],profile['node_values'])[1];maximum=max(0,natural-g['scroll'][1]);offset=min(max(0,scroll),maximum)
    arrange(c['summary'],0,summary_y,g['summary'][0],profile['node_values'],'summary')
    arrange(c['content'],0,content_y-offset,g['scroll'][0],profile['node_values'],'content',[0,content_y,*g['scroll']])
    arrange(c['actions'],0,actions_y,g['actions'][0],profile['node_values'],'actions')
    return {'status':'FIXTURE_DETAIL','title_id':title_id,'tab':tab,'coverage':coverage,'pane_size':g['pane'],
      'rows':rows,'tabs':dict(y=tabs_y,items=c['tabs']),'content_viewport':[0,content_y,*g['scroll']],
      'content_natural_height':natural,'max_scroll':maximum,'scroll':offset,'basis':c['basis']}
