; Inno Setup 6 Script fuer Mochi Desktop Pet
#ifndef AppVersion
#define AppVersion "2.0.0"
#endif

[Setup]
AppId={{B42E7A91-8D64-4CE2-A9F7-4DF869D62BC4}}
AppName=Mochi
AppVersion={#AppVersion}
AppPublisher=Nairolf
DefaultDirName={localappdata}\Programs\Mochi
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Mochi-Setup-{#AppVersion}
SetupIconFile=..\assets\mochi.ico
UninstallDisplayIcon={app}\Mochi.exe
AppMutex=MochiDesktopPetMutex
CloseApplications=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"
Name: "autostart";   Description: "Mochi mit Windows starten"

[Files]
Source: "..\dist\Mochi\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\THIRD_PARTY_LICENSES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Mochi"; Filename: "{app}\Mochi.exe"
Name: "{userdesktop}\Mochi";  Filename: "{app}\Mochi.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "Mochi"; ValueData: """{app}\Mochi.exe"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Mochi.exe"; Description: "Mochi jetzt starten"; Flags: nowait postinstall skipifsilent
; nach Silent-Update trotzdem neu starten:
Filename: "{app}\Mochi.exe"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM Mochi.exe /F"; Flags: runhidden; RunOnceId: "KillMochi"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: String;
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataDir := ExpandConstant('{userappdata}\Mochi');
    if DirExists(AppDataDir) and (not UninstallSilent) then
    begin
      if MsgBox('Möchten Sie auch die persönlichen Einstellungen und Chat-Protokolle von Mochi (' + AppDataDir + ') löschen?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(AppDataDir, True, True, True);
        Exec('cmdkey.exe', '/delete:Mochi/GeminiApiKey', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
  end;
end;
