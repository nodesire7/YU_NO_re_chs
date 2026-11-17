# この世の果てで恋を唄う少女 YU-NO（重制版）简体中文移植

把官方中文版（AI5CHS）的剧本与界面文本移植到 Steam/MAGES 引擎的 YU-NO 重制版上，
并补齐官方中文缺失的部分。当前工程已可一键构建并在实机运行。

* 制作：**A-FEI-**
* 发布/交流：**BBS.GBTGAME.ME**
* 原工程：<https://github.com/nodesire7/YU_NO_re_chs>（HIllya51）

**下载补丁：** [v1.3.2 发布页](https://github.com/nodesire7/YU_NO_re_chs/releases/tag/v1.3.2)（含安装/卸载脚本与 SHA256）。

## 当前汉化状态

> v1.3.2 修复实机发现的括号裁切和字格串笔，调整字体基线；12 组标点、数字、字母、符号及长句样例通过实机复查。此前整稿待校清单已归零。详细进度、已知限制与验证记录见 [docs/STATUS.md](docs/STATUS.md) 和 [实机检查记录](docs/font_runtime_v1.3.2.md)。

| 模块 | 状态 |
| --- | --- |
| 剧情文本（886 个 .scx） | ✅ 官方中文主体 + 日文对照补翻/校订；95,559 行整稿验证通过，待校 0 行 |
| 字体 | ✅ 正文 = 霞鹜文楷（LXGW WenKai）；标题/菜单图 = 思源宋体 |
| 标题菜单 / LOGO 页 | ✅ 开始游戏 / 设置 / 帮助 / 退出游戏 / 按任意键开始 |
| 游戏内菜单（历史记录/设置/帮助/存档/返回标题/退出） | ✅ |
| 设置界面项目名 / 选项按钮 / 小节标题 | ✅ |
| 设置界面角色名（CV 试听列表） | ✅ 有马拓也/亚由美/美月… 全中文 |
| BGM 播放模式 / 存档占位 | ✅ 单曲循环/顺序播放/列表循环/随机播放/无数据 |
| 帮助 / 操作指南 | ✅ Steam 键盘鼠标与手柄帮助、Switch 帮助图与操作提示条 |
| 操作提示栏（data01） | ✅ 按键标签/徽章/手柄丝印全中文（对白区 AUTO/SKIP = 自动/跳过） |
| 图鉴 / 音乐鉴赏（album/album_thum/music） | ✅ 全中文（标题、页签、返回、无数据占位） |
| 开场影片字幕 | ⬜ 英文为原版 USM 视频内嵌（非脚本文字，需重编码视频） |
| 窗口标题 / 品牌信息 | ✅ `A-FEI- 汉化  BBS.GBTGAME.ME` |

## 目录结构

```
localization/      中日对照.jsonl 完整校订稿、验证统计
alltexts/          从各语言版本提取的文本（ja 原文 / zh 译文 / en 英文 / jazh 对照）
work/              构建中间产物（解包、文本、字体、打包结果）
  extract/         从游戏 data/*.cpk 解包出来的原始文件
  text_final/      清理后的最终中文文本
  system_build/    待打包的 system 资源（字体 + 汉化后的 UI 图）
  ui_out/          汉化后的 UI 图片
tools/             构建与汉化工具（见下）
pack/              第三方工具：sc3tools（Rust）、mgsfontgen-dx（C#）、crifilesystem（CRI 官方）
patch/             patch.dll 源码（注入后修改窗口标题、补命令行参数）
distribution/      可重打包的安装/卸载脚本与说明
dist/              可直接分发的补丁包
```

## 构建

依赖：Python 3 + Pillow/NumPy/SciPy、Rust（cargo）、.NET SDK、MSVC（仅重建 patch.dll 时需要）。

```bat
:: 1. 解包原版 CPK（只需做一次，结果在 work/extract）
python tools\cpk.py extract "F:\game\steam\steamapps\common\YU-NO\data\script.cpk" work\extract\script
python tools\cpk.py extract "F:\game\steam\steamapps\common\YU-NO\data\scrchs.cpk" work\extract\scrchs

:: 2. 一键构建（清理文本 → 生成 charset → 生成字体 → 编码 → 打包 CPK）
python tools\build_all.py

:: 3. 安装到游戏（自动备份到 _backup_cht）
python tools\build_all.py --install
```

`patch.dll` 需要单独用 MSVC 编译：

```bat
call "<VS>\VC\Auxiliary\Build\vcvars32.bat"
cl /O2 /MT /EHsc /std:c++17 /DUNICODE /D_UNICODE /LD patch\patch.cpp patch\lib\InlineHook.c ^
   patch\lib\LDasm.c patch\lib\Detours-4.0.1\lib.X86\detours.lib user32.lib ^
   /Ipatch /Ipatch\lib /Fepatch.dll
```

## 工具说明

### 整稿校对与批量构建

正式译稿在 `localization/中日对照.jsonl`，原文在 `alltexts/ja`，对应中文在 `alltexts/zh`。共 886 个脚本（其中 18 个无文本）、95,559 行。修改译稿的 `zh` 字段，保持原文、行号及控制标签，完成核对后把 `pending` 设为 `false`。

```bat
python tools\localize_text.py prepare --localization localization --out work\localization_zh
python tools\build_all.py --install
python tools\package_release.py --version 1.3.2
python tools\verify_release.py
```

默认构建直接采用已校订的整稿，正文与数字使用霞鹜文楷。工具统一编码打包，并将全部脚本解包回读，与整稿逐行比较后安装。构建环境仍需要原游戏素材、字库生成器和 `work/extract`、`work/ref` 的原始资源；仓库和发行包不包含完整游戏。

如需重新从游戏提取一份独立对照稿：

```bat
python tools\localize_text.py extract --chinese alltexts\zh --out work\new_localization
```

本次逐条核对的是此前剩余的机翻标记和漏译条目；官方中文主体同时经过全稿格式、术语、残留、动态变量检查，不表示 95,559 行都重新翻译或全部路线实玩。结果见 `localization/verification.json`。

### 构建工具

| 工具 | 用途 |
| --- | --- |
| `tools/cpk.py` | CPK（UTF 表）解析、列出、解包 |
| `tools/build_cpk.py` | 以原版 CPK 的 ID 表为参照重新打包 |
| `tools/prepare_text.py` | 清理机翻标记、统一术语、输出最终文本 |
| `tools/make_charset.py` | 按字频生成字体 charset（前 640 字保留原版） |
| `tools/make_font.py` | 全部普通字符使用正文字体，仅保留游戏专用私用字形 |
| `tools/localize_text.py` | 从原版提取日文，生成整份中日对照译稿，验证译文行号和控制标签 |
| `tools/find_text.py` / `detect_bands.py` / `gridview.py` | UI 图片文字定位 |
| `tools/ui_edit.py` | 按 JSON 规格擦除并重绘 UI 文字 |
| `tools/ui_title.py` `ui_menu.py` `ui_config.py` `ui_brand.py` | 各界面汉化与品牌化 |
| `tools/ui_manual.py` | 从原版贴图生成 Steam 键盘鼠标和手柄帮助 |
| `tools/build_all.py` | 全流程构建 |

## 免责声明

本项目仅用于学习与交流，请支持正版。游戏素材版权归 MAGES./5pb. 与发行方所有。
