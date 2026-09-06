# 亡凉遗使谒天子事件图

`gdd_liang_audience_source.png` 是 2026-09-03 使用 Codex 内置 ImageGen 生成的
原创源图。画面定格于开封周廷：老臣段守节献上故国谱牒与残存印信，年轻嗣君
张承祚跪候其后，周天子认可其身份，礼官向使团递出准其遍告诸侯的符节。

原版 EU4 的 `GIFTS_TO_EMPEROR_eventPicture`、`IMPERIAL_SEAL_eventPicture`、
`COURT_eventPicture` 与 `DIPLOMACY_eventPicture` 只用于参考棕黑版画媒介、线描密度、
叙事层级和狭长构图；本仓库没有复制这些原版图片的像素。源图已经裁成无白边的
`2016×520` RGB 图像，运行时文件是无透明像素、无 mipmap 的 `512×132`
ARGB8888 DDS，与《天命》中国事件图的规格相同。

生成与验证：

```sh
python3 tools/generate_liang_event_picture.py
python3 tools/generate_liang_event_picture.py --check
python3 tools/validate_liang_restoration_chain.py
```

运行时 sprite 为 `gdd_liang_audience_eventPicture`，只接入 `.1`“亡凉遗使谒天子”
与 `.10`“凉使至庭”。复国、空还、归土与毁约事件保留中性配图，避免让“谒见
周天子”的具体场景在后续分支中产生语义错位。

生成提示词：

> Use case: historical-scene. Asset type: custom Europa Universalis IV event
> picture, final use is an extremely wide 512×132 banner inside the event
> window. Create an original illustration for the alternate-history event
> “亡凉遗使谒天子”, set in Kaifeng around 1444. Show elderly loyal minister
> Duan Shoujie, travel-worn and solemn, bowing deeply while presenting a faded
> genealogical scroll and a small battered bronze state seal; young exiled
> claimant Zhang Chengzuo kneels beside and slightly behind him, dignified but
> vulnerable; the Zhou Son of Heaven receives the petition from a modest raised
> seat while a court official extends a ceremonial tally toward the envoys.
> The story beat is grief, ritual restraint, and a fragile renewal of hope, not
> triumph. Match the broad visual language of classic EU4 event art: historical
> copperplate engraving or woodcut on aged warm parchment, dense hand-drawn
> crosshatching, black and dark umber ink, restrained sepia wash, weathered print
> texture, and readable silhouettes. Use a true ultra-wide panoramic tableau;
> keep essential faces, hands, scroll, seal, and tally in the central 80% so an
> exact 512×132 crop remains intact. Use late-medieval Chinese robes and court
> caps appropriate to a fictional Zhou-descended polity in 1444. No Qing queues,
> Manchu dress, European clothing, Japanese armor, text, calligraphy, captions,
> borders, UI frame, logos, or watermark.
