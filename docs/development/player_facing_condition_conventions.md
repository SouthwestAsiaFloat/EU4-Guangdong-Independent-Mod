# 玩家可见条件编写约定

内部脚本接口继续使用稳定的英文标识符（如 `zhx_*`、`gdd_*`），不要为了汉化而重命名 flag、variable 或 scripted trigger。玩家看到的是表现层，机制状态与表现层必须分开。

- 决议的 `allow`、可见事件选项的 `trigger` 若包含自有 flag、variable 或复杂 scripted trigger，必须放进 `custom_trigger_tooltip`，用一句可读的中文说明实际条件。原逻辑仍在包装块内判定，不要复制第二份逻辑。
- 纯分流、候选槽、AI 路由等不该解释给玩家的条件放进 `hidden_trigger`。不要用它隐藏玩家做选择所需的真实门槛。
- 决议与事件选项若要执行自有 flag、variable 或 scripted effect，把实际写入放进 `hidden_effect`，并用 `custom_tooltip` 概括玩家真正会得到或付出的结果。不要让“设置国家标志”“改变变量”成为效果说明。
- 简单的原版条件（稳定度、战争状态、点数等）可以保留原生展示；宗教、文化、学派、修正和国家标签等已有本地化的对象标识符也不必重复包装。
- 中文只改 `localisation_source`，随后运行编码器；`custom_trigger_tooltip` 的 `tooltip` key 必须在可读本地化源中存在。
- `debug`、`test` 与隐藏事件不属于玩家界面，但生产事件不能借此规避可读性要求。

提交前运行：

```bash
python3 tools/validate_player_facing_conditions.py
```

校验器检查自有决议的直接 `allow/effect` 和可见生产事件选项的 `trigger/effect`，并识别 `custom_trigger_tooltip`、`hidden_trigger` 与 `hidden_effect` 包装；它不会把带前缀的宗教、文化、学派、修正、标签或 event target 误判成泄漏。
