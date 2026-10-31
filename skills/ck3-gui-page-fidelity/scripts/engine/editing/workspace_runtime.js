/* Immutable baseline: edits on every selected owner compose into one transaction. */
(function(root){
  'use strict';
  const G=root.GuanchuangTitle, need=(ok,code)=>{if(!ok)throw new Error(code)};
  function request(m,edits){return {schema:'guanchuang.workspace-edit-request.v1',
    source:m.source,window:m.window,base_sha256:m.base_sha256,edits};}
  async function apply(m,r){
    need(m.schema==='guanchuang.gui-workspace.v1','WORKSPACE_SCHEMA');
    need(r.schema==='guanchuang.workspace-edit-request.v1','REQUEST_SCHEMA');
    need(r.base_sha256===m.base_sha256,'SOURCE_CONFLICT');
    need(r.source===m.source&&r.window===m.window,'TARGET_CONFLICT');
    need(r.edits&&typeof r.edits==='object'&&!Array.isArray(r.edits)&&
      Object.keys(r.edits).every(k=>Object.hasOwn(m.targets,k)),'UNSUPPORTED_TARGET');
    const fields={},changes={},encoders={};
    for(const [id,target]of Object.entries(m.targets)){
      need(target.base_sha256===m.base_sha256&&target.source===m.source&&target.window===m.window,'TARGET_BASE_CONFLICT');
      const selected=Object.hasOwn(r.edits,id)?r.edits[id]:{};
      need(selected&&typeof selected==='object'&&!Array.isArray(selected)&&
        Object.keys(selected).every(k=>Object.hasOwn(target.fields,k)),'UNSUPPORTED_EDIT');
      for(const [field,value]of Object.entries(target.fields)){
        const key=id+'.'+field;fields[key]=value;
        encoders[key]=field==='raw_text'?G.literal:field==='fontsize'?G.font:G.dimension;
      }
      for(const [field,value]of Object.entries(selected))changes[id+'.'+field]=value;
    }
    const result=await G.patch({...m,fields},changes,encoders);
    return {...result,request:r};
  }
  root.GuanchuangWorkspace={request,apply};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.GuanchuangWorkspace;
})(globalThis);
