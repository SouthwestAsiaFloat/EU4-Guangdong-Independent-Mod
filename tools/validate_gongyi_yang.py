#!/usr/bin/env python3
"""Validate cross-file government, history, localisation and DDS contracts.

Does not emulate EU4 league succession; runtime evidence remains authoritative.
"""
from pathlib import Path
import re,struct
from validate_czc_government import read_tree,one,walk,require,contains
from encode_eu4_chinese_localisation import verify_file

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'guangdong_independent_practice'

def main():
    paths=list(MOD.glob('common/*/*gongyi*.txt'))+[MOD/'events/zhx_gongyi_events.txt']
    trees={p:read_tree(p) for p in paths}
    reforms=trees[MOD/'common/government_reforms/zzz_zhx_gongyi_reforms.txt']
    registry=read_tree(MOD/'common/governments/00_governments.txt')
    republic=one(registry,'republic')
    reform_ids={key for key,_,_ in reforms}
    for key in reform_ids:
        require(any(k==key for k,_,_ in walk(republic)),f'{key}: absent from republic tier list')
    for _,_,body in reforms:
        require(one(body,'duration')=='4','native four-year election contract')
        require(one(body,'has_term_election')=='yes','term election disabled')
        for target in [v for k,_,v in walk(body) if k=='trade_city_reform']:
            require(target in reform_ids,f'unknown release/fallback reform {target}')
    expected={'HYM':'zhx_yang_trade_league_reform',**{t:'zhx_gongyi_reform' for t in ['CDE','JJG','HYA','WHU','ZHO']}}
    for tag,key in expected.items():
        files=list((MOD/'history/countries').glob(tag+' - *.txt'))
        require(len(files)==1,f'{tag}: ambiguous history')
        history=read_tree(files[0]);require(contains(history,'add_government_reform',key),f'{tag}: wrong opening reform')
        keys=[k for k,_,_ in history]
        require(keys.index('government')<keys.index('add_government_reform'),f'{tag}: government resets reform')
    events=trees[MOD/'events/zhx_gongyi_events.txt']
    ids={one(body,'id') for k,_,body in events if k=='country_event'}
    for path,tree in trees.items():
        for k,_,v in walk(tree):
            if k=='id' and isinstance(v,str) and v.startswith('zhx_gongyi.'):
                require(v in ids,f'{path}: unknown event {v}')
    source=MOD/'localisation_source/023_zhx_gongyi_readable_utf8.txt'
    verify_file(source,MOD/'localisation/replace/023_zhx_gongyi_l_english.yml')
    loc=set(re.findall(r'^ ([\w.]+):',source.read_text(),re.M))
    for path,tree in trees.items():
        for k,_,v in walk(tree):
            if k in {'tooltip','custom_tooltip','title','desc','name'} and isinstance(v,str) and v.startswith('zhx_gongyi'):
                require(v in loc,f'{path}: missing localisation {v}')
    gfx=read_tree(MOD/'interface/zhx_gongyi_yang_icons.gfx')
    sprites={one(body,'name'):body for k,_,body in walk(gfx) if k=='spriteType'}
    for key in ['zhx_gongyi_reform','zhx_yang_trade_league_reform']:
        icon=one(one(reforms,key),'icon');sprite=sprites['government_reform_'+icon]
        texture=MOD/one(sprite,'texturefile');data=texture.read_bytes()
        require(data[:4]==b'DDS ',f'{texture}: invalid DDS')
        require(struct.unpack_from('<II',data,12)==(57,57),f'{texture}: expected native 57x57')
        require(one(sprite,'noOfFrames')=='1',f'{texture}: unexpected strip')
    print('PASS: reform registration, opening histories, event routing, localisation roundtrip, and native 57px assets')

if __name__=='__main__':main()
