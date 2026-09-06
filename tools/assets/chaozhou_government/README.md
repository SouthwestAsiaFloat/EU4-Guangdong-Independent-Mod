# 潮州政府机制美术 v02

保留已批准 v01 的深木框、旧金饰边、左青右朱配色。右徽记改为龟钮方官印，没有锁形 U 环；士绅徽记采用无文字的笏板与卷册。没有修改任何 GUI、GFX 声明或政府机制。

## 来源

- 美术使用内置 `image_gen` 生成，v01 只作为视觉参考，未覆盖。
- 正式源图：`planning/chaozhou_government_art/chaozhou_government_art_v02.source.png`。
- 完整两次提示：`planning/chaozhou_government_art/chaozhou_government_art_v02.prompt.txt`。
- 第一次生成：`/Users/xinanyapiao/.codex/generated_images/01a06f5a-4775-7371-9f30-cfb8b8cffd00/exec-916b7e3e-fe4d-4feb-bcb4-72984eef2a4b.png`。
- 第二次要求仅提取背景，但工具输出了暗色底并改变明暗，因此未用于生产。该结果保留为 `chaozhou_government_art_v02.extraction_rejected.png`，来源为同目录 `exec-35a9eded-7b5c-4fc9-b292-c542b1faff55.png`。

## 透明通道与机械导出

内置工具第一张产物实际上是 RGB，浅灰棋盘被写进背景。`export_assets.py` 在五个固定裁切窗内，只将与边缘连通、RGB 最小通道不低于 175 且通道极差不超过 40 的浅色中性像素视作背景；将其 alpha 置零，并将 alpha 轮廓向内收一个源像素以移除烘焙抗锯齿白边。所有前景 RGB 保持原值。没有程序绘画、改色、重画或锐化。

随后按非透明包围盒裁切，用 Lanczos 缩放到约定大小。图标的正常/占优两帧暂时使用同一幅图。DDS 为无压缩 32 位 RGBA、传统 DDS 头、无 mipmap；每个文件都与对应 PNG 做了逐字节 RGBA 回读对照，并验证包含 0 与 255 的 alpha。

运行环境需 Python 3、Pillow 与 NumPy。可从项目根目录执行：

```sh
python3 tools/assets/chaozhou_government/export_assets.py
```

本机已验证的 Python 为 `/Users/xinanyapiao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`。`manifest.json` 保存原图与输出哈希、裁切窗、尺寸和透明像素数。

## 交付

| 资源 | DDS 尺寸 | 帧 | 用途 |
| --- | --- | --- | --- |
| frame | 280×50 | 1 | 木框和青朱底槽，无固化文字、徽记或游标 |
| gentry | 64×32 | 2，每帧32×32 | 士绅徽记 |
| ruler | 64×32 | 2，每帧32×32 | 统治者龟钮方官印 |
| pointer | 16×24 | 1 | 独立金色游标 |
| pointer_track | 5880×50 | 21，每帧280×50 | 原生权力值对应的游标位置图集 |
| government_reform | 64×64 | 1 | 改革图标 |

生产 PNG 位于本目录 `production/`；对应 DDS 位于 `guangdong_independent_practice/gfx/interface/gdd_czc_government/`。完整透明 sheet 为 `planning/chaozhou_government_art/chaozhou_government_art_v02.png`。

实际 280×50 预览有 gentry、balanced、ruler 三个位置：`planning/chaozhou_government_art/chaozhou_government_v02_280x50_*.png`。`chaozhou_government_v02_preview_4x.png` 是均势预览的最近邻放大，仅用于检查像素。

以 280×50 容器左上角为原点：frame=(0,0)，gentry=(0,9)，ruler=(248,9)，均势 pointer=(132,13)。预览验证了实际尺寸下笏板卷册和方官印仍可区分；游戏内 UI 对齐仍由集成任务验证。

`pointer_track` 只粘贴已有 `production/pointer.png`，没有新增绘画。21 帧从左到右排列，每帧透明 280×50；游标中心 x=40、50、…、240，顶部 y=13。帧 1 对应原生 `statists_vs_orangists=-1`，帧 11 对应 0，帧 21 对应 1；各帧完整坐标见 manifest。图集整体在容器 (0,0) 显示，由原生 trigger 选择帧，不使用另建镜像变量。
