// Nền môi trường tạo "ấn tượng AI": aurora sage/coral rất nhẹ + noise mịn.
// Cố định sau toàn bộ nội dung, không bắt chuột.
export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div
        className="aurora-blob absolute -top-[20%] -left-[10%] size-[55vw] rounded-full opacity-[0.18] blur-[100px]"
        style={{ background: "radial-gradient(circle, oklch(0.74 0.066 162 / 90%), transparent 65%)" }}
      />
      <div
        className="aurora-blob-2 absolute top-[10%] right-[-15%] size-[48vw] rounded-full opacity-[0.12] blur-[110px]"
        style={{ background: "radial-gradient(circle, oklch(0.72 0.13 47 / 80%), transparent 65%)" }}
      />
      <div
        className="aurora-blob absolute bottom-[-25%] left-[25%] size-[50vw] rounded-full opacity-[0.10] blur-[120px]"
        style={{ background: "radial-gradient(circle, oklch(0.6 0.08 260 / 80%), transparent 65%)" }}
      />
      <div className="noise-overlay absolute inset-0" />
    </div>
  )
}
