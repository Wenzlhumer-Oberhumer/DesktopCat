; Inno Setup 6 Script fuer Desktop Cat
#ifndef AppVersion
#define AppVersion "2.2.0"
#endif

[Setup]
AppId={{B42E7A91-8D64-4CE2-A9F7-4DF869D62BC4}}
AppName=Desktop Cat
AppVersion={#AppVersion}
AppPublisher=Nairolf
DefaultDirName={localappdata}\Programs\Mochi
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=DesktopCat-Setup-{#AppVersion}
SetupIconFile=..\assets\mochi.ico
UninstallDisplayIcon={app}\DesktopCat.exe
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
Name: "autostart";   Description: "Desktop Cat mit Windows starten"

[InstallDelete]
Type: files; Name: "{app}\Mochi.exe"
Type: files; Name: "{userprograms}\Mochi.lnk"
Type: files; Name: "{userdesktop}\Mochi.lnk"

[Files]
Source: "..\dist\DesktopCat\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\THIRD_PARTY_LICENSES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Desktop Cat"; Filename: "{app}\DesktopCat.exe"
Name: "{userdesktop}\Desktop Cat";  Filename: "{app}\DesktopCat.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; \
  ValueName: "Mochi"; Flags: deletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "Desktop Cat"; ValueData: """{app}\DesktopCat.exe"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\DesktopCat.exe"; Description: "Desktop Cat jetzt starten"; Flags: nowait postinstall skipifsilent
; nach Silent-Update trotzdem neu starten:
Filename: "{app}\DesktopCat.exe"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM DesktopCat.exe /F"; Flags: runhidden; RunOnceId: "KillDesktopCat"
Filename: "taskkill"; Parameters: "/IM Mochi.exe /F"; Flags: runhidden; RunOnceId: "KillMochi"

[Code]
// Auto-Update startet das Setup und beendet Desktop Cat danach: kurz warten, sonst bricht ein
// stilles Setup wegen AppMutex ab. Haengt der Prozess, wird er im Silent-Modus beendet.
function InitializeSetup(): Boolean;
var
  I, ResultCode: Integer;
begin
  I := 0;
  while CheckForMutexes('MochiDesktopPetMutex') and (I < 20) do
  begin
    Sleep(500);
    I := I + 1;
  end;
  if CheckForMutexes('MochiDesktopPetMutex') and WizardSilent then
  begin
    Exec('taskkill.exe', '/IM DesktopCat.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('taskkill.exe', '/IM Mochi.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1000);
  end;
  Result := True;
end;

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
      if MsgBox('Möchten Sie auch die persönlichen Einstellungen und Chat-Protokolle von Desktop Cat (' + AppDataDir + ') löschen?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(AppDataDir, True, True, True);
        Exec('cmdkey.exe', '/delete:Mochi/GeminiApiKey', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
  end;
end;
