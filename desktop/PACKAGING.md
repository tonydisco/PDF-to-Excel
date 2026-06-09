# Đóng gói app desktop (.dmg / .exe)

App = vỏ **Tauri** (React UI) + **Python sidecar** (lõi OCR `bctc`) đóng gói bằng
**PyInstaller**, nhúng vào app qua Tauri `externalBin`. Khi mở app, Tauri tự spawn
sidecar (localhost `127.0.0.1:8756`) và tắt khi thoát. **Không gọi API ngoài.**

## Yêu cầu máy build
- `.venv` ở repo root đã cài deps (`requirements.txt`) + `pyinstaller`.
- Node + `pnpm`, Rust (`rustup`), Tesseract (để dev).

## macOS → `.app` + `.dmg`
```bash
cd desktop
bash build_macos.sh
# -> src-tauri/target/<triple>/release/bundle/dmg/*.dmg
```
Script tự: đóng gói sidecar (`build_sidecar.sh`) → đặt vào `src-tauri/binaries/
bctc-sidecar-<triple>` → `tauri build --target <triple>`. Target khớp **arch của
Python** (xử lý cả Python x86_64 trên Apple Silicon → ra bản x64 chạy Rosetta).

## Windows → `.exe` / `.msi`
```bat
cd desktop
build_windows.bat
:: -> src-tauri\target\release\bundle\
```

## Chỉ đóng gói sidecar (không build app)
```bash
cd desktop && bash build_sidecar.sh
```

## Lưu ý
- **Máy chạy app vẫn cần cài Tesseract một lần** (macOS `brew install tesseract`;
  Windows: bộ UB-Mannheim). **Gói tiếng Việt `vie` đã bundle sẵn** trong sidecar.
- Binary sidecar (~36MB) **bị gitignore** (`src-tauri/binaries/`), build lại khi cần.
- Sidecar onefile khởi động ~vài giây (giải nén); app có trạng thái chờ.
- Chưa ký (codesign/notarize) → macOS lần đầu: chuột phải → Open để bỏ Gatekeeper.
