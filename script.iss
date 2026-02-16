[Setup]
AppName=CrimeScan
AppVersion=1.0
DefaultDirName={pf}\CrimeScan
DefaultGroupName=CrimeScan
OutputDir=.
OutputBaseFilename=CrimeScanSetup
Compression=lzma
SolidCompression=yes
SetupIconFile=CrimeScan\assets\logo.ico

[Files]
Source: "CrimeScan\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Icon"; Flags: unchecked
Name: "installdeps"; Description: "Install Python dependencies"; Flags: unchecked

[Icons]
Name: "{group}\CrimeScan"; Filename: "{app}\CrimeScan.exe"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{commondesktop}\CrimeScan"; Filename: "{app}\CrimeScan.exe"; Tasks: desktopicon; IconFilename: "{app}\assets\app_icon.ico"

[Run]
Filename: "{cmd}"; Parameters: "/C python -m venv ""{app}\venv"""; Flags: runhidden waituntilterminated; Tasks: installdeps

Filename: "{app}\venv\Scripts\pip.exe"; Parameters: "install -r ""{app}\requirements.txt"""; Flags: runhidden waituntilterminated; Tasks: installdeps
