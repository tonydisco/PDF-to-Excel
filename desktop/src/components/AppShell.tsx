import { useEffect, useState } from "react"
import { SquaresFour, Eye, ChartLineUp, Gear, FilePdf, SidebarSimple } from "@phosphor-icons/react"
import { documentDir } from "@tauri-apps/api/path"
import { cn } from "@/lib/utils"
import { Ambient } from "@/components/Ambient"
import { Settings } from "@/components/Settings"
import { useLlm } from "@/lib/llm"
import { useStore } from "@/lib/store"
import { useTheme } from "@/lib/theme"

export type View = "queue" | "review" | "analysis"

const NAV: { id: View; label: string; icon: typeof Eye }[] = [
  { id: "queue", label: "Dashboard", icon: SquaresFour },
  { id: "review", label: "Review", icon: Eye },
  { id: "analysis", label: "Phân tích", icon: ChartLineUp },
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
  const [collapsed, setCollapsed] = useState(false)
  const openSettings = useLlm((s) => s.openSettings)
  const refreshStatus = useLlm((s) => s.refreshStatus)
  const initTheme = useTheme((s) => s.init)

  useEffect(() => {
    refreshStatus()
    initTheme() // áp màu nhấn đã lưu
    // Mặc định lưu Excel vào thư mục Documents (nếu người dùng chưa đặt)
    if (!useStore.getState().exportDir) {
      documentDir().then((d) => { if (d && !useStore.getState().exportDir) useStore.getState().setExportDir(d) }).catch(() => {})
    }
  }, [refreshStatus, initTheme])

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Ambient />
      <Settings />

      {/* Sidebar (kính mờ, thu gọn được) */}
      <aside
        className={cn(
          "relative z-10 flex shrink-0 flex-col border-r border-sidebar-border bg-sidebar/70 backdrop-blur-xl transition-[width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
          collapsed ? "w-[64px]" : "w-60",
        )}
      >
        <div className={cn("flex items-center gap-2.5 px-4 py-4", collapsed && "justify-center px-0")}>
          <div className="relative grid size-9 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-primary to-[oklch(0.72_0.13_47)] text-primary-foreground shadow-lg shadow-primary/20">
            <FilePdf weight="fill" className="size-5" />
          </div>
          {!collapsed && (
            <div className="min-w-0 leading-tight">
              <div className="truncate text-sm font-semibold tracking-tight">BCTC → Excel</div>
              <div className="text-[11px] text-muted-foreground">Thông tư 200</div>
            </div>
          )}
        </div>

        <nav className={cn("flex flex-col gap-1 py-2", collapsed ? "px-2" : "px-2.5")}>
          {NAV.map((item) => {
            const active = view === item.id
            const Icon = item.icon
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "group relative flex items-center rounded-md py-2 text-sm transition-all duration-200 cursor-pointer",
                  collapsed ? "justify-center px-0" : "gap-3 px-3",
                  active ? "bg-sidebar-accent text-foreground" : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                {active && <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary" />}
                <Icon weight={active ? "fill" : "regular"} className={cn("size-[18px] shrink-0 transition-colors", active && "text-primary")} />
                {!collapsed && <span className="font-medium">{item.label}</span>}
              </button>
            )
          })}
        </nav>

        {/* Footer: thu gọn (trái) · cài đặt (phải), chỉ icon + tooltip */}
        <div className={cn("mt-auto py-3", collapsed ? "px-2" : "px-3")}>
          {collapsed ? (
            <div className="flex flex-col items-center gap-1">
              <button onClick={openSettings} title="Cài đặt" className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground cursor-pointer">
                <Gear className="size-[18px]" />
              </button>
              <button onClick={() => setCollapsed(false)} title="Mở rộng" className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground cursor-pointer">
                <SidebarSimple className="size-[18px] rotate-180" />
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <button onClick={() => setCollapsed(true)} title="Thu gọn" className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground cursor-pointer">
                <SidebarSimple className="size-[18px]" />
              </button>
              <button onClick={openSettings} title="Cài đặt" className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground cursor-pointer">
                <Gear className="size-[18px]" />
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <main className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col">{children}</main>
    </div>
  )
}
