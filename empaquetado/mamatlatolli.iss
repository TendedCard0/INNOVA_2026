; Instalador de Mamatlatolli (Inno Setup 6).
; Desde la raiz del repositorio, en Windows:
;   python empaquetado\construir.py
; Instalacion para toda la maquina (Program Files, pide administrador):
;   python empaquetado\construir.py --maquina

#ifndef MyAppVersion
#define MyAppVersion "0.5.0"
#endif
#ifndef MyVersionInfo
#define MyVersionInfo "0.5.0.0"
#endif

#define MyAppName "Mamatlatolli"
#define MyAppPublisher "Instituto Tecnológico de San Juan del Río"
#define MyAppExeName "Mamatlatolli.exe"

[Setup]
AppId={{B7E4A1C8-6D2F-4A91-8E35-1C0F9A2D4E67}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Mamatlatolli-Setup
SetupIconFile=..\assets\icono.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoDescription=Instalador de Mamatlatolli
VersionInfoProductName=Mamatlatolli
VersionInfoVersion={#MyVersionInfo}
MinVersion=10.0
InfoBeforeFile=aviso-instalacion.txt
#ifdef InstalacionDeMaquina
PrivilegesRequired=admin
DefaultDirName={autopf}\{#MyAppName}
#else
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#MyAppName}
#endif

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "..\dist\Mamatlatolli\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icono.ico"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icono.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Mamatlatolli"; Flags: nowait postinstall skipifsilent
