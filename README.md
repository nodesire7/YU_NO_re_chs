# この世の果てで恋を唄う少女 YU-NO（重制版）简体中文移植

把官方中文版（AI5CHS）的剧本与界面文本移植到 Steam/MAGES 引擎的 YU-NO 重制版上，
并补齐官方中文缺失的部分。当前工程已可一键构建并在实机运行。

* 制作：**A-FEI-**
* 发布/交流：**BBS.GBTGAME.ME**
* 原工程：<https://github.com/nodesire7/YU_NO_re_chs>（HIllya51）

## 当前汉化状态

| 模块 | 状态 |
| --- | --- |
| 剧情文本（886 个 .scx） | ✅ 全中文（官方中文 + 机翻补齐；清理 `JF:` 标记；补翻 zz.scx 等 109 行残留日文） |
| 字体 | ✅ 正文 = 霞鹜文楷（LXGW WenKai）；标题/菜单图 = 思源宋体 |
| 标题菜单 | ✅ 开始游戏 / 设置 / 帮助 / 退出游戏 |
| 游戏内菜单（历史记录/设置/帮助/存档/返回标题/退出） | ✅ |
| 设置界面项目名 / 选项按钮 / 小节标题 | ✅ |
| 设置界面角色名（CV 试听列表） | ✅ 有马拓也/亚由美/美月… 全中文 |
| 帮助 / 操作指南 | ✅ 全中文（子代理完成，含手柄按键表） |
| 操作提示栏（data01） | ✅ 按键标签/徽章/手柄丝印全中文 |
| 图鉴 / 音乐鉴赏（album/album_thum/music） | ✅ 全中文（标题、页签、返回、无数据占位） |
| 开场影片字幕 | ⬜ 英文（在 movie.cpk 内） |
| 窗口标题 / 品牌信息 | ✅ `A-FEI- 汉化  BBS.GBTGAME.ME` |

## 目录结构

```
alltexts/          从各语言版本提取的文本（ja 原文 / zh 译文 / en 英文 / jazh 对照）
work/              构建中间产物（解包、文本、字体、打包结果）
  extract/         从游戏 data/*.cpk 解包出来的原始文件
  text_final/      清理后的最终中文文本
  system_build/    待打包的 system 资源（字体 + 汉化后的 UI 图）
  ui_out/          汉化后的 UI 图片
tools/             构建与汉化工具（见下）
pack/              第三方工具：sc3tools（Rust）、mgsfontgen-dx（C#）、crifilesystem（CRI 官方）
patch/             patch.dll 源码（注入后修改窗口标题、补命令行参数）
dist/              可直接分发的补丁包
```

## 构建

依赖：Python 3 + Pillow/numpy、Rust（cargo）、.NET SDK、MSVC（仅重建 patch.dll 时需要）。

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

| 工具 | 用途 |
| --- | --- |
| `tools/cpk.py` | CPK（UTF 表）解析、列出、解包 |
| `tools/build_cpk.py` | 以原版 CPK 的 ID 表为参照重新打包 |
| `tools/prepare_text.py` | 清理机翻标记、统一术语、输出最终文本 |
| `tools/make_charset.py` | 按字频生成字体 charset（前 640 字保留原版） |
| `tools/make_font.py` | 把生成的字库与原版 ASCII 字形合并为 `font.png`/`font2.png` |
| `tools/find_text.py` / `detect_bands.py` / `gridview.py` | UI 图片文字定位 |
| `tools/ui_edit.py` | 按 JSON 规格擦除并重绘 UI 文字 |
| `tools/ui_title.py` `ui_menu.py` `ui_config.py` `ui_brand.py` | 各界面汉化与品牌化 |
| `tools/build_all.py` | 全流程构建 |

## 免责声明

本项目仅用于学习与交流，请支持正版。游戏素材版权归 MAGES./5pb. 与发行方所有。
