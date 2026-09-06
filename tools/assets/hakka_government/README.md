# 客家政府生产美术

三枚徽记由内置 imagegen 分别生成，完整原始提示词在 `prompts.json`。

- `sources/farmers.png`：乡社稻穗与田契。
- `sources/burghers.png`：工商算盘与织梭。
- `sources/army.png`：军府战鼓与长矛。
- `export_assets.py`：保留原图 alpha，导出游戏所需尺寸与未压缩 RGBA DDS，扩展阶层图集并制作预览。
- `manifest.json`：原图与输出 SHA-256、尺寸和上游图集来源。

源图已复制到仓库，游戏不引用 Codex 缓存路径。生成工具为内置 imagegen；军府首轮网络失败后重试成功，没有使用 API/CLI 替代路径。

运行导出器需要 Pillow，可使用 Codex bundled Python。检查器 `tools/validate_hak_government.py` 验证输出与 manifest、透明度及原图集像素。

夜测补充：`gfx/interface/ideas_EU4/gdd_hak_peasants_{loyalty,influence}_modifier{,_opposite}.dds` 复用本机原版 `ideas_EU4/burghers_*` 同类图标，供原生阶层特权界面按修正键自动查找；原派系及特权主体仍使用本目录生成资产。
