# 周天子政府改革图标

使用内置 imagegen 生成冕旒冠原画；完整提示词保存在 `prompts.json`，原画保存在 `sources/mianliu.png`。配色为玄黑、朱红、玉白和少量金饰，构图为略俯视的四分之三侧面，单冠、无人物和文字。

`export_assets.py` 依赖 Pillow，仅执行缩放与格式转换。运行 `python3 tools/assets/tianzi_government/export_assets.py` 可重建 57×57 单帧、未压缩 RGBA DDS、SHA-256 清单和预览。素材不自带边框，选中框由原生政府改革控件绘制。

生产纹理：`guangdong_independent_practice/gfx/interface/zhx_tianzi/mianliu_57.dds`。

游戏绑定：`interface/zhx_tianzi_icons.gfx` 注册 `government_reform_zhx_tianzi_mianliu`；当前周国历史已采用独立的 `zhx_tianzi_reform`，该改革的 `icon` 指向 `zhx_tianzi_mianliu`；原版 `celestial_empire` 图标字段已恢复。机制说明见 `docs/gameplay/15_tianzi_government.md`。没有覆盖原版通用的 `government_reform_celestial_empire` sprite。

已验证 DDS 尺寸、像素往返、sprite 唯一性、改革引用及 Clausewitz 语法解析，并目视检查 `planning/tianzi_government/icon_preview.png` 的实际尺寸效果。预览不是游戏截图；尚未进行游戏内显示验收。
