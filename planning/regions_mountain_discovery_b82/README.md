# B82 江淮、淮扬归华南与不可通行山脉视野

用户要求将江淮、淮扬放入华南，并修复东亚国家看不到新增不可通行山脉的问题，完成后合入本地 main。

## 区域

`jianghuai_area` 与 `huaiyang_tongtai_area` 从 `north_china_region` 移入 `south_china_region`。Area 内省份、地图像素、发展度和贸易配置均不改变。基础地图生成器与终端投影同时更新，避免重放恢复旧归属。

## 视野缺失根因与修复

20 个新增山脉已有 definition 和 climate/impassable 注册，但完全没有省份历史，因而没有 `discovered_by` 初始发现记录。既有台湾山脉 5029 已有独立历史，不属于本批缺失集合。北美等原版山脉也不属于修复范围。

- 为 20 个山脉建立只含 `discovered_by = chinese`、`discovered_by = nomad_group` 的历史文件，不添加国家、发展度或核心。
- 采用原版 Himalaya 不可通行省份历史所使用的科技组发现方式。当前自定义国家历史有 105 个中国科技组、1 个游牧科技组，均被覆盖；原版东亚的中国科技组国家也由相同规则覆盖。
- 旧存档不会重新读取初始省份历史，因此另加隐藏国家事件 `gdd_mountain_discovery.1`。启动及月度脉冲调用，限定中国/游牧科技组，以 `discover_province` 补发现这 20 个 ID，并设国家标记避免反复执行。释放的新国家也可通过月度脉冲补齐。
- 没有添加永久全球开图、额外可通行关系或山脉所有权。

## 验证与重放

20 个 ID 均有有效像素，均保留 impassable 属性；按本体、两层中文依赖、Mod 的有效历史覆盖检查，每个 ID 恰好一个历史文件。23 个受管文件重复执行哈希一致。完整终端检查、贸易网络检查和中文编码检查通过。尚未进游戏验证视野表现；旧存档的补发现逻辑需更新 Mod 后重载并推进至一次月度检查。

执行 `python3 tools/map_pipeline/apply_b82_regions_mountain_discovery.py`；加 `--check` 为只读检查。正式终端入口已在 B81 后接入本批。完整证据见 `validation.json`。
