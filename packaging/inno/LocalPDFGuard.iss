#define MyAppName "Local PDF Guard"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Local PDF Guard"
#define MyAppExeName "LocalPDFGuard.exe"

[Setup]
AppId={{9D95846C-D7C2-4C9B-982B-LocalPDFGuard}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\LocalPDFGuard
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=LocalPDFGuard-0.1.0-setup-win64
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："; Flags: unchecked

[Files]
Source: "..\..\dist\LocalPDFGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Local PDF Guard"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Local PDF Guard"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Local PDF Guard"; Flags: nowait postinstall skipifsilent
