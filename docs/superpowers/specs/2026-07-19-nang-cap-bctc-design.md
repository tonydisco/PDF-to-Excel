# Nâng cấp BCTC PDF → Excel: độ chính xác, khởi động Windows, nhiệt độ

Ngày: 2026-07-19 · Trạng thái: chờ duyệt

## 1. Bối cảnh

Ứng dụng chuyển Báo cáo tài chính PDF (chủ yếu bản scan) sang Excel theo khung
Thông tư 200. Người dùng phản ánh ba vấn đề: dữ liệu bị sót/lệch, app mở rất
chậm trên Windows 10 máy yếu, và máy nóng khi chạy.

Bản thiết kế này dựa trên khảo sát định lượng toàn bộ corpus thật, không dựa
trên phỏng đoán. Một giả định ban đầu ("phần lớn file có lớp text nên có thể bỏ
OCR") đã bị dữ liệu bác bỏ và thứ tự ưu tiên được sửa lại theo đó.

### 1.1 Số liệu corpus (2.919 PDF · 79.910 trang · 19,8 GB)

| Phân loại | Số file | % |
|---|---:|---:|
| Scan thuần (0 ký tự trích được) | 2.281 | 78,2% |
| Có lớp text nhưng **mojibake** | 273 | 9,4% |
| Có lớp text dùng được | 355 | **12,2%** |
| Quá mỏng (chỉ chữ ký/con dấu) | 9 | 0,3% |

**87,8% bắt buộc phải OCR.** Không có mốc năm nào để khai thác: tỷ lệ có text
dùng được của 2020–2025 là 11,8%, *thấp hơn* 2006–2012 (18,4%).

Các đặc điểm khác ảnh hưởng trực tiếp tới thiết kế:

- Trung vị 28 trang/file; p90 = 47; max = 202.
- **17,1% file trùng lặp** theo nội dung (499 file, 4,11 GB).
- **38,4% file có trang xoay**; 197 file xoay *lẫn lộn* trong cùng tài liệu.
- **24,4% file có trang ngang**; 21,3% số trang là khổ 584×830pt (không phải A4).
- **112 file ngân hàng/chứng khoán** (OCB, ORS) dùng mẫu `B05/TCTD` theo
  Thông tư 49/2014/TT-NHNN — không khớp TT200.
- 12,3% file scan có DPI gốc < 150 (OCR kém ở mức này).
- Tồn tại 1 file PDF 0 byte sẽ làm `fitz.open` ném lỗi.
- **187 file Excel xuất trực tiếp** (`CDKT.XLS`, `KQKD.XLS`, `LCTT.XLS`,
  `CDPS.XLS`) nằm cùng thư mục với PDF tương ứng → dùng làm đáp án chuẩn.

### 1.2 Vì sao máy nóng

Một mẻ tối đa 150 file × trung vị 28 trang × 2 lượt DPI, **cộng** lượt
`locate_pages` bị chạy lặp mỗi DPI, chạy trên *mọi luồng logic* của CPU. Đó là
hàng chục nghìn lượt gọi Tesseract ở 100% CPU liên tục nhiều giờ. Trên máy đích
(4 GB RAM, HDD, 2–4 nhân) đây là tải nhiệt tối đa kéo dài.

### 1.3 Máy đích

Windows 10, 4 GB RAM, ổ HDD, 2–4 nhân. Mọi ngưỡng tài nguyên trong tài liệu này
tính theo cấu hình đó.

## 2. Mục tiêu và tiêu chí nghiệm thu

| # | Mục tiêu | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| G1 | Giảm sót/lệch dữ liệu | Bộ hồi quy GĐ0 trên 187 cặp PDF–Excel | `sót`+`lệch` giảm ≥ 50% so với baseline |
| G2 | Không còn mất dữ liệu âm thầm | Bộ hồi quy | 0 mã số bị vứt mà không có cảnh báo |
| G3 | Khởi động Windows nhanh | Đo lần mở nguội trên Win10 + HDD | ≤ 3 giây (hiện 30–90 giây) |
| G4 | Giảm nhiệt | CPU-giây/file và %CPU đỉnh | CPU-giây giảm ≥ 40%; %CPU đỉnh ≤ 60% số luồng logic ở chế độ mặc định |
| G5 | An toàn bộ nhớ trên máy 4 GB | RSS đỉnh khi xử lý file trung vị | ≤ 250 MB (ước tính hiện tại > 500 MB) |

Ngưỡng G1 sẽ được chốt lại sau khi có baseline GĐ0; nếu baseline đã rất tốt ở
một hạng mục nào đó, ngưỡng cho hạng mục đó điều chỉnh tương ứng và ghi rõ lý do.

### 2.1 Phân đợt triển khai

Năm giai đoạn được chia làm hai đợt, mỗi đợt có kế hoạch triển khai riêng.

**Đợt 1 — GĐ0 + GĐ1 + GĐ2** (phạm vi hiện tại)

Chạm được cả ba vấn đề người dùng nêu: có thước đo khách quan (GĐ0), giảm nhiệt
rõ rệt bằng cách cắt tính toán thừa (GĐ1), và sửa dứt điểm khởi động Windows
(GĐ2). Tiêu chí nghiệm thu áp dụng cho đợt này: **G3, G4, G5** đạt ngưỡng;
**G1, G2** có baseline đo được nhưng chưa yêu cầu đạt ngưỡng.

Lý do gộp GĐ2 vào đợt đầu dù không liên quan tới hai giai đoạn kia: nó không
đụng bất kỳ file xử lý nào, nên chạy song song được và không tạo xung đột merge.

**Đợt 2 — GĐ3 + GĐ4** (sau khi đợt 1 có số liệu thực tế)

Toàn bộ hạng mục độ chính xác và tinh chỉnh nhiệt/bộ nhớ còn lại. Tiêu chí
nghiệm thu: **G1, G2** đạt ngưỡng, **G3–G5** không được xấu đi.

Cơ sở của việc hoãn đợt 2: baseline từ GĐ0 sẽ cho biết hạng mục nào trong GĐ3
thực sự gây sót/lệch nhiều nhất. Làm GĐ3 trước khi có số liệu đó là tối ưu theo
phỏng đoán — đúng thứ sai lầm đã khiến bản thiết kế đầu tiên xếp sai ưu tiên.

## 3. Nguyên tắc thiết kế

1. **Đo trước, sửa sau.** Không thay đổi logic bóc tách nào được merge nếu chưa
   chạy bộ hồi quy trước/sau.
2. **Sai thì phải ồn ào.** Mọi trường hợp không chắc chắn phải sinh cảnh báo
   hoặc tô màu; tuyệt đối không âm thầm bỏ dữ liệu.
3. **Tái dùng hình học sẵn có.** Đường đọc lớp text phải trả về đúng cấu trúc
   dữ liệu mà `ocr.ocr_lines` trả về, để `parser.py` dùng chung không phải rẽ nhánh.
4. **Tách bạch giai đoạn.** GĐ2 (đóng gói) không đụng code xử lý; GĐ1/3/4 không
   đụng file đóng gói. Hai nhánh chạy song song được.

## 4. Giai đoạn 0 — Bộ đo hồi quy

Không có bộ đo thì không chứng minh được cải thiện nào. Đây là việc đầu tiên.

### 4.1 Thành phần

```
tests/regression/
├── build_pairs.py      # quét corpus, ghép Excel ↔ PDF anh em -> pairs.json
├── groundtruth.py      # đọc Excel đáp án (xử lý được các quái chiêu định dạng)
├── run_regression.py   # chạy engine, so từng ô, xuất báo cáo
└── report.py           # kết xuất bảng đọc được + JSON
```

### 4.2 Đọc file đáp án — các cạm bẫy đã xác nhận

- **Đuôi file nói dối.** `KQKD.XLS` thực chất là OOXML (bắt đầu bằng `PK`).
  `openpyxl.load_workbook()` từ chối theo *đuôi file*, không theo nội dung.
  Giải pháp: đọc magic bytes (`PK\x03\x04` → OOXML qua `BytesIO`;
  `\xD0\xCF\x11\xE0` → BIFF cũ qua `xlrd`), không tin đuôi file.
- **Nhãn chỉ tiêu là mojibake TCVN3** (`C«ng ty CP Du LÞch §¨k L¨k`).
  Không cần giải mã: bộ đo chỉ dùng **mã số + con số**, bỏ qua nhãn.
- **Hàng tiêu đề không cố định.** Dò động hàng chứa đồng thời `Mã số` và
  `Năm nay`/`Số cuối năm` (đã chuẩn hoá bỏ dấu, chịu được cả mojibake bằng cách
  so khớp cột theo vị trí sau khi tìm được hàng số thứ tự `1|2|3|4|5`).
- **Có cột Thuyết minh** (`VI.25`) nằm giữa Mã số và cột giá trị.

### 4.3 Cách ghép cặp

Mỗi Excel đáp án ứng với **một** báo cáo (`CDKT`/`KQKD`/`LCTT`), còn PDF thường
chứa cả ba. Ghép theo thư mục chứa, rồi theo tiền tố mã công ty `NN_`. Chỉ so
sánh những báo cáo có đáp án.

### 4.4 Cách tính điểm

Với mỗi cặp `(mã số, cột)`, gọi `g` = giá trị đáp án, `o` = giá trị app xuất:

| Điều kiện | Phân loại |
|---|---|
| `g` khác 0/rỗng, `o == g` | **đúng** |
| `g` khác 0/rỗng, `o` rỗng | **sót** |
| `g` khác 0/rỗng, `o != g` | **lệch** |
| `g` rỗng/0, `o` khác rỗng | **thừa** |

Báo cáo theo từng báo cáo, từng file, và tổng hợp. Ghi kèm: thời gian thực,
**CPU-giây** (`time.process_time` + `resource.getrusage`), **RSS đỉnh**.

### 4.5 Quy mô chạy

- Bộ **nhanh** (~30 cặp, phân tầng theo năm / scan-vs-text / thường-vs-ngân hàng)
  để lặp trong lúc phát triển.
- Bộ **đầy đủ** (toàn bộ 187 cặp) chạy trước và sau mỗi giai đoạn.

## 5. Giai đoạn 1 — Cắt tính toán thừa

Đòn bẩy lớn nhất cho cả nhiệt lẫn tốc độ. Bốn thay đổi, không thay đổi logic
bóc tách nên rủi ro thấp.

### 5.1 Đưa `locate_pages` ra khỏi vòng lặp DPI

`parser.extract()` gọi `locate_pages()` ở dòng 293, còn `extract_consensus()`
gọi `extract()` một lần cho **mỗi** DPI (dòng 380). Kết quả định vị là tất định
và giống hệt nhau giữa các lượt → đang lãng phí trọn một lượt quét đầu trang
của toàn tài liệu cho mỗi DPI phụ.

Sửa: `extract()` nhận thêm tham số `scope=None`; khi `scope` được truyền thì bỏ
qua bước định vị. `extract_consensus()` gọi `locate_pages()` **một lần** rồi
truyền xuống.

Tiết kiệm: `(số_DPI − 1) × số_trang` lượt OCR mỗi file. Với file trung vị 28
trang, chế độ thường: 28 lượt/file; mẻ 150 file: **4.200 lượt OCR**.

### 5.2 Khử trùng lặp theo hash nội dung

`engine.convert_many()` băm nội dung từng file (SHA-256 theo khối, có cache
theo `(size, mtime)`), nhóm các file trùng. Chỉ xử lý một đại diện mỗi nhóm;
các file còn lại ghi cùng workbook đó ra tên file riêng của chúng và log rõ
`↩ trùng nội dung với <file>`.

Tiết kiệm: **17,1%** khối lượng xử lý toàn corpus.

### 5.3 Số luồng OCR theo nhân vật lý, có chừa headroom

`parser.MAX_WORKERS = max(2, min(8, os.cpu_count()))` dùng **luồng logic**. Trên
laptop 4 nhân/8 luồng → 8 tiến trình Tesseract ghim sạch CPU, không còn chỗ cho
luồng giao diện. Đây là nguồn nhiệt chính.

Thay bằng hàm chọn theo chế độ người dùng:

| Chế độ | Công thức | Máy 4 nhân/8 luồng | Máy 2 nhân/4 luồng |
|---|---|---:|---:|
| Tiết kiệm điện | `1` | 1 | 1 |
| Cân bằng (mặc định) | `max(1, logical//2 − 1)` | 3 | 1 |
| Tối đa | `max(1, logical − 1)` | 7 | 3 |

`MAX_WORKERS` chuyển từ hằng số module sang tham số truyền xuống, để đổi được
lúc chạy mà không phải import lại.

### 5.4 Đường đọc lớp text — có bộ lọc mojibake

File mới `bctc/textlayer.py`:

```
try_extract(doc) -> dict[page_index, lines] | None
```

Trả về **đúng cấu trúc** mà `ocr.ocr_lines()` trả về (danh sách dòng, mỗi dòng
là list dict có `text/left/top/width/height/conf/cx/cy/right/lx`), dựng từ
`page.get_text("words")` với toạ độ chuẩn hoá theo `page.rect`. Nhờ vậy toàn bộ
`parser.py` dùng chung, không cần rẽ nhánh.

**Bộ lọc bắt buộc** (nếu bỏ qua, 273 file sẽ cho ra dữ liệu sai âm thầm):

1. Số ký tự trích được phải đạt ngưỡng tối thiểu mỗi trang.
2. **Tỷ lệ ký tự có dấu tiếng Việt** trên tổng ký tự chữ cái phải ≥ 0,02.
   (Đo thực tế: file tốt trung vị 0,270; file mojibake 0,000.)
3. Loại bỏ lớp phủ chữ ký số (`Ký bởi:`, `Signature Not Verified`) trước khi
   tính hai chỉ số trên — có file 202 trang mà toàn bộ "lớp text" chỉ là con dấu
   chữ ký 99 ký tự.

Không đạt bất kỳ điều kiện nào → **quay về OCR cho cả tài liệu**, ghi log lý do.

Lợi ích: 355 file (12,2%) bỏ OCR hoàn toàn — chính xác tuyệt đối và gần như
không tốn CPU. Đây là con số thật, không phải "phần lớn corpus".

## 6. Giai đoạn 2 — Đóng gói Windows

Độc lập hoàn toàn với code xử lý; làm song song với GĐ1/3/4 được.

### 6.1 Nguyên nhân gốc

`pdf2excel.spec` dòng 42 truyền `a.binaries, a.datas` thẳng vào `EXE()` mà
không có `COLLECT()` → chế độ **onefile**. CI (`build.yml` dòng 38) copy
**toàn bộ** `C:\Program Files\Tesseract-OCR` bằng `Copy-Item -Recurse`, gồm mọi
DLL và mọi gói ngôn ngữ chocolatey cài kèm. Thêm `upx=True` (dòng 48).

Hệ quả mỗi lần mở app: bootloader giải nén toàn bộ payload ra `%TEMP%\_MEIxxxx`,
Windows Defender quét lại từng DLL vừa ghi, chạy xong thì xoá — và lặp lại y hệt
ở lần mở sau. Trên HDD đây là 30–90 giây. UPX còn là tác nhân kinh điển gây
false-positive antivirus.

`vie.traineddata` hiện bị đóng gói **hai lần** (`datas` trong spec + bản CI copy
vào `tesseract\tessdata\`).

### 6.2 Thay đổi

1. **Chuyển sang onedir**: thêm `COLLECT()`, `EXE()` chỉ nhận `a.scripts`.
   Giải nén một lần lúc cài; các lần mở sau chạy thẳng.
2. **`upx=False`**: bỏ chi phí giải nén mỗi lần chạy và giảm rủi ro antivirus.
3. **Cắt Tesseract trong CI**: giữ `tesseract.exe`, các DLL bắt buộc, và
   `tessdata/{vie,eng,osd}.traineddata`. Xoá các gói ngôn ngữ khác và thư mục
   tài liệu. Bỏ bản `tessdata` trùng trong `datas`.
4. **Bộ cài Inno Setup**: `installer/BCTC_Setup.iss`, CI thêm bước
   `choco install innosetup` → xuất `BCTC_PDF_to_Excel-Setup.exe`. Tạo shortcut
   Desktop/Start Menu, hỗ trợ gỡ cài đặt.
5. **Splash screen**: `Splash()` của PyInstaller để có phản hồi thị giác ngay.
6. **Hoãn import nặng**: `app.py` dòng 29 `from bctc import engine, ocr` kéo
   theo `fitz`, `pytesseract`, `PIL` ngay lúc khởi động (`ocr.py` dòng 29–31),
   chặn việc vẽ cửa sổ. Chuyển sang import lười ở trong luồng xử lý; cửa sổ
   hiện trước, thư viện nạp sau.

### 6.3 Về SmartScreen

File `.exe` không ký số vẫn bị cảnh báo "Windows protected your PC". Bộ cài
giúp tích luỹ uy tín (reputation) nhanh hơn file lẻ, nhưng **muốn hết hẳn cảnh
báo thì phải có chứng thư ký mã (code-signing certificate)** — nằm ngoài phạm vi
kỹ thuật, cần quyết định mua. Ghi nhận để bạn cân nhắc riêng.

## 7. Giai đoạn 3 — Độ chính xác

### 7.1 Chuẩn hoá mã số *(lỗi nghiêm trọng nhất, đã kiểm chứng)*

Khung template ghi `"01"`, `"02"` (`templates.py` dòng 142–143) nhưng báo cáo
thật in mã số là `1`, `2` — đã xác nhận trên file đáp án gốc của Du Lịch Đăk Lăk.
`parser._token_code()` (dòng 118) so khớp **chuỗi chính xác**
(`m.group(1) in valid_codes`), nên `"1"` không bao giờ khớp `"01"`.

Hệ quả: **toàn bộ dòng mã 01–09 bị bỏ ở KQHDKD và LCTT**, trong đó có mã `01`
= *Doanh thu bán hàng và cung cấp dịch vụ* — dòng đầu tiên của Báo cáo KQKD.

Sửa: thêm `_canon(code)` chuẩn hoá về dạng chính tắc trước khi tra cứu:

- bỏ dấu câu thừa ở hai đầu;
- sửa nhầm lẫn OCR **chỉ trong token có dạng mã số**: `O/o→0`, `l/I/|→1`,
  `S→5`, `B→8`, `Z→2`, `G→6`;
- chính tắc hoá số 0 đứng đầu: `"1"` và `"01"` cùng cho `"1"`.

Bảng tra `{dạng_chính_tắc: mã_template}` dựng sẵn cho từng báo cáo.

**Rủi ro:** mã 1 chữ số có thể trùng với cột số thứ tự (`1|2|3|4|5`). Giảm thiểu
bằng cách vẫn bắt buộc đi qua `detect_code_column()` (đã có) và điều kiện tăng
dần theo thứ tự template (đã có). Bộ hồi quy sẽ đo `thừa` để bắt hồi quy loại này.

### 7.2 Sửa `split_values` — nguồn gây lệch số

`parser.split_values()` (dòng 207) lấy **token số đầu tiên** ở mỗi nửa rồi bỏ
qua phần còn lại (`cur = v if cur is None else cur`). Khi OCR tách
`1.234.567` thành hai token `1.234` và `567`, ô kết quả thành **1234** — sai
1000 lần mà vẫn trông như số hợp lệ.

Sửa:

1. Gom **tất cả** token số mỗi nửa kèm toạ độ.
2. Gộp các token liền kề thành một số khi khoảng cách ngang giữa chúng nhỏ hơn
   ngưỡng theo bề rộng ký tự trung bình, và các mảnh sau đều là cụm ≤ 3 chữ số.
3. Nhận dấu âm từ token `(`/`)` đứng riêng liền kề, không chỉ từ ngoặc dính liền.
4. Nếu sau khi gộp vẫn còn **> 2 nhóm giá trị** ở vùng bên phải (báo cáo quý có
   cột Quý + Luỹ kế), **ghi cảnh báo** thay vì âm thầm lấy hai cái đầu.

### 7.3 Nhận diện đơn vị tính

`excel_writer.py` dòng 52 ghi cứng `"Đơn vị tính: VND"`. Báo cáo ghi "triệu
đồng" sẽ lệch 10⁶ lần.

Sửa: quét vùng đầu các trang đã định vị tìm `đơn vị tính`/`đơn vị:` kèm
`đồng|VND|nghìn|ngàn|triệu|tỷ`; ghi đúng đơn vị phát hiện được vào ô A2, kèm
cảnh báo khi đơn vị khác VND.

**Không tự nhân giá trị** để quy đổi — làm vậy là bịa ra độ chính xác không có
trong nguồn. Chỉ ghi nhận và cảnh báo.

### 7.4 Trang chứa hai tiêu đề báo cáo

`heading_in_lines()` (dòng 74) trả `None` khi trang có **khác 1** tiêu đề, khiến
trang bị **bỏ hoàn toàn**. Trang có CĐKT kết thúc + KQKD bắt đầu là rất phổ biến
ở doanh nghiệp nhỏ.

Sửa: chấp nhận trang nhiều tiêu đề và để vòng lặp bám tiêu đề trong trang (đã có
sẵn ở dòng 340) tự chia. Vẫn loại trang Mục lục, nhưng bằng tín hiệu khác: trang
mục lục có tiêu đề nhưng **không có cột giá trị số**. Điều kiện loại mới:
≥ 2 tiêu đề **và** số token số ở vùng giá trị dưới ngưỡng.

Đồng thời nới `fitz_rect(top_frac=0.42)` (dòng 246) — báo cáo bắt đầu ở giữa
trang hiện đang vô hình. Quét toàn trang ở DPI thấp, hoặc quét hai dải.

### 7.5 Hình học trang ngang và khổ không chuẩn

`split_values` chặn cứng `cx < 0.60`, `estimate_split` mặc định `0.84` và chỉ dò
trong khoảng `0.72–0.92`. Với 24,4% file có trang ngang và 21,3% số trang khổ
584×830pt, các mốc này sai.

Sửa: suy ra ranh giới nhãn/giá trị từ **vị trí cột Mã số đã dò được** (cộng lề)
thay vì hằng số; và thay cửa sổ cố định trong `estimate_split` bằng phân cụm
1 chiều (2-means) trên toạ độ mép phải của các token số.

### 7.6 Không âm thầm vứt mã ngoài khung

`excel_writer._write_sheet()` (dòng 68) chỉ duyệt các dòng **có trong template**.
Mã nào parser bóc được mà không khớp khung sẽ biến mất, không cảnh báo.

Sửa: thêm mục "Mã ngoài khung" ở cuối sheet liệt kê mọi mã dư, kèm cảnh báo
trong nhật ký. Đảm bảo nguyên tắc "không mất dữ liệu âm thầm" (G2).

### 7.7 Khung Quyết định 15/2006 cho file ≤ 2014

TT200 chỉ hiệu lực từ năm tài chính 2015; corpus có file từ 2006. File cũ đang
bị áp sai khung.

Thêm `bctc/templates_qd15.py` (B01/B02/B03 theo QĐ15). Chọn khung theo: (a) năm
tài chính đọc từ nội dung/tên file, (b) từ vựng đặc trưng. Ưu tiên tín hiệu nội
dung hơn tên file.

Lưu ý: CĐKT theo QĐ15 trùng nhiều mã cấp tổng với TT200 (100/200/270/440) nhưng
khác ở cấp chỉ tiêu. Cần đối chiếu văn bản gốc khi lập bảng, không suy diễn từ
TT200.

### 7.8 Mẫu ngân hàng B05/TCTD

112 file (OCB, ORS) theo Thông tư 49/2014/TT-NHNN. Các chỉ tiêu như *Cho vay
khách hàng*, *Tiền gửi tại Ngân hàng Nhà nước*, *Thu nhập lãi thuần*, *Phát hành
giấy tờ có giá* không tồn tại trong hệ thống tài khoản TT200 — hiện app cho ra
kết quả gần như rỗng.

Thêm `bctc/templates_tctd.py`, nhận diện bằng **từ vựng đặc trưng** (không dùng
tên file): `B05/TCTD`, `Cho vay khách hàng`, `Tiền gửi tại Ngân hàng Nhà nước`,
`Thu nhập lãi thuần`.

Ghi chú: 17 file ORS là công ty chứng khoán — mẫu thứ ba nữa, gồm cả báo cáo
*Tỷ lệ an toàn tài chính* vốn không có tương ứng nào trong TT200. Giai đoạn này
chỉ xử lý B05/TCTD; mẫu chứng khoán ghi nhận là hạn chế đã biết.

### 7.9 Chống file hỏng

- PDF 0 byte (đã có 1 file trong corpus), PDF hỏng, PDF mã hoá: bắt lỗi và báo
  theo từng file, không làm chết cả mẻ. `convert_many` đã có `try/except`
  (dòng 124) nhưng cần thông báo dễ hiểu thay vì traceback thô.
- Không suy ra loại file từ đuôi (`.PDF` hoa, và một file tên
  `BCTC 2019.jpeg.jpeg…`): dò magic bytes.

## 8. Giai đoạn 4 — Nhiệt và bộ nhớ

### 8.1 Render xám trực tiếp

`ocr.render_page()` (dòng 121–125) render RGB rồi `preprocess()` (dòng 128) mới
chuyển xám bằng Pillow. Dùng `page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)`
và `Image.frombytes("L", ...)` để giảm 3× bộ nhớ render và bỏ hẳn một lượt duyệt
toàn ảnh.

### 8.2 Truyền ảnh theo luồng thay vì giữ hết trong RAM

`parser.extract()` dòng 317–319 dựng danh sách `rendered` chứa ảnh của **mọi**
trang đã định vị **trước khi** OCR. Ảnh A4 300 DPI RGB ≈ 26 MB; 20 trang ≈ 520 MB,
chưa kể bản sao lúc OCR. Trên máy 4 GB điều này gây swap → thrash HDD → càng
nóng, hoặc `MemoryError`.

Sửa: một luồng render đẩy vào `queue.Queue(maxsize=workers+1)`, N luồng OCR tiêu
thụ. RSS đỉnh từ ~520 MB xuống ~40 MB.

**Lưu ý an toàn luồng:** `fitz.Document` không an toàn khi nhiều luồng cùng truy
cập trang. Giữ toàn bộ lời gọi `get_pixmap` trong **một** luồng render duy nhất
(hoặc bọc khoá) — không render trong các luồng OCR.

### 8.3 Chọn DPI thích ứng

12,3% file scan có DPI gốc < 150. Render chúng ở 300 DPI là phóng to ảnh mờ:
tốn CPU gấp bốn mà không thêm thông tin. Đọc DPI ảnh nhúng và chọn DPI render
theo đó, đồng thời **chặn trần số điểm ảnh** (≈ 4 megapixel) để các file
3,8 MB/trang không làm vỡ bộ nhớ.

### 8.4 Vòng lặp giao diện lúc rảnh

`_tick` chạy mỗi 120 ms và `_drain_queue` mỗi 80 ms **vĩnh viễn**
(`app.py` dòng 1302, 1328) — khoảng 21 lần đánh thức CPU mỗi giây kể cả khi app
không làm gì, ngăn CPU vào trạng thái tiết kiệm điện sâu. Khi không chạy chuyển
sang 500 ms.

### 8.5 Chế độ "Tiết kiệm điện"

Công tắc trên giao diện: 1 luồng OCR, một lượt DPI duy nhất, DPI thích ứng.
Dành cho máy yếu hoặc khi cần chạy nền lâu mà không muốn máy nóng.

## 9. Kiểm thử

- **Hồi quy dữ liệu**: bộ GĐ0 chạy trước/sau mỗi giai đoạn. Không merge nếu
  `sót`+`lệch` xấu đi.
- **Đơn vị**: `_canon()` (nhầm lẫn OCR, số 0 đứng đầu), gộp token số của
  `split_values` (số bị tách, dấu âm rời), bộ lọc mojibake (dựng từ chính 273
  file mojibake và 355 file text tốt đã xác định), phát hiện đơn vị tính.
- **Tài nguyên**: CPU-giây, RSS đỉnh, %CPU đỉnh ghi tự động trong mỗi lần chạy
  hồi quy.
- **Khởi động**: đo tay lần mở nguội trên máy Windows 10 + HDD thật, ba lần lấy
  trung vị. Không có máy thật thì đo trên máy ảo giới hạn 4 GB RAM + ổ giả lập.
- **Ca biên**: file 0 byte, file 202 trang, file 126,9 MB, file xoay lẫn lộn,
  file trang ngang, file mojibake, file ngân hàng.

## 10. Rủi ro

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| Chuẩn hoá mã 1 chữ số bắt nhầm cột số thứ tự | Sinh dữ liệu sai (`thừa`) | Giữ ràng buộc cột + thứ tự tăng dần; đo `thừa` trong hồi quy |
| Bảng QĐ15/TCTD lập sai | Sai có hệ thống trên cả nhóm file | Đối chiếu văn bản pháp quy gốc; kiểm bằng đáp án Excel của đúng nhóm đó |
| Refactor luồng render gây race | Crash hoặc lỗi ngắt quãng | Một luồng render duy nhất; chạy bộ đầy đủ 187 cặp để phát hiện |
| Bộ lọc mojibake quá chặt | Bỏ nhầm file text tốt sang OCR | Chỉ mất tốc độ, không mất chính xác; hiệu chỉnh ngưỡng trên 628 file đã phân loại |
| Đáp án Excel không khớp kỳ báo cáo của PDF | Điểm hồi quy sai lệch | Đối chiếu kỳ/năm khi ghép cặp; loại cặp không khớp |

## 11. Ngoài phạm vi

- Ghép báo cáo bị tách rời nhiều PDF (`CDKT.pdf` + `LCTT.pdf` riêng) — bạn đã
  chọn không làm ở đợt này.
- Mẫu tiếng Anh — chỉ 8 file duy nhất trong toàn corpus.
- Mẫu công ty chứng khoán (ORS, 17 file) — ghi nhận là hạn chế đã biết.
- Giải nén `.rar`/`.zip` (59 + 35 file, chứa BCTC chưa được đếm).
- OCR đám mây — trái nguyên tắc dữ liệu không rời máy.
- Mua chứng thư ký mã — cần quyết định thương mại, không phải kỹ thuật.
