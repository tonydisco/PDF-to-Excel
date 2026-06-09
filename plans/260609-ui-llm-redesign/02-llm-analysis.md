# Thiết kế #4 — Hệ thống hybrid LLM: phân tích tài chính & đánh giá rủi ro

> Ngày 2026-06-09 · Tài liệu THIẾT KẾ. Ràng buộc privacy đã CHỐT (§2).

## 1. Mục tiêu
Sau khi bóc số BCTC, cung cấp tính năng **nâng cao** dùng LLM cloud:
- **Phân tích báo cáo tài chính**: cơ cấu tài sản/nguồn vốn, thanh khoản, đòn bẩy, sinh lời, dòng tiền, xu hướng năm nay vs năm trước.
- **Đánh giá rủi ro doanh nghiệp**: rủi ro thanh khoản/khả năng thanh toán, đòn bẩy, chất lượng lợi nhuận, cảnh báo phá sản (Altman Z″), xếp hạng rủi ro định tính.

## 2. Ranh giới dữ liệu (ĐÃ CHỐT — keystone)
> **Chỉ CHỈ SỐ/TỈ SỐ TỔNG HỢP rời máy. KHÔNG bao giờ gửi PDF scan hay bản gốc.**

- Gửi lên cloud: **JSON các con số đã bóc + tỉ số tính sẵn** (xem §4). Tuỳ chọn **ẩn danh** (bỏ tên DN) mặc định bật.
- KHÔNG gửi: ảnh PDF, file Excel thô, tên file, thông tin định danh khác.
- **Minh bạch:** trước mỗi lần gọi, UI hiện **đúng payload sẽ gửi** + nút đồng ý. **Opt-in từng lần** (mặc định tắt). Đây là quyết định privacy MỚI, KHÁC với "gửi ô OCR nghi ngờ" — nên tách bạch rõ.

## 3. Kiến trúc hybrid (nguyên tắc cốt lõi)
> **Số học tính LOCAL & tất định; LLM chỉ DIỄN GIẢI. Không để LLM tự tính/bịa số** (cùng triết lý "không bịa số cho khớp cân đối" của B-A3).

```
bctc results {code:(cur,prior)}            (local)
        │
        ▼  ratio_engine.py  (local, tất định)   ← tính mọi tỉ số, Z-score, Δ năm
   indicators.json {ratios, flags, yoy}
        │  (chỉ phần này, sau khi user đồng ý)
        ▼  AI SDK -> cloud LLM
   nhận: nhận định + xếp hạng rủi ro + cảnh báo, THAM CHIẾU số do ta cung cấp
        │
        ▼  hiển thị trong UI (#3) + xuất kèm Excel/PDF
```

- **`ratio_engine.py` (local, mới):** đầu vào là results đã bóc, tính tất định: thanh khoản, đòn bẩy, sinh lời, hoạt động, dòng tiền, tăng trưởng, Altman Z″. Trả `indicators` + cờ ngưỡng (vd current<1 → cảnh báo). Phần này chạy được **không cần cloud**.
- **LLM:** chỉ nhận `indicators`, sinh **diễn giải + đánh giá rủi ro** bằng tiếng Việt, **trích dẫn đúng tỉ số ta đưa**, không tự tính lại.

## 4. Dữ liệu gửi đi (`indicators` schema — ví dụ)
Tính từ mã Thông tư 200 (CDKT/KQHDKD/LCTT). Ví dụ rút gọn:
```json
{
  "ky": {"nam_nay": 2025, "nam_truoc": 2024},
  "quy_mo": {"tong_tai_san_270": 805132153565, "von_chu_400": ...},
  "thanh_khoan": {"current_ratio": 1.42, "quick_ratio": 0.98, "tien_mat_110": ...},
  "don_bay": {"no_tren_von_chu": 0.83, "no_tren_tong_ts_300_270": 0.45},
  "sinh_loi": {"ROA": 0.07, "ROE": 0.15, "bien_LN_gop": 0.31, "bien_LNST": 0.08},
  "hoat_dong": {"vong_quay_ts": 0.9, "vong_quay_HTK": ..., "vong_quay_phai_thu": ...},
  "dong_tien": {"CFO_20": ..., "CFO_tren_no_ngan_han": 1.1},
  "tang_truong": {"doanh_thu_yoy": 0.12, "LNST_yoy": -0.05},
  "altman_z2": 5.1,
  "co_canh_bao": ["quick_ratio<1", "LNST_yoy<0"]
}
```
> Mỗi tỉ số kèm công thức + mã nguồn (vd `ROA = LNST_60 / TS_270`) để LLM hiểu và để **kiểm toán được** số đã gửi.

## 5. Provider, khoá, model
- **Vercel AI SDK** (model-agnostic). Mặc định qua **AI Gateway** (`"provider/model"`) để dễ đổi model + có observability; hoặc trực tiếp Anthropic nếu anh muốn.
- **Khoá API do người dùng tự cung cấp**, lưu ở **OS keychain** (Keychain/Credential Manager), không hardcode, không commit.
- Mặc định model mạnh cho phân tích (vd Claude Opus/Sonnet 4.x); cho phép đổi.
- **Zero data retention** nếu provider hỗ trợ (AI Gateway có).

## 6. Tính năng
### 6.1 Phân tích báo cáo tài chính
- Cơ cấu tài sản/nguồn vốn (% trên tổng), so sánh năm nay vs năm trước.
- Đánh giá 5 nhóm: thanh khoản, đòn bẩy, sinh lời, hiệu quả hoạt động, dòng tiền.
- Output: nhận định ngắn gọn theo nhóm + điểm mạnh/yếu, **dẫn số cụ thể**.

### 6.2 Đánh giá rủi ro DN
- Tổng hợp cờ ngưỡng (local) + Altman Z″ + diễn giải LLM → **xếp hạng rủi ro** (Thấp/Trung bình/Cao) kèm lý do.
- Cảnh báo cụ thể: mất cân đối vốn lưu động, đòn bẩy cao, dòng tiền HĐKD âm, lợi nhuận giảm, Z″ trong vùng nguy hiểm.
- **Không** đưa lời khuyên đầu tư; chỉ phân tích dựa trên số.

## 7. UX đồng ý (consent)
1. User bấm "Phân tích" → panel hiện **payload `indicators` sẽ gửi** (đọc được) + provider/model + "ẩn danh: bật".
2. Bấm Đồng ý → gọi LLM (streaming kết quả).
3. Kết quả hiển thị + lưu kèm file; có thể xuất ra Excel/PDF báo cáo.

## 8. Chi phí, lỗi, fallback
- Payload nhỏ (chỉ tỉ số) → chi phí thấp/lần. Hiện ước tính token trước khi gửi.
- Lỗi mạng/khoá → báo rõ, **ratio_engine vẫn cho kết quả định lượng local** (tỉ số + cờ) dù không có diễn giải LLM.
- Tuỳ chọn **LLM local (Ollama)** sau này cho ai muốn 100% offline (chất lượng thấp hơn).

## 9. Lộ trình
- **P0 (không cần cloud):** `bctc/ratio_engine.py` tất định + hiển thị tỉ số/cờ trong UI. Giá trị ngay, không rủi ro privacy.
- **P1:** tích hợp LLM (consent UX + AI SDK) cho diễn giải + rủi ro.
- **P2:** xuất báo cáo phân tích (Excel/PDF), so sánh nhiều DN/nhiều kỳ.

## 10. Rủi ro & lưu ý
- **Chất lượng số đầu vào:** phân tích chỉ đúng khi bóc đúng → gắn với độ chính xác (#1/B-A3) và cờ "ô nghi ngờ". Hiện cảnh báo nếu CDKT lệch cân đối.
- **LLM không tính số:** ràng buộc bằng prompt + chỉ cấp số tính sẵn; hiển thị nguồn từng tỉ số.
- Mẫu ngân hàng/TCTD có bộ chỉ tiêu khác → ratio_engine cần nhánh riêng (gắn với coverage ngân hàng còn tồn).
