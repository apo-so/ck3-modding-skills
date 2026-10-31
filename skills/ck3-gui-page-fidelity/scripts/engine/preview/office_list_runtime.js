/* Source-derived, single-column fixture model. No game callbacks or live bindings. */
(function(root){
 'use strict';const need=(ok,c)=>{if(!ok)throw new Error(c)};
 function validate(c,s){
  need(s&&s.schema==='guanchuang.office-list-snapshot.v1','LIST_SNAPSHOT_SCHEMA');
  need(s.origin==='SYNTHETIC_FIXTURE_NOT_GAME_DATA'&&s.datamodel===c.datamodel,'LIST_SNAPSHOT_SOURCE');
  need(Array.isArray(s.rows)&&s.rows.length<=10000,'LIST_ROWS_REQUIRED_OR_TOO_MANY');const ids=new Set();
  for(const r of s.rows){need(r&&typeof r.row_id==='string'&&r.row_id&&!ids.has(r.row_id),'LIST_ROW_ID_NOT_UNIQUE');ids.add(r.row_id);
   need(typeof r.title_id==='string'&&r.title_id&&r.scope_type==='Title','LIST_TITLE_CONTEXT_REQUIRED');
   need(r.bindings&&typeof r.bindings==='object'&&!Array.isArray(r.bindings)&&Object.values(r.bindings).every(v=>typeof v==='string'),'LIST_TEXT_BINDINGS_REQUIRED')}
  need(s.selected_title_id===null||typeof s.selected_title_id==='string','LIST_SELECTED_ID_INVALID');return s.rows;
 }
 function layout(c,s,scroll=0){
  const data=validate(c,s);need(typeof scroll==='number'&&Number.isFinite(scroll),'LIST_SCROLL_NOT_FINITE');
  const g=c.geometry,[, ,vw,vh]=g.viewport,[rw,rh]=g.row_size,[bw,bh]=g.button_size;
  const natural=g.content_top+data.length*g.row_step,maximum=Math.max(0,natural-vh),offset=Math.min(Math.max(0,scroll),maximum);
  const rows=data.map((r,i)=>{const top=g.content_top+i*g.row_step-offset,bottom=Math.min(vh,top+rh),clipTop=Math.max(0,top),right=Math.min(vw,rw),hitBottom=Math.min(vh,top+bh),selected=r.title_id===s.selected_title_id;
   const texts=c.texts.map(f=>{const badge=f.visible===c.selection_expression,value=badge?f.expression:r.bindings[f.expression];return {...f,text:value===undefined?'〔未提供绑定值〕':value,status:value===undefined?'UNKNOWN':'FIXTURE',visible:badge?selected:true}});
   return {row_id:r.row_id,title_id:r.title_id,index:i,rect:[0,top,rw,rh],clip:bottom>clipTop&&right>0?[0,clipTop,right,bottom-clipTop]:null,
    hit_clip:hitBottom>clipTop?[0,clipTop,Math.min(vw,bw),hitBottom-clipTop]:null,selected,texts};
  });
  return {basis:c.basis,origin:s.origin,viewport:g.viewport,content_natural_height:natural,content_allocation_height:Math.max(vh,natural),max_scroll:maximum,scroll:offset,rows,row_count:data.length,
   visible_row_ids:rows.filter(r=>r.clip).map(r=>r.row_id),selected_title_id:s.selected_title_id,selection_status:s.selected_title_id===null?'NONE':rows.some(r=>r.selected)?'PRESENT':'STALE'};
 }
 function hitTest(model,x,y){need([x,y].every(v=>typeof v==='number'&&Number.isFinite(v)),'LIST_POINT_NOT_FINITE');
  for(const r of model.rows){const c=r.hit_clip;if(c&&x>=c[0]&&x<c[0]+c[2]&&y>=c[1]&&y<c[1]+c[3])return {row_id:r.row_id,title_id:r.title_id}}return null;
 }
 root.GuanchuangOfficeList={validate,layout,hitTest};if(typeof module!=='undefined'&&module.exports)module.exports=root.GuanchuangOfficeList;
})(globalThis);
