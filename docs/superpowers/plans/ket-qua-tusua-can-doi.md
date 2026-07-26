# Kết quả tự sửa lỗi OCR 1 chữ số bằng cân đối — nghiệm thu sweep 300

Ngày 26/07/2026. Tính năng: commit `e26ab4f` (+ lõi `e04ab28`). Đo thuần PDF
(`--tier2-sample 300 --skip-tier1`), không đọc file đối chiếu nào.

## Con số chính thức

| Chỉ số (300 file) | Trước | Sau |
|---|---:|---:|
| Tỷ lệ cân đối đạt | 77,0% | 76,8% (phẳng, trong nhiễu) |
| File cân đối đạt hết | 89 | **90** (+1) |
| Độ phủ CĐKT | 28,7% | 28,7% |
| CPU-giây | 8191 | 7736 (−5,6%, nhiễu giữa 2 lần chạy) |

Đếm sâu trên 30 file cân đối hỏng: tính năng **kích hoạt trên 1 file, sửa 1 ô**
(mã 400: `271.585.493.449 -> 277.585.493.449` — sửa đúng 1 chữ số, giá trị lệch
6 tỷ đồng). 5 file "khớp lại" trong đó **4 là do OCR chạy sạch hơn ngẫu nhiên**
(tesseract không hoàn toàn tất định), chỉ 1 do tính năng này.

## Đánh giá trung thực

**Chẩn đoán ước tính ~14/85 file là QUÁ LẠC QUAN.** Thực tế kích hoạt rất hiếm
(~3% file cân đối hỏng). Ba lý do:

1. Phần lớn lỗi cân đối là lỗi **cấu trúc / nhiều chữ số**, không phải 1 chữ số
   (chính chẩn đoán đã đo: DIGIT chỉ 22% số cột lỗi; MULTI/OTHER 33%,
   COLUMN-STRUCTURE 27%).
2. Đường **thành phần** thường nhập nhằng (cả hai thành phần đều bù được 1 chữ
   số) → bỏ qua an toàn, không sửa.
3. **Oracle nghiêm ngặt**: re-OCR phải khớp CHÍNH XÁC mục tiêu; ô scan xấu đọc
   lại vẫn sai thì không nhận.

## Vì sao GIỮ LẠI (dù lợi ích nhỏ)

Khác với deskew / img2table / khử nhiễu (đã bỏ vì **lợi ích 0 hoặc âm** — tốn
CPU không đổi lấy gì), tính năng này là **lợi ích dương nhỏ ở chi phí gần 0**:

- **Chỉ tốn OCR khi cân đối HỎNG + lệch đúng 1 chữ số** — file bình thường tốn 0;
  CPU toàn sweep không tăng (đo được −5,6%, tức trong nhiễu).
- Khi kích hoạt, nó **sửa một lỗi vật chất** (ví dụ 6 tỷ đồng) và **tô cam +
  ghi log** để người soát — không âm thầm.
- **An toàn ba lớp** (khoanh + cổng 1-chữ-số + oracle) và bọc try/except: không
  bao giờ làm bóc tách tệ đi. Đã xác nhận: không file nào tệ đi, độ phủ không đổi.
- CI xanh cả 4 job trên `main`.

Đây là bản vá **độ chính xác điểm** (precision), không phải phủ diện rộng. Nó
đúng tinh thần "không lệch data" cho những ô nó chạm tới, chỉ là số ô ít.

## Bài học lặp lại

Đây là lần thứ NĂM một ước tính bị số đo thu nhỏ lại: lớp text 12,2% (không phải
"phần lớn"), QĐ15 0 file, mojibake không cứu được, deskew/img2table/khử nhiễu
lợi ích 0 — và giờ tự-sửa-cân-đối ~+1 thay vì ~14. Điểm khác biệt: bốn cái đầu
bị BỎ vì âm/0, cái này GIỮ vì dương-nhỏ-chi-phí-gần-0. Nguyên tắc nhất quán:
giữ nếu (an toàn ∧ lợi ích dương ∧ chi phí ~0), bỏ nếu (âm ∨ rủi ro).
