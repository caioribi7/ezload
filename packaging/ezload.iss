; Instalador do EZLOAD para Windows (Inno Setup 6).
; Gerado por packaging\build-windows.ps1 depois do PyInstaller.
; Instala só para o usuário (sem admin), põe o `ezload` no PATH e cria atalho no Menu Iniciar.

#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{2CFA30F3-A3BA-435D-8F92-94CBC8BA3777}
AppName=EZLOAD
AppVersion={#Versao}
AppPublisher=caioribi7
AppPublisherURL=https://github.com/caioribi7/ezload
DefaultDirName={localappdata}\Programs\EZLOAD
DefaultGroupName=EZLOAD
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=EZLOAD-Setup-{#Versao}
Compression=lzma2/max
SolidCompression=yes
ChangesEnvironment=yes
LicenseFile=..\LICENSE
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addpath"; Description: "Adicionar o comando ezload ao PATH (usar no terminal)"; Flags: checkedonce
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; Flags: unchecked

[Files]
Source: "..\dist\ezload\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\EZLOAD"; Filename: "{app}\ezload.exe"
Name: "{group}\Desinstalar EZLOAD"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EZLOAD"; Filename: "{app}\ezload.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Tasks: addpath; Check: PrecisaPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\ezload.exe"; Description: "Abrir o EZLOAD agora"; Flags: postinstall nowait skipifsilent

[Code]
function PrecisaPath(Pasta: string): Boolean;
var
  Atual: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Atual) then
    Atual := '';
  Result := Pos(';' + Uppercase(Pasta) + ';', ';' + Uppercase(Atual) + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Atual, Pasta: string;
  P: Integer;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  Pasta := ExpandConstant('{app}');
  if RegQueryStringValue(HKCU, 'Environment', 'Path', Atual) then
  begin
    P := Pos(';' + Uppercase(Pasta), Uppercase(Atual));
    if P > 0 then
    begin
      Delete(Atual, P, Length(Pasta) + 1);
      RegWriteExpandStringValue(HKCU, 'Environment', 'Path', Atual);
    end;
  end;
end;
