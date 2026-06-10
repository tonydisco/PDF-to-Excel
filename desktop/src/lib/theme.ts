import { create } from "zustand"

// Đổi MÀU NHẤN (accent) runtime bằng cách ghi đè CSS custom properties trên :root.
// Giá trị primary/fg lưu dạng tham số oklch ("L C H") để dùng trong oklch(...).
export interface Accent {
  id: string
  name: string
  primary: string // tham số oklch cho màu nhấn
  fg: string // tham số oklch cho chữ trên nền nhấn (primary-foreground)
}

export const ACCENTS: Accent[] = [
  { id: "sage", name: "Sage (mặc định)", primary: "0.74 0.066 162", fg: "0.2 0.02 162" },
  { id: "blue", name: "Xanh dương", primary: "0.62 0.14 250", fg: "0.98 0.01 250" },
  { id: "indigo", name: "Indigo", primary: "0.58 0.17 280", fg: "0.98 0.01 280" },
  { id: "teal", name: "Teal", primary: "0.72 0.12 195", fg: "0.2 0.03 195" },
  { id: "violet", name: "Tím", primary: "0.62 0.18 305", fg: "0.98 0.01 305" },
  { id: "amber", name: "Hổ phách", primary: "0.79 0.14 75", fg: "0.24 0.04 75" },
  { id: "rose", name: "Hồng", primary: "0.66 0.2 18", fg: "0.98 0.01 18" },
]

const LS_KEY = "bctc.accent"
const loadId = (): string => {
  try {
    return localStorage.getItem(LS_KEY) || "sage"
  } catch {
    return "sage"
  }
}

function applyAccent(a: Accent) {
  const root = document.documentElement
  const set = (k: string, v: string) => root.style.setProperty(k, v)
  const c = `oklch(${a.primary})`
  const fg = `oklch(${a.fg})`
  set("--primary", c)
  set("--primary-foreground", fg)
  set("--ring", c)
  set("--ok", c)
  set("--ok-foreground", fg)
  set("--sidebar-primary", c)
  set("--sidebar-primary-foreground", fg)
  set("--sidebar-ring", c)
  set("--chart-1", c)
}

interface ThemeStore {
  accent: string
  setAccent: (id: string) => void
  init: () => void
}

export const useTheme = create<ThemeStore>((set) => ({
  accent: loadId(),
  setAccent: (id) => {
    const a = ACCENTS.find((x) => x.id === id) ?? ACCENTS[0]
    applyAccent(a)
    try {
      localStorage.setItem(LS_KEY, a.id)
    } catch {
      /* ignore */
    }
    set({ accent: a.id })
  },
  init: () => {
    const a = ACCENTS.find((x) => x.id === loadId()) ?? ACCENTS[0]
    applyAccent(a)
  },
}))
