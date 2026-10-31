"""M05 adapter for the shared authored scene. All object values are synthetic."""
import copy
import json
import re

from editing.title import require,digest,TitleEditError
from preview.allocation import build_allocation,verify_sources,scenario,transition,validate,state_bindings,KINDS,identity
from preview.scene import normalize,project


def ast_walk(node):
    yield node
    for child in node.get('ordered_statements',[]):yield from ast_walk(child)


def scene_walk(node):
    yield node
    for child in node['children']+node['item']:yield from scene_walk(child)


def refine_state(contract,state,count=3,_known_identity=None):
    require(type(count)is int and 0<=count<=100,'ALLOCATION_SAMPLE_COUNT_INVALID')
    result=copy.deepcopy(state)
    kinds=[]
    for entry in contract['effects'].values():
        for node in ast_walk(entry['tree']):
            if node['key']=='set_variable':
                props={n['key']:n['scalar']for n in node['ordered_statements']if n['kind']=='assignment'and not n['has_body']}
                if props.get('name')=='cmm26_kind'and(props.get('value')or'').startswith('flag:'):kinds.append(props['value'][5:])
    kinds=list(dict.fromkeys(kinds))or['fixture-other','group','member']
    if 'office'in kinds:kinds=['office']+[x for x in kinds if x!='office']
    for grid in contract['gui']['grids']:
        source_row=next(n for w in contract['gui']['windows']for n in ast_walk(w['tree'])if n['node_id']==grid['row_owner'])
        row_expressions=[n['scalar']or''for n in ast_walk(source_row)]
        read_kinds=list(dict.fromkeys(flag for expr in row_expressions for flag in re.findall(r"ObjectsEqual\(Story\.MakeScope\.Var\('cmm26_kind'\).GetFlagName,'([^']+)'",expr)))
        office_branch="[Not(Story.MakeScope.Var('cmm26_title').IsSet)]"in row_expressions
        if office_branch and'office'in kinds:read_kinds=['office']+[k for k in read_kinds if k!='office']
        grid_kinds=read_kinds or kinds
        originals=state['rows'][grid['owner_id']];records=[]
        for i in range(count if originals else 0):
            row=copy.deepcopy(originals[i%len(originals)]);row['row_id']='scene-row:'+grid['owner_id']+':'+str(i);row['story_id']='scene-story:'+grid['owner_id']+':'+str(i)
            for key,v in list(row['values'].items()):
                field,projection=key.split('.')
                if projection in('Title','Story','Char'):row['values'][key]={'type':projection,'id':'sample-'+field+'-'+str(i+1)}
                elif projection=='GetValue':row['values'][key]=i%7 if field.endswith('depth')else i+1
            values=row['values']
            if 'cmm26_kind.GetFlagName'in values:values['cmm26_kind.GetFlagName']=grid_kinds[i%len(grid_kinds)]
            if office_branch and'cmm26_title.IsSet'in values:
                has_geographic_title=values.get('cmm26_kind.GetFlagName')!='office';values['cmm26_title.IsSet']=has_geographic_title
                if not has_geographic_title:values.pop('cmm26_title.Title',None)
            for flag in ['cmm26_uniform','cmm26_before','cmm26_office']:
                if flag+'.IsSet'in values:
                    present=i%2==0;values[flag+'.IsSet']=present
                    if not present:values.pop(flag+'.Title',None)
            if 'cmm26_owner_count.GetValue'in values:values['cmm26_owner_count.GetValue']=1 if values.get('cmm26_uniform.IsSet')else 2
            if 'cmm26_after.Title'in values:values['cmm26_after.Title']={'type':'Title','id':state['target_title_id']or'sample-after'}
            if 'cmm26_office.Title'in values and i==0:values['cmm26_office.Title']={'type':'Title','id':state['target_title_id']or'sample-office'}
            if 'cmm26_direct_after.GetValue'in values:values['cmm26_direct_after.GetValue']=values.get('cmm26_direct_before.GetValue',0)+1
            if 'cmm26_total_after.GetValue'in values:values['cmm26_total_after.GetValue']=values.get('cmm26_total_before.GetValue',0)+1
            records.append(row)
        result['rows'][grid['owner_id']]=records
    validate(contract,result,_known_identity)
    return result


def snapshot_for(contract,state,roots,scrolls=None,_known_identity=None):
    validate(contract,state,_known_identity);bindings=state_bindings(state);nodes={};lists={};labels={}
    target=state['target_title_id']
    if target:labels[target]='目标军区示例'
    for variable,key in [('cmm26_target','target_title_id'),('cmm26_pending','pending_story_id')]:
        base="GetPlayer.MakeScope.Var('"+variable+"')";ident=state[key];kind='Title'if variable=='cmm26_target'else'Story'
        bindings[base+'.IsSet']=ident is not None;bindings[base+'.'+kind]={'type':kind,'id':ident}if ident else None
        bindings[base+'.'+kind+'.IsValid']=ident is not None
    bindings["GetPlayer.MakeScope.Var('cmm26_notice').GetFlagName"]=state['notice']or'fixture-none'
    if target:
        base="GetPlayer.MakeScope.Var('cmm26_target').Title"
        for method in ['GetNameNoTooltip','GetNameNoTierNoTooltip']:bindings[base+'.'+method]=labels[target]
        for field in ['cmm26_direct_count','cmm23_count']:bindings[base+".MakeScope.Var('"+field+"').GetValue"]=3
    bindings["GetPlayer.MakeScope.Var('cmm26_last_count').GetValue"]=3
    if state['pending_story_id']:
        base="GetPlayer.MakeScope.Var('cmm26_pending').Story.MakeScope"
        for field in ['cmm26_added','cmm26_changes','cmm26_total','cmm26_moved','cmm26_returned','cmm26_unchanged','cmm26_hidden']:
            bindings[base+".Var('"+field+"').GetValue"]=3 if field in['cmm26_changes','cmm26_total']else 0
        bindings[base+".Var('cmm26_target').IsSet"]=target is not None
        bindings[base+".Var('cmm26_target').Title"]={'type':'Title','id':target}if target else None
        if target:bindings[base+".Var('cmm26_target').Title.GetNameNoTooltip"]=labels[target]
    for grid in contract['gui']['grids']:
        values=[]
        for index,row in enumerate(state['rows'][grid['owner_id']]):
            row_bindings={'Scope.Story':{'type':'Story','id':row['story_id']}}
            for key,data in row['values'].items():
                field,projection=key.split('.');expr="Story.MakeScope.Var('"+field+"')."+projection
                row_bindings[expr]=data
                if projection in('Title','Story','Char'):
                    ident=data['id']
                    if ident not in labels:labels[ident]=('州示例'if field in['cmm26_county','cmm26_title']else'军区示例')+str(index+1)
                    for method in ['GetNameNoTooltip','GetNameNoTierNoTooltip']:row_bindings[expr+'.'+method]=labels[ident]
                    row_bindings[expr+'.GetTierAsNameNoTooltip']='公国'if index%3 else'伯爵领';row_bindings[expr+'.IsValid']=True
            values.append({'row_id':row['row_id'],'bindings':row_bindings,'nodes':{},'story_id':row['story_id']})
        lists[grid['owner_id']]=values
    # Scripted IsValid is not evaluated, so source button enabled state remains UNKNOWN.
    return {'origin':'SYNTHETIC_OWNER_AND_STORY_VALUES_NOT_GAME_DATA','bindings':bindings,'nodes':nodes,'lists':lists,'scrolls':dict(scrolls or {})}


def build_preview(mod_root):
    contract=build_allocation(mod_root);verify_sources(contract)
    roots=[normalize(w['tree'])for w in contract['gui']['windows']]
    packets={};contract_id=identity(contract)
    for kind in KINDS:
        for count in[3,12]:
            key=kind if count==3 else kind+'_long';state=refine_state(contract,scenario(contract,kind,contract_id),count,contract_id)
            packets[key]={'state':state,'snapshot':snapshot_for(contract,state,roots,_known_identity=contract_id),'sample_count':count}
    actions=[('choose','cmm26_choose',None),('assign_pending','cmm26_assign','pending'),('assign_direct','cmm26_assign','changed'),
             ('confirm_changed','cmm26_confirm','changed'),('confirm_stale','cmm26_confirm','stale'),('cancel','cmm26_cancel',None),
             ('info','cmm26_info',None),('info_close','cmm26_info_close',None),('preview','cmm26_preview_pending_enter',None),('preview_close','cmm26_preview_close',None)]
    graph={};fingerprints={};seeds={};queue=[]
    def add(state,count):
        serialized=json.dumps({'state':state,'count':count},sort_keys=True,ensure_ascii=False,separators=(',',':'));fingerprint=digest(serialized.encode())
        if fingerprint in fingerprints:return fingerprints[fingerprint]
        key='fixture:'+fingerprint[:20];fingerprints[fingerprint]=key
        graph[key]={'state':state,'snapshot':snapshot_for(contract,state,roots,_known_identity=contract_id),'sample_count':count,'edges':{}};queue.append(key);return key
    for key,packet in packets.items():seeds[key]=add(packet['state'],packet['sample_count'])
    index=0
    while index<len(queue):
        require(len(queue)<=100,'ALLOCATION_FIXTURE_GRAPH_LIMIT');key=queue[index];index+=1;packet=graph[key]
        for action,command,outcome in actions:
            try:
                result=transition(contract,packet['state'],command,outcome,contract_id)
            except TitleEditError as exc:
                if str(exc)=='ALLOCATION_FIXTURE_TRANSITION_UNSUPPORTED':continue
                raise
            state=refine_state(contract,result['after'],packet['sample_count'],contract_id)
            target=add(state,packet['sample_count']);packet['edges'][action]={'command':command,'outcome':outcome,'target':target,'status':result['status'],'actual_effects':'NOT_EXECUTED'}
    require(identity(contract)==contract_id,'ALLOCATION_CONTRACT_CHANGED_DURING_COMPILATION')
    return {'schema':'guanchuang.allocation-preview.v1','contract':contract,'roots':roots,'packets':packets,'viewport':[1760,990],
            'graph':graph,'seeds':seeds,
            'scope':'SOURCE_AUTHORED_CANDIDATE; native styles/fonts/templates unexpanded; pure fixture controls only'}


def verify_preview(preview):
    require(preview.get('schema')=='guanchuang.allocation-preview.v1','ALLOCATION_PREVIEW_SCHEMA')
    verify_sources(preview['contract'])
    require(preview['roots']==[normalize(w['tree'])for w in preview['contract']['gui']['windows']],'ALLOCATION_SCENE_REPRESENTATION_CONFLICT')
    contract_id=identity(preview['contract'])
    for packet in list(preview['packets'].values())+list(preview['graph'].values()):
        validate(preview['contract'],packet['state'],contract_id)
        require(snapshot_for(preview['contract'],packet['state'],preview['roots'],packet['snapshot']['scrolls'],contract_id)==packet['snapshot'],'ALLOCATION_SNAPSHOT_REPRESENTATION_CONFLICT')
    for packet in preview['graph'].values():
        for edge in packet['edges'].values():
            require(edge['status']=='SYNTHETIC_TRANSITION_NOT_GAME_EXECUTION'and edge['actual_effects']=='NOT_EXECUTED','ALLOCATION_GRAPH_EFFECT_CLAIM_INVALID')
            require(edge['target']in preview['graph'],'ALLOCATION_GRAPH_TARGET_MISSING')
            expected=transition(preview['contract'],packet['state'],edge['command'],edge['outcome'],contract_id)['after']
            expected=refine_state(preview['contract'],expected,packet['sample_count'],contract_id)
            require(expected==preview['graph'][edge['target']]['state'],'ALLOCATION_GRAPH_TRANSITION_CONFLICT')
    require(set(preview['seeds'])==set(preview['packets']),'ALLOCATION_GRAPH_SEEDS_CONFLICT')
    for key,node in preview['seeds'].items():
        require(node in preview['graph']and all(preview['graph'][node][k]==preview['packets'][key][k]for k in['state','snapshot','sample_count']),
                'ALLOCATION_GRAPH_SEED_PACKET_CONFLICT')


def project_packet(preview,key,scrolls=None):
    require(key in preview['packets'],'ALLOCATION_PACKET_NOT_FOUND');packet=preview['packets'][key]
    snapshot=copy.deepcopy(packet['snapshot']);snapshot['scrolls']=dict(scrolls or {})
    return project(preview['roots'],snapshot,preview['viewport'])
