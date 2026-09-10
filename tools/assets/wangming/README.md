# 王命素材

由内置 ImageGen 生成 `sources/wangming_atlas_v1.png`：参考 EU4 足利幕府机制的金边圆形绘画按钮与象牙色绢底，内容为贡金、迁民木车、甲士赴王旗。第三图为军伍征调，没有将领机制。图形无文字，中文由游戏绘制。

运行 `export_assets.py`（需要 Pillow）裁切原图、清除圆章外黑色底、导出正常与灰暗两帧。`manifest.json` 记录原图及导出的 SHA-256、裁切框和尺寸。三按钮每帧 72×72，横向双帧 DDS 144×72；绢底 344×93。

`planning/wangming/native_size_preview*.png` 为布局合成示意，字体不是游戏字库，不能证明实机渲染。
