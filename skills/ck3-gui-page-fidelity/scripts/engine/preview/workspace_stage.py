"""One visual stage over existing source scenes; no game callback execution."""
import copy,re
from pathlib import Path
from core.syntax import parse_bytes
from editing.title import require,digest
from preview.components import apply_metrics,walk_scene
from preview.scene import project
from preview.scene import normalize,value
from preview.templates import ScalarComposer

SCHEMA='guanchuang.workspace-visual-stage.v1'

def auxiliary_snapshot(roots,route,count=12):
    """Explicit display fixtures for declarations already embedded in manager source."""
    b={'GetVariableSystem.cmm23_page':route,"GetPlayer.MakeScope.Var('cmm23_open').IsSet":True,"IsGameViewOpen('title_view_window')":False,"IsGameViewOpen('find_title')":False,
       "GetPlayer.MakeScope.Var('cmm23_selected').Title.GetNameNoTooltip":'北府示例',"GetPlayer.MakeScope.Var('cmm23_selected').Title.GetHolder.GetNameNoTooltip":'现任统领示例',
       "GetPlayer.MakeScope.Var('cmm23_person').IsSet":False,"GetPlayer.MakeScope.Var('cmm23_person').Char.GetNameNoTooltip":'示例人物1',
       "GetPlayer.MakeScope.Var('cmm41_pending').IsSet":False,"GetPlayer.MakeScope.Var('cmm41_target').Title.IsValid":True,"GetPlayer.MakeScope.Var('cmm41_target').Title.GetNameNoTooltip":'法理军府示例1',"GetPlayer.MakeScope.Var('cmm41_target').Title.Self":{'type':'Title','id':'legal-title-0'},
       "GetPlayer.MakeScope.Var('cmm41_notice').GetFlagName":'none',"GetPlayer.MakeScope.Var('cmm41_pending_before').IsSet":True,"GetPlayer.MakeScope.Var('cmm41_pending_child').Title.GetNameNoTooltip":'待划拨军府示例1',"GetPlayer.MakeScope.Var('cmm41_pending_before').Title.GetNameNoTooltip":'原上级军府示例',"GetPlayer.MakeScope.Var('cmm41_pending_parent').Title.GetNameNoTooltip":'法理军府示例1'}
    nodes={};lists={}
    for root in roots:
        for n in walk_scene(root):
            p=n['props']
            if p.get('enabled')and value(p['enabled'],b)['status']!='KNOWN':nodes.setdefault(n['id'],{})['enabled']=True # Chosen visual state, not is_valid.
            if not p.get('datamodel'):continue
            records=[]
            for i in range(count):
                name=p['datamodel'];row_bindings={};label='示例人物'+str(i+1)
                if 'cmm41_choices'in name:row_bindings={'Scope.Title':{'type':'Title','id':'legal-child-'+str(i)},'Title.GetNameNoTooltip':'待划拨军府示例'+str(i+1),'Title.GetDeJureLiege.IsValid':True,'Title.GetDeJureLiege.GetNameNoTooltip':'原上级军府示例'}
                elif 'cmm41_rows'in name:
                    prefix="Story.MakeScope.Var('";obj={'type':'Title','id':'legal-title-'+str(i)};row_bindings={'Scope.Story':{'type':'Story','id':'legal-row-'+str(i)},prefix+"cmm41_title').Title.Self":obj,prefix+"cmm41_title').Title.GetNameNoTooltip":'法理军府示例'+str(i+1),prefix+"cmm41_title').Title.GetDeJureLiege.IsValid":i>0,prefix+"cmm41_title').Title.GetDeJureLiege.GetNameNoTooltip":'示例上级军府',prefix+"cmm41_depth').GetValue":i%7,prefix+"cmm41_branch').IsSet":i%3==0,prefix+"cmm41_expanded').IsSet":True,prefix+"cmm41_child_count').GetValue":i%4}
                elif 'cmm23_ui_wars'in name:row_bindings={'Scope.War':{'type':'War','id':'sample-war-'+str(i)},'War.GetName':'示例防御战争 '+str(i+1)}
                else:row_bindings={'Scope.Char':{'type':'Character','id':'sample-person-'+str(i)},'Character.GetNameNoTooltip':label,'Character.GetPrimaryTitle.GetNameNoTooltip':'示例头衔'+str(i+1)}
                owned={}
                for child in[c for r in n['item']for c in walk_scene(r)]:
                    if child['props'].get('enabled'):owned[child['id']]={'enabled':True}
                records.append({'row_id':'aux-'+n['id']+'-'+str(i),'display_index':i,'bindings':row_bindings,'nodes':owned})
            lists[n['id']]=records
    return {'origin':'EXPLICIT_FRONTEND_SAMPLE_NO_REAL_FUNCTIONS','bindings':b,'nodes':nodes,'lists':lists,'scrolls':{}}

def _auxiliary(main,inventory,component_contract):
    path=Path(inventory['mod_root_read_only'])/main['source'];raw=path.read_bytes();doc=parse_bytes(raw,main['source']);names={'cmm41_commander','cmm41_defense','cmm41_legal','cmm41_legal_confirm'};selected=[n for n in doc.root.walk()if n.key=='window'and n.value('name')in names];trees=[n.to_dict()for n in selected];records=list(main['scalar_records'])
    if component_contract:
        ref=component_contract['definitions']['Background_Area_Solid'];records.append(dict(ref,name='Background_Area_Solid',origin='mod/'+main['source'],error=None,node_id=ref['tree']['node_id']))
    elif not any(r['name']=='Background_Area_Solid'and r['origin']=='mod/'+main['source']for r in records):
        records.append({'name':'Background_Area_Solid','origin':'mod/'+main['source'],'error':'STRUCTURED_STYLE_SOURCE_NOT_ATTACHED'})
    composer=ScalarComposer(records=records);roots=[normalize(composer.compose(t))for t in trees]
    if component_contract:apply_metrics(roots,component_contract,trees)
    parents={c.node_id:n.node_id for n in doc.root.walk()for c in n.statements}
    packets={route+'_'+str(count):auxiliary_snapshot(roots,route,count)for route in('legal','commander','defense')for count in(0,3,12)}
    return {'source':main['source'],'source_sha256':digest(raw),'roots':roots,'packets':packets,'declared_owners':[{'name':n.value('name'),'owner_id':n.node_id,'declared_parent':parents.get(n.node_id),'line':n.source_span['start']['line']}for n in selected],
      'basis':'Source window subtrees rooted as display scenes; declaration parent preserved in metadata. Does not prove native scripted-widget registration or effective parent visibility.'}

def source_inventory(mod_root):
    mod=Path(mod_root).resolve();files=[];windows=[];registrations=[]
    for path in sorted((mod/'gui').rglob('*.gui')):
        source=path.relative_to(mod).as_posix();raw=path.read_bytes();doc=parse_bytes(raw,source);files.append({'source':source,'sha256':digest(raw)})
        for n in doc.root.walk():
            if n.key=='window'and n.has_body:windows.append({'source':source,'owner_id':n.node_id,'name':n.value('name'),'visible':n.value('visible')})
    for path in sorted((mod/'gui/scripted_widgets').glob('*.txt')):
        raw=path.read_bytes();registrations.append({'source':path.relative_to(mod).as_posix(),'sha256':digest(raw),'text':raw.decode('utf-8-sig')})
    legal=[w for w in windows if w['name']not in('cmm23_manager','cmm23_entry','cmm23_confirm')and re.search(r"HasValue\('cmm23_page',\s*'legal'\)",w['visible']or'')]
    return {'mod_root_read_only':str(mod),'files':files,'windows':windows,'registrations':registrations,'legal_windows':legal,'legal_gui_status':'PRESENT'if legal else'MISSING_IN_SELECTED_MOD_GUI_INVENTORY'}

def _assemble(main,allocation,sidebar,component_contract,inventory):
    entries=[]
    for root in main['roots']:
        for n in walk_scene(root):
            for c in n['callbacks']:
                match=re.fullmatch(r"\[GetVariableSystem.Set\('cmm23_page','(overview|territory|legal|map|commander|defense)'\)\]",c['expression']or'')
                if match:entries.append({'owner_id':n['id'],'route':match[1],'label':n['props'].get('raw_text',n['props'].get('text')),'ordered_callbacks':n['callbacks']})
    allocation_roots=copy.deepcopy(allocation['roots']);map_roots=copy.deepcopy(sidebar['roots'])
    if component_contract:
        apply_metrics(allocation_roots,component_contract,[w['tree']for w in allocation['contract']['gui']['windows']]);apply_metrics(map_roots,component_contract,sidebar['source_trees'])
    auxiliary=_auxiliary(main,inventory,component_contract)
    initial=allocation.get('graph',{}).get(allocation.get('seeds',{}).get('selected_long'),{}).get('snapshot',{}).get('lists',{})
    back=next((n['id']for r in allocation_roots for n in walk_scene(r)if any('cmm30_leave_allocation'in(c['expression']or'')for c in n['callbacks'])),None)
    return {'schema':SCHEMA,'viewport':main['viewport'],'navigation':entries,'allocation_roots':allocation_roots,'allocation_initial_lists':initial,'allocation_back_owner':back,'map_roots':map_roots,'auxiliary':auxiliary,'map_background':sidebar['paint_ownership']['native_background'],'source_inventory':inventory,
      'routes':{'overview':{'status':'SOURCE_SCENE','scene':'main'},'territory':{'status':'SOURCE_SCENE','scene':'allocation'},'map':{'status':'SOURCE_SCENE','scene':'map'},**{route:{'status':'SOURCE_SUBTREE_DISPLAY_SCENE','scene':'auxiliary'}for route in('legal','commander','defense')}},
      'scope':'One display stage for actual imported source scenes and explicit mock navigation. Missing window sources are surfaced, not invented. Existing effect callbacks remain inert; historical image contents are display samples.'}

def build_stage(main,allocation,sidebar,resources,mod_root):
    return _assemble(main,allocation,sidebar,resources.get('native_components',{}).get('contract'),source_inventory(mod_root))

def rebind_stage(reference,main,allocation,sidebar,resources):
    return _assemble(main,allocation,sidebar,resources.get('native_components',{}).get('contract'),reference['source_inventory'])

def verify_stage(reference,main,allocation,sidebar,resources):
    require(reference.get('schema')==SCHEMA,'VISUAL_STAGE_SCHEMA');require(source_inventory(reference['source_inventory']['mod_root_read_only'])==reference['source_inventory'],'VISUAL_STAGE_SOURCE_INVENTORY_CONFLICT');require(rebind_stage(reference,main,allocation,sidebar,resources)==reference,'VISUAL_STAGE_REPRESENTATION_CONFLICT')

def normal_map_snapshot(sidebar,selected=None,label=None,scrolls=None):
    snap=copy.deepcopy(sidebar['seeds']['normal_3']['snapshot']);snap['scrolls']=dict(scrolls or{});p="GetPlayer.MakeScope.Var('cmm23_selected').Title."
    if selected is not None:
        snap['bindings'].update({p+'IsValid':True,p+'Self':{'type':'Title','id':selected},p+'GetNameNoTooltip':label or selected})
    for name,v in(('cmm26_direct_count',3),('cmm23_count',8)):snap['bindings'][p+"MakeScope.Var('"+name+"').GetValue"]=v
    snap['bindings'][p+"MakeScope.Var('cmm23_effective_parent').IsSet"]=False
    for records in snap['lists'].values():
        for i,record in enumerate(records):
            record['bindings']["Story.MakeScope.Var('cmm23_office').Var('cmm23_count').GetValue"]=i+3;record['bindings']["Story.MakeScope.Var('cmm23_ui_contains_selected').IsSet"]=i==0 and selected is not None
    return snap

def project_stage(reference,mode,snapshot,resources,main_roots=None):
    require(mode in('overview','allocation','map_normal','map_preview','legal','commander','defense'),'VISUAL_STAGE_MODE_INVALID');roots=main_roots if mode=='overview'else reference['allocation_roots']if mode=='allocation'else reference['auxiliary']['roots']if mode in('legal','commander','defense')else reference['map_roots'];require(roots is not None,'VISUAL_STAGE_MAIN_ROOTS_REQUIRED');return project(roots,snapshot,reference['viewport'],resources)
