"""Actual complete manager window, explicit display fixtures and source templates."""
import copy,json,re
from pathlib import Path
from core.syntax import parse_bytes
from editing.title import require,digest
from preview.templates import ScalarComposer,verify_records
from preview.scene import normalize,value

TABS=('overview','military','holder','territory')
ROW_TEMPLATES=('cmm40_regiment_row','cmm40_army_row','cmm40_title_row','cmm40_child_row','cmm40_county_row','cmm40_governor_row')

def walk(node):
    yield node
    for child in node['children']+node['item']:yield from walk(child)

def visual_expand(ast,templates,chain=()):
    node=copy.deepcopy(ast);rows=[]
    for item in node.get('ordered_statements',[]):
        if item['key']=='using'and item.get('scalar')in templates:
            name=item['scalar'];require(name not in chain,'MAIN_VISUAL_TEMPLATE_CYCLE');item['_visual_composed']=True;rows.append(item)
            for child in templates[name]['tree']['ordered_statements']:
                expanded=visual_expand(child,templates,chain+(name,));expanded['_visual_template_instance']=item['node_id'];rows.append(expanded)
        else:rows.append(visual_expand(item,templates,chain)if item['has_body']else item)
    node['ordered_statements']=rows;return node

def _fixture_text(raw,label,number,holder):
    """Explicit display-only filler. Never interpreted as a game binding result."""
    def item(m):
        expr=m[0]
        if 'GetMilitaryStrengthText'in expr:return '3,250'
        if 'BuildCurrentRegimentCountString'in expr:return '750 / 1,000'
        if 'GetTierAsNameNoTooltip'in expr:return '公国'
        if 'GetValue'in expr or'GetCount'in expr or'GetAge'in expr or'GetSkill'in expr or'GetProwess'in expr:return str(number)
        if 'GetName'in expr:
            if 'Character'in expr or'GetHolder'in expr:return '示例统领'
            if 'Regiment'in expr:return '示例兵团'
            if 'Army'in expr:return '示例军队'
            return label
        if 'Select_CString'in expr:
            strings=re.findall(r"'([^']*)'",expr)
            choices=[s for s in strings if re.search(r'[\u4e00-\u9fff]',s)]
            return (choices[0]if holder else choices[-1])if choices else'示例'
        return '示例'
    return re.sub(r'\[[^\]]*\]',item,raw)

def _profiles(root,list_preview,detail_preview):
    all_nodes=list(walk(root));grid_nodes=[n for n in all_nodes if n['props'].get('datamodel')]
    office=next(n for n in grid_nodes if "GetList('cmm23_view_offices')"in n['props']['datamodel']);profiles={}
    office_rows=list_preview['scenarios']['overflow']['rows'];labels={r['title_id']:r['bindings'][list_preview['contract']['texts'][0]['expression']]for r in office_rows}
    for selected in [None]+list(labels):
        original=detail_preview['profiles'].get(selected,{});holder=selected is not None and list(labels).index(selected)%3!=1;label=labels.get(selected,'无选择')
        selected_row=next((r for r in office_rows if r['title_id']==selected),None);display_values=list(selected_row['bindings'].values())if selected_row else[];kind='district'if any('军区'in text for text in display_values)else'camp';tier=next((text.split(' · ')[0]for text in display_values if' · 'in text),'公国');selected_object={'type':'Title','id':selected}if selected else None
        b={'GetVariableSystem.cmm23_page':'overview','GetVariableSystem.cmm40_detail_tab':'overview','GetVariableSystem.cmm40_coverage_view':'direct',"GetPlayer.MakeScope.Var('cmm23_open').IsSet":True,
           "GetPlayer.MakeScope.Var('cmm23_selected').Title.IsValid":selected is not None,"GetPlayer.MakeScope.Var('cmm23_selected').Title.Self":{'type':'Title','id':selected}if selected else None,
           "GetPlayer.MakeScope.Var('cmm23_selected').Title.GetNameNoTooltip":label,"GetPlayer.MakeScope.Var('cmm23_selected').Title.HasHolder":holder,"GetPlayer.MakeScope.Var('cmm23_map_open').IsSet":False,
           "IsGameViewOpen('title_view_window')":False,"IsGameViewOpen('find_title')":False,'Title.HasHolder':holder,'Title.GetHeir.IsValid':holder,'Title.Self':selected_object,'Title.GetTierAsNameNoTooltip':tier,"Title.MakeScope.Var('cmm23_kind').GetFlagName":kind,'Title.GetHolder.GetPrimaryTitle':selected_object}
        nodes=copy.deepcopy(original.get('node_values',{}));lists={}
        for grid in grid_nodes:
            if grid['id']==office['id']:
                records=[]
                for row in office_rows:
                    records.append({'row_id':row['row_id'],'title_id':row['title_id'],'bindings':{'Scope.Title':{'type':'Title','id':row['title_id']},'Title.Self':{'type':'Title','id':row['title_id']}},
                       'nodes':{f['owner_id']:{'text':row['bindings'][f['expression']]}for f in list_preview['contract']['texts']if f['expression']in row['bindings']}})
            else:
                records=[];legacy=original.get('lists',{}).get(grid['id'],[])
                count=(max(2,len(legacy))if selected else 0)
                if not holder and any(k in grid['props']['datamodel']for k in('personal','armies','holder_titles','governors','Traits')):count=0
                for i in range(count):
                    owned=copy.deepcopy(legacy[i%len(legacy)]['node_values'])if legacy else{}
                    context=' '.join(c['expression']for item in grid['item']for c in item['contexts']);match=re.search(r'\[Scope\.(Title|Char|Regiment|Army)\]',context);receiver=('Character'if match[1]=='Char'else match[1])if match else None
                    row_bindings={}
                    if receiver:
                        obj={'type':receiver,'id':str(selected)+':display:'+grid['id']+':'+str(i)};slot='Char'if receiver=='Character'else receiver
                        row_bindings={'Scope.'+slot:obj,receiver+'.Self':obj,receiver+'.IsValid':True}
                        if receiver=='Title':row_bindings.update({'Title.HasHolder':True,'Title.GetHeir.IsValid':True})
                        if receiver=='Regiment':row_bindings['Regiment.GetOriginProvince.IsValid']=True;row_bindings['Regiment.GetTotalCostString']='0.30'
                    for child in [c for r in grid['item']for c in walk(r)]:
                        raw=child['props'].get('raw_text',child['props'].get('text',''))
                        if isinstance(raw,str)and '['in raw and'text'not in owned.get(child['id'],{}):owned.setdefault(child['id'],{})['text']=_fixture_text(raw,'示例条目'+str(i+1),i+1,holder)
                        condition=child['props'].get('visible')
                        if condition:
                            resolved=value(condition,dict(b,**row_bindings))
                            owned.setdefault(child['id'],{})['visible']=resolved['value']if resolved['status']=='KNOWN'else owned.get(child['id'],{}).get('visible',False)
                    records.append({'row_id':str(selected)+':'+grid['id']+':'+str(i),'bindings':row_bindings,'nodes':owned})
            lists[grid['id']]=records;b['IsDataModelEmpty('+grid['props']['datamodel'][1:-1]+')']=not records
            counters={'cmm40_office_regiments':'cmm40_office_regiment_count','cmm40_personal_regiments':'cmm40_personal_regiment_count','cmm40_descendant_regiments':'cmm40_descendant_regiment_count','cmm40_armies':'cmm40_army_count','cmm40_direct':'cmm40_direct_count','cmm40_extent':'cmm40_extent_count','cmm40_children':'cmm40_child_count','cmm40_governors':'cmm40_governor_count','cmm40_holder_titles':'cmm40_holder_title_count'}
            list_name=re.search(r"GetList\('([^']+)'\)",grid['props']['datamodel'])
            if list_name and list_name[1]in counters:b["GetPlayer.MakeScope.Var('"+counters[list_name[1]]+"').GetValue"]=len(records)
        for node in all_nodes:
            p=node['props'];expr=p.get('visible')
            if expr and expr[1:-1].startswith('IsDataModelEmpty(')and expr[1:-1]in b:nodes.setdefault(node['id'],{})['visible']=b[expr[1:-1]]
            if expr and'visible'not in nodes.get(node['id'],{})and value(expr,b)['status']!='KNOWN':nodes.setdefault(node['id'],{})['visible']=False
            raw=p.get('raw_text',p.get('text',''))
            # Explicit mock strings for native keys whose values contain engine expressions.
            # These are owner display samples, never evaluated Character/Culture state.
            native_display={'CULTURE_LISTS_WINDOW':'示例文化','ADMIN_WINDOW_THEME_GOVERNOR_EFFICIENCY_VALUE':'73%'}
            if raw in native_display:nodes.setdefault(node['id'],{})['text']=native_display[raw]
            if isinstance(raw,str)and '['in raw and all(value(m[0],b)['status']=='KNOWN'for m in re.finditer(r'\[[^\]]*\]',raw)):nodes.get(node['id'],{}).pop('text',None)
            if isinstance(raw,str)and '['in raw and'text'not in nodes.get(node['id'],{})and node['id']not in{f['owner_id']for f in list_preview['contract']['texts']}and not all(value(m[0],b)['status']=='KNOWN'for m in re.finditer(r'\[[^\]]*\]',raw)):
                # These are explicitly authored example strings, not inferred facts.
                nodes.setdefault(node['id'],{})['text']=_fixture_text(raw,label,3,holder)
        content=next(n for n in all_nodes if n['props'].get('name')=='cmm40_detail_content')
        nodes.setdefault(content['id'],{})['bindings']={k:v for k,v in b.items()if k.startswith('Title.')};nodes[content['id']]['bindings']['Title.GetNameNoTooltip']=label
        profiles[selected or'__none__']={'origin':'SYNTHETIC_FRONTEND_DISPLAY_ONLY','bindings':b,'nodes':nodes,'lists':lists,'scrolls':{}}
    return profiles,office['id'],labels

def _assemble(raw,source,window,list_preview,detail_preview,templates,scalar_records=None,index=None,component_contract=None):
    doc=parse_bytes(raw,source);require(not doc.diagnostics,'MAIN_SOURCE_PARSE');roots=[n for n in doc.root.statements if n.key=='window'and n.value('name')==window];require(len(roots)==1,'MAIN_WINDOW_NOT_UNIQUE')
    tree=roots[0].to_dict();expanded=visual_expand(tree,templates);composer=ScalarComposer(index,scalar_records);root=normalize(composer.compose(expanded))
    if component_contract:
        from preview.components import apply_metrics
        apply_metrics([root],component_contract,[tree]+[t['tree']for t in templates.values()])
    profiles,office,labels=_profiles(root,list_preview,detail_preview)
    nodes=list(walk(root));tabs=[{'owner_id':n['id'],'value':m[1]}for n in nodes for c in n['callbacks']if(m:=re.fullmatch(r"\[GetVariableSystem.Set\('cmm40_detail_tab','([^']+)'\)\]",c['expression']or''))]
    return {'schema':'guanchuang.main-window.v1','source':source,'window':window,'source_sha256':digest(raw),'source_tree':tree,'roots':[root],'viewport':[1760,990],
       'visual_templates':templates,'scalar_records':list(composer.records.values()),'composition_issues':composer.issues,'profiles':profiles,'office_grid':office,'title_labels':labels,'tabs':tabs,
       'named_owners':{n['props']['name']:n['id']for n in nodes if n['props'].get('name')},'component_contract':component_contract,
       'scope':'Complete current manager authored window. Explicit display-only snapshots include illustrative owner strings/visibility; not game data/condition evaluation. Native inheritance/shaders/portrait/coa/font metrics remain visual gaps.'}

def build_preview(index,raw,source,window,list_preview,detail_preview):
    templates={}
    for name in ROW_TEMPLATES:
        node,error=index.definition(name,'mod/'+source,{'template','local_template'});require(error is None,'MAIN_ROW_TEMPLATE_MISSING:'+name)
        templates[name]={'source':node.source,'path':str(index.paths[node.source]),'sha256':index.document(node.source).sha256,'tree':node.to_dict()}
    return _assemble(raw,source,window,list_preview,detail_preview,templates,index=index)

def rebind_preview(raw,preview,list_preview,detail_preview):
    return _assemble(raw,preview['source'],preview['window'],list_preview,detail_preview,preview['visual_templates'],preview['scalar_records'],component_contract=preview.get('component_contract'))

def verify_preview(raw,preview,list_preview,detail_preview):
    verify_records(preview['scalar_records'])
    for name,ref in preview['visual_templates'].items():
        raw_ref=Path(ref['path']).read_bytes();require(digest(raw_ref)==ref['sha256'],'MAIN_TEMPLATE_SOURCE_CONFLICT');doc=parse_bytes(raw_ref,ref['source']);node=next((n for n in doc.root.walk()if n.name==name and n.key in('template','local_template')),None)
        require(node is not None and node.to_dict()==ref['tree'],'MAIN_TEMPLATE_REPRESENTATION_CONFLICT')
    require(rebind_preview(raw,preview,list_preview,detail_preview)==preview,'MAIN_SCENE_OR_FIXTURE_CONFLICT')

def snapshot(preview,selected='fixture-title-1',tab='overview',coverage='direct',scenario='overflow',scrolls=None):
    require(tab in TABS and coverage in('direct','all')and scenario in('empty','one','overflow'),'MAIN_VIEW_INVALID')
    if scenario=='empty':selected=None
    require(selected is None or selected in preview['title_labels'],'MAIN_SELECTED_PROFILE_UNKNOWN')
    result=copy.deepcopy(preview['profiles'][selected or'__none__']);result['bindings']['GetVariableSystem.cmm40_detail_tab']=tab;result['bindings']['GetVariableSystem.cmm40_coverage_view']=coverage;result['scrolls']=dict(scrolls or {})
    rows=result['lists'][preview['office_grid']]
    if scenario=='empty':result['lists'][preview['office_grid']]=[]
    elif scenario=='one':result['lists'][preview['office_grid']]=rows[:1]
    return result
