"""Actual map sidebar with explicit synthetic Story/Title snapshots; no map engine calls."""
import copy
import re
from pathlib import Path
from core.syntax import parse_bytes
from editing.title import require,digest
from preview.templates import ScalarComposer,verify_records
from preview.scene import normalize

SCHEMA='guanchuang.map-sidebar.v1'
SCROLLS=['cmm23_district_tree','cmm26_completed_changes','cmm26_current_extent']

def walk(node):
    yield node
    for child in node['children']+node['item']:yield from walk(child)

def _source(path,source):
    raw=Path(path).read_bytes();doc=parse_bytes(raw,source)
    require(not doc.diagnostics,'MAP_SOURCE_PARSE_DIAGNOSTICS')
    return doc,{'path':str(path),'source':source,'sha256':digest(raw)}

def _roots(trees,composer):return [normalize(composer.compose(t))for t in trees]

def _label_contract(label):
    return {'owner_id':label.node_id,'tree':label.to_dict(),'anchor_status':'UNKNOWN_ENGINE_PROVINCE_COORDINATES',
       'engine_owner':'province_map_icon / ProvinceIcon','row_context':'[Scope.Story]',
       'identity_constraint':"Story.cmm23_label_county.Title.GetProvince equals ProvinceIcon.GetProvince",'source_position_is_local_offset_only':True,'world_coordinates':None}

def snapshot_for(roots,tab='tree',count=3,preview=True,selected=None):
    require(tab in('tree','preview','extent')and type(count)is int and 0<=count<=100,'MAP_SAMPLE_INVALID')
    require(selected is None or selected in range(count),'MAP_SELECTED_ROW_INVALID')
    selected=0 if selected is None and count else selected
    b={"GetVariableSystem.cmm23_page":'map',"GetVariableSystem.cmm23_sidebar_tab":tab,
       'IsRightWindowOpen':True,"IsGameViewOpen('struggle')":False,"IsGameViewOpen('title_view_window')":False,"IsGameViewOpen('find_title')":False,
       "IsMapMode('situation')":True,"IsMapMode('realms')":False}
    # Every flag below is an explicitly chosen fixture value, never a game observation.
    flags={'cmm23_map_open':True,'cmm26_preview_open':preview,'cmm26_pending_preview_open':preview,
       'cmm26_preview_valid':True,'cmm23_selection_invalid':False,'cmm23_show_all_roots':False,
       'cmm23_root_stats_valid':False,'cmm23_root_view_truncated':False}
    for key,v in flags.items():b["GetPlayer.MakeScope.Var('"+key+"').IsSet"]=v
    for key in('cmm23_inspected_county','cmm23_inspect_owner','cmm23_inspect_root'):
        b["GetPlayer.MakeScope.Var('"+key+"').Title.IsValid"]=False
    for mode in('debug_terrain','debug_visual_regions','debug_geographical_region','dejure_counties','dejure_duchies','dejure_kingdoms'):b["IsMapMode('"+mode+"')"]=False
    sel="GetPlayer.MakeScope.Var('cmm23_selected').Title."
    b.update({sel+'IsValid':selected is not None,sel+'Self':{'type':'Title','id':'office-'+str(selected)}if selected is not None else None,
              sel+'GetNameNoTooltip':'样本军府 '+str(selected+1)if selected is not None else'无'})
    lists={}
    for grid in[n for r in roots for n in walk(r)if n['props'].get('datamodel')]:
        expr=grid['props']['datamodel'];name=re.search(r"GetList\('([^']+)'\)",expr)[1]
        b['IsDataModelEmpty('+expr[1:-1]+')']=count==0
        records=[]
        for i in range(count):
            bindings={};identity={'type':'Title','id':'office-'+str(i)}
            if name=='cmm23_map_labels':
                p="Story.MakeScope.Var('"
                bindings={p+"cmm23_office').Title.Self":identity,p+"cmm23_office').Title.GetNameNoTooltip":'样本军府 '+str(i+1)+(' · 长名称用于裁剪检查'*3 if i==count-1 else''),
                    p+"cmm23_ui_depth').GetValue":i%7,p+"cmm23_ui_has_children').IsSet":i%2==0,p+"cmm23_ui_expanded').IsSet":False,p+"cmm23_slot').GetValue":i%24}
            elif name=='cmm26_preview_items':
                bindings={"Story.MakeScope.Var('cmm26_county').Title.GetNameNoTooltip":'样本调整州 '+str(i+1)}
            elif name=='cmm26_preview_extent':bindings={'Title.GetNameNoTooltip':'样本范围州 '+str(i+1)}
            else:raise ValueError('UNSUPPORTED_MAP_DATASET:'+name)
            records.append({'row_id':name+'-'+str(i),'identity':{'type':'Title'if name=='cmm26_preview_extent'else'Story','id':name+'-'+str(i)},'bindings':bindings,'nodes':{}})
        lists[grid['id']]=records
    return {'origin':'SYNTHETIC_NOT_GAME_DATA','bindings':b,'nodes':{},'lists':lists,'scrolls':{}}

def _assemble(trees,records,sources,map_label):
    composer=ScalarComposer(records=records);roots=_roots(trees,composer)
    seeds={}
    for tab in('tree','preview','extent'):
        for count in(0,3,24):
            key=tab+'_'+str(count);seeds[key]={'tab':tab,'count':count,'preview':True,'snapshot':snapshot_for(roots,tab,count)}
    for count in(0,3,24):seeds['normal_'+str(count)]={'tab':'tree','count':count,'preview':False,'snapshot':snapshot_for(roots,'tree',count,False)}
    return {'schema':SCHEMA,'viewport':[1760,990],'roots':roots,'source_trees':trees,'template_records':list(composer.records.values()),
       'composition_issues':composer.issues,'sources':sources,'seeds':seeds,'map_label':map_label,
       'paint_ownership':{'native_background':roots[0]['id'],'transparent_mod_shell':roots[1]['id']},
       'scope':'Source-authored sidebar candidate with explicit fixture values. Native HUD background retained separately; style, font, shader, ProvinceIcon anchors and map painting unverified. No game callbacks/effects executed.'}

def build_preview(index,mod_root):
    mod=Path(mod_root);game=index.roots['vanilla'];sources=[]
    doc,s=_source(mod/'gui/cmm23_situation_window.gui','mod/gui/cmm23_situation_window.gui');sources.append(s)
    root=next(n for n in doc.root.walk()if n.key=='window'and n.value('name')=='cmm23_situation_window')
    hud,s=_source(game/'gui/hud_sidebars.gui','vanilla/gui/hud_sidebars.gui');sources.append(s)
    bg=next(n for n in hud.root.walk()if n.value('name')=='sidebar_background_right')
    labels,s=_source(mod/'gui/map_icon_layer.gui','mod/gui/map_icon_layer.gui');sources.append(s)
    label=next(n for n in labels.root.walk()if n.value('name')=='cmm23_district_map_labels')
    label_contract=_label_contract(label)
    trees=[bg.to_dict(),root.to_dict()];composer=ScalarComposer(index)
    _roots(trees,composer)
    return _assemble(trees,list(composer.records.values()),sources,label_contract)

def verify_preview(preview):
    require(preview.get('schema')==SCHEMA,'MAP_SIDEBAR_SCHEMA');docs={}
    for source in preview['sources']:
        doc,ref=_source(source['path'],source['source']);require(ref==source,'MAP_SOURCE_CONFLICT');docs[source['source']]=doc
    for tree in preview['source_trees']+[preview['map_label']['tree']]:
        n=next((n for n in docs[tree['source']].root.walk()if n.node_id==tree['node_id']),None)
        require(n is not None and n.to_dict()==tree,'MAP_REPRESENTATION_CONFLICT')
    verify_records(preview['template_records'])
    label=next(n for d in docs.values()for n in d.root.walk()if n.value('name')=='cmm23_district_map_labels')
    fresh=_assemble(preview['source_trees'],preview['template_records'],preview['sources'],_label_contract(label))
    require(fresh==preview,'MAP_SCENE_OR_SNAPSHOT_CONFLICT')
