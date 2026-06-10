import { useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { AppShell, type View } from "@/components/AppShell"
import { Dashboard } from "@/components/Dashboard"
import { Review } from "@/components/Review"
import { Analysis } from "@/components/Analysis"
import { useStore } from "@/lib/store"

function App() {
  const [view, setView] = useState<View>("queue")
  const [reviewFileId, setReviewFileId] = useState<string>(() => useStore.getState().files[0]?.id ?? "")

  return (
    <AppShell view={view} onNavigate={setView}>
      <AnimatePresence mode="wait">
        <motion.div
          key={view}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
          className="flex min-h-0 flex-1 flex-col"
        >
          {view === "queue" && (
            <Dashboard
              onOpenReview={(id) => {
                setReviewFileId(id)
                setView("review")
              }}
              onAnalyze={() => setView("analysis")}
            />
          )}
          {view === "review" && <Review fileId={reviewFileId} onBack={() => setView("queue")} />}
          {view === "analysis" && <Analysis />}
        </motion.div>
      </AnimatePresence>
    </AppShell>
  )
}

export default App
