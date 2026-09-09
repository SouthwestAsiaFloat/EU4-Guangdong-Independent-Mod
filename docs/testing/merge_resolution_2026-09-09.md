# test 合并冲突修复记录

工作目录：`E:\欧陆mod\Guangdong-Independent-GitHub`。本次只修改该仓库；原版和依赖模组仅用于只读校验，没有启动游戏、修改存档、暂存、提交或推送。

## 已核实的合并状态

- 当前分支：`codex/merge-test-20260909`。
- 本地功能提交：`9401a7dd7d9f1b0a3ff71f6dc4de1f6f7788ec92`。
- 本次合入的 test 提交：`2f1fb4b0780711c53ae06f526413eee1c63e0a65`。
- 本地 `update-staging` 仍指向上述本地功能提交。
- 七个文件的工作区冲突标记均已清除。Git 索引尚未暂存，所以执行下方 `git add` 前仍会显示 `UU`；这是待标记为已解决，不是文件中仍有冲突。

## 合并取舍

| 冲突文件 | 最终处理 |
|---|---|
| `docs/DECISION_LOG.md` | 两边记录全部保留；test 使用 D-035 至 D-043，本地领土规则改编号为 D-044。 |
| `common/on_actions/zhx_system_on_actions.txt` | 保留本地王命初始化；三个吞并回调先结算一次域外吞并王命损失，再执行 test 的灭侯计数和延迟成员清理。 |
| `common/scripted_effects/zhx_gui_roster_effects.txt` | 保留 66 个成员位置及六个非首席席位缓存；动态排除当前首席；旧 200 格面板仅清理旧目标，不恢复其运行时扫描。 |
| `common/scripted_effects/zhx_system_effects.txt` | 同时保留本地历史身份、退盟后的议事重计数，以及 test 的盟功、动态席位、政体和灭侯清理。 |
| `events/zhx_system_events.txt` | 保留 v15 领土迁移和 test 新政体初始化，最后刷新王命。 |
| `tools/encode_eu4_chinese_localisation.py` | 合并两边全部本地化文件映射。 |
| `tools/generate_zhx_tianxia_roster.py` | 统一生成上述成员与大诸侯缓存；兼容 test 已移除的旧面板，不会在重新生成时丢失六席缓存。 |

表中游戏文件路径均相对于 `guangdong_independent_practice/`。

额外解决了三处功能衔接：

- 详细成员提示扩充到第 66 格，历史核心国家目录加入 test 新增的 DMG。
- 新退出决议与本地天命按钮共用结算：移除直属周土地块、王命按发展度扣减且总计不超过 20、皇帝好感 -100；同时保留 test 的威望 -25、普通成员十年 -25 好感、二十年禁止重新申请。天子和皇帝分属两国时，天子另获十年 -50；同国时不重复叠加关系惩罚。两个入口均在实际执行时重检资格。
- 退出的按钮、决议和确认选项提示同步；确认事件正文保留叙事格式。对称布局、中间预留空白和现有图案保持本地版本。

政体验证器新增 `EU4_STEAMAPPS` 环境变量支持；客家图集检查支持从本机有效资源路径读取原版图集，并核验原始 SHA-256。游戏资源未被改动。

## 验证结果

完整结果见 [检查结果 JSON](merge_resolution_checks_2026-09-09.json)。

- 33 项天命按钮与合并衔接离线测试通过，包含两入口一致性、不同皇帝／天子、动态首席、政体退盟清理、三种吞并回调不重复结算。
- 15 项领土索还测试通过，保留实际持有国冷却、核心豁免和合法复国规则。
- 278 项诸侯政体场景、104 项客家政体场景通过。
- 天命布局、王命机制、领土、盟功、外交、公议、潮州、客家、公议阳政体的现有验证器均通过。
- 改动中的 195 个 Clausewitz 脚本解析通过；改动 Python 文件可编译；未发现 Git 冲突标记。
- 名册、详细提示、本地化编码生成器重复运行无文件变化；本地化往返编码检查通过。
- 天命界面移除新增的第 66 个盾牌代码块后，与本地 HEAD 完全一致（忽略 CRLF/LF）。
- 本轮工作区修复的 `git diff --check` 通过。相对本地 HEAD 的整个合并还包含 test 导入的原版 CB／理念文件自带尾随空格；为保留上游文件内容，未批量格式化这些文件。

这是静态检查和离线脚本测试，不代表合并版本已通过 EU4 实机运行、图形渲染或存读档验收。

## 用户执行的收尾命令

在 PowerShell 按以下顺序执行。不要再次开始 merge，不需要重新生成文件；不使用强制推送。

```powershell
Set-Location 'E:\欧陆mod\Guangdong-Independent-GitHub'

git -c core.safecrlf=false add -- docs guangdong_independent_practice tools
if ($LASTEXITCODE -ne 0) { throw '暂存失败，停止操作' }
if (git diff --name-only --diff-filter=U) { throw '仍有未解决冲突，停止操作' }

git commit -m "Merge test features with local Tianxia fixes"
if ($LASTEXITCODE -ne 0) { throw '提交失败，停止操作' }

git switch update-staging
if ($LASTEXITCODE -ne 0) { throw '切换分支失败，停止操作' }
git merge --ff-only codex/merge-test-20260909
if ($LASTEXITCODE -ne 0) { throw '快进合并失败，停止操作' }

git push origin update-staging
```

`docs`、模组和 `tools` 是本轮修改范围；test 自动合并成功的其他文件已在索引中，会一并提交。命令不会把本地 `design/`、`codex_preview/` 草图、备份和审查日志加入提交。若远端分支已有别人新增的提交，普通 push 会拒绝覆盖；保留报错后重新核对，不要改用 `--force`。

本轮政府验证的环境配置为：

```powershell
$env:EU4_STEAMAPPS = 'E:\Program Files (x86)\Steam\steamapps'
```
