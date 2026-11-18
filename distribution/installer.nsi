Unicode true
ManifestDPIAware true
RequestExecutionLevel user
Name "YU-NO 简体中文补丁"
OutFile "${OUTPUT}"
VIProductVersion "${WINDOWS_VERSION}"
VIAddVersionKey /LANG=2052 "ProductName" "GBTGames · YU-NO 简体中文补丁"
VIAddVersionKey /LANG=2052 "CompanyName" "GBTGames 乐赏游戏社区"
VIAddVersionKey /LANG=2052 "FileDescription" "YU-NO 汉化补丁安装与还原"
VIAddVersionKey /LANG=2052 "FileVersion" "${PATCH_VERSION}"
VIAddVersionKey /LANG=2052 "ProductVersion" "${PATCH_VERSION}"
VIAddVersionKey /LANG=2052 "LegalCopyright" "A-FEI- 汉化 · BBS.GBTGAME.ME"
BrandingText "GBTGames 乐赏游戏社区 · BBS.GBTGAME.ME"
SetCompressor zlib
ShowInstDetails show
!include MUI2.nsh
!include nsDialogs.nsh
!include FileFunc.nsh
!include LogicLib.nsh
!define MUI_ICON "${ASSETS}\gbt.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${ASSETS}\gbt-header.bmp"
!define MUI_ABORTWARNING
Var Mode
Var RestoreChoice

Page custom ChooseMode RememberMode
!define MUI_DIRECTORYPAGE_TEXT_TOP "请选择 Steam 版 YU-NO 的游戏目录，目录内应包含 Game.exe。"
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE CheckGame
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Function .onInit
  StrCpy $Mode "Install"
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/RESTORE" $1
  ${IfNot} ${Errors}
    StrCpy $Mode "Uninstall"
  ${EndIf}
  ${If} $INSTDIR == ""
    SetRegView 64
    ReadRegStr $INSTDIR HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 912450" "InstallLocation"
    ${IfNot} ${FileExists} "$INSTDIR\Game.exe"
      SetRegView 32
      ReadRegStr $INSTDIR HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 912450" "InstallLocation"
    ${EndIf}
    ${IfNot} ${FileExists} "$INSTDIR\Game.exe"
      ReadRegStr $0 HKCU "Software\Valve\Steam" "SteamPath"
      ${If} $0 != ""
        StrCpy $INSTDIR "$0\steamapps\common\YU-NO"
      ${EndIf}
    ${EndIf}
  ${EndIf}
FunctionEnd

Function ChooseMode
  !insertmacro MUI_HEADER_TEXT "YU-NO 简体中文补丁" "A-FEI- 汉化  ·  ${PATCH_VERSION}"
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  ${NSD_CreateRadioButton} 0 10u 96% 17u "安装或更新简体中文补丁"
  Pop $1
  ${NSD_CreateLabel} 12u 30u 92% 27u "安装剧情、界面和中文字体。首次安装会将原文件备份到游戏目录的 _backup_cht。"
  Pop $0
  ${NSD_CreateRadioButton} 0 65u 96% 17u "卸载补丁并恢复原文件"
  Pop $RestoreChoice
  ${NSD_CreateLabel} 12u 85u 92% 27u "从备份恢复游戏文件。重装前后的游戏存档均可保留。"
  Pop $0
  ${NSD_CreateLink} 0 124u 98% 13u "GBTGames 乐赏游戏社区  ·  汉化反馈与交流"
  Pop $0
  SetCtlColors $0 0x983D5D transparent
  ${NSD_OnClick} $0 OpenForum
  ${If} $Mode == "Uninstall"
    ${NSD_Check} $RestoreChoice
  ${Else}
    ${NSD_Check} $1
  ${EndIf}
  nsDialogs::Show
FunctionEnd

Function OpenForum
  Pop $0
  ExecShell "open" "https://bbs.gbtgame.me/"
FunctionEnd

Function RememberMode
  ${NSD_GetState} $RestoreChoice $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $Mode "Uninstall"
  ${Else}
    StrCpy $Mode "Install"
  ${EndIf}
FunctionEnd

Function CheckGame
  ${IfNot} ${FileExists} "$INSTDIR\Game.exe"
    MessageBox MB_ICONSTOP|MB_OK "这个文件夹里没有 Game.exe。请选择 YU-NO 的游戏目录。" /SD IDOK
    Abort
  ${EndIf}
FunctionEnd

Section
  SetErrorLevel 1
  ${IfNot} ${FileExists} "$INSTDIR\Game.exe"
    DetailPrint "游戏目录无效。"
    Abort
  ${EndIf}
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "${STAGING}\patch.ps1"
  ${If} $Mode == "Install"
    File "${STAGING}\manifest.json"
    SetOutPath "$PLUGINSDIR\files"
    File /r "${STAGING}\files\*"
    DetailPrint "正在核对补丁文件并安装……"
  ${Else}
    DetailPrint "正在恢复安装前的游戏文件……"
  ${EndIf}
  nsExec::ExecToStack '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\patch.ps1" -Mode $Mode -Game "$INSTDIR"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    DetailPrint "$1"
    MessageBox MB_ICONSTOP|MB_OK "操作失败。请确认游戏已退出、目录可写，再查看安装详情。$\r$\n$1" /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
  DetailPrint "操作完成。"
  SetErrorLevel 0
SectionEnd
