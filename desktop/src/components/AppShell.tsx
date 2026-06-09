import { Stack, Eye, ChartLineUp, Gear, FilePdf } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"

export type View = "queue" | "review" | "analysis"

const NAV: { id: View; label: string; icon: typeof Stack; hint: string }[] = [
  { id: "queue", label: "Hàng đợi", icon: Stack, hint: "Thêm & chuyển đổi PDF" },
  { id: "review", label: "Review", icon: Eye, hint: "Soát từng báo cáo" },
  { id: "analysis", label: "Phân tích", icon: ChartLineUp, hint: "Chỉ số & rủi ro" },
]

export function AppShell({
  view,
  onNavigate,
  children,
}: {
  view: View
  onNavigate: (v: View) => void
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
        <div className="flex items-center gap-2.5 px-4 py-4">
          <div className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground">
            <FilePdf weight="fill" className="size-5" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">BCTC → Excel</div>
            <div className="text-[11px] text-muted-foreground">Thông tư 200</div>
          </div>
        </div>

        <nav className="flex flex-col gap-1 px-2.5 py-2">
          {NAV.map((item) => {
            const active = view === item.id
            const Icon = item.icon
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={cn(
                  "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-200 cursor-pointer",
                  active
                    ? "bg-sidebar-accent text-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                <Icon weight={active ? "fill" : "regular"} className={cn("size-[18px]", active && "text-primary")} />
                <span className="font-medium">{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="mt-auto px-4 py-3 text-[11px] text-muted-foreground">
          <button className="mb-2 flex w-full items-center gap-2 rounded-md px-1 py-1.5 transition-colors hover:text-foreground cursor-pointer">
            <Gear className="size-4" /> Cài đặt
          </button>
          <div className="flex items-center justify-between">
            <span>v2.0 · Tauri</span>
            <span className="inline-flex items-center gap-1">
              <span className="size-1.5 rounded-full bg-primary" /> Local OCR
            </span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex min-w-0 flex-1 flex-col">{children}</main>
    </div>
  )
}
