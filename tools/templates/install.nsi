;

;---------------l-----------------
;Include Modern UI
!include "MUI2.nsh"

; The name of the installer
Name "Aceinna Devices Driver"

; Request application privileges for Windows Vista
RequestExecutionLevel admin

; Build Unicode installer
Unicode True

; The default installation directory
InstallDir $PROGRAMFILES\Aceinna\Driver

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\Aceinna_Devices_Driver" "Install_Dir"

Var appExe 

;--------------------------------
;Pages

  ;!insertmacro MUI_PAGE_LICENSE "${NSISDIR}\Docs\Modern UI\License.txt"
  ;!insertmacro MUI_PAGE_COMPONENTS
  ;!insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_INSTFILES

  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink" 
  !insertmacro MUI_PAGE_FINISH

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------

; The stuff to install
Section 'install'
  #TODO: check if there is a running instance
  StrCpy $appExe 'ans-devices.exe'
  
  SetOutPath $INSTDIR
  File "${EXECUTABLE}"
  File "${ELEVATE}"

  WriteRegStr HKLM "Software\Aceinna_Devices_Driver" "Install_Dir" "$INSTDIR"
  WriteUninstaller "uninstall.exe"

  #TODO: run exe after intall finished
SectionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\Aceinna Devices Driver"
  CreateShortcut "$SMPROGRAMS\Aceinna Devices Driver\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Aceinna Devices Driver\Aceinna Devices Driver.lnk" "$INSTDIR\$appExe"

SectionEnd

;--------------------------------

; Uninstaller
Section 'un.install'

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Aceinna_Devices_Driver"

  ; Remove files and uninstaller
  Delete "$INSTDIR\elevate.exe"
  Delete "$INSTDIR\ans-devices.exe"
  Delete "$INSTDIR\uninstall.exe"

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\Aceinna Devices Driver\*.lnk"

  ; Remove directories
  RMDir "$SMPROGRAMS\Aceinna Devices Driver"
  RMDir "$INSTDIR"
  
SectionEnd

;function要写字section之后
Function LaunchLink
    ExecShell "" "$INSTDIR\$appExe"
FunctionEnd