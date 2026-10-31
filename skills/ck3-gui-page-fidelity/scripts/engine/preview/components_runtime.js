/* Native source component frames and explicitly labeled historical image samples. */
(function(root){'use strict';const cache=new WeakMap();
function create(registry){if(!registry)return null;if(cache.has(registry))return cache.get(registry);const images=new Map(),status={images:'LOADING'};
 const load=(key,data)=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{images.set(key,im);resolve()};im.onerror=()=>reject(Error('COMPONENT_IMAGE_FAILED:'+key));im.src='data:image/png;base64,'+data});
 const ready=Promise.all([...Object.entries(registry.textures).map(([k,v])=>load(k,v.png_base64)),...Object.entries(registry.samples).map(([k,v])=>load('sample:'+k,v.png_base64))]).then(()=>{status.images='READY'});
 function sprite(ctx,key,frameSize,frame,rect){const im=images.get(key);if(!im)return false;const size=registry.textures[key]?.size||registry.samples[key.replace('sample:','')]?.size;if(!size)return false;const[fw,fh]=frameSize||size,cols=Math.floor(size[0]/fw),rows=Math.floor(size[1]/fh);frame=Number(frame||1);if(!Number.isInteger(frame)||frame<1||frame>cols*rows)throw Error('COMPONENT_FRAME_INVALID:'+key);ctx.drawImage(im,(frame-1)%cols*fw,Math.floor((frame-1)/cols)*fh,fw,fh,...rect);return true}
 function paint(ctx,row){const metric=registry.contract.metrics[row.tag];if(!metric||status.images!=='READY')return false;const[x,y,w,h]=row.rect;
  if(metric.kind==='portrait'){const c=metric.background_color;ctx.fillStyle='rgba('+c.slice(0,3).map(n=>Math.round(255*n)).join(',')+','+c[3]+')';ctx.fillRect(x,y,w,h);sprite(ctx,'sample:portrait',null,1,[x+(w-100)/2,y+h-125,100,125]);const q=metric.rank_frame,[ml,mt,mr,mb]=q.margins;sprite(ctx,q.texture,q.frame_size,registry.sample_frames.portrait_rank,[x+ml,y+mt,w-ml-mr,h-mt-mb]);return true}
  if(metric.kind==='house'){const[bw,bh]=metric.body_size,[cw,ch]=metric.coa_size,bx=x+(metric.size[0]-bw)/2,by=y+(metric.size[1]-bh)/2;sprite(ctx,'sample:house',null,1,[bx+(bw-cw)/2,by+(bh-ch)/2,cw,ch]);sprite(ctx,'gfx/interface/coat_of_arms/frames/house_frame_02.dds',metric.frame_size,registry.sample_frames.house_prestige,[bx,by,bw,bh]);return true}
  const off=row.component_override?.flow_offset||metric.flow_offset||[0,0],xx=x+off[0],yy=y+off[1],[cw,ch]=metric.crown.size,[bw,bh]=metric.body_size,[iw,ih]=metric.coa_size;
  sprite(ctx,metric.crown.texture,metric.crown.size,registry.sample_frames.title_crown,[xx+(metric.size[0]-cw)/2,yy,cw,ch]);const by=yy+ch+metric.spacing,bx=xx+(metric.size[0]-bw)/2;sprite(ctx,'sample:coa',null,1,[bx+(bw-iw)/2,by+(bh-ih)/2,iw,ih]);sprite(ctx,metric.frame_texture,null,1,[bx+(bw-metric.frame_size[0])/2,by+(bh-metric.frame_size[1])/2,...metric.frame_size]);return true;
 }
 function icon(ctx,row,props={}){let key=props.texture;if(registry.dynamic_textures[key])key=registry.dynamic_textures[key];if(!registry.textures[key]||status.images!=='READY')return false;const frame=/^\d+$/.test(String(props.frame||'1'))?Number(props.frame||1):1;return sprite(ctx,key,props.framesize?.map(Number),frame,row.rect)}
 const api={ready,status,paint,icon,sprite,registry};cache.set(registry,api);return api;
}
root.GuanchuangComponents={create};
})(globalThis);
