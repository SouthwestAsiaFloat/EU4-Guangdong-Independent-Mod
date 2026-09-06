# 邶国小篆旗字形来源

- 国别：邶国（`DMG`）
- 旗面文字：邶
- 字形：香港中文大学《汉语多功能字库》收录的小篆字形
- 条目：https://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php?word=%E9%82%B6
- 本地快照：`bei_small_seal_reference.jpg`
- 原图尺寸：57 × 75，JPEG
- 原图 SHA-256：`ae6830a4ae890f27ed827caee4a1c6c12d49a64cd6e04a627dd1af7605449184`

生成器只会校验源图哈希、反相黑白字形、清除 JPEG 浅色压缩噪点、等比例缩放并居中，不使用现代字体重绘，也不补笔。旗底沿用邶国定义中的 RGB `(91, 107, 76)`，文字沿用诸夏篆书旗的浅帛色。

```sh
python3 tools/generate_dmg_bei_small_seal_mask.py
python3 tools/generate_zhuxia_seal_flags.py
python3 tools/generate_dmg_bei_small_seal_mask.py --check
python3 tools/generate_zhuxia_seal_flags.py --check
```

输出包括：

- `tools/assets/bei_flag/bei_small_seal_mask.png`：注册进共享字形档案的 128 × 128 灰度遮罩。
- `planning/daming_refinement_b78/bei_small_seal_flag_preview.png`：最终配色预览。
- `guangdong_independent_practice/gfx/flags/DMG.tga`：由诸夏共用旗帜生成器产出的 128 × 128、24-bit、无压缩、左上原点 TGA。

源图来自中大字库的线上字例，用于记录字形依据并保证生成可复现；公开发布或再分发本地快照前，应另行核对中大字库的使用条件。
