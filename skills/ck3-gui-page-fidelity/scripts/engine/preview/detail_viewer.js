/* Source-authored detail canvas; only tabs/coverage are simulated preview commands. */
(function(root){
 'use strict';
 function mount(preview){const $=id=>document.getElementById(id),G=root.GuanchuangDetail,c=preview.contract;
  let selected=null,tab='overview',coverage='direct',scroll=0,model=null;
  function ellipsis(ctx,text,w){let chars=Array.from(text);if(ctx.measureText(text).width<=w)return text;while(chars.length&&ctx.measureText(chars.join('')+'…').width>w)chars.pop();return chars.join('')+'…'}
  function draw(){model=G.project(preview,selected,tab,coverage,scroll);scroll=model.scroll;const canvas=$('detailCanvas');canvas.width=c.geometry.pane[0];canvas.height=Math.max(c.geometry.pane[1],Number(c.empty.props.size[1]));const ctx=canvas.getContext('2d');ctx.fillStyle='#101b24';ctx.fillRect(0,0,canvas.width,canvas.height);
   if(model.status!=='FIXTURE_DETAIL'){
    const message=model.status==='NO_SELECTION'?c.empty.children.find(n=>n.props.raw_text)?.props.raw_text||'请选择军府':'缺少此对象的测试快照，详情未知';ctx.fillStyle='#d5dbcb';ctx.font='21px Microsoft YaHei,system-ui,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(message,canvas.width/2,canvas.height/2);
   }else{
    ctx.save();ctx.beginPath();ctx.rect(0,0,canvas.width,canvas.height);ctx.clip();
    for(const row of model.rows){const[x,y,w,h]=row.rect;ctx.save();if(row.clip){ctx.beginPath();ctx.rect(...row.clip);ctx.clip()}
     if(row.tag==='background'){ctx.fillStyle='#2a3d43';ctx.fillRect(x,y,w,h)}
     if(row.tag.startsWith('button')){ctx.fillStyle=row.enabled.value===false?'#253038':'#304b51';ctx.fillRect(x,y,w,h);ctx.strokeStyle=row.conditional?'#c6a566':'#6b8382';ctx.setLineDash(row.conditional?[3,3]:[]);ctx.strokeRect(x,y,w,h)}
     if(row.tag.startsWith('portrait')||row.tag.startsWith('coa_')){ctx.strokeStyle='#536970';ctx.strokeRect(x,y,w,Math.max(h,40))}
     if(row.text&&(row.tag.startsWith('text')||row.tag.startsWith('button'))){ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.fillStyle=row.text_status==='UNKNOWN'||row.conditional?'#e2b785':'#ded8b8';ctx.font=row.fontsize+'px Microsoft YaHei,system-ui,sans-serif';ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(ellipsis(ctx,row.text,w),x,y+Math.min(h/2,row.fontsize));ctx.restore()}
     ctx.restore();
    }
    let x=0;for(const item of c.tabs){const[w,h]=item.size;ctx.fillStyle=item.value===tab?'#547567':'#28414c';ctx.fillRect(x,model.tabs.y,w,h);ctx.strokeStyle='#6b8382';ctx.strokeRect(x,model.tabs.y,w,h);ctx.fillStyle='#e6ddbd';ctx.font='16px Microsoft YaHei,system-ui,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(item.label,x+w/2,model.tabs.y+h/2);x+=w+c.tab_spacing}
    ctx.restore();
   }
   $('detailScroll').max=String(model.max_scroll);$('detailScroll').value=String(scroll);$('detailScroll').disabled=model.max_scroll===0;
   const unknown=model.rows.filter(r=>r.text_status==='UNKNOWN'||r.conditional).length;
   $('detailStatus').textContent=(selected?'示例对象 '+selected:'未选择军府')+'；'+(model.status==='FIXTURE_DETAIL'?`页签 ${tab}；滚动 ${scroll} / ${model.max_scroll}；${unknown} 个绑定或条件仍未知。`:'当前 '+model.status)+' 所有动作均为预览状态，未执行游戏回调。';
   document.body.dataset.detailTitle=selected||'';document.body.dataset.detailTab=tab;document.body.dataset.detailStatus=model.status;document.body.dataset.detailScroll=String(scroll);
  }
  function select(title){if(title!==selected){selected=title;scroll=0;draw()}}
  function setTab(value){tab=value;scroll=0;draw()}
  $('detailScroll').oninput=()=>{scroll=Number($('detailScroll').value);draw()};$('detailTop').onclick=()=>{scroll=0;draw()};$('detailBottom').onclick=()=>{scroll=G.project(preview,selected,tab,coverage).max_scroll;draw()};
  $('detailCanvas').onwheel=e=>{if(model.status!=='FIXTURE_DETAIL')return;const[,top,,height]=model.content_viewport;if(e.offsetY<top||e.offsetY>=top+height)return;e.preventDefault();scroll+=e.deltaY*(e.deltaMode===1?60:e.deltaMode===2?height:1);draw()};
  $('detailCanvas').onclick=e=>{if(model.status!=='FIXTURE_DETAIL')return;let x=0;for(const item of c.tabs){if(e.offsetX>=x&&e.offsetX<x+item.size[0]&&e.offsetY>=model.tabs.y&&e.offsetY<model.tabs.y+item.size[1]){setTab(item.value);return}x+=item.size[0]+c.tab_spacing}
   for(const row of [...model.rows].reverse()){const[x,y,w,h]=row.rect;if(e.offsetX<x||e.offsetX>=x+w||e.offsetY<y||e.offsetY>=y+h)continue;if(row.clip){const[cx,cy,cw,ch]=row.clip;if(e.offsetX<cx||e.offsetX>=cx+cw||e.offsetY<cy||e.offsetY>=cy+ch)continue}
    for(const call of row.callbacks){const match=call.expression.match(/^\[GetVariableSystem.Set\('cmm40_coverage_view','(direct|all)'\)\]$/);if(match){coverage=match[1];scroll=0;draw();return}}
    if(row.callbacks.length){$('detailStatus').textContent='该控件的原始游戏回调已保留；预览不执行此动作。';return}
   }
  };
  $('detailSource').textContent=JSON.stringify({geometry:c.geometry,contexts:c.selected_contexts,source_hashes:c.subtree_hashes,reference:preview.reference,basis:c.basis,unknown_policy:c.unknown_policy},null,2);
  draw();return{select,setTab,getModel:()=>structuredClone(model),move:value=>{scroll=value;draw()}};
 }
 root.GuanchuangDetailUI={mount};
})(globalThis);
