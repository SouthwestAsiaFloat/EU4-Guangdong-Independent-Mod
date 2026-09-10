# test 与当前本地功能的合并指南

更新：用户已执行合并，本次已在 `codex/merge-test-20260909` 解决工作区中的七个冲突文件及功能衔接问题，尚未暂存、提交或推送。请按 [合并修复记录](merge_resolution_2026-09-09.md) 的收尾命令操作；下文保留为执行合并前的审查记录，无须再次创建分支或重新 merge。

原审查只读取远端并在 `codex_preview/merge-test-audit-20260909` 预演逐文件三方合并。

## 已核实状态

- 本地当前分支：`update-staging`，HEAD 为 `4510302ab227b512ff6565e4fbd870e716d618b8`，功能修改尚未提交。
- 远端 `update-staging`：同上。
- 远端 `test`：`2f1fb4b0780711c53ae06f526413eee1c63e0a65`，在该基点上增加 15 个提交、改变 600 个文件（包括大量截图和生成文件）。
- 双方改动重叠 16 个文件。按同一基点、统一换行符预演，其中 7 个文件共 13 处文本冲突；实际 Git 合并输出为准。
- `test` 新增内容包括：盟功奖励与定期排名、犯盟外交与奉辞伐罪、救患与告急、大名拆省与邶国、岭南八国、潮州继承与议会、客家派系政体、周室册封、公邑贸易联盟，以及本地化修复。

比较来源：<https://github.com/Aaronzhang11/EU4-Guangdong-Independent-Mod/compare/4510302ab227b512ff6565e4fbd870e716d618b8...2f1fb4b0780711c53ae06f526413eee1c63e0a65>

## 预计冲突与处理原则

| 文件 | 处理方式 |
|---|---|
| `docs/DECISION_LOG.md` | 两边记录都保留；本地 D-035 与 test 的 D-035 编号重复，需要重编号及更新相应引用。 |
| `guangdong_independent_practice/common/on_actions/zhx_system_on_actions.txt` | 保留本地天命启动与灭国处理，以及 test 的盟功、灭侯礼乐计数和外交队列。逐项核对作用域、时机和防重复标记，不用整文件 ours/theirs。 |
| `guangdong_independent_practice/common/scripted_effects/zhx_gui_roster_effects.txt` | 冲突本身在扩展区注释附近；保留完整六席缓存，同时检查生成器是否会覆盖动态首席排除规则。 |
| `guangdong_independent_practice/common/scripted_effects/zhx_system_effects.txt` | 同时保留本地历史政权标记、退出后重计票修复，以及 test 的灭亡标记复位、诸侯缓存更新。 |
| `guangdong_independent_practice/events/zhx_system_events.txt` | 保留完整 v13→v14→v15 迁移；同时保留 test 的册封初始化和本地天命缓存刷新，确保依赖的席位初始化完成后再刷新天命。 |
| `tools/encode_eu4_chinese_localisation.py` | 合并双方的源文件→目标文件映射，不删除任一功能的条目。相同数字前缀不代表完整文件名相同。 |
| `tools/generate_zhx_tianxia_roster.py` | 使用 66 个成员槽位，同时保留六大诸侯缓存生成能力；排除当前动态首席，不再固定排除 YAN。 |

## 没有文本冲突也要核对的功能

1. `test` 把首席从固定燕国改为动态目标，并增加第 66 个成员槽。GUI 可以自动保留本地对称坐标并加入新槽位；生成器、名册、七席校验与天命缓存必须使用同一套动态席位定义。
2. `test` 的 `decisions/zhx_diplomacy_decisions.txt` 新增 `zhx_leave_tianxia`，目前直接调用 `zhx_remove_tianxia_member`；本地 UI 退出另经 `gdd_leave_tianxia_territory_effect` 清除省份标记并扣天命。合并时应统一两入口的资格与结算，防止绕过本地领土处理，也避免重复扣关系或天命。
3. `test` 的犯盟/灭侯机制与本地天命惩罚是不同账目。可保留双方功能，但不能把触发器中的效果机械拼接到错误作用域，或把月结算逻辑移回省份易主、和谈事务中。
4. 本地化先合并可读源和编码映射，再重新生成，保证可读源与游戏编码文件一致。

## PowerShell 命令

逐段执行；任一命令报错就先停止该段。以下命令提交功能、文档和工具，保留 `design`、`codex_preview` 在本地，不把效果图和本次分析目录加入提交。

### 1. 保存本地功能并建立备份

```powershell
Set-Location -LiteralPath 'E:\欧陆mod\Guangdong-Independent-GitHub'
git switch update-staging
git -c core.safecrlf=false add -- README.md docs guangdong_independent_practice tools
git diff --cached --stat
git commit -m "保存本地天命、周天下领土修复与对称布局"
git branch codex/backup-local-before-test-20260909
```

### 2. 在合并分支整合远端

```powershell
git fetch origin
git switch -c codex/merge-test-20260909
git merge --no-edit origin/update-staging
```

上一条成功后继续；若远端 staging 在检查后出现新提交并发生冲突，先解决它，再合并 test。

```powershell
git merge --no-ff --no-commit origin/test
git diff --name-only --diff-filter=U
```

此时按上述说明编辑冲突文件，并检查功能兼容。`ours` 指合并分支保存的本地功能，`theirs` 指 `origin/test`；不要使用全局 `-X ours`、`-X theirs` 或整目录覆盖。需要退出当前尚未提交的合并时，可运行 `git merge --abort`，此前的本地功能提交仍保留。

### 3. 生成并验证

解决冲突并调整兼容逻辑后，运行以下命令。生成器的冲突必须先解决，否则可能覆盖已合并的缓存实现。

```powershell
$py = 'C:\Users\ZYT\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -B tools/generate_zhx_tianxia_roster.py
if ($LASTEXITCODE -ne 0) { throw '名册生成失败' }
& $py -B tools/encode_eu4_chinese_localisation.py
if ($LASTEXITCODE -ne 0) { throw '本地化生成失败' }

$checks = @(
    'tools/validate_gdd_eoc_layout.py',
    'tools/test_gdd_tianxia_buttons.py',
    'tools/test_gdd_tianxia_territory.py',
    'tools/validate_gdd_celestial_mandate.py',
    'tools/validate_gdd_tianxia_territory.py',
    'tools/validate_zhx_merit_store.py',
    'tools/validate_zhx_diplomacy.py',
    'tools/validate_zhou_feudatories.py',
    'tools/validate_zhx_council.py',
    'tools/validate_czc_government.py',
    'tools/validate_hak_government.py',
    'tools/validate_gongyi_yang.py'
)
foreach ($check in $checks) {
    & $py -B $check
    if ($LASTEXITCODE -ne 0) { throw "校验失败：$check" }
}
& $py -B tools/encode_eu4_chinese_localisation.py --check
if ($LASTEXITCODE -ne 0) { throw '本地化校验失败' }
```

这是合并后的验收命令，不表示当前已合并或保证这些测试无须适配。动态首席和退出机制调整后，应补充相应回归场景，不要仅修改断言来绕过失败。静态检查不能替代游戏中验证天命界面、退出、盟功排名、救患与存档迁移。

### 4. 提交合并并由你推送

```powershell
git -c core.safecrlf=false add -- README.md docs guangdong_independent_practice tools
$unmerged = @(git diff --name-only --diff-filter=U)
if ($unmerged.Count -ne 0) { throw '仍有未解决的冲突' }
git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check
if ($LASTEXITCODE -ne 0) { throw '差异检查失败' }
git commit -m "合并 test 新功能并保留本地天命与周天下修复"
```

上述成功且游戏验收完成后执行：

```powershell
git switch update-staging
git merge --ff-only codex/merge-test-20260909
git fetch origin
git merge-base --is-ancestor origin/update-staging HEAD
if ($LASTEXITCODE -ne 0) { throw '远端 staging 又有新提交，先合并并复测后再推送' }
git log --oneline origin/update-staging..HEAD
git diff --stat origin/update-staging..HEAD
git push origin HEAD:update-staging
```

使用普通 push，不使用强制推送。若最后因远端并发更新被拒绝，重新读取并合并远端后复测。
