# 周制封国改革图标

使用内置 imagegen 生成三张原画；伯、侯公提示词保存在 [prompts.json](prompts.json)，2026-09-08 新增子国提示词保存在 [zi_prompt.txt](zi_prompt.txt)。没有使用 API／CLI 生成。

- [sources/investiture_document.png](sources/investiture_document.png)：暖米色册命文书、深木卷轴与朱绶，用于子国。
- [sources/investiture.png](sources/investiture.png)：玉圭、册命与朱绶，用于伯国。
- [sources/ritual_ding.png](sources/ritual_ding.png)：青铜礼鼎、玉印与朱布，用于侯国和公国。
- `export_assets.py`：仅缩放和格式转换，将原画导出为 57×57、单帧、未压缩 RGBA DDS；检查 DDS 解码后的像素与缩小原图完全一致，并输出素材预览。
- `manifest.json`：源图与生产纹理的路径、尺寸和 SHA-256。
- 游戏绑定：`interface/zhx_feudatory_icons.gfx` 的 `government_reform_zhx_investiture_document`、`government_reform_zhx_investiture`、`government_reform_zhx_ritual_ding`。改革的 `icon` 字段使用相应后缀。

源图已复制进仓库；游戏不引用 Codex 缓存。原画不包含边框，选中金框及不可用状态继续交给原生改革控件绘制。

[素材与实际尺寸预览](../../../planning/zhou_feudatories/government_icons_preview.png)不是游戏截图。已检查三张生产纹理、sprite 引用及周制改革静态契约，尚未进行游戏内显示验收；本轮未操作用户的游戏窗口。
