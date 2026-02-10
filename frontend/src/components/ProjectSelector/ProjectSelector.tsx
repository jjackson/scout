import { useEffect } from "react"
import { useAppStore } from "@/store/store"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function ProjectSelector() {
  const projects = useAppStore((s) => s.projects)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const projectsStatus = useAppStore((s) => s.projectsStatus)
  const fetchProjects = useAppStore((s) => s.projectActions.fetchProjects)
  const setActiveProject = useAppStore((s) => s.projectActions.setActiveProject)
  const newThread = useAppStore((s) => s.uiActions.newThread)

  useEffect(() => {
    if (projectsStatus === "idle") {
      fetchProjects()
    }
  }, [projectsStatus, fetchProjects])

  function handleChange(value: string) {
    setActiveProject(value)
    newThread() // Reset conversation on project switch
  }

  if (projectsStatus === "loading") {
    return <span className="text-sm text-muted-foreground">Loading projects...</span>
  }

  if (projects.length === 0) {
    return <span className="text-sm text-muted-foreground">No projects</span>
  }

  return (
    <Select value={activeProjectId ?? ""} onValueChange={handleChange}>
      <SelectTrigger className="w-56">
        <SelectValue placeholder="Select project" />
      </SelectTrigger>
      <SelectContent>
        {projects.map((p) => (
          <SelectItem key={p.id} value={p.id}>
            {p.name} ({p.role})
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
