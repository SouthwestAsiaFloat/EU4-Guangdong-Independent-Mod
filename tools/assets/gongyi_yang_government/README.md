# 公邑与扬国政府改革图标

本轮用户明确要求制作两类政府的 icon 美术资源。使用内置 imagegen 分别生成两张原画，完整提示词见 [prompts.json](prompts.json)，未使用 API／CLI 生成。

- [公邑原画](sources/gongyi.png)：城楼与青铜自治印信，突出一城自治与防守。
- [扬国原画](sources/yang.png)：中式商船与带鞘护商刀，突出贸易网络与雇佣军。
- 两者沿用现有改革图标的深青底色、暖金光照与历史绘画质感；没有烘焙选中边框，原生控件负责绘制界面状态。

`export_assets.py` 只做 LANCZOS 缩放与格式转换，不改画面内容。输出 57×57、单帧、未压缩 RGBA DDS，并验证解码像素与缩放结果一致。`manifest.json` 记录原画与贴图的路径、尺寸及 SHA-256。

## 接入信息

贴图在 `guangdong_independent_practice/gfx/interface/zhx_gongyi_yang/`，sprite 已在 `interface/zhx_gongyi_yang_icons.gfx` 注册。已接入的政府改革 icon 字段分别使用：

- 公邑：`icon = zhx_gongyi_autonomy`
- 扬国：`icon = zhx_yang_trade_league`

2026-09-06已绑定公邑与扬国政府改革。原版贴图和选中框核对结果为57×57，已纠正原先64×64导出；实机改革列表中的两枚新图标均与原版金框对齐。机制验收详见 docs/gameplay/14_gongyi_yang_governments.md。

源图已保存在项目内；游戏贴图不引用 Codex 缓存。

[放大与 57 px 预览](../../../planning/gongyi_yang_government_art/government_icons_preview.png)为素材预览，不是游戏截图。
