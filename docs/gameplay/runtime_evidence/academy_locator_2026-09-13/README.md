# 学宫定位接口核查（2026-09-13）

这是本机 EU4 1.37.5 macOS 可执行文件的离线只读检查，未附加、启动或重启游戏，不能作为修复后的实机点击证据。

用户报告：名录定位可以打开驻地窗口，但窗口内原生定位无效。原实现只保存全局 `zhx_ad_site_<key>`，然后将其裸名称交给事件 `goto`。

- `CEvent::GetGoToProvince` +110 调用 `HasSavedEventTarget`，+169 调用 `GetSavedEventTarget`；未命中则 +207 按整数省份 ID 读取原 token。
- 上述两个目标查找函数只遍历事件根作用域的本地目标数组（+0x80 至 +0x88），没有全局目标回退。
- `CEventWindow::GoToProvinceEvent` +44 跳转到 `CEU3Idler::CenterToAndHighlight(int)`，表明原生 goto 是居中并高亮，不能据此声称打开省份面板。
- 原版 `events/OrthodoxIcons.txt` 的 `orthodox_icon_events.1` 使用顶层 `goto = eleusa_church_province`，在 immediate 的省份作用域中 `save_event_target_as`，与本次修复方式一致。

修复：名录事件 immediate 将已验证的全局驻地复制为本事件局部 `zhx_ad_goto_province`，goto 和说明文字共用这份快照。两个同类学宫通知 `.211`、`.230` 也补上局部目标。学宫位置仍以永久省份修正为权威。

一键定位核查：本机 `common/custom_gui/example.txt` 未列出自定义按钮的 goto／镜头属性；`CCustomButton::ReadMember` 只添加 trigger/effect 后委托 icon/base 读取，执行函数派发脚本效果。离线 Effects 资料没有找到可用镜头跳转效果。现阶段没有可用于该面板的已验证一键定位接口；这不是对所有引擎扩展方式的绝对不可能证明。

本轮 Computer Use 返回 `Accessibility error: AXError.cannotComplete`，因此修复后的原生定位、未探索目标与存读档未实测。需完整重启加载后重新打开驻地窗口；已经打开的旧事件不包含新增 immediate 快照。
