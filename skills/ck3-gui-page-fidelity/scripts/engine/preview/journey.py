"""One explicit pending transaction supplies confirmation and map snapshots.

This models a reviewed source subset on synthetic data. It is not a Jomini VM.
"""
import copy,json,re
from pathlib import Path
from core.syntax import parse_bytes
from editing.title import require,digest
from preview.allocation import identity,validate
from preview.allocation_scene import snapshot_for as allocation_snapshot,scene_walk,ast_walk
from preview.map_sidebar import snapshot_for as sidebar_snapshot,walk

SCHEMA='guanchuang.transaction-journey.v1'

def title(ident):return {'type':'Title','id':ident}if ident is not None else None
def same(a,b):return a==b

def ranges(transaction):
    """Reviewed nullable owner inequality and ordered add-if-absent extent subset."""
    require(transaction.get('schema')=='guanchuang.pending-transaction.v1','JOURNEY_TRANSACTION_SCHEMA')
    require(isinstance(transaction.get('items'),list),'JOURNEY_ITEMS_REQUIRED');seen=set();unknown=False;changes=[]
    for item in transaction['items']:
        require(isinstance(item.get('story_id'),str)and item['story_id']not in seen,'JOURNEY_STORY_ID_DUPLICATE');seen.add(item['story_id'])
        for key in('county','before','after'):
            if key not in item:unknown=True;continue
            obj=item[key];require(obj is None and key!='county'or isinstance(obj,dict)and obj.get('type')=='Title'and isinstance(obj.get('id'),str),'JOURNEY_TITLE_PROJECTION_REQUIRED')
        if all(k in item for k in('county','before','after'))and not same(item['before'],item['after']):changes.append(item)
    if unknown or transaction.get('before_counties')is None:return {'status':'UNKNOWN','changed_items':None,'extent':None,'before_counties':transaction.get('before_counties')}
    before=transaction['before_counties'];require(isinstance(before,list),'JOURNEY_BEFORE_LIST_REQUIRED')
    require(all(isinstance(x,dict)and x.get('type')=='Title'and isinstance(x.get('id'),str)for x in before),'JOURNEY_BEFORE_TITLE_REQUIRED')
    target=transaction.get('target');require(isinstance(target,dict)and target.get('type')=='Title','JOURNEY_TARGET_REQUIRED')
    extent=[]
    for county in before:
        if not any(same(item['county'],county)and not same(item['after'],target)for item in changes)and county not in extent:extent.append(county)
    for item in transaction['items']:
        if same(item['after'],target)and item['county']not in extent:extent.append(item['county'])
    return {'status':'SOURCE_SUBSET_SYNTHETIC','changed_items':changes,'before_counties':before,'extent':extent}

def _read_entries(mod,relative,names):
    path=Path(mod)/relative;raw=path.read_bytes();doc=parse_bytes(raw,relative)
    require(all(d['code']=='UNSUPPORTED_OPERATOR'and d['message']=='!='for d in doc.diagnostics),'JOURNEY_SOURCE_PARSE')
    entries={}
    for name in names:
        found=[n for n in doc.root.statements if n.key==name];require(len(found)==1,'JOURNEY_SOURCE_ENTRY_NOT_UNIQUE:'+name);entries[name]=found[0].to_dict()
    return {'path':str(path),'source':relative,'sha256':digest(raw),'entries':entries,'parser_diagnostics':doc.diagnostics}

def bind_routes(allocation,sidebar,refs):
    actions=[a for a in allocation['contract']['gui']['actions']if'cmm26_preview_pending_enter'in a['scripted_guis']]
    require(len(actions)==1,'JOURNEY_ENTER_NOT_UNIQUE');enter=actions[0]
    tab=[]
    for callback in enter['callbacks']:
        tab+=re.findall(r"GetVariableSystem.Set\('cmm23_sidebar_tab','([^']+)'\)",callback['expression']or'')
    require(len(tab)==1 and tab[0]in('tree','preview','extent'),'JOURNEY_ENTRY_TAB_UNRESOLVED')
    exits=[n for r in sidebar['roots']for n in walk(r)if n['props'].get('text')=='cmm30_preview_back']
    require(len(exits)==1 and any("GetScriptedGui('cmm26_preview_close')"in(c['expression']or'')for c in exits[0]['callbacks']),'JOURNEY_EXIT_NOT_UNIQUE')
    trigger=next(r['entries']['cmm26_item_changes']for r in refs if'cmm26_item_changes'in r['entries'])
    producer=allocation['contract']['effects'].get('cmm26_build_pending_preview_ranges');require(producer is not None,'JOURNEY_RANGE_SOURCE_MISSING')
    return {'entry_owner':enter['owner_id'],'entry_callbacks':enter['callbacks'],'entry_tab':tab[0],
       'exit_owner':exits[0]['id'],'exit_callbacks':exits[0]['callbacks'],'range_producer':producer,'change_predicate':trigger,
       'selection_guard_source':next(r['entries']['cmm23_select']for r in refs if'cmm23_select'in r['entries']),
       'modeled_scope':'Reviewed nullable before/after inequality, changed Story list, ordered before minus removals plus additions. Source AST retained; no Jomini/IsValid execution.'}

def fixture_transaction(state,contract):
    pending=state['pending_story_id'];target=state['target_title_id']
    if not pending:return None
    require(target is not None,'JOURNEY_PENDING_TARGET_MISSING')
    grid=next(g for g in contract['gui']['grids']if "GetList('cmm26_items')"in g['datamodel']);rows=state['rows'][grid['owner_id']]
    registry={target:'目标军区示例','fixture-other-office':'原属军府示例'};items=[];before=[]
    owners=[(target,target),('fixture-other-office',target),(target,None),(None,target),(None,None),(target,'fixture-other-office')]
    for i,row in enumerate(rows):
        county=copy.deepcopy(row['values'].get('cmm26_county.Title'));require(county is not None,'JOURNEY_COUNTY_PROJECTION_MISSING');registry[county['id']]='州示例'+str(i+1)
        a,b=owners[i%len(owners)];items.append({'story_id':row['story_id'],'row_id':row['row_id'],'county':county,'before':title(a),'after':title(b)})
        if a==target and county not in before:before.append(county)
    # Two explicit unaffected baseline counties prove extent is not just changed items.
    for i in range(2):
        county=title(pending+':unchanged-baseline-'+str(i));registry[county['id']]='原有保留州'+str(i+1);before.append(county)
    return {'schema':'guanchuang.pending-transaction.v1','origin':'EXPLICIT_SYNTHETIC_NOT_GAME_TRANSACTION','story_id':pending,'target':title(target),'items':items,
       'before_counties':before,'title_labels':registry,'sequence':1,'game_effects_executed':False}

def _story_bindings(item,labels):
    b={'Scope.Story':{'type':'Story','id':item['story_id']}}
    for field,key in[('cmm26_county','county'),('cmm26_before','before'),('cmm26_after','after')]:
        if key not in item:continue
        obj=item[key];expr="Story.MakeScope.Var('"+field+"')";b[expr+'.IsSet']=obj is not None
        if obj is not None:
            b[expr+'.Title']=obj;b[expr+'.Title.IsValid']=True
            for method in('GetNameNoTooltip','GetNameNoTierNoTooltip'):
                if obj['id']in labels:b[expr+'.Title.'+method]=labels[obj['id']]
    return b

def canonical_state(state,transaction,contract):
    result=copy.deepcopy(state)
    if transaction is None:return result
    grid=next(g for g in contract['gui']['grids']if "GetList('cmm26_items')"in g['datamodel']);records=[]
    for item in transaction['items']:
        values={}
        for field,key in[('cmm26_county','county'),('cmm26_before','before'),('cmm26_after','after')]:
            if key not in item:continue
            obj=item[key];values[field+'.IsSet']=obj is not None
            if obj is not None:values[field+'.Title']=obj
        allowed={p['field']+'.'+p['projection']for p in grid['story_projections']}
        records.append({'row_id':item['row_id'],'story_id':item['story_id'],'scope_type':'Story','values':{k:v for k,v in values.items()if k in allowed}})
    result['rows'][grid['owner_id']]=records
    impact=next((g for g in contract['gui']['grids']if "GetList('cmm26_impacts')"in g['datamodel']),None)
    if impact:
        # No office parent graph / complete direct baselines have been supplied.
        # The view removes this dataset below so absence is UNKNOWN, not known empty.
        result['rows'][impact['owner_id']]=[]
    return result

def snapshots(allocation,sidebar,state,transaction,tab,contract_id):
    semantic=canonical_state(state,transaction,allocation['contract']);validate(allocation['contract'],semantic,contract_id)
    a=allocation_snapshot(allocation['contract'],semantic,allocation['roots'],_known_identity=contract_id)
    if transaction is None:return semantic,a,None
    for grid in allocation['contract']['gui']['grids']:
        if "GetList('cmm26_impacts')"in grid['datamodel']:a['lists'].pop(grid['owner_id'],None)
    computed=ranges(transaction);labels=transaction['title_labels'];target=transaction['target'];target_label=labels.get(target['id'])
    for records in a['lists'].values():
        for row in records:
            b=row['bindings']
            for expr,obj in list(b.items()):
                if isinstance(obj,dict)and obj.get('type')=='Title'and obj['id']in labels:
                    for method in('GetNameNoTooltip','GetNameNoTierNoTooltip'):b[expr+'.'+method]=labels[obj['id']]
    item_grid=next(g for g in allocation['contract']['gui']['grids']if "GetList('cmm26_items')"in g['datamodel'])
    a['lists'][item_grid['owner_id']]=[{'row_id':item['row_id'],'story_id':item['story_id'],'bindings':_story_bindings(item,labels),'nodes':{}}for item in transaction['items']]
    pending="GetPlayer.MakeScope.Var('cmm26_pending').Story.MakeScope."
    counts={'cmm26_total':len(transaction['items']),'cmm26_changes':len(computed['changed_items'])if computed['changed_items']is not None else None}
    if computed['changed_items']is not None:
        changes=computed['changed_items'];counts.update(cmm26_added=sum(i['before']is None and i['after']is not None for i in changes),cmm26_moved=sum(i['before']is not None and i['after']is not None for i in changes),cmm26_returned=sum(i['before']is not None and i['after']is None for i in changes),cmm26_unchanged=len(transaction['items'])-len(changes))
    for field,num in counts.items():
        if num is not None:a['bindings'][pending+"Var('"+field+"').GetValue"]=num
    s=sidebar_snapshot(sidebar['roots'],tab,0,True);b=s['bindings'];b.update(a['bindings'])
    b['GetVariableSystem.cmm23_page']='map'if state['kind']=='pending_preview'else state['page'];b['GetVariableSystem.cmm23_sidebar_tab']=tab
    b["GetPlayer.MakeScope.Var('cmm23_map_open').IsSet"]=state['kind']=='pending_preview';b['IsRightWindowOpen']=state['kind']=='pending_preview'
    b["GetPlayer.MakeScope.Var('cmm26_pending_preview_open').IsSet"]=True;b["GetPlayer.MakeScope.Var('cmm26_preview_open').IsSet"]=state['kind']=='pending_preview'
    for variable in('cmm26_preview_office','cmm23_selected'):
        prefix="GetPlayer.MakeScope.Var('"+variable+"').Title."
        b[prefix+'IsValid']=True;b[prefix+'Self']=target
        if target_label:b[prefix+'GetNameNoTooltip']=target_label
    b["GetPlayer.MakeScope.Var('cmm26_preview_seq').GetValue"]=transaction['sequence']
    if computed['status']!='UNKNOWN':
        b["GetPlayer.MakeScope.Var('cmm28_preview_before_count').GetValue"]=len(computed['before_counties']);b["GetPlayer.MakeScope.Var('cmm26_preview_extent_count').GetValue"]=len(computed['extent'])
    offices=list(dict.fromkeys([target['id']]+[obj['id']for item in transaction['items']for obj in(item.get('before'),item.get('after'))if obj]))
    for grid in[n for r in sidebar['roots']for n in walk(r)if n['props'].get('datamodel')]:
        expr=grid['props']['datamodel'];name=re.search(r"GetList\('([^']+)'\)",expr)[1];records=[]
        if name=='cmm26_preview_items':
            if computed['changed_items']is None:s['lists'].pop(grid['id'],None);b.pop('IsDataModelEmpty('+expr[1:-1]+')',None);continue
            records=[{'row_id':item['row_id'],'story_id':item['story_id'],'bindings':_story_bindings(item,labels),'nodes':{}}for item in computed['changed_items']]
        elif name=='cmm26_preview_extent':
            if computed['extent']is None:s['lists'].pop(grid['id'],None);b.pop('IsDataModelEmpty('+expr[1:-1]+')',None);continue
            for obj in computed['extent']:
                bindings={'Scope.Title':obj,'Title.Self':obj}
                if obj['id']in labels:bindings['Title.GetNameNoTooltip']=labels[obj['id']]
                records.append({'row_id':obj['id'],'title_id':obj['id'],'bindings':bindings,'nodes':{}})
        else:
            for i,ident in enumerate(offices):
                prefix="Story.MakeScope.Var('cmm23_office').Title."
                bindings={'Scope.Story':{'type':'Story','id':transaction['story_id']+':map-label:'+ident},prefix+'Self':title(ident),
                    "Story.MakeScope.Var('cmm23_ui_depth').GetValue":0,"Story.MakeScope.Var('cmm23_ui_has_children').IsSet":False,"Story.MakeScope.Var('cmm23_ui_expanded').IsSet":False,
                    "Story.MakeScope.Var('cmm23_ui_contains_selected').IsSet":ident==target['id']}
                if ident in labels:bindings[prefix+'GetNameNoTooltip']=labels[ident]
                records.append({'row_id':'map-label:'+ident,'bindings':bindings,'nodes':{}})
        s['lists'][grid['id']]=records;b['IsDataModelEmpty('+expr[1:-1]+')']=len(records)==0
    return semantic,a,s

def _compile(allocation,sidebar,refs):
    routes=bind_routes(allocation,sidebar,refs);contract_id=identity(allocation['contract']);packets={};transactions={}
    for key,packet in allocation['graph'].items():
        tx=fixture_transaction(packet['state'],allocation['contract']);tx_key=None
        if tx:
            tx_key=digest(json.dumps(tx,sort_keys=True,ensure_ascii=False).encode());transactions[tx_key]=tx
        semantic,a,s=snapshots(allocation,sidebar,packet['state'],tx,routes['entry_tab'],contract_id)
        map_tabs={}
        if tx:
            for tab in('tree','preview','extent'):map_tabs[tab]=snapshots(allocation,sidebar,packet['state'],tx,tab,contract_id)[2]
        packets[key]={'state':semantic,'transaction_key':tx_key,'allocation_snapshot':a,'map_tabs':map_tabs,'entry_tab':routes['entry_tab']}
    return {'schema':SCHEMA,'routes':routes,'references':refs,'transactions':transactions,'packets':packets,
       'scope':'One explicit synthetic immutable pending Story/items/Title registry supplies both source-owned windows. Typed snapshots and source-subset projection; no engine calls/effects. Scroll retention is editor preview policy, not observed native behavior.'}

def build_journey(allocation,sidebar,mod_root):
    refs=[_read_entries(mod_root,'common/scripted_triggers/cmm26_triggers.txt',['cmm26_item_changes']),
          _read_entries(mod_root,'common/scripted_guis/cmm23_actions.txt',['cmm23_select'])]
    return _compile(allocation,sidebar,refs)

def verify_journey(journey,allocation,sidebar):
    require(journey.get('schema')==SCHEMA,'JOURNEY_SCHEMA');refs=[]
    for ref in journey['references']:
        path=Path(ref['path']);raw=path.read_bytes();require(digest(raw)==ref['sha256'],'JOURNEY_SOURCE_CONFLICT');doc=parse_bytes(raw,ref['source'])
        entries={name:next(n for n in doc.root.statements if n.key==name).to_dict()for name in ref['entries']}
        fresh=dict(ref,entries=entries,parser_diagnostics=doc.diagnostics);require(fresh==ref,'JOURNEY_SOURCE_REPRESENTATION_CONFLICT');refs.append(fresh)
    require(_compile(allocation,sidebar,refs)==journey,'JOURNEY_PROJECTION_OR_ROUTE_CONFLICT')
