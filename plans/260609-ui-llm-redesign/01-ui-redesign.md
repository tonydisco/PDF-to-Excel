# Thiết kế #3 — Redesign UI desktop (style AI hiện đại, review từng PDF)

> Ngày 2026-06-09 · Tài liệu THIẾT KẾ (chưa code). Quyết định techstack ở §2 cần anh chốt.

## 1. Mục tiêu & ràng buộc
- **Style AI hiện đại, UI/UX best** (light/dark, tinh gọn, có chuyển động nhẹ).
- **Review từng file PDF**: xem PDF gốc cạnh bảng số đã bóc, **sửa ô**, nhảy tới ô tô cam, xem trạng thái cân đối — đây là điểm tích hợp tự nhiên cho **flag của B-A3** và **quy trình sửa ground-truth**.
- **Giữ lõi OCR Python** (PyMuPDF + Tesseract) — **dữ liệu scan KHÔNG rời máy**.
- Cross-platform **macOS + Windows**, đóng gói được (`.app`/`.dmg`/`.exe`).
- Tận dụng được các skill UI/UX (design-taste-frontend, ui-ux-pro-max, shadcn) ở **phase build**.

## 2. Đề xuất techstack (cần chốt)

### ⭐ Khuyến nghị: **Tauri 2 + React/Vite + TypeScript + Tailwind + shadcn/ui**, lõi OCR Python làm **sidecar**

| Lớp | Chọn | Lý do |
|---|---|---|
| Vỏ desktap | **Tauri 2** (Rust) | Nhẹ (bundle ~3–10MB vs Electron ~100MB+), bảo mật, native `.app/.dmg/.exe`, cross-platform. WebView hệ điều hành. |
| Frontend | **React + Vite + TypeScript** | Hệ sinh thái lớn nhất, hợp với mọi skill UI/UX. Vite build nhanh. |
| Design system | **Tailwind + shadcn/ui** | Đúng "style AI hiện đại"; **shadcn MCP** + skill taste/ui-ux-pro-max áp dụng trực tiếp. |
| Xem PDF | **pdf.js (`react-pdf`)** | Render PDF trong web để review cạnh bảng số; highlight vùng, nhảy trang. |
| Lõi xử lý | **giữ nguyên `bctc/`** (Python) chạy như **sidecar** | Không vứt bỏ toàn bộ OCR/parser/excel đã làm. Đóng gói bằng PyInstaller, Tauri gọi qua sidecar (stdin/stdout JSON) hoặc local FastAPI 127.0.0.1. |
| LLM (phân tích #4) | **Vercel AI SDK** (xem doc #4) | Gọi cloud cho phân tích, chỉ gửi tỉ số tổng hợp. |

**Kiến trúc:** `React UI ⇄ Tauri (IPC) ⇄ Python sidecar (bctc engine)`. OCR chạy local trong sidecar; UI chỉ hiển thị + sửa. Phân tích LLM (#4) gọi cloud từ sidecar/UI, **chỉ với tỉ số** (không PDF).

### Phương án đã cân nhắc
| Stack | Ưu | Vì sao KHÔNG chọn làm mặc định |
|---|---|---|
| **Electron** + React | Quen thuộc, nhiều ví dụ | Nặng (~100MB+), tốn RAM; Tauri làm điều tương tự gọn hơn. |
| **pywebview** + FastAPI + React | Thuần Python đóng gói (PyInstaller), ít stack | WebView kém nhất quán, thiếu native polish; vẫn cần build frontend. Tốt nếu muốn TỐI GIẢN stack. |
| **Next.js full web (deploy Vercel)** | Skill Vercel/AI SDK mạnh nhất | Đây là tool **nhạy cảm, ưu tiên local** — đưa cả pipeline lên web đụng ràng buộc "dữ liệu không rời máy". Chỉ hợp nếu sau này làm bản SaaS riêng. |
| **Flutter desktop** | UI mượt, 1 codebase | Tách rời hệ React/shadcn + phải cầu nối Python OCR; skill UI/UX không áp dụng. |
| **Giữ Tkinter** | Ít việc nhất | Không đạt "style AI hiện đại", render PDF để review rất khó. Trần thấp. |

> Nếu ưu tiên **ít rủi ro build/đóng gói nhất** → chọn **pywebview + FastAPI + React/shadcn** (thuần Python đóng gói, vẫn dùng được toàn bộ skill UI/UX). Nếu ưu tiên **native polish + nhẹ** → **Tauri 2**. Mình nghiêng về **Tauri 2**.

## 3. Màn hình & luồng chính
1. **Trang chủ / Hàng đợi file** — kéo-thả PDF (tối đa 150), trạng thái từng file, nút Chuyển đổi, chọn thư mục lưu, light/dark.
2. **Màn hình Review (mới — trọng tâm):**
   - Trái: **PDF viewer** (pdf.js) — trang chứa báo cáo, zoom, highlight vùng số.
   - Phải: **bảng chỉ tiêu** đã bóc (3 tab CDKT/KQ/LCTT, chỉ hiện tab có dữ liệu — khớp #2), **ô tô cam** = nghi ngờ/lệch, **panel cân đối** (270=440…) xanh/đỏ.
   - Tương tác: click ô → nhảy tới vùng tương ứng trên PDF; **sửa ô inline**; nút **"đọc lại ô"** (re-OCR, hạ tầng B-A3); badge "đã sửa tay".
   - Đây cũng là nơi **sửa ground-truth** cho benchmark (xuất `bench/truth/*.json`).
3. **Tiến độ chuyển đổi** — đồng hồ tổng + từng file, log, tạm dừng/dừng (giữ tính năng hiện có).
4. **Phân tích (#4)** — sau khi có số: nút "Phân tích tài chính / Đánh giá rủi ro" → gọi LLM (chỉ gửi tỉ số), hiển thị nhận định + cảnh báo, nêu rõ "đã gửi gì lên cloud".
5. **Xuất** — Excel (giữ `excel_writer`), kèm tuỳ chọn xuất báo cáo phân tích.

## 4. Ngôn ngữ thiết kế
- Kế thừa bảng màu Coolors hiện có (f4f1de/e07a5f/3d405b/81b29a/f2cc8f) làm accent, nâng lên hệ token shadcn (radius, shadow mềm, typography rõ). Dark mode mặc định (đúng v1.3.0).
- "AI hiện đại": khoảng trắng rộng, motion tinh tế, trạng thái rõ (skeleton/streaming khi phân tích), micro-interaction.
- **Phase build sẽ chạy skill `design-taste-frontend` + `ui-ux-pro-max` + shadcn MCP** để dựng giao diện thật (không dùng template lộ liễu).

## 5. Lộ trình & đóng gói
- **P0:** dựng khung Tauri + React/shadcn, sidecar Python (bctc), luồng chuyển đổi cơ bản đạt parity với app Tkinter.
- **P1:** màn hình Review PDF (pdf.js + bảng + sửa ô + re-OCR).
- **P2:** tích hợp #4 (phân tích).
- Đóng gói: Tauri bundler → `.dmg`/`.app` (macOS), `.exe`/`.msi` (Windows); sidecar Python qua PyInstaller. Giữ `cli.py` cho power user.
- **Di trú:** lõi `bctc/` không đổi; app Tkinter giữ song song tới khi bản mới đạt parity rồi mới deprecate.

## 6. Rủi ro
- Đóng gói Python sidecar trong Tauri cần cấu hình (PyInstaller + Tauri sidecar/resource). → POC sớm phần này.
- Tesseract vẫn là phụ thuộc ngoài (như hiện tại) — bundle hoặc hướng dẫn cài.
- Học Tauri/Rust toolchain (chỉ phần vỏ; logic vẫn JS+Python).
