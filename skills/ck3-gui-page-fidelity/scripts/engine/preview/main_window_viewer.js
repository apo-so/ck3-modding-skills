/* Actual full-window frontend; display fixtures only, no game actions. */
(function(root){'use strict';
function snapshot(preview,selected,tab,coverage,scenario,scrolls={}){if(scenario==='empty')selected=null;const s=structuredClone(preview.profiles[selected||'__none__']);if(!s)throw Error('MAIN_SELECTED_PROFILE_UNKNOWN');s.bindings['GetVariableSystem.cmm40_detail_tab']=tab;s.bindings['GetVariableSystem.cmm40_coverage_view']=coverage;s.scrolls={...scrolls};if(scenario==='empty')s.lists[preview.office_grid]=[];else if(scenario==='one')s.lists[preview.office_grid]=s.lists[preview.office_grid].slice(0,1);return s}
function mount(preview,resources,options={}){const $=id=>document.getElementById(id),G=root.GuanchuangScene,skin=root.GuanchuangSkin?.create(resources?.skin);let roots=structuredClone(preview.roots),sourceProps=skin?.styles(roots),selected=Object.keys(preview.title_labels)[0]||null,tab='overview',coverage='direct',scenario='overflow',scrolls={},model,hover=null,zoom=.75;
 const components=root.GuanchuangComponents?.create(resources?.native_components);
 const contains=(r,x,y)=>r&&x>=r[0]&&x<r[0]+r[2]&&y>=r[1]&&y<r[1]+r[3];
 function current(){return snapshot(preview,selected,tab,coverage,scenario,scrolls)}
 function placeholder(c,r,label){const[x,y,w,h]=r.rect;if(!w||!h)return;c.fillStyle='#161b1b';c.fillRect(x,y,w,h);c.strokeStyle='#58594d';c.strokeRect(x,y,w,h);c.fillStyle='#89887b';c.font='12px sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillText(label,x+w/2,y+h/2)}
 function draw(){model=G.project(roots,current(),preview.viewport,resources);const canvas=$('mainCanvas');canvas.width=model.viewport[0];canvas.height=model.viewport[1];canvas.style.width=canvas.width*zoom+'px';canvas.style.height=canvas.height*zoom+'px';const c=canvas.getContext('2d');c.fillStyle='#0c151d';c.fillRect(0,0,canvas.width,canvas.height);
  for(const row of model.rows){if(!row.clip[2]||!row.clip[3])continue;c.save();c.beginPath();c.rect(...row.clip_limit);c.clip();const p=sourceProps?.get(row.owner_id)||{},[x,y,w,h]=row.rect;
   if(row.tag==='window'){if(skin?.status.images==='READY')skin.window(c,row.rect);else{c.fillStyle='#20262a';c.fillRect(x,y,w,h)}}
   else if(row.tag==='background'){if(skin?.status.images==='READY')skin.area(c,row,p)}
   else if(row.tag.startsWith('button')){if(skin?.status.images==='READY')skin.button(c,row,row.instance_id===hover?'hover':'normal');else{c.fillStyle='#28332f';c.fillRect(x,y,w,h)}}
   else if(row.tag==='icon'){components?.icon(c,row,p)}
   else if(row.tag.startsWith('coa_')){if(!components?.paint(c,row))placeholder(c,row,'纹章占位')}else if(row.tag.startsWith('portrait')){if(!components?.paint(c,row))placeholder(c,row,'头像占位')}
   if(skin?.status.fonts==='READY')skin.text(c,row,p);else if(row.text&&row.tag.startsWith('text')){c.font=row.fontsize+'px sans-serif';c.fillStyle='#c5c1b4';c.fillText(row.text,x,y+row.fontsize)}c.restore();
  }
  $('mainScenario').value=scenario;$('mainTab').value=tab;$('mainCoverage').value=coverage;
  const left=model.scrollboxes.find(s=>s.owner_id===preview.named_owners.cmm40_office_list),right=model.scrollboxes.find(s=>s.owner_id===preview.named_owners.cmm40_detail_scroll);
  for(const[prefix,box]of[['mainList',left],['mainDetail',right]]){$(prefix+'Scroll').max=String(box?.maximum||0);$(prefix+'Scroll').value=String(box?.offset||0);$(prefix+'Scroll').disabled=!box||!box.maximum}
  $('mainStatus').textContent=`完整主窗源码候选1420×800；${scenario==='empty'?0:scenario==='one'?1:8}条军府样本；${selected?preview.title_labels[selected]:'无选择'} / ${tab}。人工文本/显示状态仅用于前端；${components?'头像纹章使用带来源的历史图像样本和原生边框。':'纹章头像仍占位。'}`;
  document.body.dataset.mainTitle=selected||'';document.body.dataset.mainTab=tab;document.body.dataset.mainScenario=scenario;
  root.GuanchuangStageUI?.notify();
 }
 function resetDetail(){delete scrolls[preview.named_owners.cmm40_detail_scroll]}
 function select(id){if(id!==null&&!Object.hasOwn(preview.title_labels,id))throw Error('MAIN_SELECTED_PROFILE_UNKNOWN');selected=id;resetDetail();draw()}
 function setTab(next){if(!['overview','military','holder','territory'].includes(next))throw Error('MAIN_TAB_INVALID');tab=next;resetDetail();draw()}
 function setCoverage(next){if(!['direct','all'].includes(next))throw Error('MAIN_COVERAGE_INVALID');coverage=next;resetDetail();draw()}
 function move(owner,offset){scrolls[owner]=offset;draw()}
 function setScenario(next){if(!['empty','one','overflow'].includes(next))throw Error('MAIN_SCENARIO_INVALID');scenario=next;selected=next==='empty'?null:Object.keys(preview.title_labels)[0];scrolls={};draw()}
 $('mainScenario').onchange=()=>setScenario($('mainScenario').value);$('mainTab').onchange=()=>setTab($('mainTab').value);$('mainCoverage').onchange=()=>{coverage=$('mainCoverage').value;resetDetail();draw()};$('mainClear').onclick=()=>select(null);$('mainZoom').onchange=()=>{const scale=Number($('mainZoom').value);if(![.5,.75,1].includes(scale))throw Error('MAIN_ZOOM_INVALID');zoom=scale;draw()};
 for(const[prefix,owner]of[['mainList',preview.named_owners.cmm40_office_list],['mainDetail',preview.named_owners.cmm40_detail_scroll]]){$(prefix+'Scroll').oninput=()=>move(owner,Number($(prefix+'Scroll').value));$(prefix+'Top').onclick=()=>move(owner,0);$(prefix+'Bottom').onclick=()=>move(owner,model.scrollboxes.find(s=>s.owner_id===owner)?.maximum||0)}
 const point=e=>[e.offsetX/zoom,e.offsetY/zoom];
 $('mainCanvas').onwheel=e=>{const[x,y]=point(e),box=model.scrollboxes.find(s=>contains(s.viewport,x,y));if(!box)return;e.preventDefault();move(box.owner_id,box.offset+e.deltaY*(e.deltaMode===1?60:e.deltaMode===2?box.viewport[3]:1))};
 $('mainCanvas').onmousemove=e=>{const[x,y]=point(e),row=[...model.rows].reverse().find(r=>r.tag.startsWith('button')&&contains(r.clip,x,y)),next=row?.instance_id||null;if(next!==hover){hover=next;draw()}};$('mainCanvas').onmouseleave=()=>{hover=null;draw()};
 $('mainCanvas').onclick=e=>{const[x,y]=point(e),hit=G.hitTest(model,x,y);$('mainSelection').textContent=hit?JSON.stringify({owner_id:hit.owner_id,instance_id:hit.instance_id,rect:hit.rect,ordered_callbacks:hit.callbacks,contexts:hit.contexts,frontend_only:true},null,2):'没有动作控件。';
  const title=model.rows.find(r=>r.owner_id===options.targets?.title.owner_id&&contains(r.clip,x,y));if(title){options.onEditTarget?.('title');return}if(hit?.owner_id===options.targets?.button.owner_id){options.onEditTarget?.('button');return}
  const row=current().lists[preview.office_grid].find(r=>hit?.instance_id.includes('/row:'+r.row_id+'/'));if(row){select(row.title_id);return}
  const nav=preview.tabs.find(t=>t.owner_id===hit?.owner_id);if(nav){setTab(nav.value);return}
  for(const callback of hit?.callbacks||[]){const match=callback.expression?.match(/GetVariableSystem.Set\('cmm40_coverage_view','(direct|all)'\)/);if(match){coverage=match[1];resetDetail();draw();return}}
 };
 $('mainSource').textContent=JSON.stringify({source:preview.source,source_sha256:preview.source_sha256,scope:preview.scope,visual_templates:Object.keys(preview.visual_templates),native_visual:'NOT_VERIFIED'},null,2);
 function setEdits(values){roots=structuredClone(preview.roots);const visit=n=>{if(n.id===options.targets?.title.owner_id){n.props.raw_text=values.title.raw_text;n.props.fontsize=String(values.title.fontsize)}if(n.id===options.targets?.button.owner_id){n.props.raw_text=values.button.raw_text;n.props.size=[String(values.button.width),String(values.button.height)]}for(const c of [...n.children,...n.item])visit(c)};for(const r of roots)visit(r);sourceProps=skin?.styles(roots);draw()}
 if(components)components.ready.then(draw).catch(e=>{$('mainStatus').textContent='图像组件加载失败：'+e.message});if(skin)skin.ready.then(draw).catch(e=>{$('mainStatus').textContent='资源加载失败：'+e.message});draw();return{getModel:()=>structuredClone(model),getSnapshot:current,select,setTab,setCoverage,setScenario,move,setEdits,getZoom:()=>zoom};
}
root.GuanchuangMainWindowUI={snapshot,mount};
})(globalThis);
