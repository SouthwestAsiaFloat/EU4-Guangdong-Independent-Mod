# 礼制护土：礼乐与省份战争分数

2026-09-10：按用户确认实现，任何国家夺取周天下省份均受影响。

范围读取省份当前 owner 的 `zhx_is_tianxia_polity`，包括天子和普通成员，
不依赖进攻者身份、宗教或宣战理由。外部国家持有的土地不享受保护。
读取全局事件目标 `zhx_tianzi` 的 `zhx_ritual_authority`；天子不存在时撤除。

额外花费百分比为 `clamp(floor((礼乐值 + 100) / 10) * 5, 0, 100)`。
礼乐 -100/-50/0/50/100 对应 +0/+25/+50/+75/+100%。
这是省份本地百分比修正，不是直接增加固定战争分数点数；与其他原生战争
分数修正的实际叠加结果尚待实机比较。0% 不挂空修正，其余二十档互斥。

## 生命周期与文件

- `common/event_modifiers/zhx_ritual_warscore_modifiers.txt` 定义二十档修正。
- `common/scripted_effects/zhx_ritual_warscore_effects.txt` 读取当前身份及天子礼乐值，
  仅在目标档位不存在时清除旧档再添加新档，保留其他省份修正。
- 现有 `zhx_refresh_ritual_order` 每次调用均刷新该机制，不受国家五档礼乐修正
  的缓存旗标限制。开局已有初始化路径最终调用此入口。
- 登记成员、正常退盟、设置天子接入公共刷新。
- `common/on_actions/zhx_ritual_warscore_on_actions.txt` 的省份易主回调仅修改该省
  的修正和旗标，不做国家或世界扫描，不分发事件；月度按国家遍历自有省份
  作为身份绕过公共接口、引擎移除省份修正等情况的修复。
- 吞并事务中的成员清理入口保持无扫描；省份回调和月度刷新负责土地效果。
- 本地化源为 `localisation_source/zhx_ritual_warscore_readable_utf8.txt`，登记在
  `tools/encode_eu4_chinese_localisation.py`，使用现有中文双字节编码流程。
- 无 GUI 文件覆盖或原生功能槽占用。

## 接口证据

| 名称 | 类型/所在块 | 作用域 | 参数及版本 | 证据 | 实机状态 |
|---|---|---|---|---|---|
| local_warscore_cost_modifier | 修正 / event_modifiers | 省份 | 1.0 = +100%；Wiki 标注 1.30 引入 | 离线 Modifier list，Province modifiers > Diplomacy；本机 1.37.5 common/event_modifiers/01_mission_modifiers.txt:10021 的 fra_unification_movement_modifier | 用户截图确认省份 +100% 数值项；其他路径见下文 |
| add_province_modifier | 效果 / scripted effect | 当前省份到当前省份 | name；duration=-1 | 本机 missions/DOM_French_Missions.txt:2484，原版向 174、173 省挂上述修正 | 本轮未测 |
| on_province_owner_change | on_action | THIS 为省份，FROM 为旧国家；owner 为新国家 | 本机目标版本 1.37.5 | 项目既有 zhx_diplomacy_on_actions.txt 的同入口作用域；此新增路径不使用 ROOT/FROM/PREV | 新增修正刷新未测 |

省份效果不依赖 ROOT：owner 只在 trigger 中读取当前国家身份，全局事件目标
只在 trigger 中读取现任天子，之后 add/remove 始终作用于当前省份。
国家包装从当前国家 every_owned_province 切入省份；全局包装从 every_country
切入各国，不依赖外层事件所属国家。

## 验证

`python3 tools/validate_zhx_ritual_warscore.py`：读取实际脚本分支，检查 810 个
升降序半点取值、边界、幂等性、退盟与天子消失清理、无关修正保留、公共入口、
本地化键与中文编码。此为静态/模型检查，不模拟 EU4 的计算或事务时序。

既有周天下外交、封邦与天子校验通过。2026-09-10 用户提供的他国省份截图
确认“礼制护土 +100%”已进入实际分数说明，显示 70.65%。前次只查看玩家自有
南昌省份的测试不足以认定防守方修正失效，已撤回“实机未通过”的总体结论。
[原始观察与用户截图](runtime_evidence/ritual_warscore_2026-09-10/README.md) 保留区分。

## 原生修正的两个方向

- `local_warscore_cost_modifier` 是本省被别人割走时的花费修正，挂在省份上。
  本机制使用的就是这项“保护自己的土地”的原生接口；玩家与 AI 都经由
  `every_country -> every_owned_province` 接入，没有 `ai` 或玩家国家过滤。
- `province_warscore_cost` 是国家夺取其他国家省份时的成本修正。原版外交理念
  `flexible_negotiation` 使用 -0.2（本机 common/ideas/00_basic_ideas.txt:548）。
  不能把它当作第二个防守方加成叠进当前设计，否则改变的是进攻方成本，且可能
  让成员夺取天下外土地也变贵。
- 本机 1.37.5 原版用例、离线 Modifier list 和可执行文件的相关接口名中，
  没有找到需要另加的“玩家自有省份战争分数”修正。现有省份修正即为所需方向。

本轮保持原有 0..100% 玩法数值，明确中文描述为“其他国家割取本省”的费用，
并在校验器中锁定仅使用省份防守方修正、全体国家和自有省份覆盖，防止错误添加
国家进攻方修正或排除玩家。

后续实机验证应固定目标省份和索取方：让另一国家查看/索取玩家土地，对比礼乐
-100 与 100；再反向比较同样场景。真实和约、入盟退盟、省份易主仍待完整验收。
