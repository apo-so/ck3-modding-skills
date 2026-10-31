/* Fixture-only canvas view. Input changes preview state; it never edits GUI or runs callbacks. */
(function(root){
 'use strict';
 function mount(preview,onChange=null){
  const $=id=>document.getElementById(id),G=root.GuanchuangOfficeList,c=preview.contract;
  let scenario='empty',snapshot=structuredClone(preview.scenarios[scenario]),scroll=0,model=null;
  function elide(ctx,text,width){if(ctx.measureText(text).width<=width)return text;let chars=Array.from(text);while(chars.length&&ctx.measureText(chars.join('')+'…').width>width)chars.pop();return chars.join('')+'…'}
  function draw(){
   model=G.layout(c,snapshot,scroll);scroll=model.scroll;
   const canvas=$('listCanvas');canvas.width=model.viewport[2];canvas.height=model.viewport[3];const ctx=canvas.getContext('2d');
   ctx.fillStyle='#101b24';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.save();ctx.beginPath();ctx.rect(0,0,canvas.width,canvas.height);ctx.clip();
   for(const row of model.rows){if(!row.clip)continue;const y=row.rect[1];ctx.save();ctx.beginPath();ctx.rect(...row.clip);ctx.clip();
    ctx.fillStyle=row.selected?'#466256':'#243947';ctx.fillRect(0,y,...c.geometry.button_size);ctx.strokeStyle=row.selected?'#c6de94':'#58717b';ctx.strokeRect(0,y,...c.geometry.button_size);
    ctx.strokeStyle='#719090';ctx.strokeRect(8,y+12,46,55);ctx.fillStyle='#9eafb4';ctx.font='12px system-ui';ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText('纹章',12,y+40);
    for(const f of row.texts){if(!f.visible)continue;const[x,dy,w,h]=f.rect;ctx.save();ctx.beginPath();ctx.rect(x,y+dy,w,h);ctx.clip();ctx.font=f.fontsize+'px Microsoft YaHei,system-ui,sans-serif';ctx.fillStyle=f.status==='UNKNOWN'?'#f2b987':'#e1d9b3';ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(f.elide==='right'?elide(ctx,f.text,w):f.text,x,y+dy+h/2);ctx.restore()}
    ctx.restore();
   }ctx.restore();
   $('listScroll').max=String(model.max_scroll);$('listScroll').value=String(scroll);$('listScroll').disabled=model.max_scroll===0;
   $('listStatus').textContent=`示例 ${model.row_count} 行；滚动 ${scroll} / ${model.max_scroll}；当前可见 ${model.visible_row_ids.length} 行；选择 ${snapshot.selected_title_id||'无'}。`+(model.row_count===0?' 源码未声明空列表文字。':'');
   document.body.dataset.listScenario=scenario;document.body.dataset.listCount=String(model.row_count);document.body.dataset.listScroll=String(scroll);document.body.dataset.listMaxScroll=String(model.max_scroll);document.body.dataset.listSelected=snapshot.selected_title_id||'';
   if(onChange)onChange(structuredClone(snapshot),scenario);
  }
  function move(value){scroll=value;draw()}
  $('listScenario').onchange=()=>{scenario=$('listScenario').value;snapshot=structuredClone(preview.scenarios[scenario]);scroll=0;draw()};
  $('listScroll').oninput=()=>move(Number($('listScroll').value));$('listTop').onclick=()=>move(0);$('listBottom').onclick=()=>{move(G.layout(c,snapshot).max_scroll)};
  $('listCanvas').onwheel=e=>{e.preventDefault();const scale=e.deltaMode===1?60:e.deltaMode===2?c.geometry.viewport[3]:1;move(scroll+e.deltaY*scale)};
  $('listCanvas').onclick=e=>{const hit=G.hitTest(model,e.offsetX,e.offsetY);if(hit){snapshot.selected_title_id=hit.title_id;draw();document.body.dataset.listHitRow=hit.row_id}};
  $('listClear').onclick=()=>{snapshot.selected_title_id=null;draw()};
  $('listSource').textContent=JSON.stringify({contract:c,reference:preview.reference},null,2);
  draw();return {getModel:()=>model,getSnapshot:()=>structuredClone(snapshot),move};
 }
 root.GuanchuangOfficeListUI={mount};
})(globalThis);
