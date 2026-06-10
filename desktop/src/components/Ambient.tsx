// Nền tối SẠCH + "dòng nước" mềm. Màu DẪN XUẤT từ --primary (--flow-light /
// --flow-deep ở index.css) -> đổi theme là đổi luôn nền.
//
// Kỹ thuật (học từ orb góc dưới-phải): mỗi khối là radial-gradient FADE HẲN về
// trong suốt + blur dày -> KHÔNG có rìa hộp/đường cắt cứng. Chuyển động bằng
// transform xoáy (GPU rẻ); blob đặt lệch tâm nên khi xoay sẽ "trôi" như nước.
export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[oklch(0.15_0.005_262)]">
      {/* Vùng nước góc trên-trái: 2 blob mềm, xoay ngược chiều, 2 tông theo accent */}
      <div className="absolute -top-[26%] -left-[20%] size-[64vw]">
        <div
          className="water-swirl absolute inset-0"
          style={{
            filter: "blur(72px)",
            background: "radial-gradient(closest-side at 44% 42%, var(--flow-light), transparent 72%)",
          }}
        />
        <div
          className="water-swirl-rev absolute inset-0"
          style={{
            filter: "blur(88px)",
            background: "radial-gradient(closest-side at 60% 58%, var(--flow-deep), transparent 74%)",
          }}
        />
      </div>

      {/* Orb phụ góc dưới-phải: blob nhẹ theo accent, breathing (bản tham chiếu) */}
      <div
        className="aurora-blob-3 absolute -bottom-[16%] right-[-6%] size-[30vw] rounded-full blur-[90px]"
        style={{
          background:
            "radial-gradient(circle, color-mix(in oklch, var(--primary) 48%, transparent), color-mix(in oklch, var(--primary) 20%, transparent), transparent 68%)",
        }}
      />

      <div className="noise-overlay absolute inset-0" />
    </div>
  )
}
