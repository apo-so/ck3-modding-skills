/* Shared source-scene paint; geometry comes only from the supplied model. */
(function(root){'use strict';
function create(resources){const skin=root.GuanchuangSkin?.create(resources?.skin),components=root.GuanchuangComponents?.create(resources?.native_components),maps=new WeakMap(),solid=resources?.native_components?.contract.definitions.Background_Area_Solid?.tree.ordered_statements.find(p=>p.key==='color')?.ordered_statements.filter(p=>p.kind==='atom').map(p=>Number(p.scalar));
 function styles(roots){if(!maps.has(roots)){const m=new Map(),visit=n=>{m.set(n.id,n.props);for(const c of [...n.children,...n.item])visit(c)};for(const r of roots)visit(r);maps.set(roots,m)}return maps.get(roots)}
 function paint(c,model,roots,options={}){const props=styles(roots);c.fillStyle='#0c151d';c.fillRect(0,0,...model.viewport);
  for(const row of model.rows){if(!row.clip[2]||!row.clip[3])continue;const p=props.get(row.owner_id)||{},[x,y,w,h]=row.rect;c.save();c.beginPath();c.rect(...row.clip_limit);c.clip();
   if(row.owner_id===options.mapBackground){if(skin?.status.images==='READY')skin.window(c,row.rect,false)}
   else if(row.tag==='window'&&!options.mapBackground){if(skin?.status.images==='READY')skin.window(c,row.rect);else{c.fillStyle='#20262a';c.fillRect(x,y,w,h)}}
   else if(row.tag==='background'){if(p.using==='Background_Area_Solid'&&solid){c.fillStyle='rgba('+solid.slice(0,3).map(v=>255*v).join(',')+','+(solid[3]??1)+')';c.fillRect(x,y,w,h)}else if(skin?.status.images==='READY')skin.area(c,row,p)}
   else if(row.tag.startsWith('button')){const parentDisabled=model.rows.find(r=>r.owner_id===row.window&&r.tag==='window')?.enabled.value===false,paintRow=parentDisabled?{...row,enabled:{value:false}}:row;if(skin?.status.images==='READY')skin.button(c,paintRow,options.hover===row.instance_id?'hover':'normal')}
   else if(row.tag==='icon'){components?.icon(c,row,p)}
   else if(row.tag.startsWith('coa_')||row.tag.startsWith('portrait')){if(!components?.paint(c,row)){c.strokeStyle='#77776b';c.strokeRect(x,y,w,h)}}
   if(skin?.status.fonts==='READY')skin.text(c,row,p);c.restore();
  }
 }
 return{paint,ready:Promise.all([skin?.ready,components?.ready]),status:{skin:skin?.status,components:components?.status}};
}
root.GuanchuangCanvasRenderer={create};
})(globalThis);
