"""Static contracts for the native building page and the mod province page."""
from pathlib import Path
from PIL import Image
from test_gdd_tianxia_territory import parse

MOD = Path(__file__).resolve().parents[1] / 'guangdong_independent_practice'
BUTTONS = ('gdd_tianxia_province_member_status_button',
           'gdd_tianxia_province_add_button', 'gdd_tianxia_province_remove_button')


class Node(dict):
    def __init__(self, body):
        super().__init__(body)
        self.body = body

    def items(self):
        return self.body


def children(body):
    return {dict(v)['name']: Node(v) for k, v in body
            if isinstance(v, list) and 'name' in dict(v)}


def xy(control):
    p = dict(control['position'])
    return float(p['x']), float(p['y'])


def rect(control, size):
    x, y = xy(control)
    return x, y, x + size[0], y + size[1]


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def validate_layout(text=None):
    text = text or (MOD / 'interface/provinceview.gui').read_text()
    roots = children(parse(text)['guiTypes'])
    windows = children(roots['provinceview'].items())
    province = children(windows['province_window'].items())
    buildings = children(windows['buildings_window'].items())
    values = children(buildings['province_values_window'].items())
    panel = children(buildings['zhx_province_mod_window'].items())
    assert xy(windows['buildings_window']) == (480, 13)
    assert xy(buildings['province_values_window']) == (4, 354)
    assert dict(roots['provinceview']['size']) == {'x': '430', 'y': '580'}
    for name in ('hre_button', 'trade_company_button'):
        assert xy(province[name]) == (20, 328), f'native action moved: {name}'
        assert province[name].get('scripted') != 'yes', f'native binding overridden: {name}'
    for name in ('hre_icon', 'trade_company_icon'):
        assert xy(province[name]) == (32, 328), f'native icon moved: {name}'
        assert province[name].get('alwaystransparent') != 'yes', f'native tooltip still masked: {name}'
    # Both native pages and native close control remain intact; no footer squeeze.
    native_positions = {'center_of_revolution': (28,141), 'center_of_revolution_label': (90,140),
                        'revolution_spread': (28,141), 'spreading_to_provinces_label': (93,165),
                        'spreading_revolution_label': (90,140), 'spreaded_revolution_label': (90,140),
                        'revolution_progress': (99,172), 'revolution_progress_frame': (90,168),
                        'revolution_progress_label': (150,190)}
    for name, p in native_positions.items():
        assert xy(values[name]) == p, f'native revolution layout changed: {name}'
    assert xy(buildings['building_close_button']) == (304,120)
    assert list(buildings)[-1] == 'building_close_button', 'native close button covered'
    assert list(panel)[0] == 'zhx_province_mod_background', 'input shield must precede content'
    assert panel['zhx_province_mod_background']['scripted'] == 'yes'
    assert xy(panel['zhx_province_mod_background']) == (0,115)
    content_rects = {}
    for name,c in panel.items():
        if name == 'zhx_province_mod_background': continue
        if name in BUTTONS:
            assert name not in province and name not in values, f'{name} still occupies a native slot'
            sprite = c['quadTextureSprite'].removeprefix('GFX_')
            with Image.open(MOD / f'gfx/interface/{sprite}.tga') as art:
                size = (art.width / 4, art.height)
        elif 'maxWidth' in c: size = (int(c['maxWidth']), int(c['maxHeight']))
        else: size = (71,28)
        r=rect(c,size)
        assert r[0]>=16 and r[2]<=328 and r[1]>=130 and r[3]<=585,(name,r)
        content_rects[name]=r
    assert len({content_rects[n] for n in BUTTONS})==1,'province states occupy different slots'
    for a,ra in content_rects.items():
        for b,rb in content_rects.items():
            if a>=b or (a in BUTTONS and b in BUTTONS): continue
            assert not overlaps(ra,rb),f'panel controls overlap: {a} / {b}'
    gui = (MOD/'common/custom_gui/zhx_province_panel.txt').read_text()
    bindings = children(parse('file = {\n'+gui+'\n}')['file'])
    page=bindings['zhx_province_mod_window']
    assert 'zhx_province_mod_page' in str(page['potential'])
    assert bindings['zhx_province_mod_background']['effect']==[('hidden_effect',[])], 'background has a game action'
    for name in panel:
        if name not in BUTTONS: assert name in bindings, f'unbound control: {name}'
    return {'native_revolution_controls':len(native_positions),'mod_controls':len(panel),'button':content_rects[BUTTONS[0]]}


if __name__ == '__main__': print('PASS',validate_layout())
