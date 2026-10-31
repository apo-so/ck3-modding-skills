"""Provenance-preserving scalar using composition; structured templates stay unresolved."""
import copy
from pathlib import Path
from core.syntax import parse_bytes
from editing.title import require,digest

PAIRS={'size','position','minimumsize','maximumsize','margin','spriteborder','framesize','color'}


class ScalarComposer:
    def __init__(self,index=None,records=None):
        self.index=index;self.records={}if records is None else{(r['name'],r['origin']):r for r in records};self.issues=[]

    def resolve(self,name,origin):
        qualified='mod/'+origin if origin.startswith('gui/')else origin;key=(name,qualified)
        if key in self.records:return self.records[key]
        require(self.index is not None,'SCALAR_TEMPLATE_REFERENCE_MISSING:'+name)
        node,error=self.index.definition(name,qualified,{'template','local_template'})
        record={'name':name,'origin':qualified,'error':error}
        if node is not None:
            record.update(source=node.source,node_id=node.node_id,tree=node.to_dict(),path=str(self.index.paths[node.source]),sha256=self.index.document(node.source).sha256)
        self.records[key]=record;return record

    def expand(self,name,origin,chain=()):
        record=self.resolve(name,origin)
        if record['error']:return None,record['error']
        marker=(record['source'],name)
        if marker in chain:return None,'SCALAR_TEMPLATE_CYCLE'
        rows=[]
        for item in record['tree']['ordered_statements']:
            if item['kind']!='assignment':return None,'STRUCTURED_TEMPLATE_NOT_COMPOSED'
            if item['key']=='using':
                nested,error=self.expand(item['scalar'],item['source'],chain+(marker,))
                if error:return None,error
                rows.extend(nested)
            elif not item['has_body']or(item['key']in PAIRS and all(x['kind']=='atom'for x in item['ordered_statements'])):
                row=copy.deepcopy(item);row['_from_template']={'name':name,'source':record['source'],'definition_owner':record['node_id']};rows.append(row)
            else:return None,'STRUCTURED_TEMPLATE_NOT_COMPOSED'
        return rows,None

    def compose(self,ast):
        result=copy.deepcopy(ast);output=[]
        for item in result.get('ordered_statements',[]):
            if item['kind']=='assignment'and item['key']=='using'and not item['has_body']:
                rows,error=self.expand(item['scalar'],item['source'])
                if error:
                    item['_composition_issue']=error;self.issues.append({'owner_id':ast['node_id'],'symbol':item['scalar'],'code':error})
                else:item['_scalar_composed']=True
                output.append(item)
                if not error:
                    for row in rows:
                        row['_template_instance']=item['node_id'];output.append(row)
            else:
                if item['has_body']:item=self.compose(item)
                output.append(item)
        result['ordered_statements']=output;return result


def verify_records(records):
    cache={}
    for record in records:
        if record['error']:continue
        key=(record['path'],record['source'])
        if key not in cache:
            raw=Path(record['path']).read_bytes();require(digest(raw)==record['sha256'],'SCALAR_TEMPLATE_SOURCE_CONFLICT')
            cache[key]=parse_bytes(raw,record['source'])
        node=next((n for n in cache[key].root.walk()if n.node_id==record['node_id']),None)
        require(node is not None and node.to_dict()==record['tree'],'SCALAR_TEMPLATE_REPRESENTATION_CONFLICT')
