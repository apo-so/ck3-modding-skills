"""Source-font measurements of explicit display samples, not native/browser ink."""
import base64,io,re
from PIL import ImageFont
from editing.title import require,digest

def plain(text):return re.sub(r'#(?:[A-Za-z_][A-Za-z0-9_]*|!)\s?','',str(text)).replace('\\n','\n')
def key(text,size,style):
    import json
    return json.dumps([text,int(size)if float(size).is_integer()else size,style],ensure_ascii=False,separators=(',',':'))

def measure_requests(skin,requests):
    faces={f['style']:f for f in skin['typography']['faces']};fonts={};entries=[]
    for request in requests:
        text,size,style=request;face=faces[style];raw=base64.b64decode(face['data_base64']);require(digest(raw)==face['source']['sha256'],'TEXT_METRICS_FONT_REPRESENTATION_CONFLICT')
        cache=(style,size)
        if cache not in fonts:fonts[cache]=ImageFont.truetype(io.BytesIO(raw),int(size))
        f=fonts[cache];lines=plain(text).split('\n');ascent,descent=f.getmetrics();entries.append({'text':text,'fontsize':size,'style':style,'size':[max(f.getlength(line)for line in lines),ascent+descent]})
    return entries

def build_text_metrics(skin,preview):
    from preview.main_window import snapshot,TABS
    from preview.scene import project
    props={}
    def visit(n):
        props[n['id']]=n['props']
        for c in n['children']+n['item']:visit(c)
    for root in preview['roots']:visit(root)
    requests={}
    # Each explicit frontend profile/tab; the same rendered string shares one metric.
    for selected in preview['profiles']:
        for tab in TABS:
            scene=project(preview['roots'],snapshot(preview,None if selected=='__none__'else selected,tab),preview['viewport'])
            for row in scene['rows']:
                p=props[row['owner_id']]
                if row['tag']!='text_single'or p.get('autoresize','yes')=='no'or row['text_status'].startswith('UNKNOWN'):continue
                if p.get('size')and p['size'][0]not in('0','0.0'):continue
                text,size=row['text'],row['fontsize'];style='bold'if re.search(r'#(?:bold|b)\b',text)else'regular';requests[key(text,size,style)]=[text,size,style]
    return build_from_requests(skin,list(requests.values()),[r['id']for r in preview['roots']])

def build_from_requests(skin,requests,root_ids):
    label=skin['typography']['label_definitions']['text_single'];auto=[p['scalar']for p in label['ordered_statements']if p['key']=='autoresize'];require(auto==['yes'],'TEXT_METRICS_DEFAULT_AUTORESIZE_UNRESOLVED')
    return {'schema':'guanchuang.display-text-metrics.v1','root_ids':root_ids,'default_autoresize':'yes','requests':requests,'entries':measure_requests(skin,requests),'font_sources':[f['source']for f in skin['typography']['faces']],'label_definition':label,'method':'Pillow FreeType advance and ascent+descent, integer source font size. Explicit display samples only; browser/native shaping, baseline and linebreak not calibrated.'}

def verify_text_metrics(reference,skin):
    require(reference==build_from_requests(skin,reference['requests'],reference['root_ids']),'TEXT_METRICS_REPRESENTATION_CONFLICT')
