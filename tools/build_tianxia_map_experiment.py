#!/usr/bin/env python3
"""Isolated EU4 experiment: preserve goods with per-province flags, then paint.
Uses native goods/colours; no trade-good definitions or economic rebalance.
"""
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT/'guangdong_independent_practice'
GAME = Path.home()/'Library/Application Support/Steam/steamapps/common/Europa Universalis IV'
PREFIX = 'zhx_map_exp'
# User's red outline, 2026-09-13. Do not expand to whole areas or owner borders.
FALLEN_PROVINCES = {5298:'瓜州',5299:'苦峪',707:'玉门',5297:'嘉峪',5296:'张掖',
    708:'武威',5295:'永昌',2182:'靖远',5288:'松山',698:'宁夏',5287:'灵州',
    5286:'中卫',5277:'固原',5276:'秦安',5292:'碾伯',699:'兰州'}
FALLEN_REGIMES = ('HMI','SHZ','GZH','WGS','HZH')



def build():
    goods = set()
    # Same filename in the mod overrides the vanilla source.
    files = {p.name:p for p in (GAME/'common/tradegoods').glob('*.txt')}
    files.update({p.name:p for p in (MOD/'common/tradegoods').glob('*.txt')})
    for p in files.values():
        goods.update(re.findall(r'(?m)^(\w+)\s*=\s*\{', p.read_text(encoding='utf-8-sig')))
    assert {'tea','copper','wool','naval_supplies','unknown'} <= goods
    backup='\n'.join(f'        if = {{ limit = {{ trade_goods = {g} }} set_province_flag = {PREFIX}_saved_{g} }}' for g in sorted(goods))
    restore='\n'.join(f'        if = {{ limit = {{ has_province_flag = {PREFIX}_saved_{g} }} change_trade_goods = {g} clr_province_flag = {PREFIX}_saved_{g} }}' for g in sorted(goods))
    known=' '.join(f'trade_goods = {g}' for g in sorted(goods))
    flags=' '.join(f'has_province_flag = {PREFIX}_saved_{g}' for g in sorted(goods))
    seed_provinces='\n'.join(f'        {pid} = {{ set_province_flag = zhx_longxi_fallen_homeland set_province_flag = zhx_tianxia_province set_province_flag = zhx_tianxia_admission_reward_paid }} # {name}' for pid,name in FALLEN_PROVINCES.items())
    seed_regimes='\n'.join(f'        {tag} = {{ set_country_flag = zhx_longxi_occupying_regime }}' for tag in FALLEN_REGIMES)
    seed=f'''# Persistent historical identity, not the temporary commodity backup ledger.
zhx_seed_longxi_fallen_homeland = {{
    if = {{
        limit = {{ NOT = {{ has_global_flag = zhx_longxi_fallen_seeded_v1 }} NOT = {{ has_global_flag = zhx_tianxia_dismantled }} }}
{seed_provinces}
{seed_regimes}
        set_global_flag = zhx_longxi_fallen_seeded_v1
    }}
}}
'''
    fallen_trigger='''# Province scope. Province identity and the current owner's regime are independent.
zhx_is_fallen_zhou_province = {
    has_province_flag = zhx_tianxia_province
    OR = {
        owner = { NOT = { zhx_is_tianxia_polity = yes } }
        AND = {
            has_province_flag = zhx_longxi_fallen_homeland
            owner = { has_country_flag = zhx_longxi_occupying_regime }
        }
    }
}
'''
    effects=seed+f'''# GENERATED. Country entry; every_province enters province scope.
# Backups are written before any change. Re-entry is blocked globally.
{PREFIX}_open = {{
    if = {{
        limit = {{ NOT = {{ has_global_flag = {PREFIX}_active }} NOT = {{ any_province = {{ OR = {{ {flags} }} }} }} }}
        zhx_seed_longxi_fallen_homeland = yes
        set_global_flag = {PREFIX}_active
        add_country_modifier = {{ name = {PREFIX}_warning duration = -1 }}
        every_province = {{
            limit = {{ owner = {{ exists = yes }} OR = {{ {known} }} }}
{backup}
            if = {{
                limit = {{ has_province_flag = zhx_tianxia_province }}
                if = {{
                    limit = {{ OR = {{ has_province_flag = {PREFIX}_sample_fallen zhx_is_fallen_zhou_province = yes }} }}
                    change_trade_goods = copper
                }}
                else = {{
                    if = {{
                        limit = {{ owner = {{ zhx_is_seven_great_feudatory = yes }} }}
                        change_trade_goods = naval_supplies
                    }}
                    else = {{ change_trade_goods = tea }}
                }}
            }}
            else = {{ change_trade_goods = wool }}
        }}
    }}
}}

# Can be invoked by any human country, including after a tag change.
{PREFIX}_restore = {{
    every_province = {{
{restore}
        clr_province_flag = {PREFIX}_sample_fallen
    }}
    every_country = {{ remove_country_modifier = {PREFIX}_warning }}
    clr_global_flag = {PREFIX}_active
}}
'''
    decisions=f'''country_decisions = {{
    {PREFIX}_open_decision = {{
        major = yes
        potential = {{ ai = no NOT = {{ has_global_flag = {PREFIX}_active }} }}
        allow = {{ NOT = {{ any_province = {{ OR = {{ {flags} }} }} }} }}
        effect = {{ country_event = {{ id = {PREFIX}.1 }} }}
        ai_will_do = {{ factor = 0 }}
    }}
    {PREFIX}_restore_decision = {{
        major = yes
        potential = {{ ai = no OR = {{ has_global_flag = {PREFIX}_active any_province = {{ OR = {{ {flags} }} }} }} }}
        allow = {{ always = yes }}
        effect = {{ hidden_effect = {{ {PREFIX}_restore = yes }} }}
        ai_will_do = {{ factor = 0 }}
    }}
}}
'''
    event=f'''namespace = {PREFIX}
country_event = {{
    id = {PREFIX}.1
    title = {PREFIX}_prompt_title
    desc = {PREFIX}_prompt_desc
    picture = TRADEGOODS_eventPicture
    is_triggered_only = yes
    option = {{ name = {PREFIX}_cancel }}
    option = {{
        name = {PREFIX}_confirm
        trigger = {{ NOT = {{ has_global_flag = {PREFIX}_active }} }}
        hidden_effect = {{ {PREFIX}_open = yes }}
    }}
}}
'''
    hud = r'''        # ZHX_MAP_EXPERIMENT_HUD_BEGIN
        windowType = {
            name = "zhx_map_exp_hud"
            position = { x = 560 y = 157 }
            size = { x = 440 y = 66 }
            moveable = 0
            fullScreen = no
            scripted = yes
            guiButtonType = {
                name = "zhx_map_exp_hud_background"
                position = { x = 0 y = 0 }
                quadTextureSprite = "GFX_zhx_map_exp_hud_background"
                scripted = yes
            }
            guiButtonType = {
                name = "zhx_map_exp_hud_frame"
                position = { x = 0 y = 0 }
                size = { x = 440 y = 66 }
                quadTextureSprite = "GFX_gdd_eoc_reform_frame"
                alwaystransparent = yes
            }
            instantTextBoxType = {
                name = "zhx_map_exp_hud_title"
                position = { x = 12 y = 5 }
                font = "vic_22"
                text = "zhx_map_exp_hud_title"
                maxWidth = 416
                maxHeight = 26
                format = centre
            }
            instantTextBoxType = {
                name = "zhx_map_exp_hud_hint"
                position = { x = 12 y = 37 }
                font = "vic_18"
                text = "zhx_map_exp_hud_hint"
                maxWidth = 180
                maxHeight = 24
                format = left
            }
            guiButtonType = {
                name = "zhx_map_exp_hud_restore"
                position = { x = 204 y = 33 }
                quadTextureSprite = "GFX_standard_button_224"
                buttonText = "zhx_map_exp_hud_restore"
                buttonFont = "vic_18"
                clicksound = click
                scripted = yes
            }
        }
        # ZHX_MAP_EXPERIMENT_HUD_END'''
    topbar = MOD/'interface/topbar.gui'
    topbar_text = topbar.read_text()
    if '# ZHX_MAP_EXPERIMENT_HUD_BEGIN' in topbar_text:
        topbar_text = re.sub(r'        # ZHX_MAP_EXPERIMENT_HUD_BEGIN.*?        # ZHX_MAP_EXPERIMENT_HUD_END', lambda m:hud, topbar_text, flags=re.S)
    else:
        anchor='\t\t# Zhou/Tianxia HUD entry.'
        assert topbar_text.count(anchor)==1
        topbar_text=topbar_text.replace(anchor,hud+'\n\n'+anchor)
    bindings = '''# Topbar follows the existing zhx_tianxia_topbar_window integration.
# Viewer country scope; global active flag makes the warning survive tag changes.
custom_window = {
    name = zhx_map_exp_hud
    potential = { ai = no has_global_flag = zhx_map_exp_active }
}
custom_button = {
    name = zhx_map_exp_hud_background
    potential = { has_global_flag = zhx_map_exp_active }
    trigger = { hidden_trigger = { always = yes } }
    effect = { hidden_effect = { } }
    tooltip = zhx_map_exp_legend_tt
}
custom_button = {
    name = zhx_map_exp_hud_restore
    potential = { has_global_flag = zhx_map_exp_active }
    trigger = { hidden_trigger = { always = yes } }
    effect = { hidden_effect = { zhx_map_exp_restore = yes } }
    tooltip = zhx_map_exp_hud_restore_tt
}
'''
    loc={
      'legend_tt':'深蓝（船具）：现任七大诸侯周土。深绿（茶）：其他成员周土。橙色（铜）：沦陷周土。浅灰（羊毛）：其余领土。沦陷判定优先；收复或改选后，恢复商品并重新开启形势图即可更新。',
      'hud_title':'§Y周天下形势图已开启§!',
      'hud_hint':'§R请保持暂停！§!',
      'hud_restore':'恢复商品并退出',
      'hud_restore_tt':'恢复所有已备份省份的原商品，关闭形势图提示。不会自动推进时间或切换地图模式。',
      'open_decision_title':'【实验】打开周天下形势图',
      'open_decision_desc':'临时改写已拥有省份的商品以显示周土。仅限单人测试局；必须先暂停。关闭须执行“恢复所有商品”，切换地图或按 Esc 不会恢复。',
      'restore_decision_title':'【立即恢复】关闭形势图，恢复所有商品',
      'restore_decision_desc':'按逐省备份恢复商品并移除实验标记。请先执行本决策，再恢复时间、保存或退出游戏。',
      'sample_decision_title':'【测试样例】将首都显示为沦陷周土',
      'sample_decision_desc':'只用于验证橙色显示；不改变持有国或周籍。关闭形势图时删除该测试标记。',
      'prompt_title':'§R实验地图：暂停后才能开启§!',
      'prompt_desc':'§R仅限单人测试局。此功能会临时改写全世界已拥有省份的商品！§!\\n\\n1. 确认游戏已暂停；本实验不会替你自动暂停。\\n2. 开启后，手动选择原版“商品”地图模式。\\n3. 深蓝（船具）＝现任七大诸侯持有的周土；深绿（茶）＝其他成员持有的周土；橙色（铜）＝沦陷周土（含陇西旧占据政权治下的红圈故土）；浅灰（羊毛）＝其余已拥有省份。未殖民地保持原样。\\n4. 查看期间不要推进时间，不要存档，不要退出。商品相关数字只是临时状态。\\n5. 点击顶部“恢复商品并退出”，再继续游戏。切地图、按 Esc 均不会恢复。\\n\\n误存后请保持本实验模组启用并读档；启动恢复钩子会尝试恢复，仍应检查恢复决策。联机不受支持。陇西故土由其他周天下成员收回后，重新开图会恢复相应成员色。',
      'cancel':'返回，暂不开启',
      'confirm':'我已暂停，开启实验形势图',
      'warning':'§R商品已临时替换：禁止推进时间！§!',
      'warning_desc':'当前是实验形势图。请保持暂停，查看完毕立即点击顶部“恢复商品并退出”，也可使用恢复决策。切换地图和关闭窗口不会恢复商品。',
    }
    hud_gfx = '''spriteTypes = {
    corneredTileSpriteType = {
        name = "GFX_zhx_map_exp_hud_background"
        texturefile = "gfx/interface/scroll_track.dds"
        size = { x = 440 y = 66 }
        borderSize = { x = 4 y = 4 }
    }
}
'''
    outputs={topbar:topbar_text,
      MOD/'common/scripted_triggers/zhx_map_experiment.txt':fallen_trigger,
      MOD/'interface/zhx_map_experiment.gfx':hud_gfx,
      MOD/'common/custom_gui/zhx_map_experiment.txt':bindings,
      MOD/'common/scripted_effects/zhx_map_experiment.txt':effects,
      MOD/'decisions/zhx_map_experiment.txt':decisions,
      MOD/'events/zhx_map_experiment.txt':event,
      MOD/'common/event_modifiers/zhx_map_experiment.txt':f'{PREFIX}_warning = {{\n    global_tax_modifier = 0\n}}\n',
      MOD/'common/on_actions/zhx_map_experiment.txt':f'# Best-effort recovery on load; no automatic unpause or map switch.\non_startup = {{\n    zhx_seed_longxi_fallen_homeland = yes\n    if = {{\n        limit = {{ OR = {{ has_global_flag = {PREFIX}_active any_province = {{ OR = {{ {flags} }} }} }} }}\n        {PREFIX}_restore = yes\n    }}\n}}\n',
      MOD/'localisation_source/zhx_map_experiment_readable_utf8.txt':'l_english:\n'+''.join(f' {PREFIX}_{k}:0 "{v}"\n' for k,v in loc.items()),
    }
    return outputs,sorted(goods)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    outputs,goods=build()
    for p,text in outputs.items():
        if args.check: assert p.exists() and p.read_text()==text,p
        else: p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    sys.path.insert(0,str(ROOT/'tools'))
    from encode_eu4_chinese_localisation import encode_file,verify_file
    s=MOD/'localisation_source/zhx_map_experiment_readable_utf8.txt';t=MOD/'localisation/zhx_map_experiment_l_english.yml'
    if not args.check: encode_file(s,t)
    verify_file(s,t)
    print(('CHECKED' if args.check else 'WROTE'),len(outputs),'sources;',len(goods),'goods backed up')
