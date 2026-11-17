# v1.3.3 真实剧情文本实机检查

从正式译稿选取 16 条真实台词，临时置于序章入口连续回放；台词内容保持与正式译稿一致，背景和语音仍是序章。这项检查验证普通对白框渲染，不等于在原路线、原场景走完全部剧情。原脚本和行号见下表及 [cases.json](text_runtime_v1.3.3/cases.json)。

逐条等待文字完全显示后观察：本表 16 条正文未发现字形重叠、上下裁切、缺字或句末丢失。三行长句、引号、书名号、问叹号、省略号、中文与数字及英文专名混排均留图。字数不是精确宽度模型；本轮没有改动引擎自动换行规则。

| 截图 | 正式译稿位置 |
| --- | --- |
| [01](text_runtime_v1.3.3/01.png) | `yns_z71b_02.scx.txt:41` |
| [02](text_runtime_v1.3.3/02.png) | `yns_z64_02.scx.txt:335` |
| [03](text_runtime_v1.3.3/03.png) | `yns_z68_02.scx.txt:19` |
| [04](text_runtime_v1.3.3/04.png) | `yns_z73_03.scx.txt:354` |
| [05](text_runtime_v1.3.3/05.png) | `yns_z75_02a.scx.txt:82` |
| [06](text_runtime_v1.3.3/06.png) | `yns_d_a17_02.scx.txt:426` |
| [07](text_runtime_v1.3.3/07.png) | `yns_z72_02.scx.txt:379` |
| [08](text_runtime_v1.3.3/08.png) | `yns_d_a17_02.scx.txt:360` |
| [09](text_runtime_v1.3.3/09.png) | `yns_b11i.scx.txt:32` |
| [10](text_runtime_v1.3.3/10.png) | `yns_f24_03.scx.txt:101` |
| [11](text_runtime_v1.3.3/11.png) | `yns_z73_03.scx.txt:180` |
| [12](text_runtime_v1.3.3/12.png) | `yns_z73_03.scx.txt:374` |
| [13](text_runtime_v1.3.3/13.png) | `yns_01.scx.txt:122` |
| [14](text_runtime_v1.3.3/14.png) | `yns_17_03.scx.txt:62` |
| [15](text_runtime_v1.3.3/15.png) | `yns_22.scx.txt:39` |
| [16](text_runtime_v1.3.3/16.png) | `yns_d13_02.scx.txt:138` |

## 历史记录

[第 1–2 条](text_runtime_v1.3.3/history_01_02.png)、[第 3–6 条](text_runtime_v1.3.3/history_03_06.png)、[第 7–11 条](text_runtime_v1.3.3/history_07_11.png)、[第 12–15 条](text_runtime_v1.3.3/history_12_15.png)已检查段落换行和首尾字符。第 16 条是当时尚未推进的当前对白，没有把它计为历史条目。

**尚存的视觉限制：** 历史面板底部会透出当前对白，滚动到该区域时可能形成视觉叠加。因此不能声称历史界面“完全没有重叠”。`backlog.png` 与解包原版逐字节相同，SHA256 均为 `9fccee7e82455d31537e31dcde8d9adde6401aedf18f116de426bd687149626b`；本轮保留其原有贴图与透明度，未擅自涂成不透明底板。若要改变该行为，仍需对照原版实机确认窗口隐藏/合成逻辑。

## 正式版本恢复

临时回放包不进入发布目录。退出回放后安装 `work/out` 的正式脚本、系统资源、帮助和 DLL，逐项验证与发布构建哈希一致。已重新启动并确认序章第一句恢复，见 [正式剧情截图](text_runtime_v1.3.3/formal_story.png)。

全稿检查、逐句校对进度与剩余范围见 [校对报告](text_audit_v1.3.3.md)。全路线实玩和 95,559 行逐句精校尚未完成。
