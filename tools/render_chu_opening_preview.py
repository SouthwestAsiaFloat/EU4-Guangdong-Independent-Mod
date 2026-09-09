#!/usr/bin/env python3
"""Make a reading copy and contact sheet from the ten actual game textures."""
import json
from PIL import Image, ImageDraw
from build_lingnan_opening_events import ROOT, MOD, CHU_MANIFEST


def main():
    rows = json.loads(CHU_MANIFEST.read_text())['countries']
    directory = ROOT / 'tools/assets/event_pictures/chu_opening_v1'
    sheet = Image.new('RGB', (1060, 832), '#211d18')
    draw = ImageDraw.Draw(sheet)
    md = ['# 云梦的池沼 · 楚地十国开局背景事件 · 图文预览',
          '以下图片由游戏 DDS 导出，原生尺寸 512×132；正文沿用已审初稿。1444 新战役开局弹出对应国家的故事，点击文学按钮后进入模组介绍。',
          '已同步君主、继承人、配偶、主文化与主学派；六个楚属国均为伯国，衡归属楚国，南昌、临川保留独立伯国身份。',
          '地理差异待单独调整：州国现驻监利，文案中的兴国仍由鄂国持有；天师府现驻广信，设定写鹰潭。此次没有改省份归属或首都。楚与天师府仍使用现有政府机制。',
          '人物能力取自设定；未给定的配偶能力暂用 3/3/3，出生年份与继承人正统性为实现默认值，详见清单。图片与静态检查已完成，尚未重启游戏验证显示。']
    for i, row in enumerate(rows):
        tag = row['tag'].lower()
        dds = MOD / f'gfx/event_pictures/zhx_opening/zhx_opening_{tag}_eventPicture.dds'
        png = directory / f'{tag}_opening_preview.png'
        x, y = 12 + (i % 2) * 530, 28 + (i // 2) * 164
        with Image.open(dds) as im:
            im.save(png)
            sheet.paste(im.convert('RGB'), (x, y))
        draw.text((x, y - 18), row['tag'] + '  ' + row['event_id'], fill='#dfc894')
        ruler = row['ruler']
        md += [f'## {row["name"]}｜{row["title"]}', f'![{row["title"]}]({png})',
               f'开局君主：{ruler["dynasty"]}{ruler["name"]}；行政／外交／军事：{ruler["adm"]}／{ruler["dip"]}／{ruler["mil"]}。',
               row['body'], f'**按钮：**「{row["button"]}」',
               f'[查看完整原画]({ROOT / row["source_image"]})']
    sheet.save(directory / 'chu_native_contact_sheet.png')
    (ROOT / 'planning/opening_backgrounds/云梦的池沼_楚地十国开局背景事件_图文预览.md').write_text('\n\n'.join(md) + '\n')
    print('Exported ten native DDS previews, contact sheet and reading copy.')


if __name__ == '__main__':
    main()
