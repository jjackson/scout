import { useChat } from "@ai-sdk/react"
import { TextStreamChatTransport, type UIMessage } from "ai"
import { useEffect, useRef, useState } from "react"
import { getCsrfToken } from "@/api/client"
import { useAppStore } from "@/store/store"
import { ChatMessage } from "@/components/ChatMessage/ChatMessage"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, Square } from "lucide-react"

export function ChatPanel() {
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const threadId = useAppStore((s) => s.threadId)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState("")

  const { messages, sendMessage, status, stop, error } = useChat({
    transport: new TextStreamChatTransport({
      api: "/api/chat/",
      credentials: "include",
      headers: () => ({ "X-CSRFToken": getCsrfToken() }),
      body: () => ({ data: { projectId: activeProjectId, threadId } }),
    }),
  })

  const isStreaming = status === "streaming" || status === "submitted"

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return
    setInput("")
    sendMessage({ text })
  }

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Select a project to start chatting.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground mt-20">
            Ask a question about your data to get started.
          </div>
        )}
        {messages.map((msg: UIMessage) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {error && (
          <div className="text-sm text-destructive bg-destructive/10 rounded-lg px-4 py-2">
            {error.message}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your data..."
            disabled={isStreaming}
            className="flex-1"
          />
          {isStreaming ? (
            <Button type="button" variant="outline" size="icon" onClick={() => stop()}>
              <Square className="w-4 h-4" />
            </Button>
          ) : (
            <Button type="submit" size="icon" disabled={!input.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          )}
        </form>
      </div>
    </div>
  )
}
