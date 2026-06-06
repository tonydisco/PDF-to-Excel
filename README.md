# BCTC PDF → Excel (Thông tư 200)

Ứng dụng desktop (Windows & macOS) đọc **Báo cáo tài chính dạng PDF scan** và xuất ra **Excel**, mỗi báo cáo một sheet:

1. **Bảng cân đối kế toán**
2. **Báo cáo kết quả hoạt động kinh doanh**
3. **Báo cáo lưu chuyển tiền tệ**

Chọn được nhiều file PDF cùng lúc (tối đa **150 file**/lần) hoặc cả **một thư mục**. Mỗi PDF cho ra một file Excel cùng tên (`Tên_file.xlsx`).

**Giao diện hiện đại:** thiết kế phẳng theo bảng màu [Coolors](https://coolors.co/f4f1de-e07a5f-3d405b-81b29a-f2cc8f), có **chế độ Sáng/Tối**, **bộ đếm giờ tổng**, **tiến độ + thời gian riêng cho từng file**, và nút **Tạm dừng / Dừng hẳn**.

> 📌 Mục lục: [Vì sao OCR](#1-vì-sao-cần-ocr) · [Cài đặt](#2-cài-đặt-một-lần) · [Cách dùng](#3-cách-dùng) · [Chạy từ mã nguồn (dev)](#4-khởi-động-từ-mã-nguồn-cho-lập-trình-viên) · [Độ chính xác](#5-cơ-chế-đảm-bảo-độ-chính-xác) · [Đóng gói](#6-đóng-gói-thành-exe--app) · [Giới hạn](#7-giới-hạn--lưu-ý) · [Cấu trúc](#8-cấu-trúc-dự-án) · [Xử lý sự cố](#9-xử-lý-sự-cố-thường-gặp)

---

## 1. Vì sao cần OCR?

Hầu hết file trong bộ BCTC là **bản scan (ảnh chụp)** — không có chữ bên trong, nên không thể "copy text". Ứng dụng dùng **OCR tiếng Việt (Tesseract)** chạy **hoàn toàn trên máy bạn** — dữ liệu tài chính **không gửi lên internet**.

Để đảm bảo chính xác, ứng dụng **không** đoán bừa nhãn chỉ tiêu mà dùng **khung chỉ tiêu chuẩn Thông tư 200** làm mẫu; OCR chỉ điền **Mã số** và **con số** vào đúng dòng. Nhờ vậy nhãn luôn sạch, và số liệu được **kiểm tra cân đối tự động** (Tổng tài sản = Tổng nguồn vốn).

---

## 2. Cài đặt (một lần)

### Bước A — Cài Tesseract OCR

| Hệ điều hành | Cách cài |
|---|---|
| **Windows** | Tải bộ cài tại <https://github.com/UB-Mannheim/tesseract/wiki> → cài như phần mềm thường (nên giữ đường dẫn mặc định `C:\Program Files\Tesseract-OCR`). Gói tiếng Việt đã **đính kèm sẵn** trong ứng dụng nên không cần chọn thêm. |
| **macOS** | Mở Terminal, chạy: `brew install tesseract` |
| **Linux** | `sudo apt install tesseract-ocr` |

> Gói tiếng Việt (`vie.traineddata`) đã nằm sẵn trong thư mục `tessdata/` của ứng dụng, nên bạn **không cần** tự tải.

### Bước B — Cài Python (nếu chạy từ mã nguồn)

Tải Python 3.9+ tại <https://www.python.org/downloads/> (Windows nhớ tick **"Add Python to PATH"**).
*(Nếu dùng bản đóng gói `.exe`/`.app` thì bỏ qua bước này.)*

Thư viện cần thiết (trong [requirements.txt](requirements.txt)): `PyMuPDF`, `pytesseract`, `Pillow`, `openpyxl`.

---

## 3. Cách dùng

### Cách 1 — Chạy trực tiếp (đơn giản nhất)

* **Windows:** nhấp đúp **`run_windows.bat`**
* **macOS:** nhấp đúp **`run_macos.command`**
  *(lần đầu: chuột phải → Open để bỏ qua cảnh báo Gatekeeper)*

Ứng dụng sẽ tự cài thư viện cần thiết rồi mở cửa sổ.

### Cách 2 — Bản đóng gói (.exe/.app) — xem [mục 6](#6-đóng-gói-thành-exe--app)

### Thao tác trong cửa sổ

1. Bấm **＋ Thêm file** (chỉ nhận `.pdf`) hoặc **📁 Thêm thư mục** (tự quét toàn bộ PDF bên trong).
2. Chọn **Thư mục lưu Excel** (mặc định tạo thư mục `Excel_output` cạnh file đầu tiên).
3. Tuỳ chọn: bật **🌙 / ☀️** để đổi giao diện Sáng/Tối; tick **Chất lượng cao** nếu cần.
4. Bấm **CHUYỂN ĐỔI ▶**. Theo dõi **bộ đếm giờ tổng**, **tiến độ từng file** (thanh Sage) và **Nhật ký**.
   * **⏸ Tạm dừng** — tạm ngưng trước file kế tiếp; bấm **▶ Tiếp tục** để chạy lại.
   * **⏹ Dừng hẳn** — kết thúc sớm; các file đã xong vẫn được lưu.
5. Xong, ứng dụng tự mở thư mục chứa kết quả.

Mỗi file Excel có 3 sheet như trên, kèm cột **Mã số · Số cuối năm / Năm nay · Số đầu năm / Năm trước**.

### Cách 3 — Dòng lệnh (cho người rành kỹ thuật)

```bash
python cli.py "BCTC1.pdf" "BCTC2.pdf" -o "Excel_output"
python cli.py *.pdf --hq          # --hq = chất lượng cao (DPI 300, chậm hơn)
```

---

## 4. Khởi động từ mã nguồn (cho lập trình viên)

Phần này dành cho việc **chạy app từ mã nguồn** trên máy mới / máy dev. Người dùng cuối dùng bản đóng gói thì bỏ qua.

### 🍎 macOS

```bash
brew install tesseract                 # B1: Tesseract (một lần)
cd BCTC_PDF_to_Excel                    # B2: vào thư mục dự án
bash run_macos.command                  # B3: launcher tự tìm Python có Tk, cài lib, mở app
```

> ⚠️ **Lưu ý macOS mới (Sequoia/Tahoe):** `python3` hệ thống (`/usr/bin/python3`) thường có **Tkinter lỗi phiên bản**
> (`macOS 26 (2603) or later required, have instead 16`). Khi đó dùng **Python từ Homebrew kèm Tk**:
> ```bash
> brew install python@3.13 python-tk@3.13
> /opt/homebrew/bin/python3.13 -m pip install -r requirements.txt
> /opt/homebrew/bin/python3.13 app.py
> ```
> hoặc cài Python tại <https://www.python.org/downloads/> (đã kèm Tk tương thích).

### 🪟 Windows

```bat
:: Cài Tesseract (bộ UB-Mannheim), nhớ tick "Add Python to PATH" khi cài Python, rồi:
run_windows.bat
```

### 🐧 Linux

```bash
sudo apt install tesseract-ocr python3-tk
pip install -r requirements.txt
python3 app.py
```

### Chạy thủ công (không qua launcher)

```bash
cd BCTC_PDF_to_Excel
python3 -m pip install -r requirements.txt
python3 app.py
```

### Kiểm tra môi trường khi gặp lỗi giao diện

```bash
# Tk có chạy không? (in "Tk OK" nếu ổn)
python3 -c "import tkinter; r=tkinter.Tk(); r.destroy(); print('Tk OK')"
# Đã cài đủ thư viện chưa?
python3 -c "import fitz, pytesseract, PIL, openpyxl; print('libs OK')"
# Tesseract + gói tiếng Việt?
tesseract --version && tesseract --list-langs | grep vie
```

Nếu lệnh Tk báo lỗi version → dùng Python khác có Tk (xem lưu ý macOS ở trên).

---

## 5. Cơ chế đảm bảo độ chính xác

Số liệu tài chính cần độ tin cậy cao, nên công cụ dùng **3 lớp kiểm soát**:

**a) Đọc 2 lần, hợp nhất.** Mỗi báo cáo được OCR ở **hai độ phân giải khác nhau** rồi hợp nhất: lần đọc chính (ổn định nhất) làm chuẩn, lần đọc thứ hai chỉ **bù vào ô còn thiếu**. Cách này giảm rõ lỗi đọc sai một chữ số.

**b) Tô cam ô "nghi ngờ".** Ô nào hai lần đọc ra số **khác nhau** sẽ được **tô màu cam** ngay trong Excel — bạn chỉ cần soát đúng những ô đó so với PDF gốc, thay vì dò cả bảng.

**c) Tự kiểm tra cân đối** trên Bảng cân đối kế toán:

* `Tổng tài sản (270) = Tổng nguồn vốn (440)`
* `Tài sản ngắn hạn (100) + dài hạn (200) = 270`
* `Nợ phải trả (300) + Vốn chủ sở hữu (400) = 440`

Nếu **khớp**, Nhật ký báo **✓ OK** (dòng tiến độ màu Sage). Nếu **lệch**, báo **⚠** (màu cát). Vì số liệu sai do OCR gần như luôn làm vỡ cân đối, đây là tín hiệu chất lượng rất đáng tin.

> Với báo cáo quan trọng: ưu tiên kiểm tra các **ô tô cam** và bật **"Chất lượng cao"** (đọc 3 độ phân giải).

---

## 6. Đóng gói thành .exe / .app (để chia sẻ cho máy khác)

> PyInstaller phải chạy **trên đúng hệ điều hành đích** (muốn có `.exe` thì build trên Windows; muốn `.app` thì build trên macOS).

* **Windows:** nhấp đúp **`build_windows.bat`** → file `dist\BCTC_PDF_to_Excel.exe`
* **macOS:** chạy `bash build_macos.sh` → `dist/BCTC_PDF_to_Excel.app`

Máy nhận bản đóng gói vẫn cần **cài Tesseract một lần** (mục 2A); gói tiếng Việt đã nằm trong app.

---

## 7. Giới hạn & lưu ý

* **Ngân hàng (vd. OCB)**: dùng mẫu báo cáo của tổ chức tín dụng (khác Thông tư 200) nên khung chỉ tiêu không khớp hoàn toàn — ứng dụng sẽ cảnh báo và bóc ở mức tốt nhất có thể.
* **Báo cáo tiếng Anh (file `(en)`)**: tiêu đề tiếng Anh, khung mẫu đang theo tiếng Việt — nên dùng bản `(vi)` nếu có.
* **Bản scan quá mờ/nghiêng**: OCR có thể sót vài dòng; phép kiểm tra cân đối sẽ giúp phát hiện.
* Báo cáo lưu chuyển tiền tệ tự nhận **phương pháp trực tiếp/gián tiếp**.
* Tối đa **150 file** mỗi lần xử lý.

---

## 8. Cấu trúc dự án

```
BCTC_PDF_to_Excel/
├── app.py                 # Giao diện (Tkinter) — flat, Sáng/Tối, tiến độ từng file, Tạm dừng/Dừng
├── cli.py                 # Chạy dòng lệnh
├── bctc/                  # Lõi xử lý
│   ├── ocr.py             # render PDF + Tesseract
│   ├── parser.py          # định vị báo cáo + dò cột Mã số + bóc số
│   ├── templates.py       # khung chỉ tiêu Thông tư 200 (B01/B02/B03)
│   ├── excel_writer.py    # xuất .xlsx
│   └── engine.py          # điều phối + kiểm tra cân đối (MAX_FILES=150, hỗ trợ cancel/pause)
├── tessdata/vie.traineddata   # gói OCR tiếng Việt (đính kèm)
├── requirements.txt
├── run_windows.bat / run_macos.command       # chạy nhanh
├── build_windows.bat / build_macos.sh        # đóng gói
└── pdf2excel.spec
```

Chi tiết lựa chọn công nghệ: xem **TECHSTACK.md**.

---

## 9. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân & cách xử lý |
|---|---|
| `macOS 26 … required, have instead 16` khi mở app | Tk của Python hệ thống lỗi → dùng `python@3.13` + `python-tk@3.13` (Homebrew) hoặc Python từ python.org |
| `Không tìm thấy Tesseract OCR` | macOS: `brew install tesseract` · Windows: cài bộ UB-Mannheim · Linux: `apt install tesseract-ocr` |
| `Chưa có gói tiếng Việt (vie)` | Gói đã có trong `tessdata/`; nếu vẫn báo, đặt `TESSDATA_PREFIX` trỏ tới thư mục đó |
| Cửa sổ không mở, không báo lỗi | Chạy `python3 app.py` trực tiếp trong Terminal để xem log |
| Lệch cân đối / nhiều ô tô cam | Bản scan mờ — bật **Chất lượng cao** và soát các ô cảnh báo |
