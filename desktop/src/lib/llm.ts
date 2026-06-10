import { create } from "zustand"
import { llmStatus, type LlmStatus, type Provider } from "./api"

// Lưu LỰA CHỌN (provider + model) trong localStorage. KHÔNG bao giờ lưu API key
// ở đây — key nằm trong OS keychain do sidecar quản (keyring).
const LS_KEY = "bctc.llm.pref"

function loadPref(): { provider: Provider; model: string } {
  try {
    const j = JSON.parse(localStorage.getItem(LS_KEY) || "")
    if (j && (j.provider === "anthropic" || j.provider === "google")) {
      return { provider: j.provider, model: typeof j.model === "string" ? j.model : "" }
    }
  } catch {
    /* ignore */
  }
  return { provider: "anthropic", model: "" } // model "" => dùng mặc định của provider
}

function persist(provider: Provider, model: string) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({ provider, model }))
  } catch {
    /* ignore */
  }
}

interface LlmStore {
  provider: Provider
  model: string // "" => mặc định của provider
  status: LlmStatus | null
  settingsOpen: boolean
  setProvider: (p: Provider) => void
  setModel: (m: string) => void
  refreshStatus: () => Promise<void>
  openSettings: () => void
  closeSettings: () => void
}

export const useLlm = create<LlmStore>((set, get) => ({
  ...loadPref(),
  status: null,
  settingsOpen: false,
  setProvider: (provider) => {
    persist(provider, get().model)
    set({ provider })
  },
  setModel: (model) => {
    persist(get().provider, model)
    set({ model })
  },
  refreshStatus: async () => {
    try {
      set({ status: await llmStatus() })
    } catch {
      set({ status: null })
    }
  },
  openSettings: () => set({ settingsOpen: true }),
  closeSettings: () => set({ settingsOpen: false }),
}))
