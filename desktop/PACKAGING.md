# Đóng gói app desktop (.dmg / .exe)

App = vỏ **Tauri** (React UI) + **Python sidecar** (lõi OCR `bctc`) đóng gói bằng
**PyInstaller**, nhúng vào app qua Tauri `externalBin`. Khi mở app, Tauri tự spawn
sidecar (localhost `127.0.0.1:8756`) và tắt khi thoát. **OCR + tỉ số 100% local.**
Tính năng "Diễn giải bằng AI" là **tuỳ chọn (BYOK)**: chỉ khi người dùng bật và
xác nhận, **chỉ các tỉ số tổng hợp** mới được gửi tới nhà cung cấp họ chọn
(Claude/Gemini) — không bao giờ gửi PDF/bản gốc.

## Yêu cầu máy build
- `.venv` ở repo root đã cài deps (`requirements.txt`) + `pyinstaller`.
- Node + `pnpm`, Rust (`rustup`).
- **Tesseract** + (macOS) **dylibbundler** để nhúng engine: `brew install tesseract dylibbundler`.

## Đóng gói TRỌN GÓI Tesseract (app self-contained — KHÔNG cần cài Tesseract)
`build_sidecar.sh` / `build_windows.ps1` tự **nhúng cả engine Tesseract** vào
sidecar nếu thấy thư mục `desktop/tessbundle/`. Tạo nó trước khi build:
```bash
# macOS: gom tesseract + mọi .dylib (dylibbundler, rpath @executable_path) + tessdata
bash desktop/bundle_tesseract.sh
# Windows: copy tesseract.exe + *.dll + tessdata (cần đã cài Tesseract / choco install tesseract)
pwsh desktop/bundle_tesseract.ps1
```
`ocr.locate_tesseract()` tự tìm bản nhúng trong gói trước (đã kiểm chứng: sidecar
đông lạnh báo `tesseract` nằm trong `_MEI…/tesseract/bin/tesseract`, `has_vie:true`).
Không tạo `tessbundle/` → build vẫn chạy nhưng **dùng Tesseract hệ thống** (chỉ nhúng `vie`).

## macOS → `.app` + `.dmg`
```bash
cd desktop
bash bundle_tesseract.sh     # (tuỳ chọn) nhúng Tesseract
bash build_macos.sh
# -> src-tauri/target/<triple>/release/bundle/dmg/*.dmg
```
Target khớp **arch của Python** (Intel build trên Mac Intel, arm64 build trên Apple Silicon).

## Windows → `.msi` / `.exe`
```powershell
cd desktop
pwsh bundle_tesseract.ps1     # (tuỳ chọn) nhúng Tesseract
pwsh build_windows.ps1
# -> src-tauri\target\release\bundle\  (msi\ + nsis\)
```
(`build_windows.bat` cũ vẫn còn cho bản KHÔNG nhúng Tesseract.)

## Build tự động bằng GitHub Actions (khuyến nghị ra bản phát hành)
`.github/workflows/build.yml` build cả 3 nền (macOS Intel + Apple Silicon, Windows),
tự cài + nhúng Tesseract, rồi tải artifact. **Push tag `v*` để ra Release đính kèm:**
```bash
git tag v1.0.0 && git push origin v1.0.0
```
→ Vào tab **Actions** xem tiến trình; file cài ở **Artifacts** mỗi run, và ở **Releases** nếu push tag.

## Chỉ đóng gói sidecar (không build app)
```bash
cd desktop && bash build_sidecar.sh
```

## Tính năng AI (BYOK) khi đóng gói — BẮT BUỘC smoke-test bản đóng băng
SDK `anthropic` + `google-genai` + `keyring` được `build_sidecar.sh` bundle qua
`--collect-all`/`--copy-metadata` (best-effort, build vẫn chạy nếu thiếu). Nhưng
3 thứ này hay vỡ trong binary PyInstaller, **chỉ lộ khi đóng gói** — phải test:
1. `keyring` trong binary đóng băng: ACL keychain macOS gắn với chữ ký nhị phân →
   bản chưa ký/đổi sau mỗi rebuild có thể hỏi lại quyền hoặc không lưu được.
2. `google-genai`/`keyring` thiếu submodule/metadata → `import` lỗi runtime.

→ Sau khi build, chạy **smoke-test** trên binary đóng băng (không dùng venv):
```bash
./dist_sidecar/bctc-sidecar --port 8799 &      # hoặc binary trong .app
curl -s localhost:8799/llm/status               # sdk:true cho cả 2 provider?
# đặt key qua biến môi trường (KHÔNG phụ thuộc keychain) rồi gọi /analyze:
ANTHROPIC_API_KEY=sk-... ./dist_sidecar/bctc-sidecar --port 8799
```
**Thiết kế đã tách nguồn key** (request body → env var → keychain) nên nếu keychain
đóng băng trục trặc, app vẫn truyền key qua env/body — tính năng không vỡ.

## Lưu ý
- **Nếu đã nhúng Tesseract** (có `tessbundle/`): máy người dùng **KHÔNG cần cài gì** —
  engine + tessdata (vie/eng/osd) nằm trong app. Sidecar ~64MB.
- Binary sidecar **bị gitignore** (`src-tauri/binaries/`), build lại khi cần.
- **Khởi động lần đầu chậm hơn** (onefile giải nén + macOS verify chữ ký các .dylib
  nhúng); các lần sau nhanh hơn. App có trạng thái chờ tới khi `/health` OK.
- **Ký số (khuyến nghị cho phát hành):**
  - macOS: chưa ký → lần đầu **chuột phải → Open**; nếu tải qua mạng có thể cần
    `xattr -dr com.apple.quarantine "BCTC PDF to Excel.app"`. Để mượt: thêm Apple
    Developer ID + bật `signingIdentity`/notarize trong tauri (qua secrets CI:
    `APPLE_CERTIFICATE`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`).
    ‼️ **Notarize KHÔNG dùng được với Tesseract nhúng-trong-onefile**: binary nằm
    trong khối dữ liệu PyInstaller và chỉ giải nén lúc chạy → notary không thấy,
    hardened-runtime có thể chặn. Muốn notarize: **chuyển Tesseract sang Tauri
    `resources`** (Contents/Resources/, ký cùng app) — đồng thời bỏ luôn việc
    giải nén 64MB mỗi lần mở (khởi động nhanh hơn). (Bản hiện tại: unsigned + right-click Open.)
  - Windows: chưa ký → SmartScreen cảnh báo "Unknown publisher" (bấm More info → Run anyway).
    Ký bằng cert Authenticode để bỏ cảnh báo.
- **Smoke-test bản đóng băng** (vẫn nên chạy): `./dist_sidecar/bctc-sidecar --port 8799`
  rồi `curl localhost:8799/health` → kỳ vọng `tesseract` trỏ vào `_MEI…/tesseract`,
  `has_vie:true`; và `curl .../llm/status` → `sdk:true` cho cả 2 provider.
- **Windows chưa được test thật** (viết theo đúng quy ước) — nên chạy thử workflow 1 lần.
