#!/usr/bin/env python3
"""Export inspectable PNGs from the actual DDS and a five-city reading copy."""
import json
from PIL import Image, ImageDraw
from build_lingnan_opening_events import ROOT, MOD, GONGYI_MANIFEST


def main():
    rows = json.loads(GONGYI_MANIFEST.read_text())['countries']
    directory = ROOT / 'tools/assets/event_pictures/gongyi_opening_v1'
    sheet = Image.new('RGB', (536, len(rows) * 160 + 12), '#211d18')
    draw = ImageDraw.Draw(sheet)
    md = ['# 公邑五国开局背景事件 · 图文预览',
          '以下图片由实际游戏 DDS 导出，以 512×132 原生尺寸展示；正文来自运行清单。',
          '五邑的成立均与蒙古入侵、抗蒙守土或后勤救济相连。开局直接弹出，确认文学按钮后进入模组介绍。']
    for i, row in enumerate(rows):
        tag = row['tag'].lower()
        dds = MOD / f'gfx/event_pictures/zhx_opening/zhx_opening_{tag}_eventPicture.dds'
        png = directory / f'{tag}_opening_preview.png'
        with Image.open(dds) as im:
            im.save(png)
            sheet.paste(im.convert('RGB'), (12, 28 + i * 160))
        draw.text((12, 10 + i * 160), row['tag'] + '  ' + row['event_id'], fill='#dfc894')
        r = row['ruler']
        md += [f'## {row["name"]}｜{row["title"]}',
               f'![{row["title"]}]({png})',
               f'开局执政：{r["dynasty"]}{r["name"]} · 行政／外交／军事：3／3／3',
               row['body'], f'**按钮：**「{row["button"]}」',
               f'[查看完整原画]({ROOT / row["source_image"]})']
    sheet.save(directory / 'gongyi_native_contact_sheet.png')
    (ROOT / 'planning/opening_backgrounds/公邑五国开局背景事件_图文预览.md').write_text('\n\n'.join(md) + '\n')
    print('Exported five native DDS previews, contact sheet and reading copy.')


if __name__ == '__main__':
    main()
