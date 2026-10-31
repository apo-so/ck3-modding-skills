"""Read-only native raster/font source bundle for local frontend painting."""
import base64,io,re
from pathlib import Path
from PIL import Image
from core.syntax import parse_bytes
from editing.title import require,digest

def build_skin(game_root,mod_root,button_reference):
    game,mod=Path(game_root),Path(mod_root);sources={};textures={}
    def source(relative):
        path=mod/relative;mount='mod'
        if not path.is_file():path=game/relative;mount='vanilla'
        require(path.is_file(),'SKIN_SOURCE_MISSING:'+relative);raw=path.read_bytes()
        record={'virtual_path':relative,'path':str(path),'mount':mount,'sha256':digest(raw)};sources[relative]=record
        return raw,record
    def document(relative):
        raw,ref=source(relative);doc=parse_bytes(raw,ref['mount']+'/'+relative);require(not doc.diagnostics,'SKIN_SOURCE_PARSE:'+relative);return doc
    def named(doc,key,name):
        found=[n for n in doc.root.walk()if n.key==key and(n.name==name or n.value('name')==name)]
        require(len(found)==1,'SKIN_DEFINITION_NOT_UNIQUE:'+name);return found[0]
    def props(node):
        return {n.key:n.atoms()if n.has_body else n.scalar for n in node.statements if n.kind=='assignment'and(not n.has_body or n.key in('margin','spriteborder','size','position','framesize'))}
    def texture(relative):
        if relative in textures:return relative
        raw,ref=source(relative)
        with Image.open(io.BytesIO(raw))as im:im=im.convert('RGBA');buf=io.BytesIO();im.save(buf,format='PNG');size=list(im.size);bbox=im.getbbox()
        textures[relative]={'source':ref,'size':size,'alpha_bbox':list(bbox)if bbox else None,'png_base64':base64.b64encode(buf.getvalue()).decode()};return relative
    windows=document('gui/shared/windows.gui');buttons=document('gui/shared/buttons.gui');areas={}
    if (mod/'gui/shared/backgrounds.gui').is_file()or(game/'gui/shared/backgrounds.gui').is_file():
        backgrounds=document('gui/shared/backgrounds.gui')
        for name in('Background_Area_Light','Background_Area_Dark'):
            definition=named(backgrounds,'template',name);p=props(definition);texture(p['texture']);overlays=[]
            for child in definition.statements:
                if child.key=='modify_texture':q=props(child);texture(q['texture']);overlays.append(q)
            areas[name]={'owner_id':definition.node_id,'properties':p,'overlays':overlays}
    background=named(windows,'template','Window_Background');bg=next(n for n in background.statements if n.key=='background');background_props=props(bg)
    margin=next(n for n in bg.statements if n.kind=='block'and n.name=='bg_margins');background_props['bg_margins']=props(margin)['margin'];texture(background_props['texture'])
    bg_overlay=next(n for n in bg.statements if n.key=='modify_texture');bg_overlay_props=props(bg_overlay);texture(bg_overlay_props['texture'])
    decoration=named(windows,'template','Window_Decoration');decorations=[]
    for icon in decoration.statements:
        if icon.key!='icon':continue
        p=props(icon);texture(p['texture']);decorations.append({'owner_id':icon.node_id,'props':p})
    button=named(buttons,'type','button_standard');button_props=props(button)
    overlay=next(n for n in button.statements if n.key=='modify_texture');overlay_props=props(overlay);texture(overlay_props['texture'])
    text_block=next(n for n in button.statements if n.key=='buttonText');button_text=next(n for n in text_block.statements if n.key=='text_single')
    # The existing source-resolved button frame record retains state frame numbers.
    require(button_reference['base_texture']['virtual_path']==button_props['texture'],'SKIN_BUTTON_REFERENCE_TEXTURE_CONFLICT')
    for key in('framesize','spriteborder','upframe','uphoverframe','uppressedframe','downframe','disableframe'):
        require(button_reference['properties'][key]['value']==button_props[key],'SKIN_BUTTON_REFERENCE_PROPERTY_CONFLICT:'+key)
    raw,base_ref=source(button_props['texture'])
    with Image.open(io.BytesIO(raw))as im:base=im.convert('RGBA')
    fw,fh=map(int,button_props['framesize']);require(base.width%fw==0 and base.height%fh==0,'SKIN_FRAME_GRID_INVALID');columns=base.width//fw
    for state,key in{'normal':'upframe','hover':'uphoverframe','pressed':'uppressedframe','selected':'downframe','disabled':'disableframe'}.items():
        frame=int(button_props[key]);x=(frame-1)%columns*fw;y=(frame-1)//columns*fh;buf=io.BytesIO();base.crop((x,y,x+fw,y+fh)).save(buf,format='PNG')
        require(button_reference['base_texture']['states'][state]=={'frame':frame,'png_base64':base64.b64encode(buf.getvalue()).decode()},'SKIN_BUTTON_FRAME_REPRESENTATION_CONFLICT')
    fonts=document('fonts/fonts.font');game_font=named(fonts,'font','StandardGameFont');font_faces=[]
    for style in('regular','bold'):
        spec=next(n for n in game_font.statements if n.key=='fontstyle'and n.value('style')==style);family=named(fonts,'fontfiles',spec.value('fontfiles'))
        groups=[n for n in family.statements if n.key=='group'and any(c.key=='languages'and'l_simp_chinese'in c.atoms()for c in n.statements)]
        require(len(groups)==1,'SKIN_CHINESE_FONT_GROUP_NOT_UNIQUE');chain=next(n.atoms()for n in groups[0].statements if n.key=='files');raw,ref=source(chain[0])
        font_faces.append({'style':style,'family':'GuanchuangNative'+style.title(),'source':ref,'source_chain':chain,'data_base64':base64.b64encode(raw).decode(),'format':'opentype'})
    # Local embedded open font; keep its license with the bundle.
    license_raw,license_ref=source('fonts/Noto_Sans_SC/OFL.txt')
    labels=document('gui/preload/labels.gui');font_templates=document('gui/preload/fonts.gui');format_doc=document('gui/preload/textformatting.gui')
    formats={n.value('name'):n.value('format')for n in format_doc.root.walk()if n.key=='format'and n.value('name')}
    def color(name,chain=()):
        require(name not in chain,'SKIN_COLOR_CYCLE');value=formats.get(name,'');m=re.fullmatch(r'color:\s*\{([^}]+)\}',value)
        if m:return [float(x.strip())for x in m[1].split(',')]
        return color(value,chain+(name,))if value in formats else None
    colors={key:color(key)for key in('medium','high','clickable','low','weak','E')if color(key)is not None}
    return {'schema':'guanchuang.native-skin.v1','source_roots':{'game':str(game.resolve()),'mod':str(mod.resolve())},'sources':list(sources.values()),'textures':textures,
       'window':{'background_owner':bg.node_id,'background':background_props,'overlay':bg_overlay_props,'decorations':decorations},'areas':areas,
       'button':{'owner_id':button.node_id,'properties':button_props,'text':props(button_text),'overlay':overlay_props,'base_texture':button_reference['base_texture']},
       'typography':{'faces':font_faces,'language':'l_simp_chinese','font_alias':'StandardGameFont','label_definitions':{name:named(labels,'type',name).to_dict()for name in('text_single','text_multi')},
         'font_templates':{name:named(font_templates,'template',name).to_dict()for name in('Font_Type_Standard','Font_Size_Small')},'colors':colors,'formats':formats,'license':{'source':license_ref,'text':license_raw.decode('utf-8-sig')}},
       'scope':'Actual DDS and original fonts for local preview. Candidate corner tiling/density/overlay and text baseline; native shader, mask, glow, text rasterizer and world rendering are not reproduced or accepted.'}

def verify_skin(skin,button_reference):
    require(skin.get('schema')=='guanchuang.native-skin.v1','SKIN_SCHEMA')
    for ref in skin['sources']:require(digest(Path(ref['path']).read_bytes())==ref['sha256'],'SKIN_SOURCE_CONFLICT')
    require(build_skin(skin['source_roots']['game'],skin['source_roots']['mod'],button_reference)==skin,'SKIN_REPRESENTATION_CONFLICT')
