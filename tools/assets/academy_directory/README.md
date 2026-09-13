# 天下学宫：诸夏省面板配色

2026-09-13 用户要求以原版 EU4／诸夏省面板风格替代此前浅色古籍风。

背景材料由内置 image_gen 工具生成，参考正式 `guangdong_independent_practice/gfx/interface/zhx_province_panel_v1.tga` 的深青材质。参考仅经 PNG 格式转换供工具读取，没有修改省面板。

项目内原始素材：`tools/assets/academy_directory/teal_texture_v1.png`。
导出：`tools/build_zhx_academy_directory_art.py` 将背景缩放至 690×580，并组合源码定义的旧金边框、按钮及选中状态。背景上没有烘焙文字。五种局部字体改为浅色，并调整绿色收益／红色张力的对比度。未修改布局、按钮条件、事件或定位逻辑。

正式布局预览：`planning/religion_academies/directory_visuals/teal_chongli.png`、`teal_xunming.png`。预览是示例状态与近似系统字形，不是实机截图。此前 folio 预览保留为旧版记录。

重建：使用具备 Pillow 的 Python 运行 `tools/build_zhx_academy_directory_art.py`，再运行名录与宗教页生成器；贴图工具 `--check --preview` 可检查像素并更新布局预览。

## 最终生成提示词（内置工具，非 CLI）

Use case: background-extraction. Asset type: production Europa Universalis IV mod UI background texture. Input image 1 is the existing Zhuxia province panel, a STYLE AND MATERIAL REFERENCE. Create a full-bleed flat rectangular dark petrol-teal background texture matching ONLY the quiet dark blue-green painted/leather material inside that reference panel. Remove all gold frames, decorative corners, dividers and the courtyard illustration. No text, no symbols, no buttons, no border, no buildings. The entire canvas must be the same subtle finely mottled dark teal material, almost uniform with restrained organic wear, no large bright patches, no gradients toward black edges, no lighting hotspots, no perspective. Keep the average color near RGB 17, 40, 47. This texture will sit behind many small ivory UI labels, so very low contrast surface detail. Opaque full canvas, approximately landscape ratio 690:580.
