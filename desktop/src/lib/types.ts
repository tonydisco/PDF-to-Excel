// Kiểu dữ liệu báo cáo dùng chung (khớp với dữ liệu sidecar trả về).

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

export interface BalanceCheck {
  label: string
  ok: boolean
  detail: string
}
