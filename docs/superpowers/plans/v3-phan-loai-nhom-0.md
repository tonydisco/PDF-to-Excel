# V3 Đợt 2 — Phân loại "nhóm-0": 90 file bóc 0 ô CĐKT

Ngày đo: 2026-07-23, nhánh `feat/dot-2-chinh-xac-va-bo-nho` (HEAD = V5).
Phạm vi: **READ-ONLY chẩn đoán**, không sửa `bctc/` hay `tests/`. Mục tiêu: đếm phân
loại để quyết định **V4 có đáng thêm mẫu QĐ15/2006 và/hoặc B05/TCTD không, và cho mẫu nào**.

Dân số: 90 file trong `sweep-300-dot2.json` có `coverage.CDKT == 0` (toàn bộ 90, không lấy
mẫu). Phương pháp probe rẻ, read-only, tái dùng chính `bctc/parser.py` + `bctc/textlayer.py`:

1. **Tín hiệu rẻ** (không OCR): `is_usable`, tỷ lệ dấu, đếm ký tự, cờ tiêu đề trên lớp text.
2. **`locate_pages(doc)` thật** trên cả 90 file (strip-OCR 135 DPI cho file scan).
3. **OCR nhắm trang** (72 file không có lớp text dùng được): dò tiêu đề CĐKT, từ vựng
   ngân hàng/chứng khoán/tiếng Anh, đếm mã khung TT200, chất lượng OCR.
4. **Probe sâu + readability** cho các ca mập mờ (dump OCR thô để tách scan-rác vs không-CĐKT).
5. **ĐO LẠI parser hiện tại** (`extract_consensus` dpis=180/235) trên cả 90 file.

> ⚠️ **`sweep-300-dot2.json` đo TRƯỚC V1/V2.** File sweep commit `575a549` (22-07 22:17) là
> tổ tiên của V1 `e235521` (gom trang tiếp diễn, "+65% phủ CĐKT") và V2 `ef95510` (cứu OCR).
> Đo lại bằng parser HEAD: **18/90 file nay đã bóc CĐKT > 0** (17 thuộc nhóm LOCATE_FAIL, 1
> ngân hàng chỉ trúng 1 mã rác). Tức "90 file 0 ô" là con số CŨ; **gap thực còn 72 file**.
> Điều này CỦNG CỐ kết luận: đòn bẩy là SỬA PARSER, không phải thêm mẫu.

---

## 1. Bảng đếm

| # | Nhóm | Số file | % | Bản chất | Sửa được bằng? |
|--|--|--|--|--|--|
| 1 | **LOCATE_FAIL_TITLE_PRESENT** | **54** | **60.0%** | CĐKT mẫu TT200 CÓ trong file (mã 100/110/…/440), pipeline bóc 0 | **Sửa parser** (định vị/đọc lớp text), KHÔNG cần mẫu mới |
| 2 | FRAGMENT_1PAGE | 15 | 16.7% | File 1–2 trang, không có CĐKT (chỉ KQKD/LCTT/thuyết minh/kiểm toán) | Ngoài phạm vi (không có gì để bóc) |
| 3 | OTHER | 11 | 12.2% | Không phải CĐKT: bảng cân đối **tài khoản**, tóm tắt, thuyết minh, BC HĐQT, giải trình | Ngoài phạm vi (không có CĐKT) |
| 4 | **B05_TCTD** | **4** | **4.4%** | Ngân hàng — CĐKT dùng mã B05/TCTD, không khớp TT200 | **Cần mẫu B05** (nhưng xem §2) |
| 5 | MOJIBAKE_OR_SCAN_BAD | 3 | 3.3% | Scan xoay/lộn — OCR ra rác | Ngoài phạm vi (scan hỏng) |
| 6 | ENGLISH | 3 | 3.3% | Mẫu B01-DN **bản tiếng Anh** (mã số vẫn TT200) | Sửa parser (nới nhận tiêu đề tiếng Anh), KHÔNG cần mẫu mới |
| 7 | QD15_PRE2015 | **0** | 0.0% | — | — |
| 8 | SECURITIES_ORS | **0** | 0.0% | — | — |
| | **TỔNG** | **90** | 100% | | |

Gộp theo hướng xử lý:
- **Sửa được bằng parser (không cần mẫu mới): 57 file (63%)** = LOCATE_FAIL 54 + ENGLISH 3.
- **Ngoài phạm vi (không có CĐKT / scan hỏng): 29 file (32%)** = FRAGMENT 15 + OTHER 11 + MOJIBAKE 3.
- **Cần mẫu mới: 4 file (4%)** = B05_TCTD (và tất cả là 1 ngân hàng — OCB).

---

## 2. Khuyến nghị V4 — **KHÔNG mẫu nào đạt ngưỡng ≥15 file**

**QĐ15/2006 → KHÔNG làm (0 file cần).** Bảng cân đối kế toán QĐ15/2006 dùng **ĐÚNG bộ Mã
số như TT200** (100 Tài sản ngắn hạn, 110 Tiền, 200 Tài sản dài hạn, 270 Tổng tài sản, 300
Nợ phải trả, 400 Vốn chủ sở hữu, 440 Tổng nguồn vốn). Bằng chứng chốt: `BCTC-2012-Quy3-SG
Da Lat` in nguyên "Mẫu số B 01-DN (BH theo QĐ số 15/2006/QĐ-BTC)" nhưng hàng tổng ghi
`100=110+120+130+140+150` — trùng TT200 từng mã. **6 file trước-2015** (2007, 2010, 2011,
2012×2, 2014) đều nằm nhóm LOCATE_FAIL với **53–86 mã TT200** đọc được — chúng thất bại vì
LỚP TEXT VNI cũ làm hỏng định vị, không phải vì mã khác. Thêm mẫu QĐ15 không cứu file nào.

**B05/TCTD → KHÔNG làm NẾU mục tiêu là 90-file tail này (4 file); nhưng CÂN NHẮC nếu mục
tiêu là phủ toàn corpus.** Trong dân số 90 file, cả 4 đều là **một ngân hàng — OCB (Ngân
hàng TMCP Phương Đông)**: `OCB.pdf`, `OCB_BCTC 2018`, `35_NH TMCP Phuong Dong 2019`,
`35_NH TMCP Phuong Dong Q3.2024`. Xác nhận là ngân hàng: 9–11 từ vựng B05 mỗi file ("Cho
vay khách hàng", "Tiền gửi của khách hàng", "Tiền gửi tại NHNN", "Thu nhập lãi thuần"…) và
**0 mã TT200** khớp → CĐKT đúng là B05/TCTD, mẫu khác hẳn.
> ⚠️ **Lưu ý phạm vi:** 4 là số trong **mẫu sweep 300 file**. Theo dữ kiện corpus của tác vụ,
> **~112 file ngân hàng/chứng khoán toàn corpus dùng B05/TCTD** (TT49/2014). 4/300 ≈ 1,3% →
> ngoại suy corpus ~2919 file thì cỡ **vài chục** file B05, có thể VƯỢT ngưỡng 15. Vậy quyết
> định B05 phụ thuộc MỤC TIÊU V4: nếu chỉ vá đuôi 90-file này → không đáng (4 file, 1 pháp
> nhân); nếu nhắm phủ ngân hàng toàn corpus → mẫu B05 đáng làm và nên đánh giá trên tập bank
> đầy đủ, KHÔNG chỉ 4 file này. (Khác với QĐ15: QĐ15 vô giá trị ở MỌI quy mô vì mã = TT200.)

**SECURITIES/ORS → KHÔNG làm (0 file).** Các công ty có "chứng khoán" trong dân số (RSS-2012,
Savico giữ đầu tư CK) đều lập CĐKT mẫu **TT200** (đếm được 43–58 mã TT200) → thuộc LOCATE_FAIL,
không cần mẫu ORS.

### → Đòn bẩy V4 là nhóm **LOCATE_FAIL (54 file, 60%)** — sửa ĐỊNH VỊ/ĐỌC, không thêm mẫu

Nhóm này CĐKT mẫu TT200 **có mặt vật lý** (mã + số đọc được) nhưng pipeline bóc 0. Đây KHÔNG
phải giới hạn mẫu — là lỗi ở khâu định vị trang / tin lớp text. **V1/V2 đã có trên nhánh cứu
17/54** (ví dụ `07_Vật tư Ben Thanh Q2.2020` 0→32 ô, `SVC_BCTT Q1.2013` 0→24, `05-VHTH
Q2.2015` 0→37). 37 file còn-0 chia theo cơ chế lỗi:

1. **Locate chỉ quét dải 42% đầu trang** → tiêu đề CĐKT nằm dưới dải, hoặc trang liệt kê
   nhiều tiêu đề (`heading_in_lines` trả None khi ≠1 tiêu đề). Lớp text sạch mà vẫn trượt:
   `Savico-FS2020` (57 mã), `PNCO 2020` (58 mã, locate thấy cả 3 báo cáo nhưng bóc 0),
   `SVC.BCTC 2015/2016`.
2. **Lớp text VNI/TCVN3 cũ lọt `is_usable` (false-positive)** → parser tin lớp text rác,
   `norm("Baûng caân ñoái keá toaùn") ≠ "bang can doi ke toan"` nên không định vị; số thì
   đọc được (ASCII). Gồm `SVC 2007/2010`, `Khanh Hoi 2011`, `SG Da Lat 2012`, `20_SVC`,
   `RSS-2012`. (Đây là họ mojibake THỨ HAI, khác họ "BAD CAD TAl CHfNH" mà `is_usable` bắt
   được — họ này tỷ lệ dấu > 0 nên lọt lưới.)
3. **PDF trộn text + ảnh**: `is_usable=True` nhưng bảng CĐKT là **ảnh scan** (trang 3–5),
   pipeline đi đường text nên bỏ qua OCR các trang ảnh. `01_SVC HN Quy II.2020`,
   `01_SVC Quy III.2020`.
4. **Scan: tiêu đề CĐKT OCR trượt** dù KQ/LCTT tìm được (nhiều file Ben Thanh/Mui Ne/Hoc Mon
   có `locate=[KQHDKD,LCTT]` nhưng thiếu CDKT, mà OCR trang nhắm đếm 21–62 mã TT200).
5. **Fragment 1 trang LÀ CĐKT**: `BCDKT MX 2017.2/.3` (37–41 mã), `BCTC2016.1` (23 mã) —
   locate trượt tiêu đề trên trang đơn.

Hướng V4 đề xuất (ưu tiên theo số file chạm): (a) định vị không chỉ dựa dải 42% / nhận trang
bảng theo mật độ mã, không chỉ theo tiêu đề sạch; (b) phát hiện lớp text VNI cũ → ép OCR
(sửa false-positive `is_usable`); (c) OCR trang-ảnh trong PDF trộn dù lớp text "dùng được";
(d) nới `MAX_EN_HEADING_WORDS` cho tiêu đề tiếng Anh dài ("Balance sheet as at 31 December
2017" = 7 từ, đang bị loại ở ngưỡng 5).

---

## 3. Chi tiết từng nhóm (ví dụ, đường dẫn tương đối gốc corpus `…/` = `Documents/`)

### LOCATE_FAIL_TITLE_PRESENT — 54 (parser-addressable)
- `…/BTG document/BCTC 4/2025/Quy 2.2025/05_CTCP VHTH BT_CĐKT HC-…6 THANG DAU NAM 2025_Cty mẹ.pdf` (text, 111 mã TT200, nay bóc 21 ô)
- `…/BTG document/BCTC 8/2022/…/21_Cty CP KS DL Thang Muoi.pdf` (scan 62tr, 105 mã, locate thấy cả 3 nhưng bóc 0)
- `…/Savico-FS2020-Separate-VN.pdf` (text sạch, 57 mã, locate=∅ — tiêu đề ngoài dải 42%)
- `…/BTG document/BCTC 4/2011/…/20_SVC - Baocaotaichinh_2010_Hopnhat_kiemtoan.pdf` (VNI cũ, 65 mã)
- `…/BCTC - 2012 - Quy 3 - Cty CP SG Da Lat (chua ky).pdf` (khai QĐ15/2006 nhưng mã = TT200, 60 mã)

### B05_TCTD — 4 (ngân hàng OCB; cần mẫu B05 nhưng dưới ngưỡng)
- `…/BTG document/BCTC/2017/Quy 2.2017/OCB.pdf` (84tr, 11 từ B05, 0 mã TT200)
- `…/BCTC 7/2019/…/35_NH TMCP Phuong Dong_BCTC 2019_Hop nhat_Kiem toan.pdf`
- `…/BCTC 5/2024/Quý 3/35_NH TMCP Phuong Dong - Q3.2024 (BC rieng).pdf`
- `…/OCB_BCTC 2018_KT (hop nhat).pdf`

### ENGLISH — 3 (mẫu B01-DN tiếng Anh, mã TT200; parser-addressable)
- `…/BCTC 9/2018/…/BTJ Audited Separate Financial Statements 2018_EN.pdf` (56 mã TT200)
- `…/BCTC 7/2015/…/11-Cty LD KS Plaza-BCTC kiem toan nam 2015.pdf` ("Form B 01-DN / BALANCE SHEET", 51 mã)
- `…/BCTC/2017/Quy 4.2017/23_Cty LD Can ho va VP SG_BCTC 2017_Da kiem toan.pdf` ("Circular 200/2014", 39 mã)

### FRAGMENT_1PAGE — 15 (không có CĐKT; ngoài phạm vi)
- `…/kqkd (me) (6)_….pdf`, `…/lctt (hn)_….pdf`, `…/TM BCTC MX 2017.2/.3.pdf`, `…/BC LCTT.pdf`,
  `…/02_BC Kiem toan doc lap_Me/_HN.pdf`, `…/03_CBTT ve CTy CP Xe May….pdf` — mỗi file chỉ 1 báo
  cáo lẻ (KQKD/LCTT/thuyết minh/kiểm toán/công bố thông tin), không có bảng CĐKT.

### MOJIBAKE_OR_SCAN_BAD — 3 (scan xoay/lộn, OCR ra rác)
- `…/BCTC 11/2021/…/27_Cty CP SXKD Hàng XK Tân Bình 2021.pdf`
- `…/BCTC 8/2011/QIV-2011/27_BCTC 2011 Cty CP Tan Cang Ben Thanh.pdf` (OCR: "NỌA ĐNỎ2 ĐNỌL" = TỔNG CỘNG NGUỒN VỐN lộn ngược)
- `…/BCTC 9/2019/Quy 2.2019/03_ Cong ty CP Dich vu ben Thanh_BCTC HN BTSC Q2 2019.pdf`

### OTHER — 11 (không phải CĐKT)
- `…/Bang_can_doi_tai_khoan 14-1-21.pdf` (bảng cân đối **tài khoản** — số hiệu TK trùng mã CĐKT nhưng KHÁC báo cáo)
- `…/BCTC-TomTat-Quy02-2012.pdf` (tóm tắt, không có cột Mã số)
- `…/8. thuyet minh (hn)_….pdf`, `…/TM.pdf`, `…/04_…Thuyet minh Q1.2017.pdf` (thuyết minh lẻ)
- `…/3.bc hdqt (hn)_….pdf` (báo cáo HĐQT), `…/07_Giai Trinh BCTC 01_Me/_HN.pdf` (giải trình)
- `…/29_CTy LD Sosa BCTC 9Th-2011.pdf` (báo cáo KPI/thực hiện kế hoạch bằng USD)

---

## 4. Chốt cho V4

- **QĐ15/2006 và ORS: KHÔNG dựng ở mọi quy mô** — 0 file cần; các file đó lập CĐKT mã TT200.
- **B05/TCTD: dựa vào MỤC TIÊU V4.** Chỉ 4 file trong 90 (1 ngân hàng) → không đáng nếu vá
  đuôi này; nhưng corpus có ~112 file B05/TCTD (dữ kiện tác vụ) → nếu V4 nhắm phủ ngân hàng
  thì mẫu B05 mới đáng, cần đánh giá trên tập bank đầy đủ chứ không phải 4 file này.
- **Chuyển V4 sang sửa parser cho nhóm LOCATE_FAIL (54 file, 60%)** theo 4 hướng ở §2 — đây là
  nơi trần điểm cao nhất; V1/V2 đã chứng minh hướng đúng (cứu 17/54 mà chưa nhắm riêng).
- **26 file (FRAGMENT+OTHER) không có CĐKT** và **3 file scan hỏng** là trần cứng của dân số
  này — nên loại khỏi mọi phép đo "phủ CĐKT" để mẫu số trung thực (giống bài học pairs.json
  ở chẩn đoán Đợt-2 mở màn).
