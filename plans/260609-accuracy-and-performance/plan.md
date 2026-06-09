# Kế hoạch cải thiện hiệu suất & độ chính xác — BCTC PDF→Excel

> Ngày: 2026-06-09 · Nhánh: `feat/accuracy-and-performance`
> Tham khảo kiến trúc: [phuc-nt/scan-to-ebook](https://github.com/phuc-nt/scan-to-ebook) (pipeline OCR scan→EPUB, có benchmark OCR ground-truth).

## 0. Bối cảnh & mục tiêu

Project hiện bóc số liệu BCTC (PDF scan) theo khung Thông tư 200 bằng **Tesseract local**,
multi-DPI consensus + tô cam ô nghi ngờ + tự kiểm cân đối. Hai mục tiêu:

1. **Hiệu suất** — giảm thời gian/file, có resume cho batch lớn.
2. **Độ chính xác đọc số** — đo được, rồi giảm lỗi OCR có hệ thống.

### Quyết định đã chốt (2026-06-09)
- **Khẩu vị privacy:** hybrid — ưu tiên local; **được phép gửi cloud CHỈ cho ô lệch cân đối / nghi ngờ**, có xác nhận rõ của người dùng. (Đúng roadmap "hybrid" trong `TECHSTACK.md`.)
- **Dữ liệu:** có sẵn PDF BCTC thật + số đúng → dựng được benchmark.
- **Ưu tiên:** chạy **song song** cả hai trục; làm P1 + A0 trước.

### Bài học cốt lõi từ scan-to-ebook
- **Đo trước, tối ưu sau:** họ có report benchmark chấm điểm OCR theo ground-truth (char-sim, Δdấu, fails, cost, latency) → mọi quyết định model đều có số. Ta đang thiếu hoàn toàn lớp đo này.
- **Context pre-pass:** đọc trước vài trang rút ngữ cảnh rồi nhồi vào từng trang → nhất quán.
- **Vận hành:** resumable qua filesystem state, retry+backoff, atomic write, parallel workers, dry-run/smoke cost-gate.

---

## Trục A · Hiệu suất (local, độ tin cậy cao)

### A-P1 · Sửa bug định vị trang lặp lại  ⭐ làm trước
**Vấn đề (đã xác nhận trong code):** `bctc/parser.py` → `extract_consensus()` gọi `extract()` một lần cho mỗi DPI; mỗi `extract()` lại chạy `locate_pages()` (quét dải đầu *mọi* trang ở 135 DPI). ⇒ định vị bị lặp **2× (3× ở HQ)** với input y hệt.
**Sửa:** tách `locate_pages()` ra ngoài vòng lặp DPI — định vị **1 lần**, truyền `scope` (list trang + nhãn báo cáo) vào `extract()` để tái dùng.
**Lợi:** bỏ 1–2 lượt quét toàn bộ trang/ file. **Rủi ro:** thấp; kết quả định vị không phụ thuộc DPI render chính.
**Đo:** thời gian/file trên benchmark trước/sau.

### A-P2 · Resumable + skip file đã xong
- Bỏ qua PDF đã có `.xlsx` đầu ra hợp lệ (skip nhanh khi re-run batch 150 file).
- (Tùy chọn) cache kết quả OCR theo `(file, trang, dpi)` xuống `work/` để đổi tham số parser mà không OCR lại — ghi **atomic** (tmp + `os.replace`) như scan-to-ebook.

### A-P3 · Giảm OCR thừa
- Tái dùng OCR dải đầu (bước locate) cho pass chính khi trùng vùng/DPI thay vì OCR lại từ đầu trang.
- Cân nhắc đưa `MAX_WORKERS` & DPI vào tùy chọn nâng cao.

---

## Trục B · Độ chính xác (gated trên benchmark A0)

### B-A0 · Benchmark ground-truth + scorer  ⭐ nền tảng, làm trước
Không có lớp này thì mọi thay đổi accuracy đều không kiểm chứng được.
- **Input:** PDF thật ở `bench/pdfs/`, đáp án ở `bench/truth/<tên>.json` (định dạng: xem `bench/README.md`).
- **Scorer (`bench/score.py`):** chạy pipeline hiện tại trên từng PDF, so **theo từng ô** với truth →
  - *cell accuracy* = số ô đúng / tổng ô có giá trị (tách riêng đúng-dấu, sai chữ số, thiếu ô);
  - *balance-pass rate* (đang có trong `engine._check_balance`);
  - thời gian/file.
- **Output:** bảng Markdown (giống `report.md` của scan-to-ebook) → so sánh trước/sau mỗi thay đổi.

### B-A1 · Pass OCR whitelist chữ số cho cột số
OCR riêng vùng 2 cột số với `tessedit_char_whitelist=0123456789.,()-` + `--psm` phù hợp ô số → giảm nhầm `0/O`, `1/l`, `8/B`. Giữ pass chữ hiện tại cho cột chỉ tiêu/mã. *(local, rẻ, leverage cao)*

### B-A2 · Tiền xử lý ảnh: deskew + binarize
Thêm deskew (ước lượng góc nghiêng) + nhị phân hóa Otsu/adaptive trước OCR — bản scan nghiêng hiện làm lệch `detect_code_column`/`estimate_split`. *(local)*

### B-A3 · Dùng cân đối để ĐỊNH VỊ & gợi ý sửa ô sai
Hiện chỉ *flag* (tô cam) khi 2 DPI lệch. Nâng cấp: khi `100+200≠270` (hoặc `300+400≠440`, `270≠440`), suy ra **ô khả nghi nhất** và kiểm giả thuyết "lỗi 1 chữ số / mất dấu chấm nghìn" → đề xuất giá trị sửa. Đây là backstop cho **lỗi hệ thống mà consensus bỏ lọt**.

### B-A4 · Context pre-pass thu hẹp (cho BCTC)
Khác scan-to-ebook (ta đã có khung cố định → nhãn sạch sẵn). Pre-pass ở đây chỉ phát hiện:
- **biến thể template:** T200 / mẫu tổ chức tín dụng (ngân hàng) / tiếng Anh;
- **đơn vị & thang:** đồng / nghìn đồng / triệu đồng;
- **thứ tự cột năm:** cuối năm↔đầu năm.
→ nạp vào parser để chọn đúng khung & quy đổi.

### B-A5 · (Tùy chọn) VLM chạy LOCAL cho trang/ô điểm thấp
Ollama + qwen-VL (hoặc tương đương) đọc lại trang/ô có conf thấp hoặc lệch cân đối — đạt độ chính xác kiểu scan-to-ebook **mà dữ liệu vẫn không rời máy**. **Cần validate** throughput/độ chính xác trên máy này trước khi cam kết.

### B-A6 · (Opt-in) Cloud VLM chỉ cho ô flagged
Đúng khẩu vị đã chốt: chỉ gửi **ô lệch cân đối/nghi ngờ** (không gửi cả trang/cả file) lên VLM cloud, có **consent rõ** mỗi lần. Retry+backoff, atomic. Tắt mặc định.

---

## Lộ trình (milestones)

| Mốc | Nội dung | Cần dữ liệu? |
|---|---|---|
| **M1** | A-P1 (sửa bug locate) + B-A0 (benchmark + scorer) | A0 cần PDF mẫu |
| **M2** | B-A1 (whitelist số) + B-A2 (deskew/binarize) — đo bằng benchmark | có |
| **M3** | B-A3 (balance-repair) + A-P2 (resumable) | có |
| **M4** | B-A4 (pre-pass template/đơn vị) | có |
| **M5** | B-A5 (VLM local) / B-A6 (cloud flagged) — theo kết quả M2–M4 | có |

Nguyên tắc: **mỗi thay đổi accuracy phải chạy qua benchmark** và ghi số trước/sau vào `plans/260609-accuracy-and-performance/results.md`.

## Rủi ro & lưu ý
- Benchmark nhỏ (vài file) dễ overfit → cần đủ đa dạng mẫu (nhiều DN, có cả mẫu lệch cân đối thật).
- Whitelist số có thể bỏ sót token số viết lẫn chữ → giữ pass chữ làm fallback.
- VLM local phụ thuộc tài nguyên máy (máy này: arm64, brew ở /usr/local) — đo trước khi cam kết.
