# Chẩn đoán mở màn Đợt 2 — bốn file gần-0 điểm và 43 ô lệch mới

Ngày đo: 2026-07-22, nhánh `feat/dot-2-chinh-xac-va-bo-nho` (sau merge main).
Mốc: `sau-merge-main.json` tier-1 = **đúng 57 / sót 308 / lệch 79 / thừa 25** (469 ô chấm).
Probe chạy lại `engine.convert_pdf` thật cho cả 6 PDF tier-1 tái lập **trùng khít từng ô**
với mốc trên, nên mọi con số dưới đây đối chiếu được 1:1 với thước đo chính thức.
Nhật ký đầy đủ (lệnh + output từng probe): `.superpowers/sdd/dot2-chan-doan-report.md`.

Phát hiện xuyên suốt: điểm tier-1 thấp KHÔNG chủ yếu do pipeline bóc tách. Ba nguồn lỗi
tách bạch nhau:

1. **Dữ liệu đo sai** (~46% số ô chấm): 3/6 PDF không chứa đúng nội dung mà đáp án mô tả
   (thiếu hẳn báo cáo, hoặc in số kỳ khác).
2. **Bộ đọc đáp án (harness) sai** ở 4 file key: key bị đọc thành rỗng / mất một cột /
   lấy nhầm cột — parser bị chấm oan cả hai chiều (lệch ảo lẫn thừa ảo).
3. **Parser chọn sai cặp cột giá trị** trên bản in phần mềm kế toán 3 cột
   (Kỳ này | Kỳ trước | Lũy kế) — nguồn lệch thật lớn nhất, sửa được ngay.

---

## 1. Câu hỏi 1 — bốn PDF gần-0 mất dữ liệu ở tầng nào?

Ký hiệu tầng: LOCATE (định vị trang) → ASSIGN (gán dòng vào báo cáo) → CODE (dò cột
Mã số) → VALUE (bóc cặp giá trị). Thêm cột **DATA** = cặp PDF↔key có so sánh được không.

| File (điểm hiện tại) | LOCATE | ASSIGN | CODE | VALUE | DATA | Tầng hỏng ĐẦU TIÊN + bằng chứng |
|---|---|---|---|---|---|---|
| `18_Cty CP Sai gon Mui Ne.pdf` 2022 (0/74/19/2) | ✓ 1 tiêu đề | ✓ 36 dòng | ✓ 14/13 mã, col x=0.445 | ✓ (3 cụm cột) | **✗** | **DATA** — PDF chỉ có đúng **1 trang KQHDKD kỳ 06/2022 (6 tháng)**; 47 ô CDKT + 22 ô LCTT của key không tồn tại trong PDF; 26 ô KQ so với key `KQKD_Q2.xls` chứa số **riêng quý II** (key 01=8.960.060.275, PDF in 14.852.254.059) → khác kỳ, mọi parser đều 0 đúng |
| `bctc_6t_1.932.031.414.pdf` 2025 (0/70/0/0) | (text)✗ → OCR ✓ | ✓ 26 dòng | ✓ 19 mã | ✓ 14 dòng có số | **✗** | **DATA** — PDF **1 trang, chỉ KQHDKD**; cặp lại chỉ gán key CDKT (47 ô) + LCTT (23 ô), không có key KQ; thư mục nguồn không có PDF nào khác → 70/70 ô là "sót" cấu trúc. Phụ: lớp text qua lọc `is_usable` nhưng không chứa tiêu đề nào — fallback OCR đã cứu đúng thiết kế |
| `BCTC 2023.pdf` (0/23/0/14) | ✓ 3/3 trang | **✗ LCTT** | — | — | ✗ (key KQ) | **ASSIGN/OCR (LCTT)** — trang 7 OCR nát toàn thân bảng: 34 dòng chỉ còn '\|' và mảnh vụn, 0 token mã, `detect_code_column` bám cột rác x=0.819 (chuỗi "B 03 - DN") → trọn 23 ô LCTT sót. KQ trích tốt (11 mã) nhưng key `KQKD_2023.xls` bị bộ đọc đáp án trả **20 mã toàn None** → 14 "thừa" ảo (xem §3). CDKT mất trang nối p2-p3 (không tiêu đề lặp) nhưng không được chấm |
| `BCTC 6T ĐẦU NĂM 2025.pdf` Tân Bình (0/128/24/2) | ✓ 3/3 | **✗** | **✗ (KQ)** | ✗ | **✗** | **ASSIGN** — trang nối **p4, p5 (CDKT mã 241→440), p8 (LCTT mã 32→70) không có tiêu đề lặp → vĩnh viễn ngoài scope, không bao giờ được OCR**; thêm trang CDKT p3 OCR sập còn 8 dòng/cả trang (bảng kẻ ô scan xấu). CODE: cột Mã số trang KQ bị OCR nát → dò trúng cột số-thứ-tự chỉ tiêu x=0.101, chỉ 1 mã. DATA: ruột LCTT là số kỳ **2024** (cột-2025 PDF == cột-2024 của key trên ≥8 mã: 02, 03, 05, 07, 20, 23, 24, 27; tiền 60/70-prior của key xuất hiện y nguyên trong PDF), CDKT/KQ không khớp key ở cả 2 cột → dù sửa hết parser, cặp này vẫn ~0 đúng |

Cách đọc: 2 file đầu hỏng **hoàn toàn ở khâu ghép cặp dữ liệu đo** (139 ô sót không cách
nào cứu bằng parser). BCTC 2023 hỏng thật ở **chất lượng OCR trang LCTT** (23 ô) + lỗi
harness (14 ô). Tân Bình hỏng thật ở **mất trang nối + OCR sập** nhưng bị dữ liệu sai kỳ
đè lên nên sửa parser không đổi điểm ở file này (chỉ đổi ở corpus rộng).

### Đếm riêng bug §7.1 (`_token_code` strict: mã in "1" không khớp template "01")

Đo bằng biến thể canon-tolerant chạy song song trên cả 6 file: SGMN-2022 KQ +1 mã ('02'
in/OCR thành "2"), Tân Bình KQ +1 ('2'), Tân Bình LCTT +2 ('3','6' — file sai kỳ),
BCTC-2023 LCTT +1 ('5' — trên cột rác), còn lại 0. **Tổng ≤ 8 ô tier-1, đa số nằm trên
cặp sai-kỳ → tác động thực ~2–4 ô.** §7.1 không phải nguồn sót lớn như dự đoán. Cảnh
báo khi sửa: canon-tolerant làm `detect_code_column` chấm nhầm cột số-thứ-tự bên trái
(đã thấy ngay: Tân Bình LCTT col_canon=0.078) — chỉ nới ở `find_code_at`, GIỮ strict
khi dò cột.

---

## 2. Câu hỏi 2 — 43 ô lệch mới có phải do chọn cặp Kỳ-này/Lũy-kế?

Dump đủ 79 ô lệch (probe `q2_lech_cells.json`, phân loại từng ô rồi soát tay bằng dump
dòng OCR kèm toạ độ):

| File | Lệch | Δ so trước merge | Phân loại |
|---|---|---|---|
| `kqkd_6t.pdf` | 24 | **+21** | **24/24 = chọn sai cặp cột** — 23 swap thuần (got_cur = exp_prior và ngược lại), 1 swap kèm garble chữ số (3.377.664.564 → 3.371.664.564) |
| `18_Cty CP Sai gon Mui Ne.pdf` | 19 | **+17** | 19/19 = sai kỳ dữ liệu (PDF 6T vs key quý II) — got là số 6T/lũy kế, exp là số quý; trước merge các ô này là SÓT vì trích được ít hơn |
| `BCTC 6T ĐẦU NĂM 2025.pdf` | 24 | **+5** | ruột PDF kỳ 2024/bản khác + OCR garble (16 LCTT khớp key-prior; 5 CDKT + 3 KQ không khớp cả hai cột) |
| `Ben Thanh Hoang Thanh` | 12 | 0 | có sẵn từ trước: **9 = lỗi bộ đọc đáp án** (key thành (prior, prior) — xem §3, giá trị parser thực ra ĐÚNG), 3 = garble chữ số |
| `BCTC 2023.pdf` | 0 | 0 | (14 "thừa" của nó = key bị đọc rỗng) |

### Bằng chứng quyết định (file nhiều lệch nhất — `kqkd_6t.pdf`)

Render trang KQHDKD 150 DPI + OCR dải header: bảng có **ba** cột số với tiêu đề

```
CHỈ TIÊU | Mã số | Thuyết minh | Kỳ này | Kỳ trước | Lũy kế
                                (≈0.67)   (≈0.80)    (≈0.94)   ← right_x
```

(mảnh OCR header: "ỳ nà[y]" cx≈0.62, "…r[ước]" cx≈0.74, "Hé"≈Lũy kế cx≈0.88 — khớp
đúng ba tâm cột). `detect_value_columns` trả **[0.668, 0.802, 0.938]** và
`sel = centers[-2:] = [0.802, 0.938]` = **(Kỳ trước, Lũy kế)**. Vì đây là báo cáo
6 tháng (Kỳ kế toán 06/2024) nên Lũy kế == Kỳ này → kết quả hoán vị hoàn hảo hai cột
trên mọi dòng: ví dụ mã 01 exp=(22.730.333.061 | 20.761.958.628),
got=(20.761.958.628 | 22.730.333.061). Cặp đúng là **hai cột TRÁI** `centers[0..1]`.
Cùng bố cục này xuất hiện ở `BCTC 2023.pdf` (KQ) và `SGMN-2022` — một "gia đình" bản in
phần mềm kế toán (dấu hiệu nhận diện: "Phần I. Lãi Lỗ", "Kỳ kế toán: MM/YYYY").

### Đối chứng nhân quả: ép về đường cũ `split_values`

Chạy lại cả 6 file với `detect_value_columns` bị vô hiệu (ép nhánh split như trước
merge): tổng = 60/305/**79**/26 — **79 ô lệch giữ nguyên từng ô một**. Với 3 cụm cột và
split≈0.87, `split_values` cũng cắt đúng cặp sai (Kỳ trước | Lũy kế). Kết luận:

- **Revert merge không sửa được lệch.** Cú nhảy 36→79 không phải "pick_values chọn khác
  split_values", mà là: sau merge parser trích được NHIỀU ô hơn (sót 350→308, −42), và
  các ô mới trích rơi vào (a) key sai kỳ → hiện hình thành lệch (SGMN +17, Tân Bình +5),
  (b) gia đình 3-cột chọn sai cặp (kqkd_6t +21).

### Phán quyết

Trong **43 lệch mới**: ≈ **21 ô (49%) do chọn cặp cột** (sửa parser được),
≈ **22 ô (51%) do cặp dữ liệu đo sai kỳ** (sửa pairs.json). Trong toàn bộ 79 lệch:
24 (30%) cặp cột · 43 (54%) dữ liệu đo · 9 (11%) bộ đọc đáp án · 3 (4%) garble chữ số.

---

## 3. Lỗi bộ đọc đáp án (`tests/regression/groundtruth.py`) — 3 dạng đã xác nhận trên xls thô

| Key | Dạng lỗi | Hậu quả đo |
|---|---|---|
| `KQKD_2023.xls` | hàng đánh số `1,2,3,4,5` nằm ở cột 1,6,7,**9**,**11** (merged cell) nhưng giá trị ở cột **8**,**10** → strategy "numbering" đọc 2 cột rỗng | key 20 mã thành toàn (None, None); 14 ô parser trích ĐÚNG bị đếm "thừa"; mất ~34 ô đáp án |
| `cdkt_6t.xls`, `CDKT Q2.xls` | marker '5' ở cột rỗng c12, cột Kỳ-trước thật ở c11 | mất NGUYÊN cột prior: 47 mã chỉ còn 47 ô thay vì ~94 (mẫu số tier-1 hụt ~90 ô) |
| `BTHT ..._KQKD.xls` | sheet 4 cột giá trị (Trong kỳ nay/trước + Lũy kế nay/trước); fallback "2 cột nhiều số nhất" trúng cặp **Năm-Trước + Năm-Trước** | key = (prior, prior) → **9 ô parser đúng bị chấm lệch** (got 8.852.241.816 chính là Năm-nay thật ở cột 3 của xls) |

Hướng sửa chung: sau khi chọn cột (numbering lẫn fallback) phải **xác minh cột có ≥N ô
số thật**, nếu rỗng dò cột kề (lệch-1 do merged cell); fallback gặp 4 cột phải ghép cặp
theo NHÓM header (Trong kỳ vs Lũy kế), không lấy "2 cột nhiều số nhất" xuyên nhóm.

---

## 4. Việc cần làm (xếp hạng theo tác động ước lượng, nền = 57 đúng / 469 ô)

| # | Việc | Phạm vi | Tác động ước lượng (căn cứ đếm ở trên) |
|---|---|---|---|
| 1 | **Chọn đúng cặp cột giá trị trên bản in 3 cột**: khi có 3 cụm, nhận diện cột phải-nhất là Lũy kế (giá trị trùng cột 1 trên nhiều dòng, hoặc header "Lũy kế"/`detect_period` kind≠quarter) → lấy `centers[0..1]` thay vì `[-2:]` | `bctc/parser.py` (extract/sel) | **+~22 đúng, −22 lệch** ngay (kqkd_6t 24/24 lệch là swap); cộng hưởng với #2 mở thêm **+~24–28 đúng** ở BCTC-2023-KQ; áp dụng cho cả gia đình Misa-print trong corpus (3/6 PDF tier-1 thuộc gia đình này). Đúng tier-1: 57 → ~100–107 (12,2% → ~21–23% trên mẫu số hiện tại) |
| 2 | **Sửa 3 dạng lỗi bộ đọc đáp án** (bảng §3): xác minh cột sau numbering, dò cột kề khi rỗng, fallback ghép cặp theo nhóm header | `tests/regression/groundtruth.py` | **+9 đúng −9 lệch** (BTHT); key KQKD_2023 sống lại (~34 ô, biến 14 thừa ảo thành ô chấm thật); mẫu số trung thực thêm ~90–127 ô. Điều kiện tiên quyết cho #1 phát huy ở BCTC-2023 |
| 3 | **Làm lại 8 cặp pairs.json dính 3 PDF sai ruột** (SGMN-2022 ×3, bctc_6t ×2 chấm được, Tân Bình ×3): xác minh lại theo nội dung (kỳ + vài giá trị mốc), thay bằng cặp khác từ `pairs.candidate.json`, tối thiểu là đánh dấu `DATA_MISMATCH` để loại khỏi tổng | `tests/regression/pairs.json` (+ build_pairs thêm bước đối chiếu kỳ) | loại **~215 ô sót + ~43 ô lệch "ảo"** khỏi thước đo; tier-1 sau #1+#2+#3 phản ánh parser thật (ước ~50% đúng thay vì 12%); tránh Đợt-2 tối ưu nhầm mục tiêu |
| 4 | **Quét trang NỐI không tiêu đề lặp**: sau trang tiêu đề, đưa trang kế tiếp vào scope khi nó chứa ≥N mã hợp lệ tiếp nối của báo cáo đang mở (dừng khi gặp tiêu đề khác/thuyết minh) | `bctc/parser.py` (locate/extract) | tier-1 gần 0 (trang nối chỉ có ở Tân Bình — file sai ruột — và CDKT BCTC-2023 không được chấm) **nhưng** là fix ĐỘ PHỦ corpus: tier-2 coverage CDKT đang 11,9%, mọi CDKT nhiều trang không lặp tiêu đề hiện mất sạch nửa sau (mã 241→440) |
| 5 | **Cứu OCR trang bảng sập** (trang được locate nhưng OCR ra <15 dòng, như Tân Bình p3 = 8 dòng; hoặc bucket có tiêu đề mà 0 mã, như LCTT BCTC-2023): thử lại DPI cao hơn / preprocess khác trên đúng trang đó | `bctc/parser.py` / `ocr.py` | trần +23 ô (LCTT BCTC-2023) nếu OCR cứu được; Tân Bình không đổi điểm (sai ruột) nhưng corpus scan-xấu hưởng lợi; cần thí nghiệm trước khi hứa số |
| 6 | **§7.1 nới `_token_code` chỉ ở `find_code_at`** (canon '1'≡'01'), giữ strict ở `detect_code_column` | `bctc/parser.py` | **≤8 ô tier-1 (~2–4 ô thực)** — làm cùng #1 cho trọn, không đáng làm riêng; đo được là nhỏ, ngược dự đoán §7.1 ban đầu |

Lưu ý chống nhầm sau này: (a) không revert merge — đối chứng legacy giữ nguyên 79 lệch;
(b) mọi so sánh "trước/sau" Đợt-2 phải chạy trên pairs.json ĐÃ sửa (#3), nếu không
+/-hàng-chục ô ảo của 3 file sai ruột sẽ nuốt tín hiệu thật.
