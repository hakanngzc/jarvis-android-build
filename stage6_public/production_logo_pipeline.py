#!/usr/bin/env python3
"""Production-safe NSS REBORN logo rollout primitives.

This module deliberately does not patch test menus/onboarding/consent. It only
models validated club->style->symbol data, packs supplied logo assets, appends
atlas metadata, and extends stock ShieldAnims selectors while preserving the
stock 0..15 family.
"""
import json
import math
import re
from pathlib import Path

from append_logo_atlas import append_atlas

STOCK_MAX_STYLE=15
SYMBOL_RE=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validated_manifest(manifest, base_dir=None, require_assets=False):
    if not isinstance(manifest,dict):
        raise ValueError('logo manifest must be an object')
    if manifest.get('version',1) != 1:
        raise ValueError('unsupported logo manifest version')
    cell_size=manifest.get('cell_size',128)
    if isinstance(cell_size,bool) or not isinstance(cell_size,int) or cell_size <= 0 or cell_size > 1024:
        raise ValueError('cell_size must be an integer in 1..1024')
    clubs=manifest.get('clubs')
    if not isinstance(clubs,list) or not clubs:
        raise ValueError('logo manifest clubs must be a non-empty list')

    ids=set(); styles=set(); symbols=set(); normalized=[]
    root=Path(base_dir).resolve() if base_dir is not None else None
    for index,row in enumerate(clubs):
        if not isinstance(row,dict):
            raise ValueError(f'club row {index} must be an object')
        try:
            club_id=int(row['club_id']); style=int(row['style'])
        except (KeyError,TypeError,ValueError):
            raise ValueError(f'club row {index} requires integer club_id/style')
        symbol=row.get('symbol'); asset=row.get('asset')
        if club_id <= 0 or club_id > 0x7fffffff:
            raise ValueError(f'invalid club_id: {club_id}')
        if style <= STOCK_MAX_STYLE or style > 0x7fffffff:
            raise ValueError(f'badge style {style} collides with reserved stock range 0..15')
        if not isinstance(symbol,str) or not SYMBOL_RE.fullmatch(symbol):
            raise ValueError(f'invalid symbol for club {club_id}')
        if not isinstance(asset,str) or not asset or Path(asset).is_absolute():
            raise ValueError(f'asset for club {club_id} must be a relative path')
        if club_id in ids: raise ValueError(f'duplicate club_id: {club_id}')
        if style in styles: raise ValueError(f'duplicate badge style: {style}')
        if symbol in symbols: raise ValueError(f'duplicate logo symbol: {symbol}')
        ids.add(club_id); styles.add(style); symbols.add(symbol)
        entry={'club_id':club_id,'style':style,'symbol':symbol,'asset':asset}
        if root is not None:
            resolved=(root/asset).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                raise ValueError(f'asset escapes manifest directory: {asset}')
            if require_assets and not resolved.is_file():
                raise ValueError(f'missing logo asset: {asset}')
            entry['_asset_path']=str(resolved)
        elif row.get('_asset_path'):
            resolved=Path(row['_asset_path']).resolve()
            if require_assets and not resolved.is_file():
                raise ValueError(f'missing logo asset: {asset}')
            entry['_asset_path']=str(resolved)
        normalized.append(entry)

    normalized.sort(key=lambda r:(r['style'],r['club_id'],r['symbol']))
    return {'version':1,'cell_size':cell_size,'clubs':normalized}


def load_manifest(path, require_assets=True):
    path=Path(path)
    payload=json.loads(path.read_text(encoding='utf-8'))
    return _validated_manifest(payload,path.parent,require_assets=require_assets)


def build_style_overrides(manifest):
    checked=_validated_manifest(manifest,require_assets=False)
    return dict(sorted((row['club_id'],row['style']) for row in checked['clubs']))


def compute_atlas_layout(manifest,max_width=2048):
    checked=_validated_manifest(manifest,require_assets=False)
    cell=checked['cell_size']; count=len(checked['clubs'])
    if max_width < cell:
        raise ValueError('max_width must fit at least one cell')
    max_cols=max_width//cell
    cols=min(count,max_cols)
    rows=math.ceil(count/cols)
    return {'cell_size':cell,'columns':cols,'rows':rows,'width':cols*cell,'height':rows*cell}


def build_symbol_records(manifest,atlas_width=None,atlas_height=None,max_width=2048):
    checked=_validated_manifest(manifest,require_assets=False)
    layout=compute_atlas_layout(checked,max_width=max_width)
    if atlas_width is None: atlas_width=layout['width']
    if atlas_height is None: atlas_height=layout['height']
    cell=checked['cell_size']
    if atlas_width <= 0 or atlas_height <= 0 or atlas_width%cell or atlas_height%cell:
        raise ValueError('atlas dimensions must be positive cell-size multiples')
    cols=atlas_width//cell
    if cols*(atlas_height//cell) < len(checked['clubs']):
        raise ValueError('atlas dimensions do not fit all clubs')
    out=[]
    for index,row in enumerate(checked['clubs']):
        col=index%cols; rr=index//cols
        x0=col*cell; y0=rr*cell; x1=x0+cell; y1=y0+cell
        out.append((row['symbol'],[x0/atlas_width,y0/atlas_height,x1/atlas_width,y1/atlas_height]))
    return out


def atlas_records_for_append(manifest,atlas_width=None,atlas_height=None,max_width=2048):
    checked=_validated_manifest(manifest,require_assets=False)
    layout=compute_atlas_layout(checked,max_width=max_width)
    w=atlas_width or layout['width']; h=atlas_height or layout['height']; cell=checked['cell_size']
    bounds=dict(build_symbol_records(checked,w,h,max_width=max_width))
    records=[]
    for row in checked['clubs']:
        u0,v0,u1,v1=bounds[row['symbol']]
        records.append({
            'name':row['symbol'],
            'original_width':cell,'original_height':cell,
            'trimmed_width':cell,'trimmed_height':cell,
            'render_data':[0.0,1.0,u0,v1,1.0,0.0,u1,v0],
        })
    return records


def pack_logo_atlas(manifest,out_path,max_width=2048):
    checked=_validated_manifest(manifest,require_assets=True)
    missing=[row['asset'] for row in checked['clubs'] if not row.get('_asset_path')]
    if missing:
        raise ValueError('pack_logo_atlas requires a manifest loaded with load_manifest')
    from PIL import Image
    layout=compute_atlas_layout(checked,max_width=max_width); cell=layout['cell_size']
    atlas=Image.new('RGBA',(layout['width'],layout['height']),(0,0,0,0))
    for index,row in enumerate(checked['clubs']):
        with Image.open(row['_asset_path']) as raw:
            src=raw.convert('RGBA')
        src.thumbnail((cell,cell),Image.Resampling.LANCZOS)
        x=(index%layout['columns'])*cell+(cell-src.width)//2
        y=(index//layout['columns'])*cell+(cell-src.height)//2
        atlas.alpha_composite(src,(x,y))
    out_path=Path(out_path); out_path.parent.mkdir(parents=True,exist_ok=True); atlas.save(out_path)
    return layout


def append_manifest_atlas(key_bytes,manifest,atlas_name,max_width=2048):
    checked=_validated_manifest(manifest,require_assets=False)
    layout=compute_atlas_layout(checked,max_width=max_width)
    records=atlas_records_for_append(checked,layout['width'],layout['height'],max_width=max_width)
    return append_atlas(key_bytes,atlas_name,layout['width'],layout['height'],records)


def _supplemental_block(style_name,args,modifier,indent,manifest):
    checked=_validated_manifest(manifest,require_assets=False)
    by_style={row['style']:row['symbol'] for row in checked['clubs']}
    max_style=max(by_style)
    lines=[indent+'Rect:(0,0,0,0)',indent+f'    Selector(MatchColours,{style_name})',indent+'{']
    lines.extend(indent+'    Rect:(0,0,0,0)' for _ in range(16))
    for style in range(16,max_style+1):
        symbol=by_style.get(style)
        if symbol is None:
            lines.append(indent+'    Rect:(0,0,0,0)')
        else:
            lines.append(indent+f'    Draw:({symbol},{args},,#FFFFFFFF)')
            lines.append(indent+'        '+modifier.strip())
    lines.append(indent+'}')
    return '\n'.join(lines)+'\n'


def render_shield_extension(manifest,args='@L,@T,@W,@H',modifier='Handle(0,0)',base_indent=''):
    checked=_validated_manifest(manifest,require_assets=False)
    return (_supplemental_block('BadgeStyle1',args,modifier,base_indent,checked)+'\n'+
            _supplemental_block('BadgeStyle2',args,modifier,base_indent,checked))


def extend_shield_selectors(text,manifest):
    checked=_validated_manifest(manifest,require_assets=False)
    selector=re.compile(
        r'(?P<selindent>^[ \t]*)Selector\(MatchColours,(?P<style>BadgeStyle[12])\)\r?\n'
        r'(?P<braceindent>^[ \t]*)\{\r?\n(?P<body>.*?)(?P<close>^[ \t]*\}\r?$)',re.M|re.S)
    pos=0; pieces=[]; blocks=[]
    for m in selector.finditer(text):
        dm=re.search(
            r'(?m)^(?P<drawindent>[ \t]*)Draw:\(MapShieldDesign15,(?P<args>[^\r\n)]*)\)\r?\n'
            r'(?P<modindent>[ \t]*)(?P<modifier>(?:TweenSize|Handle)\([^\r\n]*\))',m.group('body'))
        if not dm: continue
        block=_supplemental_block(m.group('style'),dm.group('args'),dm.group('modifier'),m.group('braceindent'),checked)
        pieces.append(text[pos:m.end()]); pieces.append('\n'+block); blocks.append(block); pos=m.end()
    pieces.append(text[pos:]); out=''.join(pieces)
    report={
        'selector_insert_count':len(blocks),
        'stock_design15_count_before':text.count('Draw:(MapShieldDesign15,'),
        'stock_design15_count_after':out.count('Draw:(MapShieldDesign15,'),
        'production_symbols':[row['symbol'] for row in checked['clubs']],
        'style_overrides':build_style_overrides(checked),
        'test_overlay_present':'STAGE6_TEST_ONLY_LOGO_PROOF' in out,
    }
    if report['selector_insert_count'] < 1:
        raise ValueError('no stock BadgeStyle selector blocks found')
    if report['stock_design15_count_before'] != report['stock_design15_count_after']:
        raise AssertionError('stock Design15 entries changed')
    if report['test_overlay_present']:
        raise ValueError('test-only Stage6 overlay is forbidden in production selector output')
    return out,report
