# 潮州乡贤议会政府样板

更新日期：2026-09-06。当前是机制与界面集成样板；静态契约不能替代 EU4 的继任、读档和界面实测。下方矩阵明确区分已检查内容和待验证内容。

## 初版规则

本文记录潮州 `CZC`；客家政体另见对应文档。新一级改革为 `gdd_czc_council_reform`，名称为“潮州乡贤议会”。共和国等级、1444 年统治者郑万民、文化、宗教、国家理念与领土沿用岭南正典。

| 项目 | 士绅占优 | 统治者占优 |
|---|---|---|
| 权力条位置 | 左，青色 | 右，朱色 |
| 统治者任期 | 终身 | 终身 |
| 继任设计 | 不锁定家族，由原生继任系统产生执政者 | 原版候选人物存储与 `set_ruler` 保持同族 |
| 国家收益 | 海军上限 +10%，全球贸易竞争力 +5% | 陆军上限 +25%，稳定成本 −10% |
| 共和传统 | 按共和国基础和其他国家修正恢复 | 每年额外 −2；计入共和国基础 +1 后通常净 −1 |

政权归属直接读取原生 `states_general_mechanic`，不另建镜像变量。议政行动每次消耗 **50 行政点**，向任一方向推动原生值 `0.10`，两项行动共享 365 天冷却。点数不足时不可操作；GUI、事件选项与 AI 都通过同一带资格检查的效果扣款一次。动作只移动权力，不替换在任执政者。界面刻度与两端颜色必须同方向，不能把原生的士绅方向画反。

改革在根层固定启用原版 `has_parliament = yes`，不随两派继任条件切换。省份议席、议案及辩论使用原版议会系统；无需额外的自定义议席变量。

共和传统由原生系统在年初结算，9月5日右侧实测为 50→49；11 月推进到 12 月时没有月扣。脚本的月度回调负责检查低传统称王条件，不负责重复扣除年度传统。

1444 年历史开局共和传统为 50，权力值居中。共和传统**严格低于 20**时，在月度检查或本系统操作后的检查中触发称王；恰好 20 不触发。称王在事件 `immediate` 中完成，不等待玩家点击通知选项；现任者留任，政体变为二级君主制并采用 `autocracy_reform`。没有恢复农会、土地改革或额外资源条。

`cannot_become_dictatorship = yes` 屏蔽普通共和国在传统低于 40 时随机发生的 `republics.3` 独裁改革，防止该原生事件先替换潮州一级改革、截断专属称王路径。

## 界面与素材

获准的美术方向为深木框、旧金饰边、左青右朱；士绅端表现卷册／笏板，统治者端表现执政印信。正式政府界面使用 `countrygovernmentview` 这个原生受支持的 scripted GUI 根节点。各控件单独用 `gdd_czc_is_council_trigger` 限制为仍采用该共和国改革的 `CZC`；称王或转为其他国家标签后停止显示。

界面文件采用汉化主模组 `2976470733/interface/countrygovernmentview.gui` 的有效上游。保留原生控件名称及作用；静态验证器剔除新增的 `gdd_czc_` 控件后比较整棵上游界面树，以防皮肤影响其他国家。该完整文件覆盖仍需在汉化依赖更新后重新核对。

| 资源层 | 文件 |
|---|---|
| 原生政府界面覆盖 | `guangdong_independent_practice/interface/countrygovernmentview.gui` |
| 控件绑定、显示与按钮效果 | `guangdong_independent_practice/common/custom_gui/gdd_czc_government_gui.txt` |
| Sprite 定义 | `guangdong_independent_practice/interface/gdd_czc_government.gfx` |
| 纹理 | `guangdong_independent_practice/gfx/interface/gdd_czc_government/` |
| 已获准的方向预览 | `planning/chaozhou_government_art/chaozhou_government_art_v01.png` |
| 正式条框居中预览 | `planning/chaozhou_government_art/chaozhou_government_v02_280x50_balanced.png` |
| 正式条框四倍预览 | `planning/chaozhou_government_art/chaozhou_government_v02_preview_4x.png` |

正式纹理目前采用 ARGB32 DDS：条框为 280×50；士绅和统治者徽记各为 64×32 的两帧图集（每帧 32×32）；游标轨道为 5880×50 的 21 帧图集（每帧 280×50）；政府改革图标为 64×64。游标直接根据原生权力值选择帧，左端为第 1 帧、居中为第 11 帧、右端为第 21 帧。独立的 `pointer.dds` 是制作图集的素材，不作为界面必须引用的 Sprite。

## 脚本及历史入口

| 职责 | 文件／入口 |
|---|---|
| 改革、两派修正、任期与同族属性 | `common/government_reforms/zzz_gdd_czc_government_reforms.txt` |
| 国家资格、旧档迁入、冷却、称王阈值 | `common/scripted_triggers/gdd_czc_government_triggers.txt` |
| 初始化、议政操作、转换 | `common/scripted_effects/gdd_czc_government_effects.txt` |
| 开局、月度与继任回调 | `common/on_actions/gdd_czc_government_on_actions.txt` |
| 自动检查、议政通知和调试事件 | `events/gdd_czc_government_events.txt` |
| 一级改革注册 | `common/governments/00_governments.txt` 的共和国第一层 |
| 历史权威数据 | `planning/lingnan_nations/lingnan_nations_manifest.json` 的 `CZC.reform` |
| 对应历史文件 | `history/countries/CZC - Chaochow.txt` |
| 机制可读中文 | `localisation_source/019_gdd_czc_government_readable_utf8.txt` |
| 界面可读中文 | `localisation_source/020_gdd_czc_government_ui_readable_utf8.txt` |

除规划清单外，表中的路径相对于 `guangdong_independent_practice/`。`tools/apply_lingnan_nations.py` 会用清单**全量重写八国历史**，因此一级改革必须同时保存在清单与 `CZC` 历史中；不能只手改历史。

原有旧档仅在 `CZC` 仍为共和国、仍采用 `oligarchy_reform`、未初始化且未称王时迁入。迁入只替换这项一级改革，保留当前人物；1444.11.12 及之后的档案保留共和传统，不强制恢复到 50。已转换为其他政体的档案不强制迁回共和国。初始化标志防止每次读档重复重设权力。

## 编码与静态检查

中文依赖为 Chinese Language Mod for 1.37（`2976470733`）和 Chinese Language Supplementary Mod for 1.37（`1999055990`）。可读源使用 UTF-8；游戏本地化文件经仓库编码器转换为补丁转义字节、CP1252 映射和 UTF-8 BOM。不能把可读中文直接复制到输出 YAML。

只更新本轮本地化时可定点调用编码器，避免全局生成器写入其他进行中的内容：

```bash
python3 -c 'import sys; sys.path.insert(0, "tools"); import encode_eu4_chinese_localisation as e; names = ("019_gdd_czc_government_readable_utf8.txt", "020_gdd_czc_government_ui_readable_utf8.txt"); [e.encode_file(e.MOD / "localisation_source" / name, e.MOD / "localisation" / e.FILES[name]) for name in names]'
python3 tools/validate_czc_government.py
python3 tools/apply_lingnan_nations.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
```

验证器检查国家范围、终身任期与同族条件、严格阈值、冷却、称王回调顺序、旧档迁入、历史／清单／改革注册、跨文件引用、中文往返编码、控件绑定、原生界面保留，以及 DDS 头、尺寸、帧数和像素数据长度。`--mechanics-only` 用于美术接入过程中只检查脚本，不代表整套样板通过。

2026-09-05 完整静态检查已通过：27 个编码本地化键、10 个脚本控件、5 个已注册 DDS 纹理；21 帧阈值覆盖、显示方向、冷却提示互斥，以及原生政府界面和联省改革保留检查均通过。`apply_lingnan_nations.py --check` 也通过（八国、六组理念、两条附属关系），全量本地化 `--check` 全部通过。初始化日期用原生 `is_date`，与安装版 `common/achievements.txt` 所用语法一致；旧写法 `date` 已移除。隐藏事件保留完整标题、描述、图片与选项结构，避免该版本加载时报告缺少事件内容。

## 本次追加：原生议会与行政点成本

用户追加要求已实现：潮州乡贤议会接入原版省份议席、议案与辩论；支持士绅、支持统治者各消耗 50 行政点，保留共享 365 天冷却。低于 50 行政点时，两项行动均不可用；状态提示改为“暂不可议政 · 查看条件”，避免将点数不足误写成仍在冷却。

本次静态检查已通过：验证器核对原生议会的固定属性、共同资格检查中的 `adm_power = 50`、双方效果各仅扣款一次；完整界面契约、中文编码、八国历史清单和 `git diff --check` 均通过。游戏已加载并观察到新的 50 行政点提示，但用户截图确认首次条件式接入后仍未出现省份授席按钮。日志显示 Common Sense、Domination 已启用，启动时间晚于修改时间，因此不能直接归因于 DLC 缺失或未重启。现将议会改为改革根层固定属性，避免依赖与同族继任并列的条件块；这是一项待实机验证的修正，尚未证明多个条件块就是根因。当前待验证：重启后议会入口、省份授席、旧档刷新、两派切换后议会保持，以及 50／49 行政点边界。用户正在游玩并明确要求停止操作游戏，因此已停止 Computer Use；下方旧版验收记录不作为本次新增议会和扣款的运行证据。

## 实机验收矩阵

本机安装：`~/Library/Application Support/Steam/steamapps/common/Europa Universalis IV`。部署目录 `~/Documents/Paradox Interactive/Europa Universalis IV/mod/guangdong_independent_practice` 是指向本仓库模组目录的符号链接；编辑文件后仍须完全重启 EU4 才能确认新脚本已载入。

| 场景 | 需要观察的结果 | 证据状态 |
|---|---|---|
| 全新 1444 潮州 | 专属一级改革、历史人物、传统 50；首次月跳不重复初始化 | 已通过：原始基线为新开局专属改革、郑万民 `5/6/6`、传统 50、初始化旗标存在；最终版本重载同一基线后仍为郑万民 39 岁、游标居中、双方可议政；右侧档读档／跨月后保持权力与旗标 |
| 政府面板 | 木框、左右徽记与权力条清晰；标签、悬浮提示及按钮无遮挡 | 已通过：最终布局整洁、无原生漏条；按钮提示仅中文移动 10 与共享一年冷却，无内部标识 |
| 左右按钮及冷却 | 每次移动 0.10；同年另一按钮也禁用；365 天后恢复 | 已通过：右侧 0→10；左侧 100→90，双方禁用且再点右侧无效；430 天后自然恢复可用，未单独卡第 365 天边界 |
| 左右任期 | 各自推进超过四年，不出现原版定期选举 | 士绅端 1444→1452 同一人物持续执政、无选举，已通过；右侧长期任期未单独推进四年 |
| 士绅侧死亡 | 正常产生继任者；不被强制锁定为原家族 | 已通过：谢允恭→叶德昌，id 12763→13651 |
| 统治者侧死亡 | 新执政者为原家族；不出现选举事件改写家族 | 一次实测通过：谢启恩→谢允恭，无选举提示；存档 id 改变且姓名中的姓相同 |
| 传统变化 | 左侧恢复；右侧额外 −2／年，与界面列出的其他修正合计一致 | 已通过：士绅端 1444→1452 累计 50→58；统治者端 1452→1454 两次年初结算 50→49→48 |
| 传统 20 / 19 | 20 保持共和；19 立即执行检查时称王，现任者不变，皮肤退出 | 已通过：20 仍共和；19 转 autocracy 君主制、二级，同一 id13651 的叶德昌留任；中文事件正常且条框／按钮退出 |
| 新旧存档重载 | 已初始化值与冷却持续；旧寡头档仅迁入一次；后期旧档传统不重设 | 新样板读档保持权力与初始化旗标，冷却旗标的存档日期也已核验；旧寡头档自动迁入未实机测试 |
| 非潮州与原生联省 | `GDD`／`HAK` 不显示皮肤；荷兰原生联省界面和机制不变 | `HAK` 切换实测无潮州条框／按钮，返回 `CZC` 恢复，已通过；原生荷兰仅做了静态保留检查 |
| 分辨率／缩放 | 最低支持分辨率、1920×1080、非 100% UI 缩放下均不越界 | 待实机 |
| 日志 | 查看 `error.log`／`game.log`／`setup.log`，无新增 GUI、事件、改革或本地化错误 | 最终重载的 error.log 未见 gdd_czc 引用错误，tag/is_statists/statists_vs_orangists 的 scope 错误均为 0；既有其他错误仍存在 |

诊断事件仅供可丢弃的测试档使用，不在普通回调内调度：

```text
event gdd_czc_government.900 CZC   # 安装／重置样板，传统 50
event gdd_czc_government.901 CZC   # 强制士绅端，清冷却
event gdd_czc_government.902 CZC   # 强制统治者端，清冷却
event gdd_czc_government.904 CZC   # 杀死当前执政者，检验引擎继任
event gdd_czc_government.905 CZC   # 传统设为 20 并执行阈值检查
event gdd_czc_government.903 CZC   # 传统设为 19 并执行阈值检查
```

`states_general_mechanic` 的原生选举事件按机制本身判定资格；没有 `has_dutch_election` 不足以单独证明不会触发选举。本版保留 `has_term_election = no`、`election_on_death = no`、`duration = 0`，右端同族由原版亲族命名与人物候选机制实现。9月5日曾使用的 `conditional maintain_dynasty` 已经撤回；当时解决的条件作用域问题不代表继任契约通过。

以下为9月5日历史测试证据，不能替代9月6日修复版本的复测；最终结果见文末。

## 轻量存档证据

结果保存于 `planning/chaozhou_government_art/runtime_validation_20260905.json`，包含原始测试档的路径、大小、SHA-256、国家块摘要、人物身份、权力、共和传统，以及最终代码和日志快照。大存档保留在游戏存档目录，没有复制进仓库。

提取先进入顶层 `countries`，再定位恰好一个制表符缩进的 `CZC={` 并按引号／括号配平提取。仅在整份存档中寻找一制表符 `CZC` 仍会匹配后方顾问表；更深的同名键还可能来自贸易记录，不能误当国家。当前人物以国家的 `monarch.id` 回查本国 `history` 中相同 id 的人物记录。

| 存档日期 | 当前人物 id | 存档姓名 | 原生权力 `statists_vs_monarchists` | 共和传统 |
|---|---|---|---|---|
| 1444.11.11 | 12679 | 启恩 谢 | 1.000 | 50.000 |
| 1444.12.4 | 12763 | 允恭 谢 | 1.000 | 50.000 |
| 1452.2.1 | 12763 | 允恭 谢 | −1.000 | 58.000 |
| 1452.2.1，左侧死亡及阈值 20 | 13651 | 德昌 叶 | −1.000 | 20.000，共和国 |
| 1452.2.1，阈值 19 称王 | 13651 | 德昌 叶 | −1.000，停用的旧值 | 19.000，君主制 |
| 1453.1.1，另行重置为右侧测试 | 13651 | 德昌 叶 | 1.000 | 49.000 |
| 1454.1.1，右侧第二年 | 13651 | 德昌 叶 | 0.900 | 48.000 |

谢启恩、谢允恭两位随机共和执政者在存档中都没有独立 `dynasty` 字段；“谢氏延续”的证据是实际界面显示与 `name` 字段末尾的姓相同。`original_dynasty` 仍为历史开局的“郑”，不能将它当作当前执政家族。1452 年士绅端存档继续保留 id 12763，`last_election` 仍为 1444.11.11，并已累积恢复 8 点共和传统。叶德昌在称王前也没有独立王朝字段，称王后引擎为同一个 id13651 写入 `dynasty = 叶`，能力仍为 `4/3/1`。

1453、1454 年度证据分别保存在本次会话目录 `/tmp/czc_government_runtime_20260905/old_autosave.eu4` 和 `autosave.eu4`，从游戏自动存档复制后保留，避免恢复正常战役后被游戏自动覆盖。测试在 1452.2.1 另行运行 `.900` 重置共和传统为 50、`.902` 强制右端，再推进跨年；因此不能把表中这条当作称王后自然又恢复了共和国。1453.1.11 使用左侧按钮把权力从 1.000 移至 0.900；1454.1.1 的存档同时保留该值及当日设置的冷却旗标日期，1454.3.16 的界面已恢复可议政。JSON 记录各份副本的 SHA-256。

测试结束已载入游戏存档目录下的 `CZC_1444_ready.eu4`，它与原始基线副本字节哈希一致。当前游戏停在 1444.11.11，郑万民 39 岁、共和传统 50、权力条居中，两项议政可用；测试中的死亡、称王与年代推进没有成为用户继续游玩的起点。这份基线从一开始就使用新改革，不能把它计为旧寡头迁移测试。


## 2026-09-06 继任修复与复测

原 `conditional maintain_dynasty` 实测会在右端换族，现改为原版 `Elections.txt` 的 `name = "lastname"` 亲族命名配合 `define_exiled_ruler` / `set_ruler` 候选存储。共和国人物的姓常写在全名中，没有独立 dynasty 字段，不能用 `dynasty = ROOT` 代替亲族命名。

初始化与每次继任结束时，生成一名20—35岁的当前家族候选；右端死亡由其接任，左端保留原生新执政并更新候选。权力条切换不换人，人物任期仍为终身。国家事务标记防回调重入，人物标记防重复处理；称王时清除候选及准备标记。候选使用原生人物存储，没有另建虚构国家或镜像权力变量。

最终校验码0355的新开局通过：郑万民→右端郑继芳→左端叶维恭；在叶氏执政下存读档，再于右端死亡，实际接任者为已保存的叶文芳；跨月后 id12720 和3/6/5能力保持稳定。右端仍有一条临时候选的重复原生通知，姓名标题与能力说明可能不一致，尚未消除；宫廷与存档中的最终执政正确。

详细步骤、截图与存档摘要见 [修复复测记录](runtime_evidence/fix_2026-09-06/SESSION.md)。
