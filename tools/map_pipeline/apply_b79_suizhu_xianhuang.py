#!/usr/bin/env python3
"""B79: county-guided eight-province transaction inside the frozen Suihuang mask.

Prepare once from the current map, then apply only the frozen RLE patch. The
B47 modern Hubei/Henan domains, Suizhou and the exterior (including Dabie and
the navigable rivers) are immutable. Run after historical map writers and
before terminal religion/academy projections. --check never writes files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'guangdong_independent_practice'
MAP = MOD / 'map'
PLAN = ROOT / 'planning/suizhu_xianhuang_b79'
BACKUP = PLAN / 'pre_b79'
MANIFEST = PLAN / 'batch_manifest.json'
MARKER = 'GDD_B79_SUIZHU_XIANHUANG'
OLD = (5009, 4197, 5012, 2175, 5350)
NEW = (5383, 5384, 5385)
HB = (5009, 5383, 5012, 4197)
HN = (2175, 5384, 5350, 5385)
ALL = HB + HN
AREA = {'dean_qihuang_area': HB, 'xianhuang_area': HN}
AREA_ZH = {'dean_qihuang_area': '随邾', 'xianhuang_area': '弦黄'}
ZH = dict(zip(ALL, ('随州', '麻城', '黄州', '蕲州', '信阳', '罗山', '光州', '固始')))
EN = dict(zip(ALL, ('Suizhou', 'Macheng', 'Huangzhou', 'Qizhou', 'Xinyang', 'Luoshan', 'Guangzhou (Henan)', 'Gushi')))
DEV = dict(zip(ALL, ((4,3,4),(2,2,4),(5,6,3),(3,4,3),(4,4,3),(2,2,3),(4,5,3),(3,4,2))))
PARENT = {**{i:i for i in OLD}, 5383:5012, 5384:2175, 5385:5350}
RGB_NEW = {5383:(191,91,139), 5384:(116,163,64), 5385:(199,155,73)}
TERRAIN = {'grasslands': (5009,5384,5350), 'hills': (5383,2175), 'farmlands': (5012,4197,5385)}
GOODS_NEW = {5383:'grain', 5384:'grain', 5385:'grain'}
COUNTIES = {
    5383: ('红安县','麻城市','罗田县','英山县'),
    5012: ('黄州区','团风县','浠水县'),
    4197: ('蕲春县','武穴市','黄梅县'),
    2175: ('浉河区','平桥区'), 5384: ('罗山县',),
    5350: ('潢川县','光山县','新县'), 5385: ('固始县','商城县'),
}
SOURCE = MOD / 'localisation_source/024_gdd_b79_suizhu_xianhuang_readable_utf8.txt'
TARGET = MOD / 'localisation/replace/024_gdd_b79_suizhu_xianhuang_l_english.yml'
AREA_SOURCE = MOD / 'localisation_source/gdd_zzz_chunqiu_area_overrides_readable_utf8.txt'
AREA_TARGET = MOD / 'localisation/replace/zzz_gdd_chunqiu_area_overrides_l_english.yml'
LEGACY_SOURCE = MOD / 'localisation_source/gdd_b10_hubei_map_readable_utf8.txt'
LEGACY_TARGET = MOD / 'localisation/gdd_b10_hubei_map_l_english.yml'

sys.path.insert(0, str(ROOT / 'tools'))
from encode_eu4_chinese_localisation import encode_file, verify_file

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

helper = load('b79_blocks', ROOT / 'tools/map_pipeline/apply_b78_daming_refinement.py')
geo = load('b79_geo', ROOT / 'planning/jingxiang_yunan_b47/render_b47_geojson_proposal.py')
balance = load('b79_balance', ROOT / 'planning/jingxiang_yunan_b47/render_b47_geojson_v2.py')
bounds = helper.block_bounds
replace_block = helper.replace_block

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def definitions():
    return geo.definitions()[0]

def read(path):
    return path.read_text(encoding='cp1252')

def write(path, text):
    path.write_text(text, encoding='cp1252')

def history(pid):
    matches = [p for p in (MOD / 'history/provinces').glob('*.txt') if re.match(rf'^{pid}\D', p.name)]
    if len(matches) != 1:
        raise ValueError(f'{pid}: {len(matches)} history files')
    return matches[0]

def inject(text, key, values):
    begin, end = bounds(text, key)
    block = text[begin:end]
    indent=re.search(rf'(?m)^([ \t]*){re.escape(key)}\s*=',block)[1]
    block = block[:-1].rstrip() + '\n' + indent + '    ' + ' '.join(map(str, values)) + f' # {MARKER}\n' + indent + '}'
    return text[:begin] + block + text[end:]

def remove_members(text, values):
    # Membership files only; do not apply to histories, positions or definitions.
    output=[]
    for line in text.splitlines(keepends=True):
        body,sep,comment=line.partition('#');before=body
        for value in values:
            body=re.sub(rf'(?<![\w.]){re.escape(str(value))}(?![\w.])','',body)
        if body!=before:
            indent=re.match(r'[ \t]*',body)[0]
            body=indent+re.sub(r'[ \t]+',' ',body[len(indent):]).rstrip()
            line=body+(' #'+comment if sep else ('\n' if line.endswith('\n') else ''))
        output.append(line)
    return ''.join(output)

def set_members(text, assignments, values, nested=None):
    text = re.sub(rf'(?m)^.*# {MARKER}\n?', '', text)
    if nested:
        # Limit numeric removal to member blocks, leaving position anchors intact.
        for match in list(re.finditer(rf'(?m)^\s*{nested}\s*=\s*\{{', text))[::-1]:
            start, end = bounds(text, nested, match.start())
            text = text[:start] + remove_members(text[start:end], values) + text[end:]
    else:
        text = remove_members(text, values)
    for key, ids in assignments.items():
        if nested:
            start, end = bounds(text, key)
            text = text[:start] + inject(text[start:end], nested, ids) + text[end:]
        else:
            text = inject(text, key, ids)
    return text

def partition(mask, ids, features):
    selected = [(f, pid) for f in features for pid in ids if f['properties']['name'] in COUNTIES[pid]]
    assert len(selected) == sum(len(COUNTIES[pid]) for pid in ids)
    points = [p for f,_ in selected for poly in geo.polygons(f['geometry']) for p in poly[0]]
    west, east = min(p[0] for p in points), max(p[0] for p in points)
    south, north = min(p[1] for p in points), max(p[1] for p in points)
    ys, xs = np.where(mask)
    x0,x1,y0,y1 = int(xs.min()),int(xs.max()),int(ys.min()),int(ys.max())
    def project(p):
        return (round(x0+(p[0]-west)/(east-west)*(x1-x0)), round(y0+(north-p[1])/(north-south)*(y1-y0)))
    im = Image.new('I', (mask.shape[1], mask.shape[0]), 0)
    draw = ImageDraw.Draw(im)
    for f,pid in selected:
        for poly in geo.polygons(f['geometry']):
            draw.polygon([project(p) for p in poly[0]], fill=pid)
            for hole in poly[1:]:
                draw.polygon([project(p) for p in hole], fill=0)
    raw = np.array(im)
    labels = np.zeros(mask.shape, np.int32)
    for pid in ids:
        keep = geo.largest_component(mask & (raw == pid))
        if not keep.any():
            raise ValueError(f'No county seed for {ZH[pid]}')
        labels[keep] = pid
    q = deque((int(y),int(x)) for y,x in zip(*np.where(labels > 0)))
    while q:
        y,x=q.popleft()
        for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0<=ny<mask.shape[0] and 0<=nx<mask.shape[1] and mask[ny,nx] and not labels[ny,nx]:
                labels[ny,nx]=labels[y,x]; q.append((ny,nx))
    assert np.array_equal(labels > 0, mask)
    for pid in ids:
        assert len(geo.component_masks(labels == pid)) == 1
    # County projection is a geographic seed, not a mandate to leave the two
    # western Henan cells too small to select. Balance inside each fixed domain;
    # weights describe usable map area and are independent of development.
    weights = {5383:275,5012:280,4197:237,2175:120,5384:85,5350:145,5385:142}
    balance.v1.CELL_BY_ID = {pid:SimpleNamespace(name=ZH[pid],development=weights[pid]) for pid in ids}
    masks = {pid:labels==pid for pid in ids}
    seeds = {pid:geo.label_point(masks[pid]) for pid in ids}
    targets = balance.rebalance_component(masks,mask,list(ids),seeds)
    for pid,m in masks.items():labels[m]=pid
    return labels, {'bounds':[west,south,east,north], 'pixel_box':[x0,y0,x1,y1], 'counties':{str(pid):COUNTIES[pid] for pid in ids}, 'playable_area_targets':targets}

def owned_paths():
    paths = [MAP / n for n in ('provinces.bmp','definition.csv','default.map','area.txt','region.txt','positions.txt','terrain.txt','climate.txt','continent.txt','adjacencies.csv')]
    paths += [MOD / 'common/tradenodes/00_tradenodes.txt', MOD / 'common/trade_companies/00_trade_companies.txt', SOURCE, TARGET, AREA_SOURCE, AREA_TARGET, LEGACY_SOURCE, LEGACY_TARGET]
    paths += [ROOT / 'planning/culture_overhaul/approved_province_culture_assignments.csv', ROOT / 'docs/map/china_province_split_registry.csv']
    paths += [history(pid) for pid in OLD]
    paths += [MOD / f'history/provinces/{pid} - {EN[pid]}.txt' for pid in NEW]
    return paths

def prepare():
    if MANIFEST.exists():
        raise ValueError('B79 already frozen; use --apply or --check')
    PLAN.mkdir(parents=True, exist_ok=True)
    colors = definitions()
    assert not set(NEW) & colors.keys()
    assert not set(RGB_NEW.values()) & set(colors.values())
    for path in owned_paths():
        if path.exists():
            dest = BACKUP / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():shutil.copy2(path,dest)
    base = np.array(Image.open(MAP / 'provinces.bmp').convert('RGB'))
    masks = {pid:np.all(base == colors[pid], axis=2) for pid in OLD}
    union = np.logical_or.reduce(list(masks.values()))
    ys,xs=np.where(union); box=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
    x0,y0,x1,y1=box
    local = {pid:m[y0:y1,x0:x1] for pid,m in masks.items()}
    labels = np.zeros(local[5009].shape,np.int32); labels[local[5009]]=5009
    metadata={}
    for group, domain, ids, filename in (
        ('hubei',local[4197]|local[5012],(5383,5012,4197),'420000_full_district.json'),
        ('henan',local[2175]|local[5350],HN,'410000_full_district.json')):
        reference = ROOT / 'planning/jingxiang_yunan_b47/reference_geojson' / filename
        features=json.loads(reference.read_text())['features']
        part,meta=partition(domain,ids,features); labels[domain]=part[domain]
        meta['reference']=str(reference.relative_to(ROOT));meta['sha256']=sha(reference)
        metadata[group]=meta
    runs=[]
    for y,row in enumerate(labels):
        x=0
        while x<len(row):
            pid=int(row[x]); end=x+1
            while end<len(row) and row[end]==pid:end+=1
            if pid:runs.append([y+y0,x+x0,end+x0,pid])
            x=end
    info={
        'batch':'B79', 'marker':MARKER, 'baseline_commit':'f80662835194999dc31b3fbc5784cda87d810df2',
        'purpose':'随黄五省改为随邾、弦黄各四省；逐省游戏性发展度，不守恒',
        'old_ids':OLD,'new_ids':NEW,'target_ids':ALL,'box':box,
        'geometry_policy':'Freeze B47 modern Hubei/Henan domains and original Suizhou; project counties inside each side; exact exterior including Dabie and rivers locked.',
        'colors':{str(pid):RGB_NEW.get(pid,colors.get(pid)) for pid in ALL},
        'areas':AREA,'area_names':AREA_ZH,'development':DEV,'total_development':82,
        'parents':PARENT,'names':ZH,'geojson':metadata,'runs':runs,
        'history_policy':'Existing histories preserved except development. New children inherit parent owner, culture, religion and dated history; goods set to grain.',
        'trade_policy':'All eight retain inherited Huguang node and trade_company_huguang; no trade flow change.',
        'baseline_bitmap_sha256':sha(MAP/'provinces.bmp'),
    }
    MANIFEST.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    render(labels, box, 'b79_boundary_preview.png')
    print('B79 prepared:', {ZH[pid]:int((labels==pid).sum()) for pid in ALL})

def frozen():
    info=json.loads(MANIFEST.read_text())
    box=info['box']; x0,y0,x1,y1=box
    labels=np.zeros((y1-y0,x1-x0),np.int32)
    for y,start,end,pid in info['runs']:labels[y-y0,start-x0:end-x0]=pid
    return info, labels

def render(labels, box, filename):
    x0,y0,x1,y1=box; pad=7; scale=11
    base=np.array(Image.open(MAP/'provinces.bmp').convert('RGB'))[y0-pad:y1+pad,x0-pad:x1+pad]
    canvas=np.full(base.shape, (209,205,192),dtype=np.uint8)
    defs=definitions()
    for pid,c in defs.items():
        m=np.all(base==c,axis=2)
        if pid in (5035,5038,5039,5040):canvas[m]=(102,159,184)
        elif pid==5354:canvas[m]=(101,95,79)
    padded=np.pad(labels,pad)
    palette={5009:(108,153,131),5383:(129,169,145),5012:(91,141,122),4197:(160,185,143),2175:(202,167,103),5384:(220,191,131),5350:(188,146,85),5385:(229,205,156)}
    for pid,color in palette.items():canvas[padded==pid]=color
    edge=geo.group_edge(padded)
    canvas[edge]=(246,240,219)
    im=Image.fromarray(canvas).resize((canvas.shape[1]*scale,canvas.shape[0]*scale),Image.Resampling.NEAREST)
    sheet=Image.new('RGB',(im.width+350,max(im.height+100,720)),(247,244,234))
    sheet.paste(im,(0,70)); d=ImageDraw.Draw(sheet)
    font=lambda size:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',size)
    d.text((22,18),'随邾 · 弦黄｜八省细化',font=font(29),fill=(39,50,44))
    d.text((22,sheet.height-26),'今鄂豫省界分区 · 大别山与河流保留 · 发展度按游戏性设定',font=font(15),fill=(70,73,65))
    for pid in ALL:
        x,y=geo.label_point(padded==pid)
        s=ZH[pid]; w=d.textbbox((0,0),s,font=font(20))[2]
        d.text((x*scale-w/2,y*scale+57),s,font=font(20),fill=(255,255,245),stroke_width=2,stroke_fill=(45,55,46))
    x=im.width+22; y=90
    for area,ids in AREA.items():
        d.text((x,y),AREA_ZH[area]+f'  {sum(sum(DEV[i]) for i in ids)}发展度',font=font(24),fill=(46,60,49));y+=46
        for pid in ids:
            d.text((x,y),f'{ZH[pid]}  {sum(DEV[pid])}  ({"/".join(map(str,DEV[pid]))})',font=font(20),fill=(60,67,56));y+=37
        y+=33
    d.text((x,y),'括号：税收 / 生产 / 人力',font=font(16),fill=(95,98,88))
    sheet.save(PLAN/filename)

def update_histories():
    for pid in ALL:
        path=history(pid) if pid in OLD else MOD/f'history/provinces/{pid} - {EN[pid]}.txt'
        if pid in OLD:
            text=read(path)
        else:
            text=read(BACKUP/history(PARENT[pid]).relative_to(ROOT))
            text=re.sub(r'(?m)^#.*$', '',text,count=1).lstrip()
            text=f'# {pid} - {EN[pid]} - {MARKER}\n'+text
            text=re.sub(r'(?m)^capital\s*=.*$',f'capital = "{EN[pid]}"',text,count=1)
            text=re.sub(r'(?m)^trade_goods\s*=.*$',f'trade_goods = {GOODS_NEW[pid]}',text,count=1)
        for key,value in zip(('base_tax','base_production','base_manpower'),DEV[pid]):
            text,n=re.subn(rf'(?m)^{key}\s*=.*$',f'{key} = {value}',text,count=1)
            assert n==1
        write(path,text)

def update_localisation():
    # Refuse to overwrite a merge-split readable/encoded pair.
    verify_file(AREA_SOURCE,AREA_TARGET)
    if SOURCE.exists():verify_file(SOURCE,TARGET)
    lines=['l_english:']
    for pid in ALL:
        lines += [f' PROV{pid}:0 "{ZH[pid]}"',f' PROV_ADJ{pid}:0 "{ZH[pid]}"']
    SOURCE.write_text('\ufeff'+'\n'.join(lines)+'\n',encoding='utf-8')
    text=AREA_SOURCE.read_text(encoding='utf-8-sig')
    for area,name in AREA_ZH.items():
        for key in (area,area+'_name',area+'_adj'):
            line=f' {key}:0 "{name}"'
            pattern=rf'(?m)^\s*{key}:\d+[^\n]*'
            text=re.sub(pattern,line,text) if re.search(pattern,text) else text.rstrip()+'\n'+line+'\n'
    AREA_SOURCE.write_text('\ufeff'+text,encoding='utf-8')
    encode_file(SOURCE,TARGET);encode_file(AREA_SOURCE,AREA_TARGET)
    verify_file(LEGACY_SOURCE,LEGACY_TARGET)
    text=LEGACY_SOURCE.read_text(encoding='utf-8-sig')
    for key in ('dean_qihuang_area','dean_qihuang_area_name','dean_qihuang_area_adj'):
        text=re.sub(rf'(?m)^\s*{key}:\d+[^\n]*',f' {key}:0 "随邾"',text)
    LEGACY_SOURCE.write_text('\ufeff'+text,encoding='utf-8')
    encode_file(LEGACY_SOURCE,LEGACY_TARGET)

def update_registries():
    path=ROOT/'planning/culture_overhaul/approved_province_culture_assignments.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    rows=[r for r in rows if int(r['province_id']) not in NEW]
    for pid in NEW:
        rows.append(dict(province_id=str(pid),province_name=ZH[pid],document_group='汉文化组',document_culture='楚文化',document_entry='B79随邾弦黄八省',target_culture='gdd_chu',source_rule='B79_user_override',decision_note='继承母省文化；逐省设定游戏性发展度'))
    with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(sorted(rows,key=lambda r:int(r['province_id'])))
    path=ROOT/'docs/map/china_province_split_registry.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    rows=[r for r in rows if r['draw_batch']!='B79']
    for index,pid in enumerate(NEW,1):
        r={k:'' for k in fields};parent=PARENT[pid]
        r.update(design_key=f'B79-{index:02}',game_id=str(pid),rgb_r=str(RGB_NEW[pid][0]),rgb_g=str(RGB_NEW[pid][1]),rgb_b=str(RGB_NEW[pid][2]),macro_region='south_china' if pid in HB else 'north_china',draw_batch='B79',new_name_zh=ZH[pid],new_name_en=EN[pid],parent_id=str(parent),parent_area='dean_qihuang_area',retained_name_zh=ZH[parent],new_tax=str(DEV[pid][0]),new_production=str(DEV[pid][1]),new_manpower=str(DEV[pid][2]),proposed_owner='CHC' if pid in HB else 'SUI',split_group='b79-eight-provinces',group_dev_delta='47' if index==1 else '0',status='implemented',rationale='鄂豫省界硬约束；两区各四省；发展度独立设定，总计82。')
        rows.append(r)
    with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)

def apply():
    for path in owned_paths():
        dest=BACKUP/path.relative_to(ROOT)
        if path in (SOURCE,TARGET) or any(path.name == f'{pid} - {EN[pid]}.txt' for pid in NEW):
            continue
        if path.exists() and not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    info,labels=frozen();x0,y0,x1,y1=info['box'];colors={int(k):tuple(v) for k,v in info['colors'].items()}
    current=np.array(Image.open(MAP/'provinces.bmp').convert('RGB'));before=current.copy();local=current[y0:y1,x0:x1]
    allowed=np.zeros(labels.shape,bool)
    for color in colors.values():allowed |= np.all(local==color,axis=2)
    assert np.all(allowed[labels>0]), 'Frozen mask now contains another batch province'
    for pid,color in colors.items():local[labels==pid]=color
    owned=np.zeros(current.shape[:2],bool);owned[y0:y1,x0:x1]=labels>0
    assert not np.any(np.any(current!=before,axis=2)&~owned), 'B79 changed pixels outside its owned mask'
    Image.fromarray(current).save(MAP/'provinces.bmp',format='BMP')
    path=MAP/'definition.csv';lines=[line for line in read(path).splitlines() if not (line.split(';')[0].isdigit() and int(line.split(';')[0]) in NEW)]
    for pid in NEW:lines.append(f'{pid};{";".join(map(str,colors[pid]))};{EN[pid]};x')
    write(path,'\n'.join(lines)+'\n')
    path=MAP/'default.map';text=read(path);ceiling=int(re.search(r'max_provinces\s*=\s*(\d+)',text)[1]);write(path,re.sub(r'max_provinces\s*=\s*\d+',f'max_provinces = {max(ceiling,max(ALL)+1)}',text,count=1))
    path=MAP/'area.txt';text=read(path)
    for area,ids in AREA.items():text=replace_block(text,area,f'{area} = {{ # {MARKER}\n    {" ".join(map(str,ids))}\n}}')
    write(path,text)
    path=MAP/'region.txt';write(path,set_members(read(path),{'north_china_region':('xianhuang_area',)},('xianhuang_area',),'areas'))
    update_histories()
    path=MAP/'positions.txt';text=re.sub(rf'(?m)^#.*{MARKER}\n','',read(path))
    for pid in ALL:
        x,y=helper.deep_point({(int(x),int(y)) for y,x in zip(*np.where(labels==pid))});x+=x0;y+=y0
        coordinates=' '.join([f'{x:.3f} {current.shape[0]-y:.3f}']*7)
        text=replace_block(text,str(pid),f'# {EN[pid]} - {MARKER}\n{pid}={{\n    position={{ {coordinates} }}\n    rotation={{ 0 0 0 0 0 0 0 }}\n    height={{ 0 0 1 0 0 0 0 }}\n}}')
    write(path,text)
    for filename,assignments,values,nested in (
        ('continent.txt',{'asia':NEW},NEW,None),
        ('climate.txt',{'normal_monsoon':NEW},NEW,None),
        ('terrain.txt',TERRAIN,ALL,'terrain_override')):
        path=MAP/filename;write(path,set_members(read(path),assignments,values,nested))
    for relative,outer,inner in (('tradenodes/00_tradenodes.txt','huguang','members'),('trade_companies/00_trade_companies.txt','trade_company_huguang','provinces')):
        path=MOD/'common'/relative;write(path,set_members(read(path),{outer:ALL},ALL,inner))
    update_localisation();update_registries()
    check()
    render(labels,info['box'],'b79_applied_preview.png')

def check():
    info,labels=frozen();x0,y0,x1,y1=info['box']
    current=np.array(Image.open(MAP/'provinces.bmp').convert('RGB'))
    base=np.array(Image.open(BACKUP/'guangdong_independent_practice/map/provinces.bmp').convert('RGB'))
    exterior=np.ones(current.shape[:2],bool);exterior[y0:y1,x0:x1]=labels==0
    # Later batches may legitimately edit outside B79's mask. Validate the
    # owned pixels below; exterior preservation belongs to each apply call.
    later_exterior_changes=int(np.count_nonzero(np.any(current!=base,axis=2)&exterior))
    colors=definitions();counts={}
    for pid in ALL:
        mask=labels==pid
        assert len(geo.component_masks(mask))==1
        assert np.all(current[y0:y1,x0:x1][mask]==colors[pid])
        counts[pid]=int(mask.sum())
        text=read(history(pid))
        assert tuple(int(re.search(rf'(?m)^{key}\s*=\s*(\d+)',text)[1]) for key in ('base_tax','base_production','base_manpower'))==DEV[pid]
        parent_text=read(BACKUP/history(PARENT[pid]).relative_to(ROOT))
        for key in ('owner','controller','culture','religion'):
            assert re.search(rf'(?m)^{key}\s*=\s*(\S+)',text)[1]==re.search(rf'(?m)^{key}\s*=\s*(\S+)',parent_text)[1]
    for ids,old in ((HB,(5009,4197,5012)),(HN,(2175,5350))):
        before=np.logical_or.reduce([np.all(base[y0:y1,x0:x1]==colors[i],axis=2) for i in old])
        assert np.array_equal(np.isin(labels,ids),before), 'Modern provincial domains changed'
    for path in (MAP/'area.txt',):
        text=read(path)
        for area,ids in AREA.items():
            start,end=bounds(text,area);body=re.sub(r'#[^\n]*','',text[start:end]);actual=[int(x) for x in re.findall(r'\b\d+\b',body)]
            assert sorted(actual)==sorted(ids)
    verify_file(SOURCE,TARGET);verify_file(AREA_SOURCE,AREA_TARGET)
    total=sum(map(sum,DEV.values()));assert total==82
    print(json.dumps({'B79':'PASS','province_pixels':counts,'province_components':{i:1 for i in ALL},'later_exterior_changes':later_exterior_changes,'development':total,'owned_changed_pixels':int((np.any(base!=current,axis=2)&~exterior).sum())}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',action='store_true');group.add_argument('--apply',action='store_true');group.add_argument('--check',action='store_true')
    args=parser.parse_args()
    prepare() if args.prepare else check() if args.check else apply()
