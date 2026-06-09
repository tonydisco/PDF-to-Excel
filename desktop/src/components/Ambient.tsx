// Nền môi trường "ma mị": aurora sâu (sage·teal·coral·indigo lạnh) trôi & thở,
// + vignette tối góc gom ánh sáng vào giữa, + noise mịn. Không bắt chuột.
export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[oklch(0.14_0.006_262)]">
      {/* sage emerald */}
      <div
        className="aurora-blob absolute -top-[22%] -left-[12%] size-[62vw] rounded-full blur-[120px]"
        style={{ background: "radial-gradient(circle, oklch(0.70 0.12 165 / 95%), transparent 62%)" }}
      />
      {/* teal lạnh */}
      <div
        className="aurora-blob-2 absolute top-[6%] right-[-18%] size-[58vw] rounded-full blur-[130px]"
        style={{ background: "radial-gradient(circle, oklch(0.64 0.12 200 / 80%), transparent 62%)" }}
      />
      {/* indigo lạnh (moody) */}
      <div
        className="aurora-blob-3 absolute bottom-[-30%] left-[18%] size-[66vw] rounded-full blur-[140px]"
        style={{ background: "radial-gradient(circle, oklch(0.46 0.11 262 / 85%), transparent 60%)" }}
      />
      {/* coral ember */}
      <div
        className="aurora-blob-2 absolute bottom-[-10%] right-[8%] size-[42vw] rounded-full blur-[120px]"
        style={{ background: "radial-gradient(circle, oklch(0.66 0.16 38 / 70%), transparent 64%)" }}
      />

      {/* vignette gom sáng vào giữa, tối dần ra mép */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(120% 115% at 50% 32%, transparent 46%, oklch(0.10 0.012 262 / 82%) 100%)" }}
      />
      <div className="noise-overlay absolute inset-0 opacity-[0.04]" />
    </div>
  )
}
