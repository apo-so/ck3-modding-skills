/* Owner-scoped synthetic snapshot projection. No CK3 calls are evaluated or dispatched. */
(function(root){
 'use strict';const need=(v,c)=>{if(!v)throw new Error(c)};
 function split(s){let rows=[],start=0,depth=0,quote=false,escape=false;for(let i=0;i<s.length;i++){const c=s[i];if(escape){escape=false;continue}if(c==='\\'&&quote)escape=true;else if(c==="'")quote=!quote;else if(!quote){if(c==='(')depth++;else if(c===')')depth--;else if(c===','&&depth===0){rows.push(s.slice(start,i).trim());start=i+1}}}if(s.slice(start).trim())rows.push(s.slice(start).trim());return rows}
 function evaluate(expression,bindings){
  if(expression===undefined||expression===null)return{status:'KNOWN',value:true,basis:'NO_CONDITION'};
  let expr=String(expression).trim();if(expr.startsWith('[')&&expr.endsWith(']'))expr=expr.slice(1,-1).trim();
  if(Object.hasOwn(bindings,expr))return{status:'KNOWN',value:bindings[expr],basis:'EXPLICIT_FIXTURE'};
  const literals={yes:true,no:false,"'(bool)yes'":true,"'(bool)no'":false,true:true,false:false};if(Object.hasOwn(literals,expr))return{status:'KNOWN',value:literals[expr],basis:'LITERAL'};
  let m=expr.match(/^(And|Or|Not)\s*\(([\s\S]*)\)$/);
  if(m){const[_,op,raw]=m,args=split(raw);if(args.length!==(op==='Not'?1:2))return{status:'INVALID',value:null,basis:'VERSIONED_BINARY_LOGIC_ARITY'};
   const values=args.map(a=>evaluate(a,bindings));if(values.some(v=>v.status==='INVALID'))return{status:'INVALID',value:null,basis:'INVALID_ARGUMENT'};
   const known=values.map(v=>v.status==='KNOWN'?v.value:null);let answer;
   if(op==='Not'&&known[0]!==null)answer=!known[0];else if(op==='And'&&known.includes(false))answer=false;else if(op==='Or'&&known.includes(true))answer=true;
   else if(known.includes(null))return{status:'UNKNOWN',value:null,basis:'UNKNOWN_ARGUMENT'};else answer=op==='And'?known.every(Boolean):known.some(Boolean);
   return{status:'KNOWN',value:answer,basis:'MODELED_LOGIC'};
  }
  m=expr.match(/^GetVariableSystem\.(HasValue|Exists)\s*\(([\s\S]*)\)$/);
  if(m){const args=split(m[2]);if(args.length!==(m[1]==='HasValue'?2:1))return{status:'INVALID',value:null,basis:'VARIABLE_FUNCTION_ARITY'};
   const strip=s=>s.replace(/^'+|'+$/g,''),key='GetVariableSystem.'+strip(args[0]);if(Object.hasOwn(bindings,key))return{status:'KNOWN',value:m[1]==='HasValue'?bindings[key]===strip(args[1]):bindings[key]!==null,basis:'EXPLICIT_FIXTURE'};
  }
  return{status:'UNKNOWN',value:null,basis:'UNIMPLEMENTED_BINDING_OR_MISSING_STATE',expression:expr};
 }
 function validateProfile(p,title){
  need(p&&p.schema==='guanchuang.detail-profile.v1'&&p.origin==='SYNTHETIC_OWNER_FIXTURE_NOT_GAME_DATA','DETAIL_PROFILE_SCHEMA');need(p.title_id===title,'DETAIL_PROFILE_TITLE_CONFLICT');
  const object=v=>v&&typeof v==='object'&&!Array.isArray(v);need(object(p.node_values)&&object(p.lists),'DETAIL_OWNER_VALUES_REQUIRED');const sets=[p.node_values];
  for(const rows of Object.values(p.lists)){need(Array.isArray(rows)&&rows.length<=10000,'DETAIL_LIST_ROWS_INVALID');need(rows.every(r=>object(r)&&object(r.node_values)),'DETAIL_OWNER_VALUES_REQUIRED');const ids=rows.map(r=>r.row_id);need(ids.every(id=>typeof id==='string'&&id)&&new Set(ids).size===ids.length,'DETAIL_ROW_ID_NOT_UNIQUE');sets.push(...rows.map(r=>r.node_values))}
  for(const values of sets)for(const record of Object.values(values)){need(object(record)&&Object.keys(record).every(k=>['text','visible','enabled'].includes(k)),'DETAIL_VALUE_UNSUPPORTED');need(Object.entries(record).every(([k,v])=>typeof v===(k==='text'?'string':'boolean')),'DETAIL_VALUE_TYPE')}
 }
 function project(preview,title,tab='overview',coverage='direct',scroll=0){
  const c=preview.contract;need(c.tabs.some(t=>t.value===tab)&&['direct','all'].includes(coverage),'DETAIL_TAB_UNSUPPORTED');need(title===null||typeof title==='string','DETAIL_SELECTED_ID_INVALID');need(typeof scroll==='number'&&Number.isFinite(scroll),'DETAIL_SCROLL_NOT_FINITE');
  if(title===null)return{status:'NO_SELECTION',title_id:null,rows:[],max_scroll:0,scroll:0,empty:c.empty};
  if(!Object.hasOwn(preview.profiles,title))return{status:'UNKNOWN_SELECTION_SNAPSHOT',title_id:title,rows:[],max_scroll:0,scroll:0};
  const profile=preview.profiles[title];validateProfile(profile,title);const bindings={'GetVariableSystem.cmm40_detail_tab':tab,'GetVariableSystem.cmm40_coverage_view':coverage},rows=[];
  function number(v,base=0){if(v===undefined||v===null)return null;const value=typeof v==='string'&&v.endsWith('%')?base*Number(v.slice(0,-1))/100:Number(v);return Number.isNaN(value)?null:value}
  function pair(n,key,available){const value=n.props[key]||[];return Array.isArray(value)?[0,1].map(i=>i<value.length?number(value[i],available[i]):null):[null,null]}
  function condition(n,values,key='visible'){const owned=values[n.id]||{};return Object.hasOwn(owned,key)?{status:'KNOWN',value:owned[key],basis:'EXPLICIT_OWNER_FIXTURE'}:evaluate(n.props[key],bindings)}
  function text(n,values){const p=n.props,raw=p.raw_text??p.text??'',owned=values[n.id]||{};if(Object.hasOwn(owned,'text'))return[owned.text,'OWNER_FIXTURE'];if(typeof raw!=='string'||raw.includes('[')||raw.includes('$'))return['〔未提供此控件的绑定值〕','UNKNOWN'];if(p.text&&/^[A-Z][A-Z0-9_]+$/.test(raw))return['〔未解析本地化：'+raw+'〕','UNKNOWN'];return[raw,'STATIC_LITERAL']}
  function measure(n,width,values){const p=n.props,dims=pair(n,'size',[width,0]),w=dims[0]!==null&&dims[0]>0?dims[0]:width;
   if(p.datamodel){const items=profile.lists[n.id];return[w,(items===undefined?1:items.length)*(number(p.addrow)||50)]}
   if(dims[1]!==null&&dims[1]>0)return[w,dims[1]];
   const children=n.children.filter(x=>condition(x,values).value!==false&&x.tag!=='expand'),sizes=children.map(x=>measure(x,w,values)),spacing=number(p.spacing)||0;
   if(n.tag==='hbox')return[w,Math.max(0,...sizes.map(s=>s[1]))];if(['vbox','flowcontainer'].includes(n.tag))return[w,sizes.reduce((s,v)=>s+v[1],0)+Math.max(0,sizes.length-1)*spacing+(number(p.margin_top)||0)+(number(p.margin_bottom)||0)];
   if(n.tag.startsWith('text')||n.tag.startsWith('button'))return[w,number(p.fontsize)||24];return[w,Math.max(0,...sizes.map(s=>s[1]))];
  }
  function arrange(n,x,y,width,values,path,clip=null,conditional=false){const visible=condition(n,values);if(visible.value===false)return;const p=n.props,[w,h]=measure(n,width,values),position=pair(n,'position',[width,h]);x+=position[0]||0;y+=position[1]||0;const[value,status]=text(n,values);
   const row={owner_id:n.id,instance_id:path,tag:n.tag,name:p.name??null,rect:[x,y,w,h],text:value,text_status:status,visibility:visible,enabled:condition(n,values,'enabled'),contexts:n.contexts,callbacks:n.callbacks,clip,conditional:conditional||visible.status!=='KNOWN',geometry_status:p.size?'AUTHORED_CANDIDATE':'INHERITED_SIZE_UNMODELED_CANDIDATE',fontsize:number(p.fontsize)||15,font_basis:p.fontsize?'EXPLICIT':'FALLBACK_NOT_RESOLVED',elide:p.elide??null};rows.push(row);
   if(p.datamodel){const records=profile.lists[n.id];if(records===undefined){row.list_status='UNKNOWN';return}row.list_status='FIXTURE';const step=number(p.addrow)||50;records.forEach((record,i)=>n.item.forEach(child=>arrange(child,x,y+i*step,w,record.node_values,path+'/'+record.row_id,clip,conditional||visible.status!=='KNOWN')));return}
   let cursor=0;const spacing=number(p.spacing)||0,ml=number(p.margin_left)||0,mt=number(p.margin_top)||0,children=n.children.filter(child=>child.tag!=='expand'&&condition(child,values).value!==false);
   children.forEach((child,i)=>{if(['vbox','hbox','flowcontainer'].includes(n.tag)){const horizontal=n.tag==='hbox',[cw,ch]=measure(child,Math.max(0,w-ml),values);arrange(child,x+ml+(horizontal?cursor:0),y+mt+(horizontal?0:cursor),cw,values,path+'/'+i,clip,conditional||visible.status!=='KNOWN');cursor+=(horizontal?cw:ch)+spacing}else arrange(child,x,y,w,values,path+'/'+i,clip,conditional||visible.status!=='KNOWN')});
  }
  const g=c.geometry,spacing=g.spacing,tabsY=g.summary[1]+spacing,contentY=tabsY+g.tabs[1]+spacing,actionsY=contentY+g.scroll[1]+spacing;
  const natural=measure(c.content,g.scroll[0],profile.node_values)[1],maximum=Math.max(0,natural-g.scroll[1]),offset=Math.min(Math.max(0,scroll),maximum);
  arrange(c.summary,0,0,g.summary[0],profile.node_values,'summary');arrange(c.content,0,contentY-offset,g.scroll[0],profile.node_values,'content',[0,contentY,...g.scroll]);arrange(c.actions,0,actionsY,g.actions[0],profile.node_values,'actions');
  return{status:'FIXTURE_DETAIL',title_id:title,tab,coverage,pane_size:g.pane,rows,tabs:{y:tabsY,items:c.tabs},content_viewport:[0,contentY,...g.scroll],content_natural_height:natural,max_scroll:maximum,scroll:offset,basis:c.basis};
 }
 root.GuanchuangDetail={project,validateProfile,evaluate};if(typeof module!=='undefined'&&module.exports)module.exports=root.GuanchuangDetail;
})(globalThis);
