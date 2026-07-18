#ifndef SourceRoot
  #error SourceRoot must be defined by the build script.
#endif
#ifndef OutputDir
  #error OutputDir must be defined by the build script.
#endif
#ifndef AppVersion
  #define AppVersion "0.3.5"
#endif

#define AppName "RERCie"
#define AppExe "RERCie.exe"
#define AppUrl "https://henkelpress.github.io/rerc-grant-finder/"

[Setup]
AppId={{E07265FC-1C63-4B51-99BB-EFA80D9497B8}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=henkelpress
AppPublisherURL={#AppUrl}
AppSupportURL=https://github.com/henkelpress/rerc-grant-finder/issues
AppUpdatesURL=https://github.com/henkelpress/rerc-grant-finder/releases/latest
DefaultDirName={localappdata}\Programs\RERCie
DefaultGroupName=RERCie
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableReadyPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=RERCie-Setup
SetupIconFile=..\..\assets\rercie.ico
WizardImageFile=rercie-wizard.bmp
InfoBeforeFile=INSTALLER_NOTICE.txt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName=RERCie
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany=henkelpress
VersionInfoDescription=RERCie local grant-writing guide
VersionInfoProductName=RERCie
AppMutex=Local\RERCie-0.3

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\RERCie"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Comment: "Use a funding option and project notes to make a first draft"
Name: "{autodesktop}\RERCie"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Use a funding option and project notes to make a first draft"
Name: "{autoprograms}\RERCie website"; Filename: "{#AppUrl}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Meet RERCie"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--stop"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; RunOnceId: "StopRERCie"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\runtime\logs"
Type: filesandordirs; Name: "{app}\runtime\pids"
Type: files; Name: "{app}\*.partial"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if (CurStep = ssInstall) and FileExists(ExpandConstant('{app}\RERCie.exe')) then
    Exec(ExpandConstant('{app}\RERCie.exe'), '--stop', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;