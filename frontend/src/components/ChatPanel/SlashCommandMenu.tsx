import type { SlashCommand } from "./slashCommands"
import { SLASH_COMMANDS } from "./slashCommands"

interface SlashCommandMenuProps {
  query: string
  onSelect: (cmd: SlashCommand) => void
  visible: boolean
  selectedIndex: number
}

export function SlashCommandMenu({ query, onSelect, visible, selectedIndex }: SlashCommandMenuProps) {
  const filtered = SLASH_COMMANDS.filter((cmd) =>
    cmd.name.startsWith(query),
  )

  if (!visible || filtered.length === 0) return null

  return (
    <div
      data-testid="slash-command-menu"
      className="absolute bottom-full mb-1 left-0 w-full rounded-md border bg-popover p-1 shadow-md"
    >
      {filtered.map((cmd, i) => (
        <button
          key={cmd.name}
          data-testid={`slash-command-${cmd.name}`}
          className={`flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-left cursor-pointer ${
            i === selectedIndex ? "bg-accent" : ""
          }`}
          onMouseDown={(e) => {
            e.preventDefault()
            onSelect(cmd)
          }}
        >
          <span className="font-semibold">/{cmd.name}</span>
          <span className="text-muted-foreground">{cmd.description}</span>
        </button>
      ))}
    </div>
  )
}
