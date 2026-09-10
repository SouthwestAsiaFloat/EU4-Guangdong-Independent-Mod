#!/usr/bin/env python3
"""Native grouping and visibility contracts; does not validate native rendering."""
from validate_czc_government import MOD, one, values, walk, read_tree, contains
from encode_eu4_chinese_localisation import verify_file
from build_zhx_qinwang_score import generated
expected = {
    'zhx_feudatory_petition', 'zhx_gongyi_petition',
    'zhx_relieve_tianxia_member', 'zhx_appeal_to_tianzi_for_relief',
    'zhx_invite_qinwang', 'zhx_qinwang_willingness',
}
actions={}
for path in (MOD/'common/new_diplomatic_actions').glob('zhx*.txt'):
    for name,_,body in read_tree(path):
        assert name not in actions, 'Duplicate action'
        actions[name]=body
        assert one(body,'category')=='is_emperor_of_china', (name,'outside Zhou group')
assert expected <= actions.keys()
for name,tooltip in (
    ('zhx_relieve_tianxia_member','zhx_diplo_relief_available_tt'),
    ('zhx_appeal_to_tianzi_for_relief','zhx_diplo_appeal_available_tt'),
):
    action=actions[name];visible=one(action,'is_visible');allowed=one(action,'is_allowed')
    assert not any(k in ('is_at_war','is_in_war','any_war_enemy_country') for k,_,_ in walk(visible)), 'Temporary war conditions must grey, not hide'
    moved=next(v for v in values(allowed,'custom_trigger_tooltip') if one(v,'tooltip')==tooltip)
    assert contains(moved,'is_at_war','yes'), 'Lost war requirement'
    assert contains(moved,'attacker_leader','THIS') and contains(moved,'defender_leader','PREV' if 'relieve' in name else 'ROOT'), 'Lost direct external attack guard'
    assert any(k=='NOT' and contains(v,'zhx_is_tianxia_polity','yes') for k,_,v in walk(moved)), 'Lost external-enemy guard'
    assert contains(moved,'defenders','ROOT' if 'relieve' in name else 'FROM'), 'Lost already-joined guard'
assert one(actions['zhx_qinwang_willingness'],'is_visible')==[('always','=','no')], 'Do not show the obsolete score row'
assert one(actions['zhx_invite_qinwang'],'require_acceptance')=='no', 'Preserve send-time campaign snapshot'
assert contains(one(actions['zhx_qinwang_willingness'],'is_allowed'),'always','no')
for path,content in generated().items(): assert (MOD/path).read_text()==content, 'Generator would undo category'
loc=MOD/'localisation_source/033_zhx_diplomacy_category_readable_utf8.txt'
verify_file(loc,MOD/'localisation/replace/033_zhx_diplomacy_category_l_english.yml')
assert 'DIPLOMACYACTION_CATEGORY_is_emperor_of_china:0 "周天下"' in loc.read_text()
sprite=one(one(read_tree(MOD/'interface/zhx_diplomacy_category.gfx'),'spriteTypes'),'spriteType')
assert one(sprite,'name')=='GFX_diplomacy_action_is_emperor_of_china'
assert one(sprite,'texturefile')=='gfx/interface/icon_diplomacy_HRE.dds'
print(f'PASS: {len(actions)} Zhou actions grouped; war gates grey instead of hide; single visible Qinwang row; dispatch semantics retained; generation and Chinese encoding verified. Position/default expansion/runtime NOT validated.')
