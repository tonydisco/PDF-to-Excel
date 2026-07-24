# Cốt lõi dự án + khảo sát công cụ mã nguồn mở

Ngày 24/07/2026. Mục đích: tìm thuật toán/công cụ tốt hơn cho các góc độ trọng
yếu, và giảm rủi ro fail.

## 1. Cốt lõi dự án (rút từ tài liệu + số đo thật)

**Bài toán.** Đọc Báo cáo tài chính Việt Nam dạng PDF (chủ yếu bản scan) và
xuất ra Excel theo khung Thông tư 200 — 3 báo cáo: Bảng cân đối kế toán, Kết
quả HĐKD, Lưu chuyển tiền tệ.

**Quyết định kiến trúc cốt lõi (từ TECHSTACK.md, vẫn đúng):** không OCR cả
bảng rồi đoán, mà dùng **khung chỉ tiêu chuẩn TT200 làm mẫu** — OCR chỉ cần
đọc đúng **Mã số** và **con số**, nhãn chỉ tiêu lấy từ khung nên luôn sạch.
Kèm **tự kiểm tra cân đối** (270=440, 100+200=270, 300+400=440) làm bộ lọc
chất lượng.

**Ràng buộc bất di bất dịch — quyết định mọi lựa chọn công nghệ:**

| Ràng buộc | Hệ quả |
|---|---|
| Dữ liệu tài chính **không được rời máy** | Cấm mọi OCR đám mây |
| Máy đích: **Win10, 4 GB RAM, HDD, 2–4 nhân** | Cấm mô hình nặng |
| Đóng gói **một bộ cài ~70 MB** | **Loại mọi thứ cần PyTorch/Paddle (~2 GB)** |
| Người dùng cuối không cài được gì thêm | Phải kèm sẵn trong bộ cài |

**Corpus thật:** 2.919 PDF · 79.910 trang · 19,8 GB. **87,8% bắt buộc OCR**
(78,2% scan thuần + 9,4% có lớp text nhưng là OCR rác). 38,4% file có trang
xoay; 24,4% có trang ngang; 12,3% scan dưới 150 DPI; 17,1% file trùng lặp.

**Trạng thái sau 2 đợt:** phủ CĐKT toàn corpus 28,7% (từ 18,8%); 49/300 file
vẫn bóc 0 ô; tier-1 66,1% đúng. Chi tiết: [ket-qua-dot-2.md](ket-qua-dot-2.md).

**Điểm yếu thuật toán còn lại (theo thứ tự nghiêm trọng):**
1. **Dò cột bằng heuristic.** `detect_code_column` chấm điểm cột theo "mã khớp
   khung + tăng dần"; `estimate_split`/`detect_value_columns` tìm khoảng trống
   giữa các mép phải. Không hề dựng lại cấu trúc bảng thật → sai khi bảng
   nghiêng, trang ngang, hoặc có cột Lũy kế.
2. **Không xử lý nghiêng/xoay.** 38,4% file có trang xoay mà pipeline không có
   bước deskew nào — Tesseract tụt độ chính xác rất nhanh khi ảnh nghiêng.
3. **Tiền xử lý ảnh tối thiểu.** Chỉ `grayscale + autocontrast`. Không khử
   nhiễu, không nhị phân hoá thích ứng — trong khi 12,3% scan dưới 150 DPI.

## 2. Khảo sát công cụ — lọc theo ràng buộc đóng gói

### Nhóm A — Dùng được ngay (không cần runtime nặng)

| Công cụ | Giải quyết góc độ nào | Phụ thuộc | Đánh giá |
|---|---|---|---|
| **[img2table](https://github.com/xavctn/img2table)** | **Dò cấu trúc bảng thật** (điểm yếu #1) | OpenCV, KHÔNG PyTorch | Tác giả nêu rõ là "phương án nhẹ thay cho mạng nơ-ron, nhất là khi chạy CPU". Hỗ trợ **bảng không kẻ viền**. Cắm được thẳng vào Tesseract đang dùng. **Ứng viên số 1.** |
| **[OCRmyPDF](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html)** (ý tưởng, không nhất thiết cả gói) | **Deskew/xoay** (điểm yếu #2) | Leptonica (đã có sẵn trong Tesseract) | Dùng thuật toán *Postl variance of line sums* của Leptonica. Thứ tự pipeline chuẩn: xoay → xoá nền → deskew → làm sạch. Ta có thể áp dụng chính ý tưởng này. |
| **[vietnamese-conversion](https://github.com/duydev/vietnamese-conversion)** / [py-unicode-convert](https://github.com/vuthaihoc/py-unicode-convert) | Giải mã TCVN3/VNI | Pure Python | **Chỉ hữu ích cho file Excel đáp án** (xem §3) |

### Nhóm B — Chính xác hơn nhưng KHÔNG đóng gói được

| Công cụ | Vì sao hấp dẫn | Vì sao loại |
|---|---|---|
| [PaddleOCR / PP-StructureV2](https://github.com/PaddlePaddle/PaddleOCR) | SLANet dò cấu trúc bảng rất mạnh; có [pipeline tiếng Việt](https://github.com/vitmetmoi/Vietnamese-OCR) fine-tune sẵn | Cần PaddlePaddle runtime — phá vỡ mốc 70 MB |
| [Table Transformer (TATR)](https://github.com/microsoft/table-transformer) | Chuẩn vàng học sâu cho cấu trúc bảng | PyTorch |
| [Surya](https://github.com/VikParuchuri/surya) | Phân tích bố cục mạnh nhất nhóm; hơn Tesseract 30–50% CER trên bố cục phức tạp | PyTorch |
| [VietOCR](https://github.com/pbcquoc/vietocr) (Transformer OCR tiếng Việt) | Chuyên tiếng Việt, tốt hơn Tesseract trên chữ viết tay/mờ | PyTorch |
| olmOCR / Qwen2.5-VL | Đọc theo ngữ cảnh, giữ được bảng | LLM đa phương thức — vừa nặng vừa vi phạm "không rời máy" nếu gọi API |

> **Ghi chú chiến lược:** nhóm B không phải bỏ đi vĩnh viễn. Chúng phù hợp cho
> một **"chế độ chính xác cao" tuỳ chọn** cài riêng trên MỘT máy mạnh của bộ
> phận kế toán (không phát cho toàn bộ người dùng), hoặc cho bản desktop mới
> (Tauri) vốn có kiến trúc sidecar. Không phù hợp cho bộ cài phổ thông.

## 3. Kiểm chứng: "mojibake" trong PDF KHÔNG phải lỗi bảng mã

Giả thuyết ban đầu (của tôi) là 273 file "có lớp text nhưng mojibake" bị lỗi
bảng mã TCVN3/VNI, nên chỉ cần thư viện chuyển mã là có text hoàn hảo, khỏi
OCR — tiết kiệm lớn. **Đã kiểm chứng trên file thật và BÁC BỎ:**

```
PDF  raw : CONG Ty co pHAN sxKD HANG xui.T KHAU rAN BiNH
     thật: CÔNG TY CỔ PHẦN SXKD HÀNG XUẤT KHẨU TÂN BÌNH
```

Chữ hoa/thường đảo lộn (`cHr`, `xui.T`) và nhầm r↔n, l↔i là **nhầm lẫn quang
học** — bảng mã sai không bao giờ làm đảo hoa/thường và luôn ánh xạ 1-1. Đây là
**OCR rác do phần mềm máy scan Canon nhúng sẵn**; thông tin đã mất thật, không
thư viện nào cứu được.

→ **Kết luận: cơ chế `is_usable` + quay về OCR mà ta đã xây là ĐÚNG.** Không
thêm thư viện chuyển mã cho đường PDF.

Ngược lại, **file Excel đáp án đúng là TCVN3 thật**, giải mã hoàn hảo:

```
raw    : C«ng ty CP Du LÞch §¨k L¨k       -> Công ty CP Du Lịch Đăk Lăk
raw    : B¸o c¸o kÕt qu¶ ho¹t ®éng...    -> Báo cáo kết quả hoạt động...
```

→ Đáng thêm thư viện chuyển mã **cho hạ tầng kiểm thử** (`groundtruth.py`) để
đối chiếu tên công ty khi lập cặp — đúng điểm yếu "tier-1 quá mỏng, ghép cặp
phải xác minh tay".

## 4. Đề xuất, xếp theo (tác động × khả thi) ÷ rủi ro

### ~~Đ1 — Deskew trước khi OCR~~ → **ĐÃ THỬ, ĐÃ BÁC BỎ (24/07/2026)**

Đề xuất ban đầu dựa trên hai giả định, **cả hai đều sai khi đo thật**:

**Giả định 1: "38,4% file có trang xoay nên cần nắn."** Sai — con số đó nói về
`/Rotate` (xoay vuông góc 90/180/270), mà **PyMuPDF đã tự xử lý**: `get_pixmap`
trả ảnh đã đứng thẳng (kiểm chứng trên file `/Rotate 270`: pixmap 596×842 khớp
`page.rect` 595×842). Không có vấn đề gì để sửa.

**Giả định 2: "ảnh scan nghiêng đáng kể, hại OCR."** Sai — đo 25 trang scan
ngẫu nhiên: **trung vị |góc| = 0,25°**, chỉ 1/25 trang vượt 1°, max 2,5°.

| |góc| | Số trang |
|---|---|
| > 0,25° | 7/25 |
| > 1,0° | 1/25 |
| > 2,0° | 1/25 |

**Thử A/B trên chính các trang nghiêng ≥0,5°** (đếm mã số Tesseract nhận được,
trước vs sau khi xoay bù):

```
TỔNG mã số: trước = 85   sau deskew = 85   (+0)
```

Một trang được thêm 1 mã, một trang mất 1 mã. **Lợi ích ròng bằng 0** —
Tesseract vốn đã chịu nghiêng tới 2,5° tốt trên loại tài liệu này.

**Thử tiếp trên đúng nhóm đích cuối cùng** (trang định vị được nhưng OCR ra 0
mã — nơi deskew sẽ đóng vai biến thể cứu hộ của V2): quét 60 file chỉ tìm được
**1 trang** như vậy, và trang đó nghiêng **0,00°** → deskew không thể cứu.
Tổng mã cứu được: **0**.

**Kết luận: KHÔNG làm deskew.** Nó sẽ thêm chi phí CPU (ước lượng góc + xoay
ảnh) vào một dự án vốn đã vượt ngân sách CPU 84%, để đổi lấy 0 ô dữ liệu.

> Bài học lặp lại lần thứ tư trong dự án này: mọi đề xuất dựa trên số liệu
> *mô tả corpus* ("38,4% file có trang xoay") phải được kiểm chứng bằng thí
> nghiệm *đo lợi ích thật* trước khi viết code. Ba lần trước: lớp text 12,2%
> (không phải "phần lớn"), khung QĐ15 (0 file — cùng mã với TT200), mojibake
> (OCR rác chứ không phải lỗi bảng mã).

### Đ2 — Thử img2table cho việc dò cột *(tác động cao, rủi ro trung bình)*

Thay heuristic dò cột bằng dựng lại cấu trúc bảng thật. Cách làm an toàn:
chạy **song song** với heuristic hiện tại trên sweep 300, so số ô đúng, chỉ
thay khi thắng rõ. OpenCV thêm ~60 MB vào bộ cài — chấp nhận được, nhưng phải
đo lại thời gian khởi động (đã tốn công tối ưu ở Đợt 1).

### Đ3 — Tiền xử lý thích ứng cho scan mờ *(tác động vừa, rủi ro thấp)*

12,3% scan dưới 150 DPI. Thêm nhị phân hoá thích ứng (Sauvola/adaptive
threshold) + khử nhiễu cho riêng nhóm DPI thấp, giữ nguyên đường xử lý cho
file rõ. Có OpenCV rồi thì gần như miễn phí.

### Đ4 — Giải mã TCVN3 trong bộ đọc đáp án *(tác động thấp, rủi ro rất thấp)*

Cho phép đối chiếu tên công ty khi lập cặp → mở rộng tier-1 từ 3 PDF lên nhiều
hơn mà vẫn an toàn. Thư viện pure-Python, không ảnh hưởng bộ cài.

### Đ5 — "Chế độ chính xác cao" tuỳ chọn *(để sau, cần bạn quyết)*

PaddleOCR/PP-Structure hoặc VietOCR cài riêng trên 1 máy mạnh, dùng cho các
file khó nhất (49 file còn bóc 0 ô, file ngân hàng). Không phát cho toàn bộ
người dùng. Là hướng tự nhiên cho bản desktop Tauri (đã có kiến trúc sidecar).

## 5. Giảm rủi ro fail — việc không liên quan thuật toán

Từ review tổng nhánh Đợt 2, đây là các rủi ro vận hành đáng lo hơn cả thuật toán:

1. **CI không chạy một test nào** — 301 test chưa từng chạy trên CI ở bất kỳ
   commit nào. Một lỗi làm vỡ bóc tách sẽ đi thẳng vào bộ cài phát cho người
   dùng. **Đây là rủi ro fail lớn nhất hiện tại, và sửa rất rẻ.**
2. **Test dựa corpus tự bỏ qua im lặng** — trên CI (không có corpus/tesseract)
   chúng skip, nên "suite xanh" trên CI sẽ không chứng minh được gì về chất
   lượng bóc tách. Cần tách bộ test không cần corpus và bắt CI chạy nó.
3. **tier-1 chỉ 3 PDF / 2 doanh nghiệp** — mỗi cải thiện đều rơi vào file mà
   bản sửa được phát triển trên đó. Cần thêm cặp có xác minh kỳ (Đ4 giúp việc này).
4. **`_KHO_ANH` là singleton mức module** — an toàn hôm nay vì xử lý tuần tự;
   sẽ đụng nhau nếu sau này chạy song song nhiều file.

**Thứ tự tôi đề xuất:** làm mục 1+2 (CI chạy test) TRƯỚC mọi thay đổi thuật
toán — vì không có lưới an toàn thì mọi tối ưu sau đều là đánh cược.

## Nguồn

- [img2table](https://github.com/xavctn/img2table) · [microsoft/table-transformer](https://github.com/microsoft/table-transformer) · [PdfTable toolkit](https://github.com/CycloneBoy/pdf_table)
- [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) · [OCRmyPDF advanced](https://ocrmypdf.readthedocs.io/en/latest/advanced.html)
- [vitmetmoi/Vietnamese-OCR (PaddleOCR fine-tune tiếng Việt)](https://github.com/vitmetmoi/Vietnamese-OCR) · [bmd1905/vietnamese-ocr](https://github.com/bmd1905/vietnamese-ocr)
- [vietnamese-conversion](https://github.com/duydev/vietnamese-conversion) · [py-unicode-convert](https://github.com/vuthaihoc/py-unicode-convert) · [vietnamese-encoding-converter](https://github.com/ultoxtung/vietnamese-encoding-converter)
- [Surya OCR](https://www.solosoft.dev/post/surya-ocr-2026/) · [Khảo sát OCR mã nguồn mở 2026](https://unstract.com/blog/best-opensource-ocr-tools/) · [A Survey on Vietnamese Document Analysis and Recognition](https://arxiv.org/html/2506.05061v1)
