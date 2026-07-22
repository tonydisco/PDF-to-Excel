; Bộ cài Windows cho BCTC PDF -> Excel
; Dựng bằng: iscc /DAppVersion=<phiên bản> installer\BCTC_Setup.iss
; (CI đọc <phiên bản> từ version.py — xem .github/workflows/build.yml;
;  thiếu /DAppVersion thì ISCC báo lỗi ngay, không lặng lẽ dựng bản vô danh)
;
; Vì sao cần bộ cài: bản onedir giải nén MỘT lần lúc cài, các lần mở sau chạy
; thẳng (~2 giây). Bản onefile cũ giải nén lại toàn bộ payload ra %TEMP% mỗi
; lần khởi động - trên Win10 ổ HDD mất 30-90 giây MỖI LẦN.
;
; Các chuỗi hiển thị trong [Tasks]/[Icons]/[Run] dùng tiếng Việt KHÔNG dấu
; có chủ đích: an toàn tuyệt đối qua mọi biến thể codepage/phiên bản Inno.

#define AppName "BCTC PDF to Excel"
#define AppExe "BCTC_PDF_to_Excel.exe"
#define AppPublisher "BTG"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\BCTC_PDF_to_Excel
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=BCTC_PDF_to_Excel-Setup
Compression=lzma2/max
SolidCompression=yes
; Cài cho riêng người dùng nếu không có quyền admin - máy văn phòng thường
; bị khoá quyền cài đặt.
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}

; Chưa kèm bản dịch tiếng Việt chính thức (.isl) nên phần khung của bộ cài
; (Next/Install/Finish...) tạm hiển thị tiếng Anh — bản thân ứng dụng vẫn
; hoàn toàn tiếng Việt. Khi Inno có Vietnamese.isl chính thức: đổi
; MessagesFile bên dưới là xong.
[Languages]
Name: "default"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tao bieu tuong tren man hinh nen"; \
    GroupDescription: "Tuy chon:"

[Files]
Source: "..\dist\BCTC_PDF_to_Excel\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Go cai dat {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Mo ung dung ngay"; \
    Flags: nowait postinstall skipifsilent
