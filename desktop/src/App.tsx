// Khung tạm thời (P0) — chỉ để xác nhận Vite + Tailwind + Tauri chạy.
// Giao diện thật sẽ dựng ở phiên build UI bằng skill design-taste-frontend /
// ui-ux-pro-max + shadcn/ui (xem plans/260609-ui-llm-redesign/01-ui-redesign.md).

function App() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 antialiased">
      <header className="flex items-center gap-3 border-b border-neutral-800 px-6 py-4">
        <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-[#e07a5f] to-[#81b29a] text-sm font-bold text-neutral-950">
          BC
        </div>
        <div>
          <h1 className="text-sm font-semibold tracking-tight">BCTC PDF → Excel</h1>
          <p className="text-xs text-neutral-500">Tauri 2 · React · Tailwind · shadcn (P0 scaffold)</p>
        </div>
      </header>

      <main className="grid place-items-center px-6 py-24">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-6 grid size-16 place-items-center rounded-2xl border border-neutral-800 bg-neutral-900 text-2xl">
            📄→📊
          </div>
          <h2 className="mb-2 text-lg font-semibold">Khung dự án đã sẵn sàng</h2>
          <p className="text-sm leading-relaxed text-neutral-400">
            Vite + Tailwind v4 + Tauri 2 đã chạy. Bước kế: dựng các màn hình thật
            (hàng đợi file, <span className="text-neutral-200">review từng PDF</span>,
            phân tích LLM) bằng shadcn/ui và các skill UI/UX.
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
