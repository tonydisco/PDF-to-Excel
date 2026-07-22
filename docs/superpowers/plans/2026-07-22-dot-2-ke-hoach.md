# Kế hoạch Đợt 2 — Độ chính xác + Bộ nhớ

Nền tảng: [chẩn đoán mở màn](chan-doan-dot-2.md) · [baseline sạch](baseline-dot-2-sach.json)
· [sweep 300 file](sweep-300-dot2.json). Nhánh: `feat/dot-2-chinh-xac-va-bo-nho`.

## Trạng thái vào đợt (sau 3 việc mở màn đã xong)

- Thước đo đã sạch: pairs v2 (7 cặp/3 PDF, 160 ô), bộ đọc đáp án đã sửa 3 lỗi.
- Fix #1 (cặp cột Kỳ này/Kỳ trước) đã hạ cánh: tier-1 **97/45/11/6 = 60,6% đúng**.
- Sweep 300: phủ CĐKT 18,8% / KQ 35,0% / LC 26,0%; **90/300 file bóc 0 ô CĐKT**.
- RSS đỉnh 992 MB (lượt 300 file) — G5 chưa đạt.

## Ngưỡng nghiệm thu Đợt 2 (chốt trên số liệu sạch)

| Tiêu chí | Ngưỡng | Mốc hiện tại |
|---|---|---|
| **G1** — sót+lệch tier-1 giảm ≥50% so baseline sạch | ≤ 43 ô (87 → 43) | 56 |
| **G1b** — phủ corpus (sweep 300 chạy lại cuối đợt) | CĐKT ≥ 28%; nhóm-0 ≤ 60 file | 18,8%; 90 file |
| **G2** — không mất dữ liệu âm thầm | Mã ngoài khung phải hiện ra + cảnh báo | chưa có |
| **G5** — bộ nhớ | RSS đỉnh ≤ 250 MB trên lượt đo chuẩn n=30 | 665–733 MB |
| G3/G4 | Không xấu đi (CPU-giây ±10%, khởi động giữ nguyên cơ chế) | CPU ~536s |

## Các khối việc (thứ tự thực thi = thứ tự tác động kỳ vọng)

### V1 — Gom trang tiếp diễn vào scope *(nghi phạm chính của phủ CĐKT thấp)*

CĐKT dài 2–3 trang nhưng `locate_pages` chỉ giữ trang CÓ tiêu đề; trang tiếp
diễn không lặp tiêu đề bị vứt (bằng chứng: BCTC 6T Tân Bình mất CĐKT p4–p5,
LCTT p8). Sửa: sau khi định vị, mở rộng scope — trang nằm giữa một trang báo
cáo và mốc kế tiếp (tiêu đề khác / trang thuyết minh) được gán vào báo cáo
đứng trước, có trần K trang và điều kiện dừng (gặp text "thuyết minh"/mật độ
mã số = 0 ở 2 trang liên tiếp). Nghiệm thu: phủ CĐKT tier-2 n=30 tăng rõ;
tier-1 không xấu đi; CPU tăng có kiểm soát (log số trang thêm).

### V2 — Cứu OCR trang sập

Trang được định vị nhưng OCR ra <N dòng hoặc 0 mã số (BCTC-2023: LCTT thành
ký tự ống, CĐKT p3 còn 8 dòng) → thử lại trang đó ở DPI cao hơn + PSM khác,
lấy kết quả tốt hơn theo số mã khớp. Nhắm thẳng 35 sót còn lại của BCTC-2023.

### V3 — Phân loại nhóm-0 (90 file bóc 0 ô)

Chẩn đoán read-only trên 90 file của sweep: locate có thấy tiêu đề không? Có
phải B05/TCTD (từ vựng ngân hàng)? QĐ15 (trước 2015)? Mảnh 1 trang? Mojibake?
Ra bảng phân loại đếm được → quyết định V4 làm khung nào trước (có thể chỉ
một loại đáng làm trong đợt này).

### V4 — Khung bổ sung theo kết quả V3

QĐ15 (B01/B02/B03 cũ) và/hoặc B05/TCTD — chỉ làm nhánh có số lượng file lớn
theo V3; nhánh còn lại ghi nhận là hạn chế nếu ít. Nhận diện bằng từ vựng
đặc trưng trong nội dung, không dùng tên file.

### V5 — G5 bộ nhớ: render xám + streaming (§8.1–8.2 spec)

`get_pixmap(colorspace=csGRAY)` + hàng đợi render 1 luồng → N luồng OCR
(`queue.Queue(maxsize=workers+1)`), mọi `get_pixmap` ở đúng một luồng.
Trần điểm ảnh ≈4MP cho file 3,8 MB/trang (§8.3). Nghiệm thu: RSS ≤ 250 MB
trên lượt n=30, kết quả bóc tách không đổi từng ô.

### V6 — Gói G2 + vệ sinh nhỏ

- §7.6: mục "Mã ngoài khung" cuối sheet Excel + cảnh báo — đóng G2.
- §7.3: nhận diện đơn vị tính, ghi đúng vào A2 + cảnh báo khi khác VND
  (không tự quy đổi).
- §7.1 thu hẹp: nới find_code_at cho mã 1 chữ số (KHÔNG đụng
  detect_code_column — chẩn đoán chứng minh nới ở đó gây hại).
- §7.9: chặn PDF 0 byte/hỏng với thông báo tử tế (một phần đã có).

### V7 — Nút chế độ hiệu năng trên GUI

`app.py`: chọn Tiết kiệm điện / Cân bằng / Tối đa (MODE_LABELS đã có sẵn từ
Đợt 1), truyền `mode` xuống `convert_many`. Mặc định Cân bằng.

### V8 — Chốt đợt

Đo đầy đủ: tier-1 pairs v2 + tier-2 n=30 + sweep 300 chạy lại. Báo cáo
`ket-qua-dot-2.md` đối chiếu từng ngưỡng. Review tổng nhánh. Merge `main`,
push, CI build.

## Ngoài phạm vi đợt này

Hình học text-layer (để đường text phát huy — cần V1/V2 ổn định trước);
ghép báo cáo tách rời nhiều PDF; mẫu chứng khoán ORS; tiếng Anh; ký số.
