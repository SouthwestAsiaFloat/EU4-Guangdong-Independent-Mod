# 礼乐悬停：当前效果与年度预估

天下秩序的 `zhx_gui_order_tt` 只展示当前礼乐档位的税收、生产、训练度等实际修正、礼制护土的省份战争分数修正，以及按当前局势计算的年度礼乐净变化和非零分项。移除非法夺地、灭侯等一次性规则说明；不将年度结算换算为每月变化。

年度分项包括基础恢复、天下和平、诸侯内战、天下显学、天子稳定、威望、厌战和首都控制。显示的是当前条件保持不变时的年度变化，尚未扣除礼乐上下限的截断，也不预测未来战争或一次性事件。实际结算仍限制在 -100 至 100。

`zhx_compute_ritual_yearly_forecast` 计算派生变量，年度结算调用同一效果后将合计加入礼乐值。打开面板时刷新，面板打开期间由天子的月度脉冲刷新；预览不改变礼乐值。界面沿用现有 CZH 天子锚点。首都控制检查在首都作用域使用 PREV，避免从玩家界面调用时误将 ROOT 玩家当成天子。

实现位于 `zhx_ritual_tooltip_effects.txt`、`zhx_ritual_tooltip_on_actions.txt` 和 `customizable_localization/zhx_ritual_tooltip.txt`。名册刷新入口和生成器同步维护，中文由可读源文件编码生成。

验证：`tools/validate_zhx_ritual_tooltip.py` 通过 10,752 组源代码驱动的年度情形，检查分项、纯预览、重复调用、共享结算、刷新入口和中文编码。外交和议会静态契约检查通过。未重启游戏验证悬停排版。

另有既存的 `validate_zhx_merit_store.py` 检查不一致：它禁止名册构建调用 `zhx_allocate_gui_roster_slot`，但 HEAD 中已有投票阶段的该调用。本次不修改这项无关契约。
