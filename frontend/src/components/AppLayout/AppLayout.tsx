import { useAppStore } from "@/store/store"
import { ChatPanel } from "@/components/ChatPanel/ChatPanel"
import { ProjectSelector } from "@/components/ProjectSelector/ProjectSelector"
import { Button } from "@/components/ui/button"
import { LogOut, MessageSquarePlus } from "lucide-react"

export function AppLayout() {
  const user = useAppStore((s) => s.user)
  const logout = useAppStore((s) => s.authActions.logout)
  const newThread = useAppStore((s) => s.uiActions.newThread)

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold">Scout</h1>
          <ProjectSelector />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={newThread} title="New conversation">
            <MessageSquarePlus className="w-4 h-4" />
          </Button>
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="icon" onClick={logout} title="Sign out">
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </header>

      {/* Main area */}
      <main className="flex-1 overflow-hidden">
        <ChatPanel />
      </main>
    </div>
  )
}
