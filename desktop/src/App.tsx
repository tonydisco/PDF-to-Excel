import { useState } from "react"
import { AppShell, type View } from "@/components/AppShell"
import { Dashboard } from "@/components/Dashboard"
import { Review } from "@/components/Review"
import { Analysis } from "@/components/Analysis"

function App() {
  const [view, setView] = useState<View>("queue")
  const [reviewFileId, setReviewFileId] = useState<string>("f03")

  return (
    <AppShell view={view} onNavigate={setView}>
      {view === "queue" && (
        <Dashboard
          onOpenReview={(id) => {
            setReviewFileId(id)
            setView("review")
          }}
        />
      )}
      {view === "review" && <Review fileId={reviewFileId} onBack={() => setView("queue")} />}
      {view === "analysis" && <Analysis />}
    </AppShell>
  )
}

export default App
