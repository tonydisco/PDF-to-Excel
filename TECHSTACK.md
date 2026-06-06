# Đề xuất công nghệ & lý do lựa chọn

Tài liệu này giải thích **techstack** của công cụ và vì sao đây là lựa chọn phù hợp nhất cho bài toán: chuyển **Báo cáo tài chính PDF (bản scan)** sang **Excel** trên cả Windows lẫn macOS.

## Tóm tắt stack

| Lớp | Công nghệ chọn | Vai trò |
|---|---|---|
| Ngôn ngữ | **Python 3.9+** | Chạy đa nền tảng (Windows/macOS), hệ sinh thái OCR/Excel mạnh |
| Đọc PDF → ảnh | **PyMuPDF (fitz)** | Render trang scan ra ảnh độ phân giải cao, rất nhanh |
| OCR | **Tesseract 5 + gói `vie`** (qua **pytesseract**) | Nhận dạng chữ & số tiếng Việt, **chạy offline** |
| Xử lý ảnh | **Pillow** | Chuyển xám, tăng tương phản trước khi OCR |
| Bóc tách | **Mã nguồn riêng** (`parser.py` + khung Thông tư 200) | Định vị báo cáo, dò cột Mã số, tách 2 cột số |
| Xuất Excel | **openpyxl** | Tạo `.xlsx` nhiều sheet, định dạng số, tô màu |
| Giao diện | **Tkinter/ttk** (chuẩn trong Python) | App cửa sổ, đóng gói gọn nhất |
| Đóng gói | **PyInstaller** | Tạo `.exe` (Windows) và `.app` (macOS) |

## Vì sao những lựa chọn này?

**Python** là nền tảng hợp lý nhất: cùng một mã nguồn chạy được trên Windows và macOS, và có sẵn mọi thư viện cần cho OCR + Excel. Không cần hai codebase riêng.

**OCR là bắt buộc, không phải tùy chọn.** Khảo sát 44 file thực tế cho thấy **42/44 là bản scan** (ảnh, không có text). Vì vậy đây **không** phải bài toán "đọc text PDF" — mà là bài toán OCR. Đã chọn **Tesseract** (mã nguồn mở, miễn phí, có gói tiếng Việt) chạy **ngay trên máy**, để **dữ liệu kiểm toán nhạy cảm không bao giờ rời máy** — ưu tiên hàng đầu với báo cáo tài chính.

**Bóc tách theo khung Thông tư 200 thay vì OCR cả bảng.** Đây là quyết định cốt lõi giúp kết quả chính xác:
- Báo cáo theo Thông tư 200 có **Mã số chỉ tiêu cố định** (100, 110, 270, 440…).
- Công cụ chỉ cần OCR đúng **Mã số** và **con số**, rồi điền vào **khung chỉ tiêu chuẩn** — nhãn chỉ tiêu lấy từ khung nên **luôn sạch**, không bị lỗi OCR.
- Vị trí cột Mã số khác nhau giữa các mẫu (bên trái hoặc giữa trang) → parser **tự dò đúng cột** bằng cách tìm cột có dãy mã khớp khung và **tăng dần theo thứ tự** template.

**Tự kiểm tra cân đối.** Sau khi bóc, công cụ đối chiếu `Tổng tài sản = Tổng nguồn vốn` (và các tổng con). Số liệu OCR sai gần như luôn làm vỡ cân đối, nên đây là "bộ kiểm tra chất lượng" rất hiệu quả mà các công cụ chuyển PDF thông thường không có.

**Tối ưu tốc độ OCR.** Tesseract 5 mặc định tự đa luồng, gây tranh chấp khi xử lý nhiều trang. Công cụ đặt `OMP_THREAD_LIMIT=1` rồi **song song hoá theo trang** (ThreadPool) — nhanh hơn ~2.8×. Thêm cơ chế **quét nhanh dải đầu trang** để định vị báo cáo và **dừng sớm** khi đã đủ 3 báo cáo, tránh OCR thừa hàng chục trang thuyết minh. Dùng model `vie` bản **fast**: nhanh gấp ~3× bản đầy đủ mà độ chính xác con số tương đương.

**Tkinter cho giao diện.** Có sẵn trong Python (không thêm phụ thuộc), **đóng gói bằng PyInstaller ổn định nhất** trên cả hai hệ điều hành — quan trọng để app "chạy là được" trên máy người dùng cuối.

## Các phương án đã cân nhắc

| Hạng mục | Lựa chọn khác | Vì sao **không** chọn |
|---|---|---|
| OCR | **Cloud** (Google Document AI, Azure Document Intelligence) | Chính xác bảng cao hơn, **nhưng** tốn phí, cần internet, và **gửi dữ liệu tài chính lên cloud** |
| OCR | EasyOCR / PaddleOCR | Nặng (cần PyTorch), khó đóng gói gọn, không lợi hơn rõ rệt cho mẫu chuẩn này |
| Đọc bảng | Camelot / Tabula | Chỉ hiệu quả với **PDF có text**; vô dụng với bản scan |
| Giao diện | PyQt/PySide | Đẹp hơn nhưng nặng, đóng gói cồng kềnh, license phức tạp |
| Xuất Excel | pandas + xlsxwriter | openpyxl đủ dùng và kiểm soát định dạng/sheet tốt hơn cho nhu cầu này |

## Hướng nâng cấp về sau

- Thêm khung chỉ tiêu cho **tổ chức tín dụng** (ngân hàng) và **mẫu tiếng Anh**.
- Tùy chọn **gửi lên cloud** cho các trang OCR điểm thấp (chế độ "kết hợp").
- Xuất kèm sheet **đối chiếu** đánh dấu ô có độ tin cậy OCR thấp để soát nhanh.
