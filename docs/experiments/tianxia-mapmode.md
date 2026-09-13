# Temporary trade-goods map experiment

Branch: `codex/tianxia-mapmode-experiment`, created from main with the existing
uncommitted province panel and bronze seal work preserved. `handoff.md` already
had unrelated edits and was not touched by this experiment. Nothing committed.

## Player workflow

Single-player disposable campaign only. Pause manually, then use **【实验】打开周天下形势图**
in decisions. Read the modal warning; cancel is the first option. Confirm only
while paused. Select the native **贸易品 / 商品 (Trade Goods)** map mode manually.
Tea's dark green displays member-held Zhou provinces; copper's orange displays
non-member-held Zhou provinces or the disposable fallen sample; wool's pale grey
displays other owned provinces. Unowned provinces retain their actual goods.
These are native colours and icons, not a newly registered map mode.

The sample decision paints the player's Zhou capital orange without changing
ownership or permanent Zhou flags. It demonstrates the third colour, not the
complete Longxi fallen-territory canon. While active, a fixed topbar panel displays **周天下形势图已开启**, a pause reminder,
and **恢复商品并退出**. Click that button to restore; the original recovery decision
remains available as a fallback.
Switching map modes, Escape, closing a province or event does NOT restore goods.
Do not advance time, save or quit while open in normal use. The disposable
validation plan deliberately saves active state to test emergency recovery.

Original goods are backed up in persistent per-province flags before mutation.
The global open gate and any existing backup both block another opening, even
following a country switch. Recovery is available to every human country and
restores provinces regardless of their current owner. Unknown future mod goods
are skipped. A startup hook attempts recovery on load; it is not yet engine-verified.
Do not remove this experiment from an active-state save before restoring it.
The warning modifier has zero tax effect; all economic effects of temporarily
changing actual goods remain real while the experiment is active.

## Evidence and interface contracts

| Interface | Scope and meaning | Evidence | Runtime status |
| --- | --- | --- | --- |
| `trade_goods = key` | province trigger, exact good identity | local Wiki Triggers rev 175855 | activation/restoration observed in engine |
| `change_trade_goods = key` | province effect, sets actual good | local Wiki Effects rev 176072; vanilla events/flavorBYZ.txt | activation/restoration observed in engine |
| province flags | per-province persistent backup ledger | existing project scripts | full restored-save comparison passed |
| `add_country_modifier` | country effect; `duration = -1` | local Wiki Effects; initial launch rejected incorrect `days`, fixed | corrected build reloaded without related errors |
| `on_startup` effect | recovery through country-scoped startup hook | existing common/on_actions/zhx_system_on_actions.txt | active-save recovery pending |
| map switch / pause | performed manually by player | no automatic script interface assumed | activation/restoration observed in engine |

Build: `python3 tools/build_tianxia_map_experiment.py`; check: append `--check`.
This enumerates all 32 goods in the local base game, respecting same-filename mod
overrides. Encoded Chinese localization is produced by the existing encoder.

`python3 tools/test_tianxia_map_experiment.py`: 6 tests passed against the actual
generated effect syntax in a narrow interpreter. Covers all 32 goods (including
gold, latent coal and unknown), three categories, double-open protection,
recovery after global flag loss / country change, repeated recovery, sample flag
cleanup, unsupported goods and unowned provinces. This does not emulate engine
price calculation, coal activation, monthly income, native modifiers, UI or loading.

Initial runtime launch exposed two issues: `days` was invalid for country
modifier duration, and `icon` is no longer supported in event modifiers. Both
were corrected in the generator. The initial loaded build is superseded.
## Runtime validation — 2026-09-13

The user subsequently authorized runtime testing and requested quitting the game
and sleeping the display when finished. A disposable CZH campaign remained paused
on 1444-11-11 throughout activation and restoration.

The first HUD build (1.37.5 Inca, 66d5) displayed the warning after confirmation,
kept it visible after closing the country panel, and restored goods from the HUD
button. The warning immediately disappeared. Native Trade Goods icons visibly
returned to their original variety. The topbar custom-window/button integration
is empirically functional in this project, despite its absence from the generic
custom-GUI supported-window list.

Baseline and restored saves are preserved under the EU4 user save directory at
`zhx-hud-test-20260913/{baseline,after}.eu4`, with `comparison.json`:
5385 province entries compared, zero differences in current trade_goods and
latent_trade_goods fields, zero remaining backup flags, no active global flag,
and both dates 1444.11.11. This is not a test of elapsed-time economic rollback.

The original transparent outline allowed map labels to interfere and approached
the country-panel close button. The final build moves the HUD to x560/y157 and
adds an opaque bronze-brown native scroll-track texture beneath the gold outline. Its new launch
checksum is a581. Final visual verification is recorded below.

Startup recovery from an intentionally active save, monthly economic effects,
and full Longxi fallen-territory classification remain unverified/out of scope.
Pause and map-mode selection are manual; restore does not select a map mode.

Final a581 HUD verified in game: opaque bronze background, gold title and outline,
red pause reminder, legible restore button, no overlap with the country close
control. Closing the country panel left the HUD visible; clicking the final
button hid it immediately while the game remained paused on 1444-11-11. No
zhx_map_exp / zhx_map_experiment errors occurred in this launch error.log.
The warning text was then updated to direct players to the top button; encoded
localization generation and six tests passed. That wording-only update was not
reloaded again.

## Red-outline homeland and seven seats — 2026-09-13

User confirmed: seven great feudatories share a distinct colour, using current
seat identity; other Zhou members reconquering fallen homeland restore its
normal colour. No new country bonuses or election rules.

Authoritative province list is `FALLEN_PROVINCES` in the generator (16 provinces):
瓜州5298、苦峪5299、玉门707、嘉峪5297、张掖5296、武威708、永昌5295、
靖远2182、松山5288、宁夏698、灵州5287、中卫5286、固原5277、秦安5276、
碾伯5292、兰州699。The screenshot outline, not whole areas or countries, defines
this set; adjacent 沙州、西宁、阿拉善、额济纳、河套 are excluded.

A once-only startup initializer registers these provinces as Zhou homeland and
marks the opening occupying regimes HMI/SHZ/GZH/WGS/HZH. The initializer is also
called before first opening for a loaded session that has not run it. It respects
dismantlement and does not re-add provinces on later openings. Persistent
historical flags survive commodity restoration; commodity backup flags do not.

Classification order: Zhou province under a nonmember OR historical homeland
under an opening occupying regime -> copper/orange; remaining Zhou province
owned by `zhx_is_seven_great_feudatory` -> salt/light blue; remaining Zhou province
-> tea/green; other owned land -> wool/grey. The regime country flag survives tag
changes, and transfers between marked regimes remain fallen. A member outside
those regimes recovers normal/seven-seat colour; loss back to a marked regime
restores orange. Ownership, not temporary wartime controller, is authoritative.
This is a snapshot on opening; close/restore and reopen after political changes.

The visible disposable sample decision is removed; cleanup of its legacy flag
remains. HUD background hover now provides the four-colour legend. No provinces.bmp,
tradegoods definitions, ownership, cores, seat bonuses or election code changed.

Eight generated-script tests passed, including live seat change, fallen-over-seat
priority, all 16 homeland initialization, reconquest, recapture, persistent
historical flags and deliberate province removal not being undone. Native salt
colour is read from installed 1.37.5 tradegoods. Startup province/tag scopes and
flag contracts reuse existing project initialization patterns. This extension
has not been reloaded or tested in-game; prior HUD/restoration runtime evidence
above applies to the preceding build, not the new four-colour classification.

## Seven-seat colour adjustment and automatic switching investigation

User requested naval_supplies instead of salt. Generator, encoded legend and
eight tests updated: seven-seat territory now uses native dark blue naval supplies
(0.11, 0.17, 0.4). Earlier salt/light-blue descriptions above are historical.
Build/check and eight tests passed; this colour change has not been runtime reloaded.

Automatic event-confirmation map switching remains unimplemented. No mapmode or
map_mode effect was found in the local effects corpus, installed vanilla events
or CWTools EU4 effect schema (https://github.com/cwtools/cwtools-eu4-config/blob/master/effects.cwt).
This establishes no supported route found, not proof no engine route can exist.
Console mapmode commands must not be substituted for an event effect. The player
still selects Trade Goods manually after confirming.
