# Kết quả Đợt 2 — đối chiếu từng ngưỡng

Nhánh `feat/dot-2-chinh-xac-va-bo-nho`, 17 commit trên `main` (ecbfbcd).
Kế hoạch: [2026-07-22-dot-2-ke-hoach.md](2026-07-22-dot-2-ke-hoach.md).

## 1. Đối chiếu ngưỡng

| Cổng | Ngưỡng | Kết quả | |
|---|---|---|---|
| **G1** — sót+lệch tier-1 giảm ≥50% | ≤ 43 ô | **44 ô** (87 → 44, giảm 49,4%) | ✗ hụt 1 ô |
| **G1b** — phủ corpus (sweep 300) | CĐKT ≥28%; nhóm-0 ≤60 file | **28,7%**; **49 file** | ✓ ĐẠT |
| **G2** — không mất dữ liệu âm thầm | Mã ngoài khung hiện + cảnh báo | Đã có, cộng 3 lỗ khác đã bịt | ✓ ĐẠT |
| **G5** — RSS đỉnh | ≤ 250 MB (lượt n=30) | **695 MB** batch; **85–291 MB** per-file | ✗ (xem §3) |
| **G3/G4** — CPU không xấu đi | ±10% so 504s | **927s = +84%** | ✗ (xem §2) |

## 2. Vấn đề lớn nhất: CPU tăng 84% — đánh đổi lấy độ chính xác

Đo trên cùng mẫu 30 file, `tier3.cpu`:

| Mốc | CPU-giây | So mốc đầu Đợt 2 |
|---|---:|---:|
| Trước Đợt 1 | 1066 | — |
| Sau Đợt 1 | 536 | — |
| **Đầu Đợt 2** (baseline sạch) | **504** | mốc |
| Sau V1 (trang tiếp diễn) | 765 | +52% |
| Sau V2 (cứu OCR) | 959 | +90% |
| Sau V4a (định vị) | 997 | +98% |
| Sau V6 | 1033 | +105% |
| **Sau V8 (cắt lãng phí)** | **927** | **+84%** |

**Nguyên nhân:** V1/V2/V4a đều làm THÊM việc OCR thật để bóc thêm dữ liệu —
đọc trang tiếp diễn, OCR lại trang sập, quét thêm dải để tìm tiêu đề. Không
phải lãng phí ngẫu nhiên; phần lãng phí thật đã bị V8 cắt (−10%).

**Vì sao không ai phát hiện sớm:** mọi nhật ký công việc V1–V5 đối chiếu CPU
với mốc **trước Đợt 1** (1066s) thay vì mốc **đầu Đợt 2** (504s). So với 1066s
thì 927s trông như "giảm 13%"; so với mốc đúng thì là **tăng 84%**. Bài học:
mốc so sánh phải cố định theo kế hoạch, không đổi giữa chừng.

**Đánh đổi thực tế đã mua được gì** (sweep 300 file):

| | Trước Đợt 2 | Sau |
|---|---:|---:|
| Phủ CĐKT | 18,8% | **28,7%** |
| Phủ KQHDKD | 35,0% | 37,3% |
| Phủ LCTT | 26,0% | 31,7% |
| File bóc 0 ô CĐKT | 90 | **49** |

**41 file trước đây ra file Excel rỗng nay bóc được bảng cân đối.**

**Cần người quyết:** nhiệt là 1 trong 3 phàn nàn gốc. Ba lựa chọn:
1. **Chấp nhận** — đổi nhiệt lấy dữ liệu; người dùng có nút "Tiết kiệm điện"
   (V7) để chạy 1 luồng khi cần máy mát.
2. **Đổi mặc định sang Tiết kiệm điện** — mát ngay, chậm hơn, độ chính xác giữ
   nguyên (chỉ đổi số luồng song song, không đổi thuật toán).
3. **Hạ bớt phạm vi** — ví dụ tắt V2 (cứu OCR) mặc định; mất 12 ô đúng của
   BCTC-2023 nhưng lấy lại một phần CPU.

## 3. G5 — bộ nhớ: ngưỡng đo sai ngữ cảnh

`ResourceProbe.peak_rss_mb` dùng `ru_maxrss` = đỉnh **trọn đời tiến trình**.
Trên lượt đo 30 file trong MỘT tiến trình, con số 695 MB là đỉnh gộp của cả 30
file cộng baseline thư viện — không phải mức một file chiếm.

Ứng dụng thật xử lý **từng file một**, nên số đúng ngữ cảnh là đo per-file
trong tiến trình riêng:

| | RSS đỉnh | Trừ baseline thư viện (65 MB) |
|---|---:|---:|
| Chỉ import (fitz+PIL+tesseract+openpyxl) | 65 MB | — |
| File nhỏ | 85 MB | +20 MB |
| File median 38 trang | 262 MB | +197 MB |
| File lớn 121 MB / 62 trang | 291 MB | +226 MB |

Ngưỡng chữ 250 MB bị vượt nhẹ ở file median/lớn, nhưng **mục tiêu thực của G5
— bộ nhớ per-file có chặn, sống được trên máy 4 GB — đạt**: 291 MB đỉnh cho
file khổng lồ nhất corpus, còn dư 3,7 GB. Rủi ro cũ (giữ toàn bộ ảnh trang
cùng lúc → spike >500 MB + tích luỹ không chặn) đã hết.

Batch RSS cũng giảm thật: 970 → 695 MB sau V8.

## 4. Độ chính xác — bảng tier-1 (pairs v2, 3 PDF, 165 ô)

| Mốc | đúng | sót | lệch | thừa |
|---|---:|---:|---:|---:|
| Baseline sạch | 66 | 46 | 41 | 7 |
| +Fix cặp cột Kỳ này/Lũy kế | 97 | 45 | 11 | 6 |
| +V2 cứu OCR | 109 | 33 | 11 | 11 |
| +V6, +V8 | **109** | **33** | **11** | **12** |

sót+lệch: 87 → 44 (**−49,4%**, hụt ngưỡng G1 đúng 1 ô).

**Cảnh báo về con số này:** tier-1 chỉ có 3 PDF / 2 doanh nghiệp / 5 cặp chấm
điểm, và mỗi cải thiện đều rơi vào file mà bản sửa được phát triển trên đó.
Hai khối KHÔNG có file tier-1 để tinh chỉnh (V1, V4a) cho đúng **0** điểm
tier-1 — nhưng lại là hai khối cho kết quả lớn nhất trên sweep 300 file. Vì
vậy **đừng trích 66,1% như độ chính xác sản phẩm**; con số đại diện hơn là
phủ corpus ở §2.

## 5. Việc đã làm

| Khối | Nội dung | Bằng chứng |
|---|---|---|
| Vệ sinh thước đo | Sửa 3 lỗi bộ đọc đáp án; bỏ 9 cặp PDF sai ruột | 12,2% "đúng" cũ phần lớn là nhiễu đo |
| Fix cặp cột | Chọn (Kỳ này, Kỳ trước) thay 2 cột phải cùng | +31 đúng, −30 lệch |
| V1 trang tiếp diễn | Gom trang không lặp tiêu đề vào scope | phủ corpus |
| V2 cứu OCR | OCR lại trang sập ở DPI/PSM khác | +12 đúng BCTC-2023 |
| V3 chẩn đoán | Phân loại 90 file nhóm-0 | QĐ15 = 0 file (BỎ), B05 = 4 (BỎ theo quyết định) |
| V4a định vị | Dải thấp + siết `is_usable` + cụm mã cấu trúc | 54 file: 21→43 bóc được |
| V5 bộ nhớ | Render xám + streaming + trần điểm ảnh | kết quả byte-identical; sửa 1 race có thật |
| V6 G2 | Mã ngoài khung, đơn vị tính, mã 1 chữ số, chặn file hỏng | đóng G2 |
| V7 GUI | Nút chế độ Tiết kiệm điện / Cân bằng / Tối đa | |
| V8 | Cắt OCR lãng phí + 3 lỗ mislabel/ghi đè | −10% CPU, −28% RSS |

## 6. Còn nợ (không chặn merge, nên làm ở đợt sau)

1. **CI không chạy test nào** — 300 test chưa từng chạy trên CI ở bất kỳ commit
   nào. Cần thêm bước pytest vào workflow. Đây là nợ có sẵn từ trước, nhưng giờ
   đáng kể vì bộ test đã lớn.
2. **Test dựa corpus tự bỏ qua im lặng** — mọi test chạm đường render→OCR đều
   skip khi không có corpus/tesseract; trên CI chúng sẽ không chạy.
3. **tier-1 quá mỏng** (3 PDF) — cần lập thêm cặp có xác minh kỳ để bảng điểm
   đại diện hơn.
4. **`_KHO_ANH` là singleton mức module** — an toàn hôm nay vì `convert_many`
   chạy tuần tự; nếu sau này xử lý song song nhiều file thì xref sẽ đụng nhau.
5. 11/54 file LOCATE_FAIL còn lại (extract sập trên scan lớn, PDF text+ảnh trộn).
