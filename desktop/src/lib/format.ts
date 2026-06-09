// Định dạng số kiểu Việt Nam: 1.234.567 ; âm trong ngoặc (1.234)
export function fmtVN(v: number | null): string {
  if (v === null || v === undefined) return ""
  const neg = v < 0
  const s = Math.abs(v).toLocaleString("vi-VN")
  return neg ? `(${s})` : s
}

export function fmtSize(mb: number): string {
  return `${mb.toFixed(1)} MB`
}
