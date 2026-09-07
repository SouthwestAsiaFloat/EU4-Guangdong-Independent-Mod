# 周天下整合夜测：2026-09-06 至 09-07

硬截止：Asia/Shanghai 2026-09-07 08:00（UTC00:00）。实际开始约23:11。

基线：main ce4e9f882867e2560c407354e91931413f23aeb8；在此前已推送f806628之后另有地图/山脉发现提交，保留并测试当前最新本地main。

尚未开始新战局。本轮Computer Use首次请求时游戏未就绪；随后看到启动画面。自动存档已保全，见preserved_autosaves.json。不把启动等待当成已完成运行覆盖。

计划：开局诸侯/继承人/公邑 → 潮州/客家/商盟补边界 → 长期AI与25年换届/公议 → 截止保存暂停与报告。

## 23:38 opening heir failure and controlled experiment
Fresh 89fe UI: GUI/NUN/TZZ/LIL/DAI all show no legal heir. Saved original before ticks. Control: DAI unchanged. GUI adds death_date, NUN monarch_name, TZZ both, LIL history date one day earlier. These are temporary experimental edits, not a final fix. Backup paths in heir_history_experiment.json.
Input method interference resolved using sky ctrl+space, then normal per-key console input works.

## 00:10 controlled result / fix on disk
Experiment checksum b3f6: GUI (death_date only) and TZZ (both fields) have current heirs in UI and saved refs. NUN (monarch_name only), LIL (date earlier), DAI (unchanged) still have no current heir. Formal generator change adds only historical heir death_date = 1821.1.1 to six named heirs; all experimental edits replaced by generated canonical history. Generator/apply/check pass, 7 files / 11 insertions. Formal fix requires full restart and new game, not yet retested.

## 00:42 formal fix and CZC costs
Loaded b27a fresh opening: six named heirs have correct current refs and identities; saved opening. After actual advancement to 1446.6.8 all six retain same heir ids; DAI current ruler changes while underage heir persists, remaining five same ruler. CZC cost UI: 49 disabled both; 50 enabled and right click =>0; refill100 still cooldown blocks both. On1446.6.8 expired, leftclick252=>202 and new cooldown date saved. Exact day364/365 fixture created separately, only current cooldown flag date changed. Not yet loaded.

Day364 fixture loaded successfully; actual button disabled at202ADM. Natural low-speed advancement passed boundary but did not capture exact next day; console does NOT pause game in this build. Paused1446.7.2. Creating separate identical day365-point fixture by changing only cooldown date; do not claim exact natural364→365 capture.

## 01:02 AI checkpoint
Observer from1446.6.8 to1450.1.2, actual autosave1450.1.1 preserved as codex_night0906_ai_1450.eu4; audit includes SHA. CZH term_year5, years_remaining20. HYM + all five initial cities still one native league; Yang3 provinces and five OPMs with intended reforms. CZC and HAK reforms retained. Scoped error-log scan:0 matching relevant namespaces among2798 total lines (not a globally clean log). No crash observed. Exact day365 point fixture UI202=>152 and new cooldown; pair day364/day365 passed as loaded-state boundary tests, not claimed exact natural one-day capture.

## 01:19–01:22 AI1460 checkpoint
Actual autosave1460.1.1 preserved, observer screen1460.3.28. CZH term15/remaining10. HAK now communal republic after natural AI transition, farmers60/army40/burghers0; provinces11→5 due wars, RT53.560, election1459.3.21. Real government/reform UI confirms selected gdd_hak_communal_republic_reform and active three-party presentation. CZC provinces6, RT68.710, native statists_vs_monarchists0.400, council retained. Yang and five OPMs retain same native league. Higher-tier native reforms changed election rules for some OPMs; do not interpret every later non-four-year last_election as a broken first-tier reform.

## 01:50–02:00 首届换届与力量投射缺陷

实际时间推进到1470，1469年自动年度结算完成：七席 YUE/CHC/WUU/YAN/QIN/ZHA/WEI → CHC/YAN/QIN/GDD/DQU/CDE/JIZ；方伯燕→楚；所有现存成员本届盟功归零；周期0/25；桂国的测试用本届已请封标记清除。并非控制台直接调用结算。1470自动档保留。

发现力量投射清理失败：旧七席落选后仍10、燕仍20、秦连任由10叠到20。原脚本负数 add_power_projection 未撤销来源。四组原生语法实测：key字段不生效；type字段有/无amount均正确移除。安本纳尔使用type；本地1.35 patchnotes写key与实际1.37.5不符，以实测为准。正式效果改为 remove_power_projection={type=zhx_merit_dignity_power_projection}，仅清专属身份来源。修复后的真实换届回归待完成。详见rollover_comparison、rollover_projection、pp_syntax_result及截图125–131。

## 02:05 换届力量投射修复回归通过

完整重启校验码80f9，加载1469.1.1同一测试起点，自然年度结算。实际1470自动档：楚20，燕/秦/南海/大瞿/常/箕子朝鲜各10；越/吴/赵/魏旧身份来源消失。七席和方伯正确、本届盟功均0、周期0/25、桂国已请封标记清除。对照证据ai_1470_ppfixed_audit及rollover_projection_fixed.json。暂停指令有一次未生效，随后Space实测暂停于1471.6.20；1470结果取自old_autosave，不是同日期的older_autosave。

## 02:08 其余预设继承人缺失同源修复

1444已保留新档补查CZH/JIZ/HLD/YAN/KOR/SNG，六国均无当前heir引用；各自历史确有预设继承人且缺death_date。与前述四组受控实验结论一致，分别补同样历史选择结束日期1821.1.1，保留原有编码、换行、人名及属性；B60源生成脚本三处同步。只调用B60只读validate通过，未重跑地图批次。完整重启校验码4a36，待新档UI与当前人物引用复核。

## 02:14 十二国开局继承人实机复核通过

4a36全新1444.11.11档，六处新增修复逐国宫廷截图156/158–162显示预设继承人；保存后的当前heir引用复核12/12存在且人名、家族、生日、能力与预设一致。纯新档高丽1444_11_11_night0906_allheirs.eu4已保存，未修改点数或政治值；其余政府与初始商盟也在同一审计JSON。后续继续日/月推进验证。

## 02:27 潮州右—左—读档—右继任实机回归

4a36全新1444开局，实际政府按钮右移112→62行政、权力+.10；控制台kill仅触发死亡：郑万民→绍昌郑（6/3/4，id12678），跨月至1444.12.26不变。独立fixture只设权力左端，kill→伯道詹（1/4/5，id12865）。保存并真实读档，人物仍不变；fixture只切右端，kill→承恭詹（4/3/1），推进至1445.2.1仍在位。没有用直接任命人物的测试效果代替正式回调。左右endpoint由测试fixture设定，非自然政治演化；第一次右移是真实政府按钮。

右端均两条原生通知，第二条保留临时人物能力/说明但标题指向最终人物，已知显示瑕疵仍在。左端仅正常单条。宫廷与存档实际人物为准。十二国预设继承人在1444.12.26引用也均与开局一致。证据czc_right1/left/right2_audit和截图166–197。

## 03:18 CST — 侯升公正反分支与精确截止日

- 4a36：南海20城、200发展度、200本届盟功，实际外交请求获AI天子受理，1444.12.1开始365日公议。初始实际AI票为2赞同/7反对/58弃权。
- 初始档自然推进至1445.12.4：仍侯爵/rank1，pending/from标志与submitted_merit归零，used_this_term保留，公议界面回到天下无事。负面结果事件未截图，不把此条当成事件文本通过。
- 读回初始档，实际切换安南、闽、潮州通过公议按钮改为赞同，得到5/4/58；跨月保持。没有直接调用晋爵或结算效果。
- 自然推进并逐日暂停：1445.11.30仍在投票；1445.12.1出现新爵获天下承认。前后存档对比：侯爵/rank1→公爵/rank2，君主3169与继承人3170完全保留，天子rank3，pending清除、snapshot200→0、used_this_term保留。详见hou_promotion_deadline_comparison.json及277–284截图。
- 否决分支另发现南海自然继承人死亡后，同日先创建承祚又死亡并被原版文礼替代。1445.4.7历史有两个连续heir块；gdd_heir.2在on_heir_death同步define_heir，疑似原版后续处理覆盖，尚未下结论或修改。正面分支继垣仍在，因此未影响晋爵保人验证。接下来单独复现该回调。

## 03:59 CST — 南海指定继承人生命周期缺陷与修复

- 4a36 自然死亡分支中，继垣1445.4.7去世后同日先创建承祚、随即死亡并被原版文礼替代。另用真实console kill_heir GDD，在暂停1445.12.1重现：承祚创建通知后立即死亡，宫廷无继承人，gdd_named_heir_bug_audit.json当前引用为空。
- 第一次9ebd修复仅把死亡/废储hook延后1天：这两路实际跨月通过，但正常国君死亡时承祚仍被原版维新覆盖。证据333截图、gdd_succession_bug_audit.json。该临时on_actions改动已撤销。
- 最终91c1修复：gdd_heir.2仍同步记录资格与一次性created/pending标记，在原有gdd_startup.6清掉先君标记前安排gdd_heir.3 days=1；新隐藏事件次日清pending并安装原有设定的承祚。没有变更人物、能力范围或增加旧存档迁移。
- 正常继位：实际kill GDD后保存pending档，再原版UI读回；存档确有days=1延迟事件。次日承祚生效，1446.1.15仍是同一13170，5/2/5，国君为原继垣3170。
- 死亡：最终版kill_heir GDD后次日承祚，1446.1.15仍为13168，4/3/4，原国君3169。
- 废储：最终版实际宫廷按钮扣50威望，次日承祚，1446.1.14仍为13168，4/4/4，原国君3169。
- 三路created均保留，pending均清除；详见gdd_heir_final_three_path_results.json，截图350/352/362/371。
- 03:26起Computer Use偶发noWindowsAvailable：截图和键盘仍可用，无新游戏崩溃报告。依照已有macos-runtime-testing.md，精确识别并重启SkyComputerUseService辅助进程，未终止游戏或其他进程，点击恢复。后续把每次加载结束的画面单独读取后再操作，未再连续出现。

### 04:21 客家称王三点边界与特权持久性（91c1）

通过实际阶层菜单授予自耕田保障、乡社推举权、乡勇约法，保存1444.11.15基准。原版派系开局缓存需要运行后刷新，11.15显示军府掌权；不修改此引擎刷新行为。受控console fixture只设置RT/原版派系影响力，不调用称王或其检查效果。军府掌权RT20实点支持军府：MIL98→88，仍共和；乡社掌权RT19实点支持乡社：ADM98→88，仍共和；军府掌权RT19实点支持军府：MIL88→78，实际军府称王事件，转autocracy monarchy/rank2。四档核对同一君主id3710，三项特权及1454.11.15撤销期、农民60.040%土地都保留，称王后faction数组为空。实际UI读回称王档，自然推进1444.12.26，仍同一君主与三特权；贵族阶层按原版君主制自然激活。处理原版低王室领地事件选择自行解决。证据393/398/402/405/411/412，hak_crown_boundary_results.json与hak_crown_month_audit.json。下一步独立还政于民分支。

### 04:32 乡社共和还政与自然四年选举（91c1）

独立读回乡社掌权的1444.11.18负对照，仅原版RT设置59时实点还政按钮禁用；设置60时实点成功，保留三派、君主3710及三项农民特权，last_election仍1444.11.11。自然推进至1448.11.12截图捕获原版选举（跨越11.11触发日），选择行政候选人陈守道4/1/1。下一届日期按实际选择日更新1452.11.12。自然跨月至12.16，同人且正常获得学者性格，三特权仍在。无直接事件/选举调用。证据418–421、434–437及hak_civil/elected_audit.json。处理原版徇私事件选择保留官员；此正常事件造成DIP等变化，不归为政府机制成本。下一步扬国/公邑独立开局。

### 04:35–05:03 公邑动态国家与审批竞争条件

91c1 实际外交界面显示扬国与常、九、汉、芜、舟的初始贸易联盟。原版同一贸易节点只能释放有限贸易城市：开局高邮因芜/舟已在同节点同盟而按钮禁用；实际让芜、舟退出同盟后，原版省份按钮成功释放高邮 T00，立即公邑改革，随后自然原版初次选举。不是绕过节点限制的脚本释放。原版新城初次选举后君主id12755、last_election1444.12.1。

原生省份转移fixture仅把泰州4977给T00，所有权回调立即剥夺公邑，保留人物和选举日期；返还后恢复一省仍普通共和国。实际天子对申请者好感99禁用请授，100启用。实际提交申请并收到天子审批事件。

发现审批窗口缓存：窗口打开后申请者增加到两省，旧91c1仍能点批准得到公邑（489截图、gaoyou_stale_bug_audit）。修复只在批准效果内重新执行现有资格trigger，失格清pending走现有拒绝结果。完整重启44f1，05:03停在同一申请测试起点。

### 05:03–07:29 中断；07:29恢复

05:03之后没有新增截图或存档证据。任务历史显示连续远程上下文压缩网络断连失败；恢复时goal已被标记blocked。不能将这段墙钟时间计入实机测试。07:29 Computer Use重新核实游戏仍暂停在1444.12.3原审批窗口。

### 07:30–07:36 公邑审批修复双分支及跨月通过

44f1同一起点：审批窗口打开后原生转移第二省，实际点击批准，T00保持普通共和改革，pending清除、cooldown1444.12.2保留，君主12755与last_election1444.12.1不变；存档gaoyou_stale_fixed_audit。重新实际加载相同未改资格的起点、实际批准：OPM正常获公邑，pending清除、charter1444.12.3，人物不变，gaoyou_granted_audit。自然跨月至1445.1.11仍公邑及同一人物，gaoyou_grant_month_audit。处理诸子临朝选择暂缓、原版贸易科技选择小心行事；不把这些事件点数变动归因政府。证据501、508、512、516。未单独核验申请者通知文案。

### 07:38–07:53 最终44f1整合AI续跑与交接档

从实际1471.1.1 observer存档自然推进至1480.3.3（早先07:29交接摘要称1471.6.20，实际加载日期为1.1，以截图519和存档为准），未观察到新崩溃。1475/1480自动档独立保留，五公邑OPM与改革保留，同在HYM联盟；HYM六省商盟改革；HAK一省乡社共和；CZC1475剩一省、1480无领土。1480周期10/15。检查所有力量投射来源，CHC20，YAN/QIN/GDD/DQU/CDE/JIZ10，旧YUE/WUU/ZHA/WEI无身份来源。

实际暂停tag HYM用于宫廷/政府UI核对及保存，未继续让玩家控制扬国运行。保存扬1480_03_03_night0906_final44f1_paused.eu4，并真实UI读取回来，534确认同日期与红色暂停。final_paused_audit含SHA。

07:38静态契约全部通过。最终日志1776行中12条相关命中均为gdd_heir.1/.2/.3隐藏事件缺少title/desc/options/picture提示；未当成全清，也未在截止前擅自展开全局日志清理。其他日志问题未纳入国家机制修复范围。

关键截图留仓库，433张中间原图移到本机预先保全目录raw_screenshots，不删除；evidence_inventory.json列绝对路径及哈希。

07:54 收尾完整性检查：50份含path/SHA的存档审计逐一读取原文件重算，全部一致，无丢失或哈希不符。

### 08:00 截止

2026-09-07T08:01:00.558954+08:00：Computer Use只读取屏幕，确认仍1480.3.3暂停，535截图。未再推进游戏。已移除本轮唯一游戏目录fixture zgy_night_20260906.txt，内容保留在证据目录。测试档与用户原进度保全；未commit/push。自动化与goal随后关闭。
