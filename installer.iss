#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppName=Terminal Server RPA
AppVersion={#AppVersion}
AppPublisher=SrMarinho
DefaultDirName={localappdata}\TerminalServerRPA
DefaultGroupName=Terminal Server RPA
OutputDir=dist
OutputBaseFilename=TerminalServerRPA_Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\TerminalServerRPA.exe
PrivilegesRequired=lowest
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Ícones adicionais:"

[Files]
Source: "dist\TerminalServerRPA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Terminal Server RPA"; Filename: "{app}\TerminalServerRPA.exe"; Parameters: "gui"
Name: "{group}\Desinstalar"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Terminal Server RPA"; Filename: "{app}\TerminalServerRPA.exe"; Parameters: "gui"; Tasks: desktopicon

[Run]
Filename: "{app}\TerminalServerRPA.exe"; Parameters: "gui"; Description: "Iniciar Terminal Server RPA"; Flags: nowait postinstall skipifsilent
