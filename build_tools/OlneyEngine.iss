#define MyAppName "Olney Engine"
#define MyAppVersion "1.8.9"
#define MyAppExeName "Olney Engine.exe"

[Setup]
AppId={{1F949036-0F5B-4B09-9BE5-B6F8E9A4F73C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Sébastien
LicenseFile=..\LICENSE
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=Olney_Engine_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\olney_windows_v3.ico
WizardImageFile=..\assets\installer_star_large.bmp
WizardSmallImageFile=..\assets\installer_star_small.bmp
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\_internal\assets\olney_windows_v3.ico
VersionInfoVersion=1.8.9.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
Source: "..\dist\Olney Engine\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\olney_windows_v3.ico"; IconIndex: 0
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\olney_windows_v3.ico"; IconIndex: 0; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  { Warm parchment identity shared with Olney's light mode. }
  WizardForm.Color := $00A3D8F4;
  WizardForm.WelcomePage.Color := $00A3D8F4;
  WizardForm.FinishedPage.Color := $00A3D8F4;
  WizardForm.MainPanel.Color := $00D0F0FF;
  WizardForm.InnerPage.Color := $00D0F0FF;
end;
