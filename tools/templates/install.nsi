;
;--------------------------------

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

;--------------------------------

; The stuff to install
Section 'install'
  #TODO: check if there is a running instance

  SetOutPath $INSTDIR
  File "${EXECUTABLE}"

  WriteRegStr HKLM "Software\Aceinna_Devices_Driver" "Install_Dir" "$INSTDIR"
  WriteUninstaller "uninstall.exe"

  #TODO: run exe after intall finished
SectionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\Aceinna Devices Driver"
  CreateShortcut "$SMPROGRAMS\Aceinna Devices Driver\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Aceinna Devices Driver\Aceinna Devices Driver.lnk" "$INSTDIR\ans-devices.exe"

SectionEnd

;--------------------------------

; Uninstaller
Section 'un.install'

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Aceinna_Devices_Driver"

  ; Remove files and uninstaller
  Delete $INSTDIR\ans-devices.exe
  Delete $INSTDIR\uninstall.exe

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\Aceinna Devices Driver\*.lnk"

  ; Remove directories
  RMDir "$SMPROGRAMS\Aceinna Devices Driver"
  RMDir "$INSTDIR"
  
SectionEnd