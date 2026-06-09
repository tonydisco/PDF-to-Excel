# Kết quả & nhật ký — cải thiện hiệu suất & độ chính xác

> Ghi số trước/sau cho mỗi thay đổi. Dữ liệu: `sample data/` (44 PDF BCTC thật).

## Đã làm

### ✅ A-P1 · Sửa bug định vị trang lặp lại (2026-06-09)
- `locate_pages()` được hoist ra khỏi vòng lặp DPI trong `extract_consensus()`.
- **Kiểm chứng:** mock đếm → `locate_pages` chạy **1 lần** thay vì = số DPI (trước: 2× thường, 3× HQ).
- Tác động: bỏ 1–2 lượt quét dải đầu *toàn bộ trang*/file. Không đổi kết quả định vị (locate dùng scan_dpi=135 cố định, độc lập DPI render).

### ✅ B-A0 · Benchmark + scorer (2026-06-09)
- `bench/score.py`: đo proxy KHÔNG cần ground-truth (coverage, balance-pass, conflicts, time) + cell-accuracy nếu có `bench/truth/*.json`.
- `bench/README.md`: định dạng ground-truth + quy trình tạo bán tự động.

## Baseline (subset đại diện — thiên về ca khó)

`bench/score.py "sample data" --filter 23 35 12` → `bench/results-baseline-subset.md`

| File | CDKT | KQ | LC | Balance | Conflicts | Time |
|---|---|---|---|---|---|---|
| 12 PLAZA (vi) | 54 | 17 | 25 | **2/2 ✓** | 8 | 6.1s |
| 12 PLAZA (en) | 0 | 0 | 0 | 0/0 ⚠ | 0 | 4.7s |
| 23 Căn hộ & VP Sài Gòn | 24 | 13 | **0** | 0/0 ⚠ | 8 | 4.5s |
| 35 NH Phương Đông (HN) | 0 | 0 | 0 | 0/0 ⚠ | 0 | 13.4s |
| 35 NH Phương Đông (riêng) | 0 | 0 | 0 | 0/0 ⚠ | 0 | 12.9s |

→ Coverage TB 1.0/3 · Balance-pass 1/5 (subset CỐ TÌNH chọn ca khó).

### 3 nhóm lỗi lớn (đã xác nhận trên dữ liệu thật)
1. **Báo cáo tiếng Anh** (`(en)`): locator dùng pattern tiếng Việt → 0/3. → bước B-A4 (nhận diện biến thể + tiêu đề tiếng Anh).
2. **Mẫu ngân hàng/TCTD** (`35_NH...`): khung khác T200 → 0/3, lại còn chậm hơn (~13s). → B-A4 (khung riêng cho TCTD).
3. **File 23 (T200 vi):** thiếu **LCTT** + **balance 0/0** (không đủ chỉ tiêu tổng 270/440 để kiểm) dù CDKT có 24 dòng → lỗ hổng locate/extract cần điều tra (B-A3 + locate).

## ⭐ BASELINE đầy đủ — 44 file (`bench/results-baseline-full.md`)

- Chạy được **44/44**, ~**7.2s/file** (toàn corpus ~5 phút).
- **Coverage:** 3/3 = **32 file** · 2/3 = 7 · 1/3 = 1 · 0/3 = **4** (Anh×2 + NH×2). TB **2.52/3**.
- **Balance-pass:** PASS đủ = **20** · lệch một phần = 14 · 0/0 thiếu tổng = **10**.
- **Ô nghi ngờ:** 300 tổng.

→ Mục tiêu cải thiện rõ ràng: **24/44 file chưa "sạch" cân đối** (14 lệch do lỗi đọc số + 10 thiếu chỉ tiêu tổng), 12 file < 3/3 coverage.

### Nhóm để tấn công theo hạng mục
- **B-A4 (coverage):** 4 file 0/3 = tiếng Anh (12en,13en) + ngân hàng (35×2); + ~8 file 2/3 thiếu 1 báo cáo (thường LCTT).
- **B-A1 + B-A3 (balance):** 14 file lệch một phần = lỗi đọc số phá cân đối → đo bằng balance-pass.
- **Điều tra riêng:** 10 file "0/0" (04×2, 23, 26, 27, 32, 39…) — CDKT có dòng nhưng KHÔNG bắt được tổng 270/440 → lỗ hổng locate/extract chỉ tiêu tổng.

## Ground-truth (bán tự động)
- `bench/make_truth_draft.py` sinh nháp từ pipeline.
- Đã sinh 3 nháp sạch để verify tay: `bench/truth/{03_CTCP DV Ben Thanh, 09_CTCP DV Sai Gon O to, 24_Cty TNHH Ben Thanh - RSC}*.draft.json`.
- **Chờ user:** sửa ô sai (đối chiếu PDF; chú ý mục `_review`), bỏ đuôi `.draft` → thành truth thật → bật cell-accuracy.

## ❌ B-A1 · Pass whitelist chữ số — KẾT QUẢ TIÊU CỰC (2026-06-09)
Đã thử (pass OCR thứ hai chỉ-chữ-số trên trang, gán token số về dòng theo y). **Đo bằng scorer → tệ hơn**, nên **TẮT mặc định** (`digit_pass=False`; giữ code + cờ `--no-digit-pass` làm thí nghiệm).

A/B trên 7 file (OFF → ON, balance & conflicts):
| File | OFF | ON |
|---|---|---|
| 03 (sạch) | 6/6 c=2 | 6/6 **c=9** |
| 01 Riêng | 2/4 c=11 | **0/3** c=16 |
| 05 Riêng | 0/2 c=13 | 0/0 c=22 |
| 25 | 2/4 c=11 | 2/4 c=15 |
| 04 Riêng | 0/0 c=2 | 0/0 **c=18** |

**Nguyên nhân (chẩn đoán):** model `vie` vốn đọc cụm số có dấu chấm nghìn tốt; whitelist toàn-trang (a) thỉnh thoảng thêm chữ số sai (`729809027`→`7298090279`), (b) sinh rác ở cột mã/thuyết minh. Cả 2 DPI dùng digit mode → kém ổn định → conflicts tăng.
**Bài học:** whitelist nên dùng **có mục tiêu** (re-OCR crop ô nghi ngờ trong B-A3), không phải thay thế toàn trang. Hạ tầng (`ocr_lines(whitelist=)`, `assign_value_tokens`) giữ lại cho B-A3.

## ✅ Total-detection fix (một phần B-A3) — AN TOÀN, có đo (2026-06-09)
Nhóm "0/0" thiếu dòng tổng 270/440 do 3 lỗi: mã dính ngoặc `[270`, OCR dính chữ `TỔNGCỘNGTÀSẢN`, giá trị dính `]`. Vá:
- `forced_total_code`: thêm khớp bản BỎ DẤU CÁCH (`congtaisan`/`congtasan`/`congnguonvon`). ✅
- `split_values`: strip `[]{}|` quanh token số. ✅
- ~~`_token_code` nới strip ngoặc~~ → **REVERT**: benchmark cho thấy nó làm lệch `detect_code_column` → MẤT mã tổng ở file đang tốt (05/28 HN 6 phép→2). Dòng tổng dính ngoặc đã được `forced_total_code` lo.

**Đo (44 file, baseline → sau):** tốt hơn **5 file / thụt lùi 0**; phép cân đối tính được **148→155**, đạt **118→121**; coverage giữ 2.52. ("balance sạch 20→19" là do 31/BCKT lộ thêm 1 phép LỆCH THẬT — đúng hành vi.) File: `bench/results-after-totalfix.md`. So sánh từ log stderr (tên đầy đủ, tránh bug cắt tên trong `compare.py`).

## ❌ B-A2 (deskew + binarize) — KẾT QUẢ TIÊU CỰC trên corpus này (2026-06-09)
- **Deskew:** đo góc nghiêng (projection-profile, PIL `resize((1,H))`) trên nhiều CDKT → **≈ 0°** (tối đa -0.4°). Scan chất lượng cao/thẳng → không có gì sửa.
- **Otsu binarize toàn cục:** A/B → **tệ hơn rõ** (21: 4/6 c26 → 1/4 c52; 03 sạch: 6/6→4/6). Tesseract tự binarize tốt; ép 1-bit mất thông tin anti-alias cho LSTM.
- → Không ship. Adaptive/Sauvola có thể thử nhưng EV thấp (scan đã sạch + cần numpy/convolution nặng).

## 🔑 Nhận định sau 3 thí nghiệm (B-A1, deskew, Otsu — đều ÂM)
**OCR đọc của Tesseract trên grayscale đã gần tối ưu cho bộ scan SẠCH này.** Lỗi còn lại KHÔNG sửa được bằng tiền-xử-lý-ảnh hay tinh chỉnh OCR-config. Headroom thật nằm ở **LOGIC**:
- **B-A4 (coverage):** 4 file 0/3 (Anh ×2, ngân hàng ×2) — đang bóc ĐƯỢC 0, headroom lớn nhất; là vấn đề pattern/template, không phải chất lượng OCR.
- **B-A3 (arithmetic repair):** dùng cân đối để SỬA lỗi 1-chữ-số mà consensus bỏ lọt (đúng công cụ cho lỗi số còn lại, vì sửa ở tầng ảnh/OCR không ăn thua).
- Điều tra locate-miss: 32 (CDKT không locate), 27 (tổng ngoài trang), các file 2/3 thiếu LCTT.

## ✅ B-A4 (coverage tiếng Anh) — THÀNH CÔNG, đo sạch (2026-06-09)
3 thay đổi an toàn:
1. **Tiêu đề tiếng Anh** (`EN_TITLES`: balance sheet / income statement / cash flow statement…). Nhận diện chỉ khi khớp ở ĐẦU dòng + dòng ≤5 từ → loại prose ("the income statement when…"), "OFF BALANCE SHEET ITEMS", và dòng mục lục.
2. **Dấu phẩy phân cách nghìn** (`_NUM_RE`, `looks_like_value` chấp nhận `,`): tiếng Anh dùng `805,132,153,565` — trước đây bị loại → mất hết số.
3. **forced_total tiếng Anh** (`total assets`→270, `total resources`/`total liabilities and owner|equity`→440).

**Đo (vs sau-total-fix, 0 regression):**
- 12en: 0/3 → **3/3, balance 5/6** (xác nhận đúng) · 13en: 0/3 → **3/3, balance 2/2** · 16(VN): 1/3→2/4 (comma-fix giúp thêm).

**Tích luỹ cả phiên:** coverage 2.52→**2.66**, file 3/3: 32→**34**, phép cân đối tính được 148→**164** (+16), ĐẠT 118→**129** (+11). 0 file thụt lùi.

## Còn lại
- **Ngân hàng/TCTD (35×2): vẫn 0/3** — template KHÁC T200 (mã chỉ tiêu khác hẳn cho tổ chức tín dụng). Cần khung riêng → việc lớn.
- **B-A3 đầy đủ** (balance-repair số học) cho ~14 file lệch một phần.
- Locate-miss: 32 (CDKT không locate), 27, các file 2/3 thiếu LCTT.
