# 项目状态（v1.0）

YU-NO 重制版简体中文补丁 —— 由 A-FEI- 制作，发布/交流：BBS.GBTGAME.ME

## 一、已完成的汉化范围

### 剧情与系统文本（scrchs.cpk，886 个 .scx）

| 内容 | 状态 |
| --- | --- |
| 官方中文版剧情移植 | ✅ 100% |
| 机翻补全部分（8,236 行） | ✅ 已做批量规范化（`JF:` 标记、`‥‥`→`……`、重复标点、括号、人名统一、常见错译） |
| 官方中文缺失的整段日文（zz.scx 独白等 109 行） | ✅ 人工补翻 |
| 系统 UI 词汇（设置项、按钮、手柄键名、播放模式、存档占位） | ✅ 全部对齐界面图用语 |
| 人名译法 | ✅ 拓也／亚由美／美月／绘里子／正胜／澪／神奈／香织／幸三／秀夫／优诺／阿曼达／塞蕾丝／北条笃 |

### 图片 UI（syschs.cpk，18 个资源）

| 图片 | 内容 | 状态 |
| --- | --- | --- |
| titlechip.png | 标题菜单（开始游戏/设置/帮助/退出游戏）、LOGO 页「按任意键开始」、GBT 铭牌 | ✅ |
| menuchip.png | 游戏内菜单（历史记录/设置/帮助/存档/返回标题/退出游戏） | ✅ |
| config.png | 设置界面项目名、选项按钮、小节标题、角色语音名单 | ✅ |
| data01.png | 操作提示（取消/跳过/道具/自动/确定、手柄丝印、注意） | ✅ |
| help.png | 帮助页（操作说明 + 15 行按键功能表） | ✅ |
| guide.png | 操作指南三条提示条 | ✅ |
| album.png / music.png | 图鉴（美术室/图像鉴赏）、音乐室（音乐鉴赏/重制版/原版）、返回、无数据 | ✅ |
| album_thum.png / data03.png / eff_lenzflare.png / yuno_ui*.png | 无文字，原样保留 | — |
| font.png / font2.png | 霞鹜文楷字库（3943 字形） | ✅ |
| backlog.png | 左侧竖排 `BACK LOG` 装饰字 | ⬜ 保留原样（见下） |

### 程序与品牌

| 项 | 状态 |
| --- | --- |
| patch.dll（窗口标题） | ✅ `在世界尽头咏唱爱的少女 YU-NO   A-FEI- 汉化  BBS.GBTGAME.ME` |
| GBT logo | ✅ 标题图铭牌 + 补丁包内 `GBT_logo.png` |
| 安装/卸载脚本 | ✅ `dist\安装到游戏目录.bat` / `卸载还原.bat`（自动备份到 `_backup_cht`） |

## 二、已知限制（非文本、无法在本工程范围内处理）

1. **开场影片字幕**：`movie.cpk` 里的 USM 视频自带英文标语（`A girl who chants love at the bound of this world.`）。属于视频画面，不是脚本文字，需要解包并重编码视频才能替换。
2. **backlog.png 竖排 `BACK LOG`**：装饰性拉丁字，直接画在羊皮纸纹理上；清除会破坏底纹，保留原样。游戏内其它相关文字（历史记录菜单项等）均为中文。
3. **部分 TIPS 百科条目**：保留英文专有名词/缩写（如 JAXA、CIA、SERN），属于原文引用，未强行意译。
4. **机翻润色**：批量问题已清理，但 8,236 行机翻仍非逐句精修；如有具体读感问题可按行反馈，后续版本继续修。

## 三、构建与验证

```bat
python tools\build_all.py --font-family "LXGW WenKai"        :: 全量构建
python tools\build_all.py --font-family "LXGW WenKai" --install  :: 构建并安装
```

构建链：`prepare_text → patch_jp_lines → patch_ui_lines → final_clean → make_charset → mgsfontgen → make_font → sc3tools replace-text → cpkmakec`。

实机验证截图见 `_recon/`：

| 截图 | 内容 |
| --- | --- |
| `r2_final_title.png` | 标题菜单（四项全中文） |
| `r3_config_names.png` | 设置界面角色语音名单 |
| `r4_story.png` | 对白界面（自动/跳过） |
| `r5_scene2.png` | 序章 CG + 中文对白 |
| `r6_menu.png` | 游戏内菜单 |
| `help_check_dark.png` | 帮助页 |
| `album_check_dark.png` | 图鉴 |
| `music_check_dark.png` | 音乐鉴赏 |

## 四、机器翻译免责声明

本项目仅用于学习交流，请支持正版。游戏素材版权归 MAGES./5pb. 及发行方所有。
