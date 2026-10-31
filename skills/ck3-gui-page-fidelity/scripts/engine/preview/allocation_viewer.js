/* Shared scene painter/controller for compiled source-backed synthetic state branches. */
(function(root){'use strict';
function mount(preview,resources=null,options={}){const $=id=>document.getElementById(id),G=root.GuanchuangScene;let key=preview.seeds.no_target,scrolls={},model=null,selectedScroll=null;const remembered=new Map();
 const skin=root.GuanchuangSkin?.create(resources?.skin),skinStyles=skin?.styles(preview.roots);
 const contains=(r,x,y)=>r&&x>=r[0]&&x<r[0]+r[2]&&y>=r[1]&&y<r[1]+r[3];
 const names={choose:'示例选择目标',assign_pending:'示例划拨→待确认',assign_direct:'示例直接变化',confirm_changed:'示例确认→变化',confirm_stale:'示例确认→过期',cancel:'示例取消',info:'示例查看归属',info_close:'归属返回',preview:'待确认地图预览',preview_close:'地图预览返回'};
 function text(ctx,row){const[x,y,w,h]=row.rect;if(!row.text||!row.tag.startsWith('text')&&!row.tag.startsWith('button'))return;ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.fillStyle=row.text_status.startsWith('UNKNOWN')||row.conditional?'#e4b381':'#e3dbc5';ctx.font=row.fontsize+'px Microsoft YaHei,system-ui,sans-serif';ctx.textAlign='left';ctx.textBaseline='top';
  const lines=row.text.replace(/\\n/g,'\n').split('\n');let yy=y;for(const line of lines){let chunk='';for(const char of Array.from(line)){if(chunk&&ctx.measureText(chunk+char).width>w){ctx.fillText(chunk,x,yy);yy+=row.fontsize*1.3;chunk='';if(yy>=y+h)break}chunk+=char}if(yy<y+h)ctx.fillText(chunk,x,yy);yy+=row.fontsize*1.3;if(yy>=y+h)break}ctx.restore()}
 function currentPacket(){const base=preview.graph[key];return options.packetFor?{...base,...options.packetFor(key)}:base}
 function draw(){const packet=currentPacket(),snapshot={...(packet.allocation_snapshot||packet.snapshot),scrolls};model=G.project(preview.roots,snapshot,preview.viewport,resources);const canvas=$('allocationCanvas');canvas.width=model.viewport[0];canvas.height=model.viewport[1];const ctx=canvas.getContext('2d');ctx.fillStyle='#0c151d';ctx.fillRect(0,0,canvas.width,canvas.height);
  for(const row of model.rows){if(row.clip[2]<=0||row.clip[3]<=0)continue;ctx.save();ctx.beginPath();ctx.rect(...row.clip_limit);ctx.clip();const[x,y,w,h]=row.rect;
   if(row.tag==='window'){if(skin&&skin.status.images==='READY')skin.window(ctx,row.rect);else{ctx.fillStyle='#172831';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#829083';ctx.strokeRect(x,y,w,h)}}
   else if(row.tag.startsWith('button')){if(skin&&skin.status.images==='READY')skin.button(ctx,row);else{ctx.fillStyle=row.enabled.value===false?'#26323b':'#2c4650';ctx.fillRect(x,y,w,h);ctx.strokeStyle=row.conditional||row.enabled.status!=='KNOWN'?'#a38b66':'#67878a';ctx.setLineDash(row.conditional?[3,3]:[]);ctx.strokeRect(x,y,w,h)}}
   else if(row.tag.startsWith('coa_')){ctx.strokeStyle='#7b8880';ctx.strokeRect(x,y,w,h)}
   else if(row.tag==='scrollbox'||row.tag==='scrollarea'){ctx.strokeStyle='#4b6877';ctx.strokeRect(x,y,w,h)}
   if(skin&&skin.status.fonts==='READY')skin.text(ctx,row,skinStyles.get(row.owner_id));else text(ctx,row);ctx.restore();
  }
  if(!model.rows.length){ctx.fillStyle='#d3c69f';ctx.font='24px Microsoft YaHei,system-ui,sans-serif';ctx.textAlign='center';ctx.fillText(options.packetFor?'当前事务进入下方地图侧栏；返回后恢复此核对窗口。':'当前样本进入地图预览：按源码隐藏三个划拨窗口。',canvas.width/2,canvas.height/2)}
  const select=$('allocationScrollOwner');select.replaceChildren();for(const[order,s]of model.scrollboxes.entries()){const option=document.createElement('option'),row=model.rows.find(r=>r.owner_id===s.owner_id);option.value=s.owner_id;option.textContent=row?.name||'滚动区 '+(order+1);select.appendChild(option)}
  if(!model.scrollboxes.some(s=>s.owner_id===selectedScroll))selectedScroll=model.scrollboxes[0]?.owner_id||null;select.value=selectedScroll||'';
  const current=model.scrollboxes.find(s=>s.owner_id===selectedScroll);$('allocationScroll').max=String(current?.maximum||0);$('allocationScroll').value=String(current?.offset||0);$('allocationScroll').disabled=!current||current.maximum===0;
  for(const action of Object.keys(names))$('allocationAction_'+action).disabled=!Object.hasOwn(packet.edges,action);
  const visible=model.windows.filter(w=>w.rect).map(w=>w.name),unknown=model.rows.filter(r=>r.text_status.startsWith('UNKNOWN')||r.conditional).length;
  $('allocationStatus').textContent=`人工样本 ${packet.state.kind}；显示 ${visible.join(' + ')||'无划拨窗口'}；${packet.sample_count} 行样本；${unknown} 个文本/条件仍未知。实际IsValid和游戏效果未执行。`;
  $('allocationState').textContent=JSON.stringify({origin:packet.state.origin,kind:packet.state.kind,target_title_id:packet.state.target_title_id,pending_story_id:packet.state.pending_story_id,operation_story_id:packet.state.operation_story_id,notice:packet.state.notice,game_effects_executed:false,source_commands:Object.fromEntries(Object.entries(packet.edges).map(([k,e])=>[k,e.command]))},null,2);
  document.body.dataset.allocationKind=packet.state.kind;document.body.dataset.allocationNode=key;document.body.dataset.allocationWindows=visible.join(',');document.body.dataset.allocationCount=String(packet.sample_count);
  if(options.onState)options.onState(key,packet);
  root.GuanchuangStageUI?.notify();
 }
 function move(owner,amount){if(!owner)return;scrolls[owner]=amount;selectedScroll=owner;draw()}
 function enter(next,reset=false){remembered.set(key,{...scrolls});key=next;scrolls=reset?{}:{...(remembered.get(key)||{})};selectedScroll=null;draw()}
 $('allocationScenario').onchange=()=>enter(preview.seeds[$('allocationScenario').value],true);
 $('allocationScrollOwner').onchange=()=>{selectedScroll=$('allocationScrollOwner').value;draw()};$('allocationScroll').oninput=()=>move(selectedScroll,Number($('allocationScroll').value));$('allocationTop').onclick=()=>move(selectedScroll,0);$('allocationBottom').onclick=()=>move(selectedScroll,model.scrollboxes.find(s=>s.owner_id===selectedScroll)?.maximum||0);
 for(const action of Object.keys(names))$('allocationAction_'+action).onclick=()=>{const edge=preview.graph[key].edges[action];if(edge)enter(edge.target);else $('allocationStatus').textContent='该测试分支未编排此步骤；这不代表游戏限制。'};
 $('allocationCanvas').onwheel=e=>{const window=[...model.windows].reverse().find(w=>contains(w.rect,e.offsetX,e.offsetY));const box=[...model.scrollboxes].reverse().find(s=>s.window===window?.owner_id&&contains(s.viewport,e.offsetX,e.offsetY));if(!box)return;e.preventDefault();move(box.owner_id,box.offset+e.deltaY*(e.deltaMode===1?60:e.deltaMode===2?box.viewport[3]:1))};
 $('allocationCanvas').onclick=e=>{const hit=G.hitTest(model,e.offsetX,e.offsetY);$('allocationSelection').textContent=hit?JSON.stringify({owner_id:hit.owner_id,instance_id:hit.instance_id,window:hit.window,rect:hit.rect,clip:hit.clip,contexts:hit.contexts,ordered_callbacks:hit.callbacks,enabled:hit.enabled,readonly:true},null,2):'此处没有可检查的回调控件，或被上层窗口遮挡。';document.body.dataset.allocationHit=hit?.instance_id||''};
 $('allocationSource').textContent=JSON.stringify({scope:preview.scope,source_files:preview.contract.sources,windows:preview.contract.gui.windows.map(w=>({name:w.name,size:w.size,visible:w.visible})),grids:preview.contract.gui.grids.map(g=>({owner_id:g.owner_id,datamodel:g.datamodel,row_context:g.row_context,step:g.step})),native_render:'NOT_RUN'},null,2);
 if(skin)skin.ready.then(draw).catch(e=>{$('allocationStatus').textContent='原生资源加载失败：'+e.message});
 draw();return{getModel:()=>structuredClone(model),getPacket:()=>structuredClone(currentPacket()),getSnapshot:()=>structuredClone({...((currentPacket().allocation_snapshot)||currentPacket().snapshot),scrolls}),getKey:()=>key,move,enterSeed:seed=>enter(preview.seeds[seed],true),action:name=>$('allocationAction_'+name).onclick()};
}
root.GuanchuangAllocationUI={mount};
})(globalThis);
