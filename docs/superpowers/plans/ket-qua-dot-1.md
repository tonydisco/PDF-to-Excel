# Kết quả Đợt 1 — Bộ đo, cắt tính toán thừa, đóng gói Windows

Ngày đo cuối: 2026-07-22 · Nhánh: `feat/nang-cap-do-chinh-xac-hieu-nang`
Mẫu đo cố định: seed 20260719 — 6 PDF tầng 1 (16 cặp đáp án) + 30 file tầng 2.
File số liệu: [baseline-2026-07-19.json](baseline-2026-07-19.json) · [sau-dot-1.json](sau-dot-1.json)
(`sau-gd1.json` là mốc trung gian trước guard fallback, giữ lại để đối chiếu.)

## 1. Bảng so sánh trước / sau

| Chỉ số | Trước | Sau | Thay đổi |
|---|---:|---:|---:|
| **CPU-giây** (chỉ số nhiệt) | 1.065,9 | 536,1 | **−49,7%** |
| Thời gian thực (s) | 273,7 | 216,0 | −21,1% |
| RSS đỉnh (MB) | 817,6 | 665,3 | −18,6% |
| Tầng 1 — đúng | 58 | 58 | 0 |
| Tầng 1 — sót | 350 | 350 | 0 |
| Tầng 1 — lệch | 36 | 36 | 0 |
| Tầng 1 — thừa | 10 | 10 | 0 |
| Độ phủ CĐKT | 11,1% | 11,1% | 0,0đ% |
| Độ phủ KQHDKD | 20,0% | 20,1% | +0,1đ% |
| Độ phủ LCTT | 12,8% | 12,8% | 0,0đ% |
| Cân đối đạt | 81,5% | 81,5% | 0,0đ% |

**Độ chính xác được bảo toàn đúng từng ô** — đó là thiết kế: Đợt 1 chỉ cắt
tính toán thừa và đóng gói, không đụng logic bóc tách. Toàn bộ mức giảm CPU
là "miễn phí" về mặt dữ liệu.

## 2. Đối chiếu tiêu chí nghiệm thu

| Tiêu chí | Ngưỡng | Kết quả | Trạng thái |
|---|---|---|---|
| **G4** — giảm nhiệt | CPU-giây −40% | **−49,7%** | ✅ ĐẠT |
| **G3** — khởi động Windows | ≤ 3 giây | Đã sửa gốc rễ (onedir + bộ cài Inno Setup + lazy import + splash); số đo thật cần máy Win10 + bộ cài từ CI | ⏳ CHỜ ĐO trên máy thật |
| **G5** — bộ nhớ máy 4 GB | RSS ≤ 250 MB | 665 MB (−18,6%) | ❌ CHƯA ĐẠT — xem §4 |
| **G1** — giảm sót/lệch | (chốt ngưỡng ở Đợt 2) | Baseline đã có: sót 350, lệch 36 / 454 ô | ✔ có mốc |
| **G2** — không mất dữ liệu âm thầm | 0 mã bị vứt không cảnh báo | Baseline đã có; sửa ở Đợt 2 (§7.6) | ✔ có mốc |

### Vì sao G5 chưa đạt — và vì sao điều đó đúng kế hoạch

Phần sửa bộ nhớ (render xám trực tiếp + truyền ảnh theo luồng, spec §8.1–8.2)
nằm ở **GĐ4 = Đợt 2**. Việc spec §2.1 xếp G5 vào tiêu chí Đợt 1 là **mâu thuẫn
phân đợt trong spec** — ghi nhận tại đây thay vì sửa lùi tiêu chí. Mức giảm
18,6% của Đợt 1 là hiệu ứng phụ của việc bớt lượt render (hoist locate_pages),
không phải fix chủ đích.

## 3. Nguồn gốc mức giảm CPU −49,7%

| Thay đổi | Cơ chế |
|---|---|
| Hoist `locate_pages` khỏi vòng DPI (T6) | Bỏ 1 lượt quét đầu-trang toàn tài liệu cho mỗi DPI phụ — trên file thử đơn lẻ đo được −37% CPU |
| Workers theo nhân thực, chừa headroom (T7) | Máy đo 10 nhân: 8 → 4 tiến trình tesseract; tổng CPU-giây giảm nhẹ do bớt tranh chấp, nhiệt đỉnh giảm mạnh (đỉnh %CPU ~50% thay vì ~100%) |
| Khử trùng lặp SHA-256 (T8) | Không phát huy trên mẫu 30 file (mẫu không chứa bản trùng) — trên corpus thật 17,1% file là bản sao, mức tiết kiệm sẽ lớn hơn số đo này |
| Đường text + guard (T9 + fix) | Xem §4 — hiện đóng góp ~0 |

## 4. Phát hiện quan trọng ngoài dự kiến

1. **Đường text hiện bóc được 0 giá trị trên MỌI file text-usable của corpus.**
   Bộ lọc mojibake hoạt động đúng, nhưng hình học của `get_text("words")`
   (mã số và giá trị nằm ở block PDF khác nhau; trang ngang 4 cột) khiến
   parser hiện tại không gán được giá trị nào. Guard đã thêm: text-path ra
   0 giá trị → log `↻` → tự quay về OCR. **Chất lượng dữ liệu về đúng mức
   OCR ở mọi nơi; lợi ích tốc độ của đường text tạm bằng 0** cho tới khi
   Đợt 2 sửa hình học parser (§7.2/§7.5 — gom cụm theo toạ độ y xuyên block).
   Hạ tầng text-layer + bộ lọc đã sẵn sàng để hưởng lợi ngay khi đó.

2. **Dự đoán spec §7.1 không hiện ở mức tổng** (đã ghi chú vào spec): độ phủ
   KQ (20%) cao hơn CĐKT (11%) chứ không thấp hơn — chữ ký của lỗi mã 01–09
   bị che bởi thất bại bóc tách diện rộng. Lỗi vẫn đúng ở mức đơn vị.
   **Đợt 2 phải mở màn bằng chẩn đoán per-file các ca bóc-ra-0** (4/6 PDF
   tầng 1 gần như trắng) trước khi quy công cho bất kỳ hạng mục §7 nào.

3. **Baseline tệ hơn spec ước tính nhiều**: chỉ 12,8% ô đúng trên bộ đáp án.
   Đây là con số trung thực đầu tiên về chất lượng thật của app — và là lý do
   bộ đo (GĐ0) đáng giá: mọi tuyên bố cải thiện từ nay có mốc để chứng minh.

## 5. Đóng gói Windows (GĐ2) — thay đổi hành vi người dùng

- **Trước:** 1 file `.exe` onefile + UPX → tự giải nén toàn bộ ra `%TEMP%`
  mỗi lần mở, Defender quét lại từ đầu → 30–90s trên máy HDD.
- **Sau:** CI xuất **bộ cài `BCTC_PDF_to_Excel-Setup.exe`** (Inno Setup,
  cài được không cần quyền admin) → giải nén một lần lúc cài; app onedir
  + lazy import + splash. Tesseract đóng gói rút gọn (exe + DLL + vie/eng/osd),
  `vie.traineddata` hết bị gói hai lần.
- **Số đo G3 thật** (mở nguội ≤3s) đo trên máy Win10 thật sau khi cài bản
  Setup từ artifact CI của lần push này — 3 lần, lấy trung vị.

## 6. Sai lệch so với kế hoạch (khai báo đầy đủ)

| Kế hoạch nói | Thực tế làm | Lý do |
|---|---|---|
| Đáp án "187 cặp" | 16 cặp / 6 PDF sau cổng xác nhận tay | Ghép ngây thơ tạo cặp sai công ty/cơ sở lập — thà ít mà đúng |
| Task 14 đo `--tier2-sample 300` | Đo mẫu 30 cố định (so sánh cùng-mẫu chặt); sweep 300 dời sang mở màn Đợt 2 | So sánh khác cỡ mẫu không hợp lệ về thống kê; sweep 300 kiêm luôn vai trò chẩn đoán Đợt 2 |
| Review từng task 10–13 | Gộp vào review tổng cuối nhánh | Yêu cầu tăng tốc của người dùng; cổng chất lượng vẫn phủ toàn nhánh |
| §7.1 dự đoán KQ/LC phủ thấp | Không hiện ở mức tổng | Ghi chú vào spec, chẩn đoán per-file dời Đợt 2 |

## 7. Tồn đọng chuyển Đợt 2

- G5 (RSS 665 MB → ≤250 MB): render xám + streaming ảnh (§8.1–8.2).
- Hình học text-layer (§7.2/§7.5) để đường text thật sự phát huy.
- Chẩn đoán per-file 4 ca bóc-ra-0 của tầng 1 + sweep tier2 n=300.
- Toàn bộ hạng mục độ chính xác §7 (mã 01–09, split_values, đơn vị tính,
  trang 2 tiêu đề, QĐ15, B05/TCTD, mã ngoài khung).
- Danh sách Minor tồn đọng: xem `.superpowers/sdd/progress.md` (đã được
  review tổng cuối nhánh phân loại giữ/sửa).

## 8. Bổ sung sau khi hợp nhất với `main` (2026-07-22)

Nhánh được rebase lên `origin/main` (28 commit song song: app desktop mới +
cải tiến parser cột Quý). Giao nhau thật sự chỉ 3 file; pipeline CI Tkinter
tách sang `build-tkinter.yml`, pipeline desktop của main giữ nguyên.

Đo lại trên đúng mẫu cố định, sau hợp nhất ([sau-merge-main.json](sau-merge-main.json)):

| Chỉ số | Đợt 1 (trước merge) | Sau merge | Diễn giải |
|---|---:|---:|---|
| CPU-giây | 536 | 539 | Mức giảm −50% GIỮ NGUYÊN sau merge |
| Tầng 1 — sót | 350 | **308** | Parser cột Quý của main bóc được nhiều hơn |
| Tầng 1 — lệch | 36 | **79** | Nhiều ô mới không khớp đáp án — nghi sai cặp cột Kỳ này/Lũy kế |
| Tầng 1 — đúng | 58 | 57 | Ròng chưa đổi |
| Độ phủ KQHDKD | 20,1% | 25,8% | |
| Cân đối đạt | 81,5% | 83,9% | |

Kết luận: hai dòng công việc bổ trợ nhau — main tăng ĐỘ PHỦ, Đợt 1 cung cấp
THƯỚC ĐO cho thấy phần phủ thêm đang lệch đáp án ở đâu. Việc Đợt 2 cần làm
đầu tiên: đối chiếu quy tắc chọn cặp cột (Kỳ này vs Lũy kế) với kỳ của file
đáp án — 43 ô lệch mới nhiều khả năng cùng một nguyên nhân này.
