# 国家开局背景事件：岭南八国、公邑五国与楚地十国

2026-09-07：原岭南八国流程已获用户实测确认；随后扩展公邑五国与楚地十国，当前共23国。新增两批仅做文件与静态检查，未重启游戏。

## 玩家流程

1444-11-11 开始的新战役中，人类玩家选择南海、桂林、潮州、客家、侬国、田州、俚寮、安南、常、九、汉、芜或舟，由原生 `on_startup → events` 直接显示本国背景介绍，不设置天数延迟。点击文学按钮后，同步进入四类模组介绍目录。按钮只有显示流程效果，没有钱粮、威望或其他奖励。

其他国家直接进入模组介绍目录。AI 不显示这批介绍。已进行中的旧战役不补弹 1444 历史背景；正常存档中的待处理事件与国家标记由游戏保存，不加入额外每月或每日扫描。

| 国家 | 事件 | 标题 |
| --- | --- | --- |
| GDD 南海 | zhx_opening.101 | 番禺旧帆 |
| GUI 桂林 | zhx_opening.102 | 八桂残疆 |
| CZC 潮州 | zhx_opening.103 | 八邑共推 |
| HAK 客家 | zhx_opening.104 | 山中有国 |
| NUN 侬国 | zhx_opening.105 | 众峒举火 |
| TZZ 田州 | zhx_opening.106 | 桂娇遗约 |
| LIL 俚寮 | zhx_opening.107 | 高凉旧将 |
| DAI 安南 | zhx_opening.108 | 两重冠冕 |
| CDE 常 | zhx_opening.201 | 一堤之众 |
| JJG 九 | zhx_opening.202 | 江口公秤 |
| HYA 汉 | zhx_opening.203 | 留门待归 |
| WHU 芜 | zhx_opening.204 | 炉火照江 |
| ZHO 舟 | zhx_opening.205 | 潮外有约 |

## 文件与状态

`planning/opening_backgrounds/lingnan_opening_manifest.json` 与同目录 `gongyi_opening_manifest.json` 分别保存两批文案、路由和图片裁切；后者还保存五邑的开局执政者。修订对应清单后，重新运行 `tools/build_lingnan_opening_events.py`；Markdown 保留为图文审阅材料。

生成器输出专用 events、scripted_effects、scripted_triggers、sprite .gfx、二十三张 512×132 RGBA DDS 以及中文可读源和编码结果。原画分别在 `tools/assets/event_pictures/lingnan_opening_v1/` 和 `gongyi_opening_v1/`；游戏纹理位于 `gfx/event_pictures/zhx_opening/`。不覆盖原版 `EventWindow` 或其他 .gui。

国家介绍使用独立的 `zhx_opening_background_on_actions.txt`：十三个可见背景事件和启动专用目录 `zhx_guide.0` 直接注册在原生 `on_startup.events`，与安装版原版明朝、马穆鲁克开局事件同样使用原生事件列表。没有隐藏启动分发、`days` 定时器或逐国初始化扫描。

国家与日期资格由 `zhx_should_show_opening_background` 判断。故事显示时才设置 `zhx_opening_background_pending` 与 `zhx_opening_background_seen`；目录同时检查故事资格和 pending，因此无论引擎先检查哪一个事件，都只显示应有的窗口。故事确认按钮清除 pending，调用同步的 `zhx_open_mod_guide`；手动决议也同步打开目录。可重读目录 `zhx_guide.1` 和首次目录 `zhx_guide.0` 共享内容与导航，只有首次入口带已读及故事排除条件。

2026-09-07用户报告新战役过一天未显示背景。日志证实新版目录已加载，但不足以证明未显示背景的准确引擎时序。最初检查发现全局初始化内的人类国家扫描及仅限11月11日的安排条件存在风险；曾改成两段次日分发，随后按用户要求移除延迟，改用原生可见开局事件。当前补充测试覆盖78组日期、事件列表正反顺序、独立国家作用域、无世界初始化旗标、故事与目录互斥、同步跳转和重开；静态通过不代表已重新实机验证。

中文通过现有 EU4 双字节编码流程生成，映射已加入 `tools/encode_eu4_chinese_localisation.py`，文件为 `026_zhx_opening_backgrounds`。文学出处留在审阅稿，不占用游戏正文。

## 验证

使用具备 Pillow 的 Python 环境运行：

```sh
python3 tools/build_lingnan_opening_events.py --check
python3 tools/validate_lingnan_opening_events.py
python3 tools/encode_eu4_chinese_localisation.py --check
python3 tools/validate_zhou_feudatories.py
python3 tools/validate_zhx_opening_schools.py
```

以上检查已通过。专项校验直接解析生成的脚本，覆盖十三国路由、AI 排除、开局日期边界、重复初始化、故事待确认状态、模拟保存／恢复状态、一次性完成和其他国家的总览。该校验不会模拟 EU4 引擎；还核验了事件／图片引用、DDS 尺寸、编码回读及构建结果一致性。

已逐图检查实际尺寸纹理拼图，修正人物头部被裁切的问题。游戏文件夹现有符号链接指向本仓库，无需另复制一份 Mod。正在运行的游戏不会因此热加载新事件。

实机待验：重启游戏后选取新增五公邑分别新开 1444 战役，不推进日期，检查标题、完整长文、插图与文学按钮；确认关闭背景后才出现系统总览。再对一个待确认事件存档重载，验证没有重复排队，并检查当前 error.log。此次遵循用户此前的“文件与静态检查”要求，未操作或重启游戏。

## 公邑五国新增内容

五国文案采用蒙古入侵为创立背景，分别写治水供军、江口粮运、守城救民、匠户铸器、海上救难。五幅插图采用内置 imagegen 独立生成；完整提示词及来源记录在 `tools/assets/event_pictures/gongyi_opening_v1/generation_manifest.json`。

为使事件里的姓名与开局人物一致，国家历史增加标记包围的1444年执政者块：彭守成、陶秉钧、杜应川、沈砺、叶素卿。能力统一采用实现默认值3/3/3，出生日期默认1400.1.1，叶素卿为女性；不增加继承人、特质或世袭规则。生成器保留原国家配置，只更新自己的具名人物块，发现其他统治者定义时拒绝覆盖。

原有公邑改革、四年选举、主学派、领土和商盟均沿用现行配置。人物历史使用既有双字节原始脚本编码，事件本地化走可读源到编码YAML的流程。

图文预览：`planning/opening_backgrounds/公邑五国开局背景事件_图文预览.md`；五图实际尺寸拼图在素材目录的 `gongyi_native_contact_sheet.png`。

本轮静态结果：十三国开局78组日期／顺序／作用域检查、五位人物与改革检查、67国学派检查、全量中文编码回读、模组介绍91页420条跳转均通过。已核对五个国家原配置与HEAD一致（仅新增具名人物块），并核对五篇审阅正文与运行清单逐字一致。五张512×132实际DDS拼图已人工检视；新增五国未做实机验收。


## 楚地十国新增内容（当前批次）

清单：`planning/opening_backgrounds/chu_opening_manifest.json`。文学正文逐字沿用《云梦的池沼》初稿；来源 DOCX 原文与校验和另存快照。事件 `zhx_opening.301` 至 `.310` 依次对应 CHC、CSA、HNG、ZHU、QVN、ACG、EGU、NCH、LCH、TSF。继续沿用原生 `on_startup` 即时显示和文学按钮打开介绍目录的流程。

十张 EU4 油画风插图分别生成，原图2172×724，生产裁切 top=82、高560，再缩至512×132；保留完整原画及提示词、输出路径和 SHA-256。图文预览：`planning/opening_backgrounds/云梦的池沼_楚地十国开局背景事件_图文预览.md`。

开局配置按新版设定同步：

- 长沙、衡、州、权、安成、鄂为楚国的六个伯国附属国；安成从侯改伯，衡补入普通附庸关系。南昌、临川为独立伯国。
- 十国均奉礼教；南昌主法家，其余九国主道家。67国总名录保持不变，各家数量为儒14、法8、墨10、道16、兵9、纵横10；仅修正开局分配，不动学派清理、践履与原生界面同步流程。
- 安成主文化改荆楚；其他国家保留与来源一致的文化。没有改省份文化。
- 君主和继承人的姓名与三维来自用户设定，配偶具名。出生年份为实现默认值，配偶未给的三维暂用3/3/3，继承人正统性默认70；这些默认值不声称来自原稿。继承人与配偶使用历史有效终点1821.1.1，沿用已有历史人物字段，不安排死亡事件。
- 不新增楚大公国或天师府特殊政府机制。楚仍使用现有公国改革，天师府沿用既有政府；“大公国”目前是背景中的设定尊称，不额外提高政府等级。

地理差异明确留存：州国首都仍为监利5344，文案中的兴国5016仍属鄂国；天师府仍在广信4993，设定写鹰潭。此次未修改省份所属、疆界或首都，后续地理调整应单独处理。

复现顺序：先运行 `tools/apply_chu_opening_setup.py`，再运行 `tools/build_lingnan_opening_events.py`；两者均支持 `--check`。预览由 `tools/render_chu_opening_preview.py` 导出。楚专项检查使用 `tools/validate_chu_opening.py`，另运行开局事件、周封国、开局学派、模组介绍和中文编码检查。

本批静态结果：23国共138组开局流程检查通过；91页模组介绍420条跳转通过；58国爵制与278组晋封规则检查通过；67国学派分配通过。原13张图片和五位公邑执政的字节校验和保持不变。十张实际DDS已人工检查。尚未在运行中的EU4验证新人物、长文完整显示和新附属关系，勿把静态通过记作实机验收。
