/* One canonical source-owned fixture packet coordinates both rendered windows. */
(function(root){'use strict';
function mount(manifest){const journey=manifest.journey,$=id=>document.getElementById(id);let allocation,currentKey=null;
 const map=root.GuanchuangMapSidebarUI.mount(manifest.map_sidebar,manifest.resources,{controlled:true});
 function sync(key,packet){currentKey=key;const linked=journey.packets[key],tx=linked.transaction_key?journey.transactions[linked.transaction_key]:null;
  map.bindJourney(linked,tx,()=>allocation.action('preview_close'));
  $('journeyStatus').textContent=tx?`同一人工事务 ${tx.story_id}；目标 ${tx.target.id}；${tx.items.length} 项。${linked.state.kind==='pending_preview'?'当前地图预览；返回恢复此前确认清单与滚动。':'当前划拨核对；地图入口沿源码进入“调整后范围”。'} 影响军府汇总缺少层级基线，保持未知。`:'请在划拨样本中选择目标并进入待确认，再预览本次地图。';
  document.body.dataset.journeyTransaction=tx?.story_id||'';document.body.dataset.journeyTarget=tx?.target.id||'';document.body.dataset.journeyRoute=linked.state.kind==='pending_preview'?'map':'allocation';
 }
 allocation=root.GuanchuangAllocationUI.mount(manifest.allocation_preview,manifest.resources,{packetFor:key=>journey.packets[key],onState:sync});
 root.guanchuangAllocationPreview=allocation;root.guanchuangMapSidebarPreview=map;
 $('journeySource').textContent=JSON.stringify({scope:journey.scope,routes:journey.routes,references:journey.references.map(r=>({source:r.source,sha256:r.sha256,parser_diagnostics:r.parser_diagnostics})),game_effects_executed:false},null,2);
 return{allocation,map,getState:()=>structuredClone({key:currentKey,packet:journey.packets[currentKey],transaction:journey.transactions[journey.packets[currentKey].transaction_key]||null}),
  capture:()=>structuredClone({key:currentKey,allocation_snapshot:allocation.getSnapshot(),allocation_model:allocation.getModel(),map_snapshot:map.getSnapshot(),map_model:map.getModel()})};
}
root.GuanchuangJourneyUI={mount};
})(globalThis);
