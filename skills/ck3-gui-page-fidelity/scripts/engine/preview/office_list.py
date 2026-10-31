"""Actual office-list source contract and explicit fixture layout, never live game state."""
import copy
import math
from pathlib import Path

from core.syntax import parse_bytes
from editing.title import digest, require, _pair


def one(rows, code):
    require(len(rows) == 1, code)
    return rows[0]


def bind_office_list(raw, source, window, name='cmm40_office_list'):
    doc = parse_bytes(raw, source)
    root = one([n for n in doc.root.statements if n.key == 'window' and n.value('name') == window], 'WINDOW_NOT_UNIQUE')
    owner = one([n for n in root.walk() if n.key == 'scrollbox' and n.value('name') == name], 'OFFICE_LIST_NOT_UNIQUE')
    for key in ('autoresizescrollarea', 'scrollbarpolicy_horizontal'):
        require(len(owner.occurrences(key)) == 1, 'LIST_POLICY_NOT_UNIQUE:' + key)
    override = one([n for n in owner.statements if n.key == 'blockoverride' and n.name == 'scrollbox_replace_vbox'], 'LIST_CONTENT_OVERRIDE_NOT_UNIQUE')
    outer = one([n for n in override.statements if n.key == 'vbox'], 'LIST_OUTER_VBOX_REQUIRED')
    rail = one([n for n in outer.statements if n.key == 'hbox'], 'LIST_DATA_RAIL_REQUIRED')
    grid = one([n for n in rail.statements if n.key == 'fixedgridbox'], 'LIST_GRID_REQUIRED')
    for key in ('addcolumn', 'addrow', 'datamodel', 'datamodel_reuse_widgets'):
        require(len(grid.occurrences(key)) == 1, 'LIST_GRID_PROPERTY_NOT_UNIQUE:' + key)
    item = one(grid.occurrences('item'), 'LIST_ITEM_NOT_UNIQUE')
    row = one([n for n in item.statements if n.key == 'widget'], 'LIST_ROW_WIDGET_REQUIRED')
    button = one([n for n in row.statements if n.key == 'button_standard_list'], 'LIST_ROW_BUTTON_REQUIRED')
    require(len(row.occurrences('datacontext')) == 1, 'LIST_CONTEXT_CHAIN_NOT_SUPPORTED')
    require(len(button.occurrences('down')) == 1, 'LIST_SELECTION_NOT_UNIQUE')
    require(row.value('datacontext') == '[Scope.Title]', 'LIST_REQUIRES_EXPLICIT_TITLE_CONTEXT')
    require(owner.value('autoresizescrollarea') == 'no' and owner.value('scrollbarpolicy_horizontal') == 'always_off', 'UNSUPPORTED_VIEWPORT_POLICY')
    require(grid.value('layoutpolicy_vertical') == 'fixed' and rail.value('layoutpolicy_vertical') == 'fixed', 'LIST_FIXED_ROWS_REQUIRED')
    texts = [n for n in row.statements if n.key == 'text_single']
    require(len(texts) == 5 and texts[-1].value('raw_text') == '已选', 'OFFICE_ROW_TEXT_SHAPE_CHANGED')
    fields = []
    for n in texts:
        key = 'text' if n.value('text') is not None else 'raw_text'
        require(not (n.value('text') is not None and n.value('raw_text') is not None), 'TEXT_AND_RAW_TEXT_AMBIGUOUS')
        fields.append({'owner_id': n.node_id, 'key': key, 'expression': n.value(key),
                       'rect': _pair(n, 'position') + _pair(n, 'size'),
                       'fontsize': int(n.value('fontsize')), 'visible': n.value('visible'),
                       'elide': n.value('elide'), 'autoresize': n.value('autoresize')})
    require(all(n['visible'] is None for n in fields[:-1]) and fields[-1]['visible'] == button.value('down'), 'ROW_VISIBILITY_CONTRACT_CHANGED')
    require(button.value('down') is not None, 'ROW_SELECTION_BINDING_REQUIRED')
    width, height = _pair(owner, 'size'); rw, rh = _pair(row, 'size')
    try:
        column, step, top = float(grid.value('addcolumn')), float(grid.value('addrow')), float(outer.value('margin_top', '0'))
    except (ValueError, TypeError) as exc:
        raise ValueError('LIST_GEOMETRY_NOT_STATIC') from exc
    require(all(math.isfinite(v) for v in [width, height, rw, rh, column, step, top])
            and min(width, height, rw, rh, column, step) > 0 and top >= 0 and rh <= step and rw <= column,
            'UNSUPPORTED_LIST_GEOMETRY')
    require(column <= width < column * 2, 'FIRST_LIST_MODEL_SINGLE_COLUMN_ONLY')
    a, b = doc.byte_offsets[owner.start], doc.byte_offsets[owner.end]
    parents = {child.node_id: n for n in root.walk() for child in n.statements}
    ancestors = []; current = owner
    while current.node_id in parents:
        current = parents[current.node_id]
        if current.value('visible') is not None:
            ancestors.append({'owner_id': current.node_id, 'expression': current.value('visible')})
    return {'schema': 'guanchuang.office-list.v1', 'source': source, 'window': window, 'name': name,
            'source_sha256': digest(raw), 'subtree_sha256': digest(raw[a:b]), 'owner_id': owner.node_id,
            'owner_line': owner.source_span['start']['line'],
            'owners': {'scrollbox': owner.node_id, 'content': outer.node_id, 'rail': rail.node_id,
                       'grid': grid.node_id, 'item': item.node_id, 'row': row.node_id, 'button': button.node_id},
            'datamodel': grid.value('datamodel'), 'datamodel_reuse_widgets': grid.value('datamodel_reuse_widgets'),
            'ancestor_visibility': list(reversed(ancestors)), 'fixture_assumption': 'Overview and root are visible; ancestor conditions are not evaluated',
            'row_context': row.value('datacontext'), 'selection_expression': button.value('down'),
            'callbacks': [n.scalar for n in button.occurrences('onclick')],
            'texts': fields, 'geometry': {'viewport': [0, 0, width, height], 'row_size': [rw, rh],
                'button_size': _pair(button, 'size'), 'column_step': column, 'row_step': step, 'content_top': top},
            'bounds': {'allocation': 'SOURCE_SIZE', 'content': 'CANDIDATE_TOP_LEFT_FIXED_ROWS_AND_TRAILING_EXPAND',
                'visible_frame': 'UNKNOWN_NOT_OBSERVED', 'background': 'NATIVE_TEMPLATE_NOT_COMPOSITED',
                'viewport_native_inner_padding': 'NOT_INDEPENDENTLY_OBSERVED'},
            'empty_text': None, 'empty_text_basis': 'No explicit empty message in replaced content; viewer status is outside viewport',
            'basis': 'SOURCE_DERIVED_CANDIDATE_NOT_NATIVE_GEOMETRY_ACCEPTANCE'}


def scenarios(contract):
    """Deliberately synthetic values keyed by exact source binding, not expression evaluation."""
    names = ['北府示例', '河东军府示例', '南境行营示例', '西路军府示例', '中州军府示例', '长名测试·边境联合防务军府示例', '东路行营示例', '末行军府示例']
    records = []
    for i, name in enumerate(names):
        values = [name, ('公国 · 军区' if i % 2 == 0 else '王国 · 行营') + ' · 统领 示例统领' + str(i + 1),
                  '直属 ' + str(i + 1) + ' 州 · 点击查看法理汇总与军力', '法理上级：' + ('示例皇朝' if i else '无法理上级')]
        records.append({'row_id': 'fixture-occurrence-' + str(i + 1), 'title_id': 'fixture-title-' + str(i + 1),
                        'scope_type': 'Title', 'bindings': {f['expression']: v for f, v in zip(contract['texts'][:-1], values)}})
    def state(rows):
        return {'schema': 'guanchuang.office-list-snapshot.v1', 'origin': 'SYNTHETIC_FIXTURE_NOT_GAME_DATA',
                'datamodel': contract['datamodel'], 'rows': copy.deepcopy(rows), 'selected_title_id': None}
    return {'empty': state([]), 'one': state(records[:1]), 'overflow': state(records)}


def validate_snapshot(contract, snapshot):
    require(isinstance(snapshot, dict) and snapshot.get('schema') == 'guanchuang.office-list-snapshot.v1', 'LIST_SNAPSHOT_SCHEMA')
    require(snapshot.get('origin') == 'SYNTHETIC_FIXTURE_NOT_GAME_DATA' and snapshot.get('datamodel') == contract['datamodel'], 'LIST_SNAPSHOT_SOURCE')
    rows = snapshot.get('rows')
    require(isinstance(rows, list) and len(rows) <= 10000, 'LIST_ROWS_REQUIRED_OR_TOO_MANY')
    ids = set()
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('row_id'), str) and row['row_id'] and row['row_id'] not in ids, 'LIST_ROW_ID_NOT_UNIQUE')
        require(isinstance(row.get('title_id'), str) and row['title_id'] and row.get('scope_type') == 'Title', 'LIST_TITLE_CONTEXT_REQUIRED')
        require(isinstance(row.get('bindings'), dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in row['bindings'].items()), 'LIST_TEXT_BINDINGS_REQUIRED')
        ids.add(row['row_id'])
    selected = snapshot.get('selected_title_id')
    require('selected_title_id' in snapshot and (selected is None or isinstance(selected, str)), 'LIST_SELECTED_ID_INVALID')
    # An absent/stale selection is kept as a fact; it must not select row zero.
    return rows


def layout(contract, snapshot, scroll=0):
    rows = validate_snapshot(contract, snapshot)
    require(type(scroll) in (int, float) and math.isfinite(scroll), 'LIST_SCROLL_NOT_FINITE')
    g = contract['geometry']; _, _, vw, vh = g['viewport']; rw, rh = g['row_size']
    natural = g['content_top'] + len(rows) * g['row_step']
    maximum = max(0, natural - vh); offset = min(max(0, scroll), maximum)
    result = []
    for i, row in enumerate(rows):
        top = g['content_top'] + i * g['row_step'] - offset
        bottom = min(vh, top + rh); left = 0; right = min(vw, rw); clipped_top = max(0, top)
        visible = bottom > clipped_top and right > left
        fields = []
        selected = row['title_id'] == snapshot.get('selected_title_id')
        for f in contract['texts']:
            badge = f['visible'] == contract['selection_expression']
            value = f['expression'] if badge else row['bindings'].get(f['expression'])
            fields.append(dict(f, text=value if value is not None else '〔未提供绑定值〕',
                               status='FIXTURE' if value is not None else 'UNKNOWN', visible=selected if badge else True))
        bw, bh = g['button_size']; hit_bottom = min(vh, top + bh)
        result.append({'row_id': row['row_id'], 'title_id': row['title_id'], 'index': i,
                       'rect': [0, top, rw, rh], 'clip': [left, clipped_top, right-left, bottom-clipped_top] if visible else None,
                       'hit_clip': [0, clipped_top, min(vw, bw), hit_bottom-clipped_top] if hit_bottom > clipped_top else None,
                       'selected': selected, 'texts': fields})
    return {'basis': contract['basis'], 'origin': snapshot['origin'], 'viewport': g['viewport'],
            'content_natural_height': natural, 'content_allocation_height': max(vh, natural),
            'max_scroll': maximum, 'scroll': offset, 'rows': result, 'row_count': len(rows),
            'visible_row_ids': [r['row_id'] for r in result if r['clip'] is not None],
            'selected_title_id': snapshot.get('selected_title_id'),
            'selection_status': 'NONE' if snapshot.get('selected_title_id') is None else 'PRESENT' if any(r['selected'] for r in result) else 'STALE'}


def hit_test(model, x, y):
    require(all(type(v) in (int, float) and math.isfinite(v) for v in [x, y]), 'LIST_POINT_NOT_FINITE')
    for row in model['rows']:
        clip = row['hit_clip']
        if clip and clip[0] <= x < clip[0]+clip[2] and clip[1] <= y < clip[1]+clip[3]:
            return {'row_id': row['row_id'], 'title_id': row['title_id']}
    return None


def build_list_reference(index, source, window, name):
    doc = index.document('mod/' + source)
    node, error = index.definition('scrollbox', 'mod/' + source, {'type'})
    require(error is None and node.base == 'scrollarea', 'NATIVE_SCROLLBOX_DEFINITION_UNRESOLVED')
    require(any(n.key == 'block' and n.name == 'scrollbox_replace_vbox' for n in node.walk()), 'NATIVE_CONTENT_BLOCK_MISSING')
    files = [index.paths[node.source]]
    mod = index.roots['mod']
    for rel in ['common/scripted_effects/cmm23_data_effects.txt', 'common/scripted_guis/cmm23_actions.txt', 'common/scripted_guis/cmm40_overview_actions.txt']:
        p = mod / rel
        require(p.is_file(), 'OFFICE_DATA_SOURCE_MISSING:' + rel)
        files.append(p)
    return {'status': 'CURRENT_LOCAL_SOURCE_REFERENCE_NOT_RUNTIME',
            'files': [{'path': str(p), 'sha256': digest(p.read_bytes())} for p in files],
            'scrollbox_type': {'source': node.source, 'base': node.base, 'line': node.source_span['start']['line']},
            'data_chain': 'GetPlayer character variable_list cmm23_view_offices → item Scope → Scope.Title → Title text/down/callbacks',
            'producer': 'cmm23_open_manager clears/discovers; cmm23_discover_character adds every held office title',
            'selection': 'First cmm23_select, then cmm40_refresh_overview; retained, not executed',
            'current_runtime_version': 'NOT_REOBSERVED', 'runtime_data': 'NOT_LOADED'}


def verify_list_reference(reference):
    for record in reference['files']:
        require(digest(Path(record['path']).read_bytes()) == record['sha256'], 'LIST_DEPENDENCY_CONFLICT')
