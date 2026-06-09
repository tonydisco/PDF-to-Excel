// Dữ liệu MẪU để dựng UI. Lõi OCR Python (bctc) sẽ thay thế qua sidecar.

export type FileStatus = "queued" | "processing" | "done" | "error"

export interface QueueFile {
  id: string
  name: string
  sizeMB: number
  pages: number
  status: FileStatus
  progress: number // 0..1
  found: 0 | 1 | 2 | 3 // số báo cáo bóc được
  conflicts: number
  balanceOk: boolean | null // null = chưa kiểm/không đủ chỉ tiêu
}

export const MOCK_FILES: QueueFile[] = [
  { id: "f03", name: "03_CTCP DV Bến Thành 2025.pdf", sizeMB: 26.8, pages: 41, status: "done", progress: 1, found: 3, conflicts: 2, balanceOk: true },
  { id: "f12vi", name: "12_LD KS Plaza 2025 (vi).pdf", sizeMB: 10.2, pages: 35, status: "done", progress: 1, found: 3, conflicts: 8, balanceOk: true },
  { id: "f12en", name: "12_LD KS Plaza 2025 (en).pdf", sizeMB: 9.8, pages: 35, status: "done", progress: 1, found: 3, conflicts: 3, balanceOk: false },
  { id: "f23", name: "23_Căn hộ & VP Sài Gòn 2025.pdf", sizeMB: 1.2, pages: 18, status: "done", progress: 1, found: 2, conflicts: 8, balanceOk: null },
  { id: "f06", name: "06_TM Phú Nhuận 2025 - Mẹ.pdf", sizeMB: 18.4, pages: 47, status: "processing", progress: 0.46, found: 0, conflicts: 0, balanceOk: null },
  { id: "f35", name: "35_NH Phương Đông 2025 (riêng).pdf", sizeMB: 7.5, pages: 62, status: "error", progress: 0, found: 0, conflicts: 0, balanceOk: null },
  { id: "f31", name: "31_Nhôm Sapa Bến Thành 2025.pdf", sizeMB: 6.3, pages: 29, status: "queued", progress: 0, found: 0, conflicts: 0, balanceOk: null },
]

export interface Row {
  code: string | null
  label: string
  level: 0 | 1 | 2 | 3
  kind: "header" | "section" | "total" | "item" | "sub"
  cur: number | null
  prior: number | null
  flagCur?: boolean
  flagPrior?: boolean
}

export interface Statement {
  key: "CDKT" | "KQHDKD" | "LCTT"
  title: string
  rows: Row[]
}

// CDKT mẫu theo số thật của file 03 (cân đối khớp: 100+200=270=440=300+400)
const CDKT: Statement = {
  key: "CDKT",
  title: "Bảng cân đối kế toán",
  rows: [
    { code: null, label: "TÀI SẢN", level: 0, kind: "header", cur: null, prior: null },
    { code: "100", label: "A - TÀI SẢN NGẮN HẠN", level: 0, kind: "section", cur: 28993909682, prior: 25845072463 },
    { code: "110", label: "I. Tiền và tương đương tiền", level: 1, kind: "total", cur: 1676431854, prior: 729809027 },
    { code: "120", label: "II. Đầu tư tài chính ngắn hạn", level: 1, kind: "total", cur: 25000000000, prior: 23900000000, flagCur: true },
    { code: "130", label: "III. Các khoản phải thu ngắn hạn", level: 1, kind: "total", cur: 2024477828, prior: 1024263436 },
    { code: "200", label: "B - TÀI SẢN DÀI HẠN", level: 0, kind: "section", cur: 14973675409, prior: 17539138010 },
    { code: "220", label: "II. Tài sản cố định", level: 1, kind: "total", cur: 13899453207, prior: 16234551290 },
    { code: "270", label: "TỔNG CỘNG TÀI SẢN", level: 0, kind: "total", cur: 43967585091, prior: 43384210473 },
    { code: null, label: "NGUỒN VỐN", level: 0, kind: "header", cur: null, prior: null },
    { code: "300", label: "C - NỢ PHẢI TRẢ", level: 0, kind: "section", cur: 3957471219, prior: 2754607519 },
    { code: "310", label: "I. Nợ ngắn hạn", level: 1, kind: "total", cur: 3957471219, prior: 2754607519 },
    { code: "400", label: "D - VỐN CHỦ SỞ HỮU", level: 0, kind: "section", cur: 40010113872, prior: 40629602954 },
    { code: "410", label: "I. Vốn chủ sở hữu", level: 1, kind: "total", cur: 40010113872, prior: 40629602954, flagPrior: true },
    { code: "440", label: "TỔNG CỘNG NGUỒN VỐN", level: 0, kind: "total", cur: 43967585091, prior: 43384210473 },
  ],
}

const KQHDKD: Statement = {
  key: "KQHDKD",
  title: "Kết quả hoạt động kinh doanh",
  rows: [
    { code: "01", label: "1. Doanh thu bán hàng và cung cấp DV", level: 1, kind: "item", cur: 16983509250, prior: 11150559393 },
    { code: "11", label: "3. Giá vốn hàng bán", level: 1, kind: "item", cur: 10276240365, prior: 5186240347 },
    { code: "20", label: "5. Lợi nhuận gộp", level: 1, kind: "total", cur: 6707268885, prior: 5964319046 },
    { code: "50", label: "16. Tổng lợi nhuận kế toán trước thuế", level: 1, kind: "total", cur: 3561238251, prior: 2772040440 },
    { code: "60", label: "18. Lợi nhuận sau thuế TNDN", level: 1, kind: "total", cur: 2848990601, prior: 2217632352 },
  ],
}

const LCTT: Statement = {
  key: "LCTT",
  title: "Lưu chuyển tiền tệ",
  rows: [
    { code: "20", label: "Lưu chuyển tiền thuần từ HĐKD", level: 1, kind: "total", cur: 3120445012, prior: 1985003221 },
    { code: "30", label: "Lưu chuyển tiền thuần từ HĐ đầu tư", level: 1, kind: "total", cur: -1100000000, prior: -850000000, flagCur: true },
    { code: "50", label: "Lưu chuyển tiền thuần trong kỳ", level: 1, kind: "total", cur: 946622827, prior: 1135003221 },
  ],
}

export const MOCK_STATEMENTS: Record<string, Statement[]> = {
  f03: [CDKT, KQHDKD, LCTT],
  f23: [CDKT, KQHDKD], // thiếu LCTT -> chỉ 2 tab
}

export interface BalanceCheck {
  label: string
  ok: boolean
  detail: string
}

export const MOCK_BALANCE: BalanceCheck[] = [
  { label: "Tổng tài sản = Tổng nguồn vốn", ok: true, detail: "43.967.585.091 = 43.967.585.091" },
  { label: "100 + 200 = 270", ok: true, detail: "28.993.909.682 + 14.973.675.409 = 43.967.585.091" },
  { label: "300 + 400 = 440", ok: true, detail: "3.957.471.219 + 40.010.113.872 = 43.967.585.091" },
]
