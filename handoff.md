# 省份周天下化重构：功能实机测试交接

更新：2026-09-11。用户最终要求合入并 push 到 main，再交给下一会话继续实机测试；重点跑通主要功能，不做大量边界测试。**必须使用 Computer Use 操作游戏。**

## 当前结论与分支

- 开发分支：`codex/zhou-province-integration`；用户最终指定合入个人仓库 `origin/main`，当前交付分支为 `main`，不推送 `upstream/test`。
- 合并基线提交：`dfcf9d68cdf40841803f9ae0ba7532d0886a208e`，包含本地 `c7afd9d` 与远端 test `6f68e6e` 的整合。
- 本次另提交此前工作区中的手动索还选择器、翻页修正、相关测试、规划与实机证据。
- **省份入籍／外国持有者退籍已实测；整个重构尚未完成实机验收。** 退盟、改革、解散属于未测主功能，不能称为“只剩边界”。
- 需求依据：[设计报告](docs/planning/zhou_province_test_merge_plan_2026-09-10.md)、[36 项已确认决策](grill-me-sessions/省份周天下化重构.grill.md)、[整合说明](docs/gameplay/zhou_province_integration_2026-09-10.md)。不要重新采访已确定的规则。

## 已取得的实机证据

本轮证据目录：`docs/gameplay/runtime_evidence/zhou_integration_2026-09-11/core-runtime/`。

游戏版本参考本机 launcher 配置为 EU4 1.37.5.0 Inca；本轮未读取主菜单 checksum，不能把配置版本当成本轮 checksum 实证。已重新启动游戏后载入 `zppafter.eu4`。安装的 mod 路径解析为本仓库 `guangdong_independent_practice`，见 `preflight.json`。

| 场景 | 实際生产交互和持久化结果 | 结论 |
| --- | --- | --- |
| 首次省份入籍 | CZH 的开封 688、发展度 19；fixture 仅清除省籍及奖励标记。真实省份窗口点击“周＋”，登记与已结算标记写入，天命 85.100 → 87.000 | 通过 |
| 外国持有者退籍 | fixture 将 688 交 KOR，切 KOR；真实省份按钮打开确认事件并确认。登记清除、礼制 active 标记和 warscore modifier 均无、奖励 ledger 保留，天命 87.000 → 85.100 | 通过 |
| 礼制保护的首次生成 | 入籍后存档存在 `zhx_ritual_warscore_045`，但 fixture 没清旧保护，基线已存在该 modifier | **不足以证明从无到有的刷新**，下一轮补一例；退籍后的清除已证明 |
| 再入籍不重复奖励 | 已临时将 688 返还 CZH，尚未再点入籍或保存该状态 | 未完成 |

准确存档提取及 SHA256 见 `core-save-audit.json`。天命必须从顶层 `celestial_empire` 块提取，不能用全文件第一个 `imperial_influence`。

注意证据命名陷阱：`zcoreadmit.eu4` 与 `zcorebefore.eu4` 相同，当时误点了洛阳状态图标；`01-admitted.png` 也只是洛阳状态，不是开封入籍证据。真正成功的是 `zcoreadmitted.eu4` 和 `02-kaifeng-admitted.png`。`03-province-removed.png` 带一个原生外交通知，最终清理以存档为准。

上轮索还实机证据在 `docs/gameplay/runtime_evidence/zhou_picker_2026-09-10/README.md`，本轮没有重新执行：正式外交入口、10 省 3 页往返、确认返回、取消后保存／载入、选遵化 5213 并由 AI 接受，仅该省实际归还 YAN；取消没有年度冷却，发送后有持有国冷却。玩家答复分支未测。实现说明见 [索还选择器](docs/gameplay/zhou_unlawful_province_picker.md)。

## 下一轮建议顺序（每项一条正常流程即可）

1. **国家退盟（优先）**：载入清楚的隔离基线，选择独立、和平成员。通过天朝窗口“退出周天下”并确认，核对成员标记、爵位／改革、直属省份登记和礼制保护清除，20 年再入盟禁令生效。不要用 effect 直接完成退盟冒充 UI 验证。若本身有属国，顺带核对属国土地未被清除，无需特造复杂宗属结构。
2. **改革执行（优先）**：fixture 只准备合法执行者、支持票和至少 50 天命，真实点击改革；确认改革状态、天命消耗至 0、稳定度不扣。若方便，再真实撤销一次，查普通成员 -10／原执行者 -50 关系修正；未跑到的单独标未测。
3. **省份再入籍和保护刷新**：从 `zcoreremoved.eu4` 开始，把 688 返还 CZH 并确保和平、自控、完整核心，保留已结算 ledger，真实点入籍。确认省籍及保护从无到有、天命不再次奖励。这一个正常流程即可补齐两项证据。
4. **求援拒绝**：建立一场符合条件的内部受侵战局，成员从正式外交入口向天子求援，实际选择拒绝，核对受援国对天子 -50。没有提出请求不应自行惩罚。无需反复叠到 -200。
5. **天命解耦**：另开测试分支存档，准备没有原生 EOC 持有者、但周天子／成员政治身份仍合法的场景；正常入籍／退籍应能完成，首次 ledger 仍写入，不补发。准备方法必须先读生产规则，勿误把“摧毁周天下”当成移除 EOC。
6. **解散（最后、破坏性测试）**：独立隔离存档准备天子及仍存活七大诸侯首都控制条件，真实点击解散确认。核对周天下全局状态、成员／爵位、天子改革、王畿税、禁军训练、待处理状态清理，而原生 EOC 与既有实际部队保留。

如用户希望尽快收尾，先跑完 1—3，再报告可验收范围，不需要长期 AI 跑年或全边界矩阵。

## 游戏与存档接续

- 游戏根目录：`/Users/xinanyapiao/Library/Application Support/Steam/steamapps/common/Europa Universalis IV`
- 用户目录：`/Users/xinanyapiao/Documents/Paradox Interactive/Europa Universalis IV`
- 存档都在上述用户目录的 `save games/`，未把约 45 MB 的存档放进 Git。
- `zcorebefore.eu4`：CZH，1445.2.14，688 未登记／未奖励；基线有 fixture 遗留旧保护，不适合证明首次保护生成。
- `zcoreadmitted.eu4`：成功入籍后，CZH，1445.2.14。
- `zcoreremoved.eu4`：成功退籍后，KOR，1445.2.14，688 在 KOR、ledger 保留、无省籍无礼制保护；建议下一轮从这个明确存档分支。
- `zppbaseline.eu4`／`zppafter.eu4`：上轮索还测试存档，含人工设置的 KRC 十省场景，**不是新开局初始化验收档**。
- 自动存档及原 `zppafter.eu4` 备份：`save games/zhou-core-runtime-backup-20260911/`。不要未经检查恢复覆盖用户后来进度。
- 最后观察到游戏暂停于 1445.2.14，操作者 CZH；688 已通过 fixture 从 KOR 返还 CZH，未再次入籍、未保存。屏幕为中原地图及“匹配”省份搜索窗。后续 CUA 返回“Computer Use is not active”，最后一次关闭搜索并点省份的操作**没有执行**。新会话必须重新获取 app 状态，不沿用坐标／假设用户没操作。
- 国家退盟尚未尝试：之前切 QIN、打开的是“诸夏王会”，未找到带退出按钮的原生天朝窗口。曾向用户询问入口，未收到答复。右下圆形按钮在当时只打开诸夏王会；不要把未找到入口报告成退盟脚本失败。

## Computer Use 操作经验

已使用 `eu4-ui-methodology`、`eu4-script-contracts` 技能及 macOS runtime testing 参考；下一会话按需要读取。所有 UI 用 `mcp__cua_repl`，禁用 osascript／CGEvent 等替代输入。

```js
var eu = await cua.getApp('/Users/xinanyapiao/Library/Application Support/Steam/steamapps/common/Europa Universalis IV/eu4.app');
await eu.getAXStateAndScreenshot();
```

EU4 AX 仅提供窗口与菜单，实际按钮通过新截图定位。动作后取 AX，再截图；同一次调用立即截图偶尔显示旧画面，应先重新观察，不要连续盲点。工具提示用户改变 app 或控制失效时，重新读状态再操作。

控制台 `grave` 打开后可能留下一个反引号，先观察并清掉再输入；`typeText` 本轮能输入英文，但第一次命令常因这个字符失败，必须看到 executed／Now Playing。相对 `run zcore*.txt` 可准备前提；`savegame ...` 控制台命令未成功，**用 Escape → 保存游戏**。存档名的 Ctrl+A 无效，点击名字后多次 BackSpace 清空再输入，保存前确认名字。省份搜索快捷键 `f`，有“前往首都”按钮。

本轮 fixture 源码已保存在证据目录；只做准备，不作为生产交互证据。安装根目录下本轮三个临时 fixture 在交接时已清理；下一轮若需使用，检查内容、复制到安装根目录后仅在隔离存档执行，并在结束时删除自己创建的文件。

## 检查与交付要求

本次 push 前复跑：领土／选省 31 项、按钮 33 项、领土静态校验、外交分类与中文编码校验全部通过。日志与命令环境见 `core-runtime/push-checks.json`。系统 Python 缺 Pillow，改用已有 bundled Python 后通过：

`/Users/xinanyapiao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`

父目录 `static-results.json` 是此前 15 项检查的记录，不要当成下一轮重新执行过。启动 error.log 有既有原版任务／区域等噪音，不可声称全日志无错；下一轮按本轮修改命名空间检查。

每项保留 UI 截图、前后存档路径／hash／关键状态摘要；读存档须进入顶层 countries／provinces，处理引号与花括号，压缩档先解 gamestate。代码若修改必须重新加载游戏后复测，明确已加载版本。最终写实测覆盖表，保留未测项，游戏停在暂停状态，并告知用户具体存档和日期。
