# Benchmark độ chính xác — dữ liệu & định dạng ground-truth

Mục tiêu: đo độ chính xác đọc số **theo từng ô** trước/sau mỗi thay đổi (xem
`plans/260609-accuracy-and-performance/plan.md`).

## Thư mục
- `bench/pdfs/` — PDF BCTC thật (mỗi file một doanh nghiệp/kỳ). **Không commit lên GitHub** nếu nhạy cảm (đã đề xuất gitignore).
- `bench/truth/<tên-pdf>.json` — đáp án đúng (đã verify tay) cho file PDF tương ứng.
- `bench/score.py` — scorer (sẽ thêm ở bước B-A0).

## Định dạng `truth/<tên>.json`
Khóa báo cáo: `CDKT` (bảng cân đối), `KQHDKD` (kết quả KD), `LCTT` (lưu chuyển tiền tệ).
Mỗi mã số → `[số_cuối_năm, số_đầu_năm]` (tức `[năm nay, năm trước]`). Ô trống = `null`.
Số là **số nguyên** theo đúng đơn vị in trên báo cáo (không dấu phân tách).

```json
{
  "pdf": "CongTyABC_2023.pdf",
  "don_vi": "đồng",
  "CDKT":   { "100": [12345678, 11000000], "110": [5000000, 4200000], "270": [98765432, 90000000], "440": [98765432, 90000000] },
  "KQHDKD": { "01": [80000000, 75000000], "11": [60000000, 56000000] },
  "LCTT":   { "20": [3000000, 2500000] }
}
```
Chỉ cần điền những mã có trên báo cáo; thiếu mã = scorer bỏ qua (không tính sai).

## Cách tạo ground-truth nhanh (bán tự động — khuyến nghị)
Đỡ phải gõ tay toàn bộ:
1. Bỏ PDF vào `bench/pdfs/`.
2. Chạy app/CLI hiện tại để sinh **bản nháp** `truth/<tên>.json` từ kết quả OCR.
3. Mở file nháp, **chỉ sửa những ô sai** (đối chiếu PDF gốc) — ô tô cam trong Excel là gợi ý nên soát.
4. Lưu lại → thành ground-truth.

> Nếu anh đã có **Excel đúng** (đối chiếu tay từ trước), cứ đưa kèm vào `bench/truth/`;
> mình sẽ viết adapter đọc Excel đó → JSON chuẩn trên (cho mình biết layout cột).
