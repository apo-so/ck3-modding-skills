"""M05 source and explicit scenario core. No Jomini evaluation or game mutation."""
import copy
import json
import math
from pathlib import Path
import re

from core.syntax import parse_bytes
from core.state import evaluate
from editing.title import digest,require,_pair
from preview.office_list import one

WINDOWS=('cmm26_allocation','cmm26_confirm','cmm26_ownership')
KINDS=('no_target','selected','pending','pending_preview','ownership','changed','stale')
COMMANDS={'cmm26_choose','cmm26_assign','cmm26_confirm','cmm26_cancel','cmm26_info','cmm26_info_close',
          'cmm26_preview_pending_enter','cmm26_preview_close'}


def bind_allocation(raw,source='gui/cmm26_allocation.gui'):
    doc=parse_bytes(raw,source);require(not doc.diagnostics,'ALLOCATION_GUI_PARSE_ERRORS')
    roots=[];grids=[];actions=[]
    for name in WINDOWS:
        node=one([n for n in doc.root.statements if n.key=='window'and n.value('name')==name],'ALLOCATION_WINDOW_NOT_UNIQUE:'+name)
        roots.append({'name':name,'owner_id':node.node_id,'size':_pair(node,'size'),'position':next((p.atoms()for p in node.occurrences('position')),None),
          'parentanchor':node.value('parentanchor'),'widgetanchor':node.value('widgetanchor'),'visible':node.value('visible'),
          'subtree_sha256':digest(raw[doc.byte_offsets[node.start]:doc.byte_offsets[node.end]]),'tree':node.to_dict()})
        parents={c.node_id:n.node_id for n in node.walk()for c in n.statements}
        for owner in node.walk():
            if owner.value('datamodel'):
                item=one(owner.occurrences('item'),'ALLOCATION_ITEM_NOT_UNIQUE')
                rows=[n for n in item.statements if n.has_body and n.key in('widget','vbox','hbox')]
                row=one(rows,'ALLOCATION_ROW_NOT_UNIQUE')
                require([p.scalar for p in row.occurrences('datacontext')]==['[Scope.Story]'],'ALLOCATION_ROW_REQUIRES_STORY')
                projections=set()
                for n in row.walk():
                    if n.scalar:
                        projections.update(re.findall(r"Story\.MakeScope\.Var\('([^']+)'\)\.(Title|Story|Char|GetValue|GetFlagName|IsSet)",n.scalar))
                grids.append({'window':name,'owner_id':owner.node_id,'datamodel':owner.value('datamodel'),
                   'column':owner.value('addcolumn'),'step':owner.value('addrow'),'item_owner':item.node_id,'row_owner':row.node_id,
                   'row_context':'[Scope.Story]','row_size':_pair(row,'size'),
                   'story_projections':[{'field':f,'projection':p}for f,p in sorted(projections)],
                   'context_owners':[{'owner_id':n.node_id,'parent_id':parents.get(n.node_id),'ordered_contexts':[p.scalar for p in n.occurrences('datacontext')]}for n in row.walk()if n.occurrences('datacontext')]})
            callbacks=[{'key':p.key,'expression':p.scalar}for p in owner.statements if p.kind=='assignment'and p.key in('onclick','onrightclick')]
            if callbacks:
                calls=[m for p in callbacks for m in re.findall(r"GetScriptedGui\('([^']+)'\)",p['expression']or'')]
                actions.append({'window':name,'owner_id':owner.node_id,'line':owner.source_span['start']['line'],
                    'name':owner.value('name'),'label':owner.value('raw_text',owner.value('text')),
                    'enabled':owner.value('enabled'),'visible':owner.value('visible'),'callbacks':callbacks,'scripted_guis':calls})
    ordered=[n.value('name')for n in doc.root.statements if n.key=='window'and n.value('name')in WINDOWS]
    return {'schema':'guanchuang.allocation-source.v1','source':source,'source_sha256':digest(raw),'window_order':ordered,
       'windows':roots,'grids':grids,'actions':actions,'scope_rule':'Generic Scope → Story; Title/Story/Character projections retain their actual owner',
       'basis':'SOURCE_ONLY_NOT_ENGINE_LAYOUT_OR_EFFECT_ACCEPTANCE'}


def entry(node):
    return {'name':node.key,'scope':node.value('scope'),'tree':node.to_dict()}


def build_allocation(mod_root):
    mod=Path(mod_root).resolve();path=mod/'gui/cmm26_allocation.gui';raw=path.read_bytes();gui=bind_allocation(raw)
    needed={x for action in gui['actions']for x in action['scripted_guis']}|COMMANDS
    references=[{'path':str(path),'source':gui['source'],'sha256':digest(raw)}];scripted={};duplicates=set()
    for p in sorted((mod/'common/scripted_guis').glob('cmm*.txt')):
        source=p.relative_to(mod).as_posix();doc=parse_bytes(p.read_bytes(),source);found=[n for n in doc.root.statements if n.key in needed and n.has_body]
        if found:references.append({'path':str(p),'source':source,'sha256':doc.sha256})
        for n in found:
            if n.key in scripted:duplicates.add(n.key)
            scripted[n.key]={'source':source,**entry(n)}
    require(not duplicates,'ALLOCATION_SCRIPTED_GUI_AMBIGUOUS')
    require(COMMANDS<=set(scripted),'ALLOCATION_PREVIEW_COMMAND_SOURCE_MISSING')
    effects={}
    for p in sorted((mod/'common/scripted_effects').glob('cmm26*.txt')):
        source=p.relative_to(mod).as_posix();doc=parse_bytes(p.read_bytes(),source)
        references.append({'path':str(p),'source':source,'sha256':doc.sha256})
        for n in doc.root.statements:
            if n.has_body:
                require(n.key not in effects,'ALLOCATION_EFFECT_AMBIGUOUS')
                effects[n.key]={'source':source,**entry(n)}
    return {'schema':'guanchuang.allocation-contract.v1','gui':gui,'sources':references,'scripted_guis':scripted,
       'unresolved_scripted_guis':sorted(needed-set(scripted)),'effects':effects,
       'simulation_scope':'Explicit fixture branches only; is_valid/transactions/map commands remain unexecuted'}


def verify_sources(contract):
    docs={}
    for record in contract['sources']:
        raw=Path(record['path']).read_bytes();require(digest(raw)==record['sha256'],'ALLOCATION_SOURCE_CONFLICT')
        docs[record['source']]=parse_bytes(raw,record['source'])
    gui_source=contract['gui']['source'];require(gui_source in docs,'ALLOCATION_SOURCE_MISSING')
    require(bind_allocation(docs[gui_source].raw_bytes,gui_source)==contract['gui'],'ALLOCATION_GUI_REPRESENTATION_CONFLICT')
    for registry in ['scripted_guis','effects']:
        for name,record in contract[registry].items():
            require(record['source']in docs,'ALLOCATION_ROUTE_SOURCE_MISSING')
            node=one([n for n in docs[record['source']].root.statements if n.key==name],'ALLOCATION_ROUTE_NOT_UNIQUE')
            require({'source':record['source'],**entry(node)}==record,'ALLOCATION_ROUTE_REPRESENTATION_CONFLICT')


def identity(contract):
    return digest(json.dumps(contract,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8'))


def scenario(contract,kind,_known_identity=None):
    require(kind in KINDS,'ALLOCATION_SCENARIO_UNSUPPORTED')
    pending=kind in('pending','pending_preview','stale');selected=kind!='no_target'
    state={'schema':'guanchuang.allocation-fixture.v1','origin':'SYNTHETIC_STATE_NOT_GAME_EXECUTION','contract_sha256':_known_identity or identity(contract),
       'kind':kind,'target_title_id':'fixture-office-1'if selected else None,'pending_story_id':'fixture-pending-1'if pending else None,
       'operation_story_id':'fixture-operation-1'if kind=='changed'else None,'notice':'stale'if kind=='stale'else'changed'if kind=='changed'else'selected'if selected else None,
       'page':'map'if kind=='pending_preview'else'territory','allocation_open':True,'preview_open':kind=='pending_preview',
       'info_open':kind=='ownership','pending_open':pending,'native_views':{'find_title':False,'title_view_window':False},
       'rows':{},'fixture_assumptions':['GUI variable flags and object identities are explicit samples, not queried from game','Window conditions are evaluated only against these explicit flags'],
       'game_effects_executed':False}
    for grid in contract['gui']['grids']:
        count=0 if not selected else 3
        if grid['window']=='cmm26_confirm'and not pending:count=0
        if grid['window']=='cmm26_ownership'and not state['info_open']:count=0
        records=[]
        for i in range(count):
            values={}
            for ref in grid['story_projections']:
                field,projection=ref['field'],ref['projection'];key=field+'.'+projection
                if projection in('Title','Story','Char'):values[key]={'type':projection,'id':'fixture-'+field+'-'+str(i+1)}
                elif projection=='GetValue':values[key]=i if field.endswith('depth')else i+1
                elif projection=='GetFlagName':values[key]='fixture'
                else:values[key]=True
            records.append({'row_id':'fixture-row:'+grid['owner_id']+':'+str(i),'story_id':'fixture-story:'+grid['owner_id']+':'+str(i),
                            'scope_type':'Story','values':values})
        state['rows'][grid['owner_id']]=records
    return state


def validate(contract,state,_known_identity=None):
    # Private compiler fast path: callers compute this from the verified immutable
    # contract, never from an input packet, and check the whole contract again after.
    require(isinstance(state,dict)and state.get('schema')=='guanchuang.allocation-fixture.v1'and state.get('origin')=='SYNTHETIC_STATE_NOT_GAME_EXECUTION','ALLOCATION_STATE_SCHEMA')
    require(state.get('contract_sha256')==(_known_identity or identity(contract)),'ALLOCATION_STATE_SOURCE_CONFLICT')
    require(state.get('kind')in KINDS and state.get('game_effects_executed')is False,'ALLOCATION_STATE_NOT_FIXTURE')
    for key in ['allocation_open','preview_open','pending_open','info_open']:require(type(state.get(key))is bool,'ALLOCATION_FLAGS_REQUIRED')
    for key in ['target_title_id','pending_story_id','operation_story_id']:require(state.get(key)is None or isinstance(state[key],str),'ALLOCATION_ID_TYPE')
    require(isinstance(state.get('page'),str)and isinstance(state.get('native_views'),dict),'ALLOCATION_VIEW_STATE_REQUIRED')
    require(all(type(v)is bool or v is None for v in state['native_views'].values()),'ALLOCATION_VIEW_FLAG_TYPE')
    require(isinstance(state.get('rows'),dict)and set(state['rows'])=={g['owner_id']for g in contract['gui']['grids']},'ALLOCATION_GRID_OWNERS_MISMATCH')
    specs={g['owner_id']:{x['field']+'.'+x['projection']:x['projection']for x in g['story_projections']}for g in contract['gui']['grids']}
    for grid_id,records in state['rows'].items():
        require(isinstance(records,list)and len(records)<=10000,'ALLOCATION_ROWS_INVALID');ids=[]
        for row in records:
            require(isinstance(row,dict)and row.get('scope_type')=='Story'and isinstance(row.get('values'),dict),'ALLOCATION_ROW_REQUIRES_STORY')
            require(isinstance(row.get('row_id'),str)and isinstance(row.get('story_id'),str),'ALLOCATION_ROW_IDS_REQUIRED');ids.append(row['row_id'])
            require(set(row['values'])<=set(specs[grid_id]),'ALLOCATION_STORY_FIELD_NOT_IN_SOURCE')
            for key,value in row['values'].items():
                projection=specs[grid_id][key]
                if projection in('Title','Story','Char'):
                    require(isinstance(value,dict)and value.get('type')==projection and isinstance(value.get('id'),str),'ALLOCATION_TYPED_PROJECTION_CONFLICT')
                elif projection=='GetValue':require(type(value)in(int,float)and math.isfinite(value),'ALLOCATION_STORY_NUMBER_TYPE')
                elif projection=='GetFlagName':require(isinstance(value,str),'ALLOCATION_STORY_FLAG_TYPE')
                else:require(type(value)is bool,'ALLOCATION_STORY_PRESENCE_TYPE')
        require(len(ids)==len(set(ids)),'ALLOCATION_ROW_ID_NOT_UNIQUE')
    for key in ['preview_return_state','ownership_return_state']:
        if key in state:
            original=state[key];require(isinstance(original,dict)and not any(k in original for k in['preview_return_state','ownership_return_state']), 'ALLOCATION_RETURN_PACKET_NESTED')
            validate(contract,original,_known_identity)


def state_bindings(state):
    bindings={'GetVariableSystem.cmm23_page':state['page']}
    for variable,key in [('cmm26_open','allocation_open'),('cmm26_preview_open','preview_open'),('cmm26_pending_open','pending_open'),('cmm26_info_open','info_open')]:
        bindings["GetPlayer.MakeScope.Var('"+variable+"').IsSet"]=state[key]
    for name in ['find_title','title_view_window']:
        value=state['native_views'].get(name)
        if type(value)is bool:bindings["IsGameViewOpen('"+name+"')"]=value
    return bindings


def visible_windows(contract,state):
    validate(contract,state)
    bindings=state_bindings(state)
    return [{'name':root['name'],'visibility':evaluate(root['visible'],bindings)}for root in contract['gui']['windows']]


def transition(contract,state,command,outcome=None,_known_identity=None):
    """Select a test branch. This is deliberately not a scripted-GUI execution engine."""
    validate(contract,state,_known_identity);require(command in COMMANDS and command in contract['scripted_guis'],'ALLOCATION_COMMAND_UNSUPPORTED')
    kind=state['kind'];target=None
    if command=='cmm26_choose':target='selected'
    elif command=='cmm26_assign'and kind in('selected','changed','stale'):
        target=outcome or'pending';require(target in('pending','changed'),'ALLOCATION_FIXTURE_BRANCH_UNSUPPORTED')
    elif command=='cmm26_confirm'and kind in('pending','stale'):
        target=outcome or'changed';require(target in('changed','stale'),'ALLOCATION_FIXTURE_BRANCH_UNSUPPORTED')
    elif command=='cmm26_cancel'and kind in('pending','stale'):target='selected'
    elif command=='cmm26_info'and kind in('selected','changed'):target='ownership'
    elif command=='cmm26_info_close'and kind=='ownership':target='selected'
    elif command=='cmm26_preview_pending_enter'and kind in('pending','stale'):target='pending_preview'
    elif command=='cmm26_preview_close'and kind=='pending_preview':target='pending'
    require(target is not None,'ALLOCATION_FIXTURE_TRANSITION_UNSUPPORTED')
    if command=='cmm26_preview_pending_enter':
        after=copy.deepcopy(state);after.update(kind='pending_preview',preview_open=True,page='map')
    elif command=='cmm26_info':
        sample=scenario(contract,'ownership',_known_identity);after=copy.deepcopy(state);after.update(kind='ownership',info_open=True)
        for grid in contract['gui']['grids']:
            if grid['window']=='cmm26_ownership':after['rows'][grid['owner_id']]=sample['rows'][grid['owner_id']]
    elif command=='cmm26_preview_close'and'preview_return_state'in state:after=copy.deepcopy(state['preview_return_state'])
    elif command=='cmm26_info_close'and'ownership_return_state'in state:after=copy.deepcopy(state['ownership_return_state'])
    else:after=scenario(contract,target,_known_identity)
    if command=='cmm26_preview_pending_enter':after['preview_return_state']=copy.deepcopy(state)
    if command=='cmm26_info':after['ownership_return_state']=copy.deepcopy(state)
    if state['target_title_id']is not None:after['target_title_id']=state['target_title_id']
    if state['pending_story_id']is not None and after['pending_open']:after['pending_story_id']=state['pending_story_id']
    return {'status':'SYNTHETIC_TRANSITION_NOT_GAME_EXECUTION','command':command,'before_kind':kind,'after':after,
       'scripted_gui_scope':contract['scripted_guis'][command]['scope'],'actual_is_valid':'NOT_EVALUATED','actual_effects':'NOT_EXECUTED'}
