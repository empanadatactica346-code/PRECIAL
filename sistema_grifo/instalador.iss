; Instalador de PRECIAL (Inno Setup 6)
; Compilar:  ISCC.exe instalador.iss   (requiere haber generado antes dist\PRECIAL con PyInstaller)
; Se instala por usuario (sin pedir administrador) en %LOCALAPPDATA%\Programs\PRECIAL,
; una carpeta donde el programa puede guardar sus datos.

#define MiApp "PRECIAL"
#define MiVersion "2.0"
#ifndef Origen
  #define Origen "dist\PRECIAL"
#endif

[Setup]
AppId={{6F1B2C3D-8A4E-4C55-9B21-PRECIAL00002}
AppName={#MiApp}
AppVersion={#MiVersion}
AppVerName={#MiApp} {#MiVersion} — Gestión y optimización de precios para grifo
AppPublisher=Modelos Cuantitativos y de Optimización
DefaultDirName={autopf}\{#MiApp}
DefaultGroupName={#MiApp}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..
OutputBaseFilename=PRECIAL_Instalador_v{#MiVersion}
SetupIconFile=precial.ico
UninstallDisplayIcon={app}\PRECIAL.exe
UninstallDisplayName={#MiApp} {#MiVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#Origen}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LEAME_USUARIOS.txt"; DestDir: "{app}"; DestName: "LEAME.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MiApp}"; Filename: "{app}\PRECIAL.exe"
Name: "{group}\Léame de {#MiApp}"; Filename: "{app}\LEAME.txt"
Name: "{group}\Desinstalar {#MiApp}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MiApp}"; Filename: "{app}\PRECIAL.exe"; Tasks: escritorio

[Run]
Filename: "{app}\PRECIAL.exe"; Description: "Abrir {#MiApp} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Se borran los archivos temporales; los datos del usuario se conservan salvo que elija borrarlos
Type: files; Name: "{app}\datos_salida\.cache_fifo.pkl"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and DirExists(ExpandConstant('{app}\datos_salida')) then
    if MsgBox('¿Desea borrar también sus datos (ventas, compras, configuración y exportaciones)?' + #13#10 +
              'Si responde No, se conservarán para una futura reinstalación.',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{app}'), True, True, True);
end;
