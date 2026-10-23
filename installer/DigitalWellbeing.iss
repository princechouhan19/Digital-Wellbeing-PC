; Inno Setup Script for Digital Wellbeing
; Ref: https://jrsoftware.org/isinfo.php

[Setup]
SourceDir=..
AppId=Digital Wellbeing
AppName=Digital Wellbeing
AppVersion={#MyAppVersion}
AppPublisher=Prince Chouhan
AppPublisherURL=https://digitalwellbeing.vercel.app
AppSupportURL=https://digitalwellbeing.vercel.app
AppUpdatesURL=https://digitalwellbeing.vercel.app
DefaultDirName={autopf}\DigitalWellbeing
DisableDirPage=yes
DefaultGroupName=Digital Wellbeing
DisableProgramGroupPage=yes
UsePreviousGroup=no
OutputDir=dist
OutputBaseFilename=DigitalWellbeingSetup
SetupIconFile=assets\icons\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=Prince Chouhan
VersionInfoDescription=Digital Wellbeing Setup Installer
VersionInfoCopyright=Copyright (C) 2026 Prince Chouhan. All rights reserved.
VersionInfoProductName=Digital Wellbeing
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes
UninstallDisplayIcon={app}\DigitalWellbeing.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start Digital Wellbeing automatically when Windows boots"; GroupDescription: "Startup:"; Flags: unchecked

[InstallDelete]
; Clean up legacy shortcuts from v2.5.2 and earlier
Type: files; Name: "{userprograms}\Digital Wellbeing\Digital Wellbeing.lnk"
Type: dirifempty; Name: "{userprograms}\Digital Wellbeing"
Type: files; Name: "{commonprograms}\Digital Wellbeing\Digital Wellbeing.lnk"
Type: dirifempty; Name: "{commonprograms}\Digital Wellbeing"
Type: files; Name: "{userdesktop}\Digital Wellbeing.lnk"
Type: files; Name: "{commondesktop}\Digital Wellbeing.lnk"
Type: files; Name: "{userstartup}\Digital Wellbeing.lnk"
Type: files; Name: "{commonstartup}\Digital Wellbeing.lnk"
; Clean up previous NYW shortcuts
Type: files; Name: "{userprograms}\NYW\NYW.lnk"
Type: dirifempty; Name: "{userprograms}\NYW"
Type: files; Name: "{userdesktop}\NYW.lnk"
Type: files; Name: "{userstartup}\NYW.lnk"

[Files]
Source: "dist\DigitalWellbeing\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Digital Wellbeing"; Filename: "{app}\DigitalWellbeing.exe"; AppUserModelID: "PrinceChouhan.DigitalWellbeing.App"
Name: "{userdesktop}\Digital Wellbeing"; Filename: "{app}\DigitalWellbeing.exe"; Tasks: desktopicon; AppUserModelID: "PrinceChouhan.DigitalWellbeing.App"
Name: "{userstartup}\Digital Wellbeing"; Filename: "{app}\DigitalWellbeing.exe"; Parameters: "--background"; Tasks: startup; AppUserModelID: "PrinceChouhan.DigitalWellbeing.App"

[Registry]
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\PrinceChouhan.DigitalWellbeing.App"; ValueType: string; ValueName: "DisplayName"; ValueData: "Digital Wellbeing"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\PrinceChouhan.DigitalWellbeing.App"; ValueType: string; ValueName: "IconUri"; ValueData: "{app}\assets\icons\app_icon.ico"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\PrinceChouhan.DigitalWellbeing.App"; ValueType: dword; ValueName: "ShowInSettings"; ValueData: 1; Flags: uninsdeletekey

[Run]
Filename: "{app}\DigitalWellbeing.exe"; Description: "{cm:LaunchProgram,Digital Wellbeing}"; Flags: nowait postinstall skipifsilent
