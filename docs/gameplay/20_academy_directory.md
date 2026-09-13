# 天下学宫界面

2026-09-13：代码已接入正式模组加载文件，专项离线检查通过；本轮未完成实机加载或交互验收。Computer Use 两次连接 EU4 均返回 `Accessibility error: AXError.cannotComplete`，未重启游戏或操作存档。

## 玩家入口与交互

宗教页标题行右侧新增“天下学宫”。入口复用 `zhx_is_lijiao_country`，只向具有现行礼教资格的人类玩家显示；不要求 Cradle of Civilization、不限制地图探索状态。礼教玩家可查看外国及非礼教国家持有的学宫。

名录按儒、法、墨、道、兵、纵横排列。固定显示六行，右侧上下箭头每次移动一行；下方固定详情区。主表显示名称、学派、当前驻地、所属国、传承／逐学／流散状态与定位按钮。选中项和滚动偏移按查看国家保存，合卷后重新打开不重置。

详情显示地方收益、本国关系与遗址数量。“本国关系”区别本派协同、宾学保护、改制保护和未受保护造成的思想张力；协同悬停包含清单中的实际国家增益并说明不叠加。流散时地方收益标为“复兴后”，不能定位；关系悬停解释原有年度复兴流程，不增加主动招揽。

“遗址”悬停列出地图上所有对应永久遗址，数量来自当前省份记录。遗址不计为活跃学宫，不生成迁徙年代或顺序。

本国学宫详情提供逐学、撤令入口，先打开具名确认事件；选项显示代价且结算时重新检查资格与当前所有权，再调用既有生命周期效果。事件 ID 与学宫绑定，后续改变选中行不会改变已经打开的确认对象。外国学宫不显示管理按钮。原有两个决议保留。

## 用户批准的兼容交互

用户于本轮明确选择“采用已验证接口，先完成可用版本”：

- 使用上下箭头逐行滚动，支持偏移保存；不声称支持鼠标滚轮或拖动滑块。
- 点击定位先收起名录并打开带原生 `goto` 的学宫驻地事件，玩家通过原生定位按钮前往。宗教页的关闭及省份面板打开由原生交互处理，本轮没有证明自动关闭宗教页、一步打开省份或未探索目标跳转。
- 定位事件提供“返回名录”与“合卷”。返回恢复原选中项和偏移。

这两项替代了最初概念图中的自由滚动与一步定位要求，不能将概念图当作当前实机截图。

## 实现与权威状态

生成入口为 `tools/build_zhx_academy_directory.py`，读取 `planning/religion_academies/academy_manifest.json`。生成 custom GUI、scripted triggers/effects、具名确认和定位事件、动态本地化、中文源与 GFX。

`tools/build_zhx_countryreligionview.py` 把名录控件插入既有、锁定哈希的汉化宗教页基线，仍保留原生宗教页与传教列表。原生根为 `countryreligionview`，GUI 的 ROOT／FROM 是查看国家。名录是其 `custom_window` 子窗口，不占用新的原生宗教机制；布局目标为 1280×768 及以上逻辑画布，实际缩放／裁切仍待游戏验证。

活跃学宫唯一权威仍是永久省份修正。`zhx_ad_site_<key>` 全局省份目标只作为所有玩家共用的世界索引，每次读取再次核对对应永久修正。不会把初始驻地或国家宗教当成学宫位置。

打开名录时一次 `every_province` 重建位置索引并计算查看国的遗址数量，不在 GUI potential 中扫描世界。安装新址与逐学完成后调用 `zhx_ad_refresh_viewers`，只为曾打开过名录的人类国家更新显示缓存；这两个调用由原生命周期生成器生成。省份普通易主不改变省份索引，持有国显示直接读取该省份的当前 Owner。

查看国的 `zhx_ad_initialized`、`zhx_ad_visible`、`zhx_ad_offset`、`zhx_ad_selected` 和遗址计数只负责呈现。原生宗教页关闭并不会伪称清理这些旗标；重新进入仍可继续浏览。改出礼教后 custom window 的资格门立即隐藏界面。

## 接口依据与限制

| 接口 | 依据与作用域 | 本轮实机状态 |
| --- | --- | --- |
| custom_button / custom_window / custom_text_box / custom_icon | 安装版 1.37.5 `common/custom_gui/example.txt`；宗教页 ROOT=FROM=查看国 | 未测新窗口 |
| 箭头、变量及可见性控制 | 现有天朝界面的脚本翻动控件；本名录每次偏移一行 | 离线边界验证通过 |
| 全局省份目标 + 修正重查 | 现有学宫到达／撤令省份目标，索引不拥有机制状态 | 迁徙与失效索引离线验证通过 |
| `goto = <event target>` | 既有 `.211` 学宫到达事件与 `.230` 撤令事件；country_event 顶层，不是脚本 effect | 新定位事件未测 |
| 每省遍历 + PREV 计数 | `every_province` 内 PREV 为当前查看国；不用 ROOT 猜测调用者 | 多遗址／不同查看国离线验证通过 |
| 逐学／撤令 | 调用现有具名 begin 效果及公共 withdraw 效果，确认时重新检查 | 旧生命周期静态契约通过，新 UI 未测 |

## 验证记录

- 新增 `tools/test_zhx_academy_directory.py`：16 项通过，覆盖滚动上下限、每个偏移的六行名录、保留浏览位置、不同玩家的独立状态、迁徙与多遗址索引、过期索引阻止定位、宗教资格、学派／宾学／改制保护、资源门槛、确认前易主和精确撤令身份。
- 生成文件一致性、GUI 绑定唯一性、引用的原生 sprites／贴图存在性、本地化编码通过。
- 学宫、生命周期、学派、开局学派、宗教定义、宗教 GUI 生成器检查通过。
- 生命周期校验器原先因继承的 `00_event_modifiers.txt` 非 UTF-8 注释报错，已改为仅在全局 ASCII 标识符扫描时采用无损 Latin-1 回退，未改动该游戏文件。
- 扩展检查 `validate_zhx_harmony_retirement.py` 存在既有失败：`stale pinned Harmony-retirement override: missions/DOM_Chinese_Missions.txt`。该任务文件与 HEAD 完全相同，SHA256 为 `dfbc2e5ba6dd61a132cd74fb434cc22bfe0c5a6411cc0818eec4e1ac96a64076`，本次未重写此任务或其生成器。
- 脚本已知失误窄审计未发现 PREVPREV／scripted-trigger export 问题；该审计不证明完整引擎支持。

建议使用已有 bundled Python 运行测试（系统 Python 缺 Pillow）：

```sh
python tools/build_zhx_academy_directory.py
python tools/build_zhx_countryreligionview.py
python tools/build_zhx_academy_lifecycle.py
python tools/encode_eu4_chinese_localisation.py
python -m unittest discover -s tools -p test_zhx_academy_directory.py -v
python tools/validate_zhx_academy_lifecycle.py
```

## 待实机验收

加载本轮代码后，确认宗教页入口、非礼教隐藏、名录打开／合卷／Escape、六行逐行滚动与返回位置、长国名和非默认缩放、遗址悬停内容。随后通过正式界面测试一次本国逐学确认与取消、一次精确撤令、外国定位与流散禁用，以及迁徙后仍打开名录时的状态刷新。需单独验证未探索省份的原生定位行为。保留前后截图和一次保存／读取证据，不以本轮离线测试替代这些实机结论。

## 2026-09-13：定位修复与清雅古籍美化

用户确认名录可打开驻地事件，但事件内定位没有效果。原因是原生事件 goto 只读取事件本地目标，原实现错误地引用了全局世界索引。现在 12 个驻地事件在 immediate 内复制当前有效驻地为局部 `zhx_ad_goto_province`，goto 与说明文字使用同一份快照；其他玩家刷新名录不会改写已经打开事件的快照。顺带修复同类的到达通知 `.211` 和撤令通知 `.230`。接口证据及限制见 [定位核查](runtime_evidence/academy_locator_2026-09-13/README.md)。

用户已批准“清雅古籍／书目式横条／作用优先”。正式 GUI 保留 690×580 尺寸与六行容量，改为浅暖纸底、细墨分隔、朱色侧线、淡赭选中底与小状态印框；底部依次显示题名、本国关系、收益、驻地与操作。箭头旁保留翻阅进度。仅为名录新增字体颜色定义，复用已依赖的汉化字体 `zh-hans-16/18/24`；没有修改全局字体或宗教页既有文字颜色。

13 张无文字的原生界面贴图由 `tools/build_zhx_academy_directory_art.py` 确定性生成，包括轻纸纹、边线、印框、按钮与箭头。没有新插画和地图数据。重建时先运行该工具（需 Pillow），再运行名录与宗教页生成器、本地化编码器。`--check` 校验贴图尺寸和像素；`--preview` 使用正式 GUI 坐标、正式贴图与示例世界状态生成预览。

预览位于 `planning/religion_academies/directory_visuals/folio_chongli.png` 与 `folio_xunming.png`。已目视检查两种示例的文本空间、选中行和操作区；预览使用近似系统中文字形，是布局预览，不是实机截图，图中各宫归属也不表示真实存档。

本轮 16 项离线回归、学宫及生命周期校验、相关生成器一致性、13 张贴图一致性、本地化编码及 `git diff --check` 通过。新增回归区分全局目标与事件局部目标，覆盖全部 12 个定位事件、目标失效和不同窗口快照。实机连接仍失败，新定位修复与美化尚未重载或点击验收；需完整重启 EU4 后重新打开名录和驻地事件。

## 当前视觉版本：深青与旧金

2026-09-13 用户要求改为与原版 EU4／诸夏省面板协调的风格，覆盖前述浅色古籍方案。当前正式贴图采用低对比深青纹理、旧金细框和角饰，正文为米白、标题为浅金；选中行使用青灰底和金色边线。深底上的收益与张力分别使用较亮的绿、朱红。六行布局、详情顺序和定位修复保持原样。

背景由内置 image_gen 参考正式诸夏省面板生成；项目素材、最终提示词和导出方式见 [素材记录](../../tools/assets/academy_directory/README.md)。当前预览为 `planning/religion_academies/directory_visuals/teal_chongli.png` 与 `teal_xunming.png`，旧 folio 图仅作历史记录。

本轮 16 项名录回归、生成器一致性、13 张贴图像素检查与 diff 检查通过。已检查新预览；未重启游戏或进行本轮实机验收。
