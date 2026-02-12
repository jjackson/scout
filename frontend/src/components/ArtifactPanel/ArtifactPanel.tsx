import { useAppStore } from "@/store/store"
import { X } from "lucide-react"

export function ArtifactPanel() {
  const artifactId = useAppStore((s) => s.activeArtifactId)
  const closeArtifact = useAppStore((s) => s.uiActions.closeArtifact)
  const isOpen = artifactId !== null

  return (
    <aside
      className={`overflow-hidden border-l border-border transition-[flex] duration-200 ${
        isOpen ? "flex-1 min-w-0" : "w-0 border-l-0"
      }`}
    >
      {artifactId && (
        <div className="flex h-full flex-col">
          <div className="flex h-14 items-center justify-between border-b border-border px-4">
            <span className="text-sm font-medium">Artifact</span>
            <button
              onClick={closeArtifact}
              className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              title="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <iframe
            key={artifactId}
            src={`/api/artifacts/${artifactId}/sandbox/`}
            className="flex-1 w-full"
            sandbox="allow-scripts"
            title="Artifact"
          />
        </div>
      )}
    </aside>
  )
}
